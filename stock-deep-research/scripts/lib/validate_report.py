#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告结构验收器。

把 report_spec.md 中最容易漏掉的硬要求转成可执行检查：
    - 固定章节是否存在、顺序是否正确；
    - 政策/要闻是否逐条包含“内容解读”和“影响分析”；
    - 非共识、风险提示、数据来源和免责声明是否存在；
    - 是否残留 TODO/TBD 等占位符。

用法:
    python validate_report.py <report.md> --profile daily-basic
    python validate_report.py <report.md> --profile daily-deep
    python validate_report.py <report.md> --profile stock

退出码:
    0  报告结构通过
    1  存在 CRITICAL
    2  参数或文件错误
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class Check:
    check_id: str
    name: str
    level: str
    expected: str = ""
    actual: str = ""
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


PROFILES = {
    "daily-basic": {
        "sections": [
            ("市场总览", ("市场总览",)),
            ("行业与风格", ("行业与风格",)),
            ("宏观与流动性", ("宏观与流动性",)),
            ("海外市场与全球资产", ("海外市场与全球资产",)),
            ("政策与要闻", ("政策与要闻",)),
            ("重要公告与事件", ("重要公告与事件",)),
            ("机构观点", ("机构观点",)),
            ("关注方向与风险提示", ("关注方向",)),
            ("非共识 α 观点", ("非共识",)),
            ("情绪分析", ("情绪分析",)),
            ("两融水平及分析", ("两融水平",)),
            ("资金分析", ("资金分析",)),
            ("风险提示汇总", ("风险提示（汇总）", "风险提示(汇总)", "风险提示汇总")),
        ],
        "min_counts": {
            "内容解读": 2,
            "影响分析": 2,
            "风险提示": 3,
        },
        "terms": ("数据来源", "不构成投资建议"),
        "headings_only": True,
        "authoritative_min": 1,
    },
    "daily-deep": {
        "sections": [
            ("总体分析", ("总体分析",)),
            ("海外市场与全球资产", ("海外市场与全球资产",)),
            ("政策与要闻", ("政策与要闻",)),
            ("重要公告与事件", ("重要公告与事件",)),
            ("机构观点", ("机构观点",)),
            ("情绪与资金分析", ("情绪与资金",)),
            ("非共识 α 观点", ("非共识",)),
            ("板块推荐", ("板块推荐",)),
            ("市场驱动板块", ("市场驱动板块",)),
            ("政策驱动板块", ("政策驱动板块",)),
            ("个股深度分析", ("个股深度分析",)),
            ("ETF 关注组合", ("ETF",)),
            ("组合建议", ("组合建议",)),
            ("风险提示汇总", ("风险提示（汇总）", "风险提示(汇总)", "风险提示汇总")),
        ],
        "min_counts": {
            "内容解读": 2,
            "影响分析": 2,
            "风险提示": 5,
            "次日观察": 1,
            "复盘": 1,
            "触发条件": 1,
        },
        "terms": ("数据来源", "不构成投资建议"),
        "cross_ref": True,
        "headings_only": True,
        "authoritative_min": 2,
    },
    "stock": {
        "sections": [
            ("核心判断", ("核心判断",)),
            ("五维度", ("五维度", "基础版")),
            ("产业链", ("产业链",)),
            ("政策链", ("政策链", "政策")),
            ("非共识 α 观点", ("非共识",)),
            ("情景推演", ("情景",)),
            ("风险提示", ("风险提示",)),
        ],
        "min_counts": {
            "单季度": 1,
            "累计": 1,
            "收现比": 1,
            "应收账款": 1,
            "合同负债": 1,
            "资产负债率": 1,
            "风险提示": 3,
            "事实": 1,
            "推理": 1,
            "假设": 1,
            "市场一致预期": 1,
            "非共识点": 1,
            "证伪条件": 1,
            "止损": 1,
            "止盈": 1,
            "数据溯源": 1,
            "观察清单": 1,
            "触发条件": 1,
        },
        "terms": (
            "客观评级",
            "估值",
            "财务",
            "资金",
            "技术",
            "消息",
            "数据来源",
            "不构成投资建议",
        ),
        "headings_only": True,
        "authoritative_min": 1,
    },
}


PLACEHOLDER_RE = re.compile(
    r"(?i)\b(TODO|TBD|FIXME)\b|待补充|待填写|占位符"
)
REPORT_DATE_RE = re.compile(r"20\d{2}[-年/]\d{1,2}")
SOURCE_NAMES = (
    "同花顺",
    "问财",
    "东方财富妙想",
    "妙想",
    "公告",
    "新闻",
    "研报",
    "交易所",
)
OFFICIAL_DOMAINS = (
    "pbc.gov.cn",
    "stats.gov.cn",
    "csrc.gov.cn",
    "mof.gov.cn",
    "ndrc.gov.cn",
    "miit.gov.cn",
    "safe.gov.cn",
    "sse.com.cn",
    "szse.cn",
    "bse.cn",
    "cninfo.com.cn",
    "chinamoney.com.cn",
    "federalreserve.gov",
    "home.treasury.gov",
    "bls.gov",
    "bea.gov",
    "sec.gov",
    "ecb.europa.eu",
    "bankofengland.co.uk",
    "boj.or.jp",
    "imf.org",
    "worldbank.org",
    "oecd.org",
    "bis.org",
    "eia.gov",
    "opec.org",
    "noaa.gov",
    "lme.com",
)


class Report:
    def __init__(self, profile: str, path: str):
        self.profile = profile
        self.path = path
        self.checks: list[Check] = []

    def add(self, check_id, name, level, expected="", actual="", detail=""):
        self.checks.append(
            Check(
                check_id=check_id,
                name=name,
                level=level,
                expected=expected,
                actual=actual,
                detail=detail,
            )
        )

    def summary(self) -> dict:
        result = {"pass": 0, "fail": 0, "warn": 0}
        for item in self.checks:
            if item.level == "PASS":
                result["pass"] += 1
            elif item.level == "CRITICAL":
                result["fail"] += 1
            elif item.level == "WARN":
                result["warn"] += 1
        return result


def _first_position(
    text: str,
    alternatives: tuple[str, ...],
    *,
    prefer_last: bool = False,
    headings_only: bool = False,
) -> int:
    # 优先用 Markdown 标题定位，避免正文提到同一关键词时把章节顺序弄乱。
    heading_positions: list[int] = []
    for item in alternatives:
        for match in re.finditer(
            rf"(?m)^#{{1,6}}\s*[^\n]*{re.escape(item)}",
            text,
        ):
            heading_positions.append(match.start())
    if heading_positions:
        return max(heading_positions) if prefer_last else min(heading_positions)
    if headings_only:
        return -1

    body_positions = [text.find(item) for item in alternatives if text.find(item) >= 0]
    return min(body_positions) if body_positions else -1


def _check_sections(
    report: Report,
    text: str,
    sections,
    *,
    headings_only: bool = False,
) -> None:
    positions: list[int] = []
    for label, alternatives in sections:
        # “风险提示（汇总）”可能同时出现在章节内的小标题和文末汇总章节，
        # 对汇总章节取最后一次出现，避免把 8.3 误当成最终风险汇总。
        position = _first_position(
            text,
            alternatives,
            prefer_last=(label == "风险提示汇总"),
            headings_only=headings_only,
        )
        if position < 0:
            report.add(
                f"section.{label}",
                f"章节存在: {label}",
                "CRITICAL",
                expected="存在对应章节",
                actual="未找到",
            )
            continue
        positions.append(position)
        report.add(
            f"section.{label}",
            f"章节存在: {label}",
            "PASS",
            actual=f"位置={position}",
        )

    if len(positions) == len(sections) and positions != sorted(positions):
        report.add(
            "section.order",
            "章节顺序",
            "WARN",
            expected="章节顺序与报告规范一致",
            actual="存在逆序或重复位置",
            detail="请检查报告章节是否按规范排列。",
        )
    else:
        report.add(
            "section.order",
            "章节顺序",
            "PASS",
            actual="顺序正常" if len(positions) == len(sections) else "存在缺失章节",
        )


def _check_counts(report: Report, text: str, min_counts: dict) -> None:
    for term, minimum in min_counts.items():
        count = text.count(term)
        level = "PASS" if count >= minimum else "CRITICAL"
        report.add(
            f"count.{term}",
            f"最低内容覆盖: {term}",
            level,
            expected=f">= {minimum} 次",
            actual=f"{count} 次",
            detail=(
                ""
                if level == "PASS"
                else "该关键词覆盖不足，报告可能遗漏规范要求的内容。"
            ),
        )


def _check_terms(report: Report, text: str, terms) -> None:
    for term in terms:
        found = term in text
        report.add(
            f"term.{term}",
            f"必要内容: {term}",
            "PASS" if found else "CRITICAL",
            expected="必须出现",
            actual="已出现" if found else "未找到",
        )


def _check_placeholders(report: Report, text: str) -> None:
    matches = PLACEHOLDER_RE.findall(text)
    if matches:
        report.add(
            "report.placeholders",
            "无占位符残留",
            "WARN",
            expected="不出现 TODO/TBD/待补充等占位符",
            actual=f"发现 {len(matches)} 处: {', '.join(sorted(set(matches)))}",
        )
    else:
        report.add(
            "report.placeholders",
            "无占位符残留",
            "PASS",
            actual="未发现",
        )


def _check_source_coverage(report: Report, text: str) -> None:
    found = [name for name in SOURCE_NAMES if name in text]
    source_level = "PASS" if len(found) >= 2 else "WARN"
    report.add(
        "report.sources",
        "数据来源覆盖",
        source_level,
        expected="至少出现 2 类可识别来源",
        actual=", ".join(found) if found else "未识别到来源",
        detail="" if source_level == "PASS" else "报告应注明问财、妙想、公告、新闻或研报来源。",
    )

    date_count = len(REPORT_DATE_RE.findall(text))
    date_level = "PASS" if date_count >= 5 else "WARN"
    report.add(
        "report.dates",
        "数据日期密度",
        date_level,
        expected="至少 5 处日期标记",
        actual=f"{date_count} 处",
        detail="" if date_level == "PASS" else "报告中的关键数据应标注日期，便于复核时效性。",
    )


def _check_authoritative_sources(
    report: Report,
    text: str,
    minimum: int,
) -> None:
    lowered = text.lower()
    found = sorted({domain for domain in OFFICIAL_DOMAINS if domain in lowered})
    level = "PASS" if len(found) >= minimum else "CRITICAL"
    report.add(
        "report.authoritative_sources",
        "权威原始来源覆盖",
        level,
        expected=f"至少 {minimum} 个官方来源域名",
        actual=", ".join(found) if found else "未识别到官方来源域名",
        detail=(
            ""
            if level == "PASS"
            else "政策、宏观、监管、公告或海外数据必须优先引用原始发布方；"
            "不得只引用新闻标题或搜索摘要。"
        ),
    )


def _check_cross_reference(report: Report, text: str) -> None:
    """检查板块推荐里的股票代码是否出现在个股深度分析中。"""
    board_pos = text.find("板块推荐")
    stock_pos = text.find("个股深度分析")
    if board_pos < 0 or stock_pos < 0:
        return
    board_text = text[board_pos:stock_pos]
    stock_text = text[stock_pos:]
    pattern = re.compile(r"[（(](\d{6})[）)]")
    board_codes = set(pattern.findall(board_text))
    stock_codes = set(pattern.findall(stock_text))
    missing = sorted(board_codes - stock_codes)
    if missing:
        report.add(
            "cross_reference.stock_codes",
            "板块龙头股与个股深度分析交叉引用",
            "WARN",
            expected="板块推荐中的股票代码都进入个股深度分析",
            actual="未进入: " + ", ".join(missing),
            detail="请检查板块推荐中的龙头股是否全部完成个股分析。",
        )
    else:
        report.add(
            "cross_reference.stock_codes",
            "板块龙头股与个股深度分析交叉引用",
            "PASS",
            actual=f"板块代码 {len(board_codes)} 个，深析 {len(stock_codes)} 个",
        )


def validate_report(path: str, profile: str) -> Report:
    report = Report(profile, path)
    if profile not in PROFILES:
        report.add(
            "profile",
            "报告类型",
            "CRITICAL",
            actual=profile,
            expected="daily-basic/daily-deep/stock",
        )
        return report
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            text = handle.read()
    except OSError as exc:
        report.add(
            "file",
            "报告文件可读",
            "CRITICAL",
            actual=repr(exc),
            expected="文件存在且可读",
        )
        return report

    config = PROFILES[profile]
    _check_sections(
        report,
        text,
        config["sections"],
        headings_only=config.get("headings_only", False),
    )
    _check_counts(report, text, config["min_counts"])
    _check_terms(report, text, config["terms"])
    _check_placeholders(report, text)
    _check_source_coverage(report, text)
    _check_authoritative_sources(
        report,
        text,
        int(config.get("authoritative_min", 1)),
    )
    if config.get("cross_ref"):
        _check_cross_reference(report, text)
    return report


def make_payload(report: Report) -> dict:
    summary = report.summary()
    return {
        "schema_version": 1,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "profile": report.profile,
        "path": os.path.abspath(report.path),
        "summary": summary,
        "report_valid": summary["fail"] == 0,
        "blocking_reasons": [
            item.name for item in report.checks if item.level == "CRITICAL"
        ],
        "warnings": [
            item.name for item in report.checks if item.level == "WARN"
        ],
        "checks": [item.to_dict() for item in report.checks],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Markdown 研报结构验收")
    parser.add_argument("report", help="报告 Markdown 文件")
    parser.add_argument(
        "--profile",
        required=True,
        choices=sorted(PROFILES.keys()),
        help="报告类型",
    )
    parser.add_argument("--out", default=None, help="验收 JSON 输出路径")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.report):
        print(f"错误: 文件不存在: {args.report}", file=sys.stderr)
        return 2

    report = validate_report(args.report, args.profile)
    payload = make_payload(report)
    out_path = args.out or args.report + ".validation.json"
    try:
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"错误: 无法写入 {out_path}: {exc}", file=sys.stderr)
        return 2

    summary = payload["summary"]
    print(
        f"Report validation: {summary['pass']} pass / {summary['fail']} fail / "
        f"{summary['warn']} warn"
    )
    for item in report.checks:
        if item.level == "CRITICAL":
            print(f"  [CRITICAL] {item.name}: {item.actual}")
        elif item.level == "WARN":
            print(f"  [WARN] {item.name}: {item.actual}")
    print(f"  结果已写入: {out_path}")
    return 0 if payload["report_valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
