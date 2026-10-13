#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据一致性校验器（研报生成前的防错门禁）。

对 fetch_daily_data.ps1 抓取到 <data_dir> 的 JSON 做勾稽校验，输出 data_quality.json。
目的是拦截「数据存在但不可信」的情况——现有门禁只检查文件是否有条目，
无法发现同一个事实在两次查询中互相矛盾。

用法:
    python validate_facts.py <data_dir> [--out <path>] [--strict]
    python validate_facts.py "D:\\codex\\研报\\data\\2026-10-07"

退出码:
    0  无 CRITICAL
    1  存在 CRITICAL（配合 --strict 用于中止流程）
    2  参数或路径错误

实现要点:
    - 问财返回的字段形如 "融资余额[20260930]"，本脚本按前缀匹配并抽出日期。
    - 文件由 PowerShell `Out-File -Encoding utf8` 写入，带 UTF-8 BOM，
      必须用 utf-8-sig 解码，否则 json.load 会抛 "Unexpected UTF-8 BOM"。
    - 校验失败不抛异常，而是记录为结构化结果，保证一次运行能看到全部问题。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, date
from typing import Any, Optional

# ---------------------------------------------------------------- 常量

# 关键文件缺失时视为 CRITICAL（与 fetch_daily_data.ps1 的 criticalFiles 对齐）
CRITICAL_FILES = [
    "margin_level.json",
    "margin_flow.json",
    "market_turnover.json",
    "market_breadth_up.json",
    "market_breadth_down.json",
    "indices_cn.json",
]

# 宏观数据新鲜度阈值（天）
MACRO_STALE_DAYS = 60

# 涨跌家数之和的合理上界（沪深京 A 股总数，2026 年约 5,400–5,500 只）
BREADTH_SUM_MAX = 6500

# 两融恒等式容差
MARGIN_IDENTITY_TOL = 0.01

# 融资净买入隐含变动率 vs 接口报的环比增长率，允许的倍数偏差
MARGIN_CHANGE_TOL_FACTOR = 2.0

# 两融余额占流通市值的合理区间（A股历史大致 1.5%~4%）
MARGIN_RATIO_MIN = 1.5
MARGIN_RATIO_MAX = 4.0

# 市场类文件允许的最大日历跨度（覆盖周末/短假期，但不能容忍跨月或跨年错配）
MARKET_DATE_SPAN_MAX_DAYS = 7

DATE_SUFFIX_RE = re.compile(r"\[(\d{8})\]")


# ---------------------------------------------------------------- 数据结构

@dataclass
class CheckResult:
    check_id: str
    name: str
    level: str  # PASS / CRITICAL / WARN / STALE / MISSING / SKIP
    expected: str = ""
    actual: str = ""
    detail: str = ""
    sources: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class Report:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.results: list[CheckResult] = []
        self._cache: dict[str, Any] = {}

    # -------------------------------------------------- 文件读取

    def path(self, filename: str) -> str:
        return os.path.join(self.data_dir, filename)

    def load(self, filename: str) -> Optional[dict]:
        """读取并缓存 JSON。带 BOM 的文件用 utf-8-sig 解码。"""
        if filename in self._cache:
            return self._cache[filename]
        p = self.path(filename)
        if not os.path.exists(p):
            self._cache[filename] = None
            return None
        try:
            with open(p, "r", encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except Exception:
            # 退回 utf-8，兼容不带 BOM 的情况
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:
                data = None
        self._cache[filename] = data
        return data

    def rows(self, filename: str) -> list:
        data = self.load(filename)
        if not isinstance(data, dict):
            return []
        for key in ("datas", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return []

    # -------------------------------------------------- 字段抽取

    @staticmethod
    def pick(row: dict, prefix: str) -> tuple[Optional[float], Optional[str]]:
        """按前缀匹配字段，返回 (数值, 日期)。

        问财字段形如 "融资余额[20260930]"。若存在多个同前缀字段，取日期最新者。
        也支持不带日期后缀的精确字段名。
        """
        if not isinstance(row, dict):
            return None, None

        best_value: Optional[float] = None
        best_date: Optional[str] = None

        for key, value in row.items():
            if key == prefix:
                num = Report._to_number(value)
                if num is not None:
                    best_value = num
                    best_date = None
                continue
            if not key.startswith(prefix):
                continue
            match = DATE_SUFFIX_RE.search(key)
            if not match:
                continue
            suffix = match.group(1)
            if best_date is None or suffix > best_date:
                num = Report._to_number(value)
                if num is not None:
                    best_value = num
                    best_date = suffix

        return best_value, best_date

    @staticmethod
    def _to_number(value: Any) -> Optional[float]:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def pct(numerator: float, denominator: float) -> Optional[float]:
        if not denominator:
            return None
        return numerator / denominator * 100.0

    # -------------------------------------------------- 结果记录

    def add(self, check_id, name, level, expected="", actual="", detail="", sources=None):
        self.results.append(
            CheckResult(
                check_id=check_id,
                name=name,
                level=level,
                expected=expected,
                actual=actual,
                detail=detail,
                sources=sources or [],
            )
        )

    def summary(self) -> dict:
        out = {"pass": 0, "fail": 0, "stale": 0, "missing": 0, "warn": 0}
        for r in self.results:
            if r.level == "PASS":
                out["pass"] += 1
            elif r.level == "CRITICAL":
                out["fail"] += 1
            elif r.level == "STALE":
                out["stale"] += 1
            elif r.level == "MISSING":
                out["missing"] += 1
            elif r.level == "WARN":
                out["warn"] += 1
        return out


# ---------------------------------------------------------------- 校验项

def check_files_present(rep: Report) -> None:
    """关键文件是否存在且可解析。"""
    for filename in CRITICAL_FILES:
        if not os.path.exists(rep.path(filename)):
            rep.add(
                f"file.{filename}",
                f"关键文件存在: {filename}",
                "CRITICAL",
                expected="文件存在且可解析",
                actual="文件不存在",
                detail="fetch 脚本未产出该文件，后续所有依赖它的结论都不可信",
                sources=[filename],
            )
            continue
        if rep.load(filename) is None:
            rep.add(
                f"file.{filename}",
                f"关键文件可解析: {filename}",
                "CRITICAL",
                expected="合法 JSON",
                actual="解析失败",
                detail="文件存在但不是合法 JSON（可能被错误信息污染）",
                sources=[filename],
            )
            continue
        rep.add(
            f"file.{filename}",
            f"关键文件存在: {filename}",
            "PASS",
            sources=[filename],
        )


def check_margin_identity(rep: Report) -> None:
    """两融余额 = 融资余额 + 融券余额（恒等式）。"""
    rows = rep.rows("margin_level.json")
    if not rows:
        rep.add("margin.identity", "两融恒等式", "MISSING",
                detail="margin_level.json 无数据")
        return

    row = rows[0]
    financing, d1 = rep.pick(row, "融资余额")
    securities, d2 = rep.pick(row, "融券余额")
    total, d3 = rep.pick(row, "两融余额")

    if financing is None or securities is None or total is None:
        rep.add("margin.identity", "两融恒等式", "MISSING",
                detail=f"缺字段: 融资余额={financing}, 融券余额={securities}, 两融余额={total}",
                sources=["margin_level.json"])
        return

    computed = financing + securities
    diff = abs(computed - total)
    rel = diff / total if total else 1.0
    ok = rel <= MARGIN_IDENTITY_TOL

    rep.add(
        "margin.identity",
        "两融恒等式: 两融余额 = 融资余额 + 融券余额",
        "PASS" if ok else "CRITICAL",
        expected=f"相对偏差 <= {MARGIN_IDENTITY_TOL:.1%}",
        actual=f"融资+融券={computed:,.0f}, 两融余额={total:,.0f}, 相对偏差={rel:.4%}",
        detail="" if ok else "恒等式不成立，说明数据取自不同口径或不同日期",
        sources=["margin_level.json"],
    )


def check_margin_change_consistency(rep: Report) -> None:
    """融资净买入 ÷ 融资余额 应约等于接口报的融资余额环比增长率。

    实测反例: 2026-09-30 净买入 -164.88 亿 / 融资余额 12040.89 亿 = -1.37%，
    但 margin_change.json 报 -50.68%，相差 37 倍。这条校验就是为捕获它而设。
    """
    level_rows = rep.rows("margin_level.json")
    change_rows = rep.rows("margin_change.json")

    if not level_rows or not change_rows:
        rep.add("margin.change_consistency", "融资余额环比一致性", "MISSING",
                detail="margin_level.json 或 margin_change.json 无数据")
        return

    financing, _ = rep.pick(level_rows[0], "融资余额")
    net_buy, _ = rep.pick(level_rows[0], "融资净买入额")
    if net_buy is None:
        net_buy, _ = rep.pick(rep.rows("margin_flow.json")[0] if rep.rows("margin_flow.json") else {}, "融资净买入额")

    reported, _ = rep.pick(change_rows[0], "融资余额环比增长率")

    if financing is None or net_buy is None or reported is None:
        rep.add("margin.change_consistency", "融资余额环比一致性", "MISSING",
                detail=f"缺字段: 融资余额={financing}, 融资净买入={net_buy}, 环比增长率={reported}",
                sources=["margin_level.json", "margin_change.json", "margin_flow.json"])
        return

    implied = rep.pct(net_buy, financing)  # 单位 %
    if implied is None:
        rep.add("margin.change_consistency", "融资余额环比一致性", "MISSING",
                detail="融资余额为 0，无法计算")
        return

    scale = max(abs(implied), 0.01)
    factor = abs(reported) / scale
    ok = factor <= MARGIN_CHANGE_TOL_FACTOR

    rep.add(
        "margin.change_consistency",
        "融资余额环比一致性: 净买入隐含变动 ≈ 接口报的环比增长率",
        "PASS" if ok else "CRITICAL",
        expected=f"两口径倍数偏差 <= {MARGIN_CHANGE_TOL_FACTOR}x",
        actual=(f"净买入隐含={implied:.4f}%, 接口报={reported:.4f}%, "
                f"倍数偏差={factor:.1f}x"),
        detail="" if ok else (
            "同一事实的两个口径互相矛盾。**不要假定哪一个是对的**——两个派生值可能"
            "同样来自被污染的原始字段。正确做法: (1) 用 margin.ratio 检查判断余额字段"
            "本身是否可信; (2) 与交易所/权威渠道的独立数据交叉核对; "
            "(3) 核对完成前，报告中不要引用任何基于该余额的比例指标。"
            " 历史案例: 2026-09-30 的融资余额字段约为真值一半，"
            "此时接口环比(-50.68%)反而是对的（反推上一日约2.44万亿），余额字段才是坏的。"
        ),
        sources=["margin_level.json", "margin_change.json"],
    )


def check_margin_ratio(rep: Report) -> None:
    """两融余额 ÷ 流通市值 的比例合理性。

    这是识别「余额字段本身被污染」的关键校验。A股两融余额占流通市值长期落在
    1.5%~4% 区间。若显著偏低，说明余额可能只覆盖部分范围（单市场、单日不完整），
    此时基于该余额派生的一切比例指标都不可信。

    实测案例: 2026-09-30 报 1.265%（异常偏低，余额约为真值一半）；
              2026-10-12 报 2.592%（正常）。
    """
    rows = rep.rows("margin_level.json")
    if not rows:
        rep.add("margin.ratio", "两融余额/流通市值合理性", "MISSING",
                detail="margin_level.json 无数据")
        return

    row = rows[0]
    total, total_date = rep.pick(row, "两融余额")
    float_cap, cap_date = rep.pick(row, "流通市值")

    if total is None or float_cap is None or not float_cap:
        rep.add("margin.ratio", "两融余额/流通市值合理性", "MISSING",
                detail=f"缺字段: 两融余额={total}, 流通市值={float_cap}",
                sources=["margin_level.json"])
        return

    ratio = total / float_cap * 100.0
    ok = MARGIN_RATIO_MIN <= ratio <= MARGIN_RATIO_MAX

    date_note = ""
    if total_date and cap_date and total_date != cap_date:
        date_note = f"; 日期不一致: 两融={total_date}, 流通市值={cap_date}"

    rep.add(
        "margin.ratio",
        "两融余额/流通市值合理性",
        "PASS" if ok else "CRITICAL",
        expected=f"{MARGIN_RATIO_MIN}% ~ {MARGIN_RATIO_MAX}%",
        actual=(f"两融={total / 1e12:.3f}万亿, 流通市值={float_cap / 1e12:.2f}万亿, "
                f"占比={ratio:.3f}%{date_note}"),
        detail="" if ok else (
            "比例超出 A 股历史区间，高度怀疑余额字段本身被污染"
            "（常见原因: 只取到单市场、单日数据不完整、接口返回错误量级）。"
            "此时基于该余额计算的所有比例指标（融资余额占流通市值、净买入隐含变动等）"
            "都不可信，必须换数据源交叉核对后再使用。"
        ),
        sources=["margin_level.json"],
    )


def check_breadth_sum(rep: Report) -> None:
    """上涨家数 + 下跌家数 应 <= 全A总数。"""
    up_rows = rep.rows("market_breadth_up.json")
    down_rows = rep.rows("market_breadth_down.json")

    if not up_rows or not down_rows:
        rep.add("market.breadth_sum", "涨跌家数总量校验", "MISSING",
                detail="market_breadth_up/down.json 无数据")
        return

    up, up_date = rep.pick(up_rows[0], "上涨家数")
    down, down_date = rep.pick(down_rows[0], "下跌家数")

    if up is None or down is None:
        rep.add("market.breadth_sum", "涨跌家数总量校验", "MISSING",
                detail=f"缺字段: 上涨={up}, 下跌={down}")
        return

    total = up + down
    ok = total <= BREADTH_SUM_MAX

    date_note = ""
    if up_date and down_date and up_date != down_date:
        date_note = f"；警告: 上涨家数日期={up_date} 与 下跌家数日期={down_date} 不一致"

    rep.add(
        "market.breadth_sum",
        "涨跌家数总量校验",
        "PASS" if ok else "CRITICAL",
        expected=f"上涨+下跌 <= {BREADTH_SUM_MAX}",
        actual=f"上涨={int(up)}, 下跌={int(down)}, 合计={int(total)}{date_note}",
        detail="" if ok else "合计超过 A 股总数上界，数据口径可能有误",
        sources=["market_breadth_up.json", "market_breadth_down.json"],
    )

    if up_date and down_date and up_date != down_date:
        rep.add(
            "market.breadth_date",
            "涨跌家数日期一致性",
            "WARN",
            expected="两个文件取自同一交易日",
            actual=f"up={up_date}, down={down_date}",
            sources=["market_breadth_up.json", "market_breadth_down.json"],
        )


def _row_date(row: dict) -> Optional[str]:
    """从一行问财数据中抽出 YYYYMMDD 日期。"""
    if not isinstance(row, dict):
        return None
    raw = row.get("时间") or row.get("日期")
    if isinstance(raw, str):
        compact = raw.replace("-", "").replace("/", "")
        if re.fullmatch(r"\d{8}", compact):
            return compact
    latest = None
    for key in row.keys():
        match = DATE_SUFFIX_RE.search(str(key))
        if not match:
            continue
        candidate = match.group(1)
        if latest is None or candidate > latest:
            latest = candidate
    return latest


def check_market_date_consistency(rep: Report) -> None:
    """市场类文件应来自同一个交易日窗口。"""
    targets = [
        ("margin_level.json", "两融水平"),
        ("margin_flow.json", "两融流向"),
        ("market_turnover.json", "成交额"),
        ("market_breadth_up.json", "上涨家数"),
        ("market_breadth_down.json", "下跌家数"),
        ("indices_cn.json", "A股指数"),
    ]
    dated: list[tuple[str, str]] = []
    for filename, label in targets:
        rows = rep.rows(filename)
        if not rows:
            rep.add(
                f"market.date.{filename}",
                f"市场数据日期: {label}",
                "MISSING",
                detail=f"{filename} 无数据",
                sources=[filename],
            )
            continue
        stamp = _row_date(rows[0])
        if not stamp:
            rep.add(
                f"market.date.{filename}",
                f"市场数据日期: {label}",
                "WARN",
                actual="未找到日期",
                sources=[filename],
            )
            continue
        dated.append((filename, stamp))

    if len(dated) < 2:
        rep.add(
            "market.date_consistency",
            "市场类文件日期一致性",
            "MISSING",
            actual=f"可解析日期文件数={len(dated)}",
            sources=[item[0] for item in dated],
        )
        return

    parsed = []
    for filename, stamp in dated:
        try:
            parsed.append((filename, datetime.strptime(stamp, "%Y%m%d").date()))
        except ValueError:
            continue
    if len(parsed) < 2:
        return
    oldest_file, oldest = min(parsed, key=lambda item: item[1])
    newest_file, newest = max(parsed, key=lambda item: item[1])
    span = (newest - oldest).days
    level = "PASS" if span == 0 else ("WARN" if span <= MARKET_DATE_SPAN_MAX_DAYS else "CRITICAL")
    rep.add(
        "market.date_consistency",
        "市场类文件日期一致性",
        level,
        expected=f"日期跨度 <= {MARKET_DATE_SPAN_MAX_DAYS} 天",
        actual=f"{oldest.isoformat()}({oldest_file}) ~ {newest.isoformat()}({newest_file})，跨度={span}天",
        detail=(
            ""
            if level == "PASS"
            else "市场文件可能来自不同交易日；超过 7 天的数据不得拼在同一份报告中。"
        ),
        sources=[item[0] for item in parsed],
    )


def check_macro_freshness(rep: Report) -> None:
    """宏观数据新鲜度：报告期距今不得超过阈值。"""
    targets = [
        ("macro_she.json", "社融存量", MACRO_STALE_DAYS),
        ("macro_cpi.json", "CPI", MACRO_STALE_DAYS),
        ("macro_ppi.json", "PPI", MACRO_STALE_DAYS),
        ("macro_m2.json", "M2", MACRO_STALE_DAYS),
        ("macro_lpr.json", "LPR", MACRO_STALE_DAYS),
        ("macro_usdcny.json", "美元兑人民币", 7),
        ("macro_global.json", "全球利率与汇率", 7),
        ("macro_assets.json", "全球商品", 7),
    ]
    today = date.today()

    for filename, label, stale_days in targets:
        rows = rep.rows(filename)
        if not rows:
            rep.add(f"macro.{filename}", f"宏观数据存在: {label}", "MISSING",
                    detail=f"{filename} 无数据", sources=[filename])
            continue

        row = rows[0]
        # 支持两种格式: 顶层 "时间": "20251231" 或字段后缀 "[20251231]"
        stamp = None
        raw_time = row.get("时间") or row.get("日期")
        if isinstance(raw_time, str) and re.fullmatch(r"\d{8}", raw_time):
            stamp = raw_time
        else:
            for key in row.keys():
                m = DATE_SUFFIX_RE.search(str(key))
                if m:
                    candidate = m.group(1)
                    if stamp is None or candidate > stamp:
                        stamp = candidate

        if not stamp:
            rep.add(f"macro.{filename}", f"宏观数据新鲜度: {label}", "WARN",
                    expected="能解析出报告期",
                    actual="未找到日期字段",
                    detail="无法判断数据是否过期，引用时需人工确认报告期",
                    sources=[filename])
            continue

        try:
            report_date = datetime.strptime(stamp, "%Y%m%d").date()
        except ValueError:
            rep.add(f"macro.{filename}", f"宏观数据新鲜度: {label}", "WARN",
                    actual=f"日期格式异常: {stamp}", sources=[filename])
            continue

        age = (today - report_date).days
        stale = age > stale_days

        rep.add(
            f"macro.{filename}",
            f"宏观数据新鲜度: {label}",
            "STALE" if stale else "PASS",
            expected=f"报告期距今 <= {stale_days} 天",
            actual=f"报告期={report_date.isoformat()}, 距今={age} 天",
            detail=("数据已过期，报告中必须标注报告期，不得表述为『最新』" if stale else ""),
            sources=[filename],
        )


def check_north_scope(rep: Report) -> None:
    """北向资金口径识别: 个股级龙虎榜 ≠ 全市场净买入。"""
    rows = rep.rows("sentiment_north.json")
    if not rows:
        rep.add("sentiment.north_scope", "北向资金口径识别", "MISSING",
                detail="sentiment_north.json 无数据",
                sources=["sentiment_north.json"])
        return

    first = rows[0]
    is_stock_level = ("股票代码" in first) or ("股票简称" in first)

    if is_stock_level:
        names = []
        for row in rows[:5]:
            nm = row.get("股票简称") or row.get("股票代码")
            if nm:
                names.append(str(nm))
        rep.add(
            "sentiment.north_scope",
            "北向资金口径识别",
            "WARN",
            expected="全市场北向资金净买入（市场合计口径）",
            actual=f"返回的是个股级席位数据，共 {len(rows)} 条",
            detail=(
                "该数据是『沪股通/深股通专用席位』龙虎榜口径，"
                "不能代表北向资金整体流向。报告中必须标注口径，"
                "不得表述为『北向资金净买入 X 亿』。"
                f"样例: {', '.join(names)}"
            ),
            sources=["sentiment_north.json"],
        )
    else:
        rep.add("sentiment.north_scope", "北向资金口径识别", "PASS",
                actual="疑似市场合计口径",
                sources=["sentiment_north.json"])


def check_turnover(rep: Report) -> None:
    """成交额合理性。"""
    rows = rep.rows("market_turnover.json")
    if not rows:
        rep.add("market.turnover", "成交额有效性", "MISSING",
                detail="market_turnover.json 无数据")
        return
    value, stamp = rep.pick(rows[0], "成交额")
    if value is None:
        rep.add("market.turnover", "成交额有效性", "MISSING",
                detail="未找到成交额字段", sources=["market_turnover.json"])
        return
    # 合理区间: 1e11 (1000亿) ~ 1e13 (10万亿)
    ok = 1e11 <= value <= 1e13
    rep.add(
        "market.turnover",
        "成交额有效性",
        "PASS" if ok else "WARN",
        expected="1,000亿 ~ 10万亿",
        actual=f"{value / 1e8:,.0f} 亿元 (日期={stamp})",
        sources=["market_turnover.json"],
    )


# ---------------------------------------------------------------- 主流程

CHECKS = [
    check_files_present,
    check_margin_identity,
    check_margin_change_consistency,
    check_margin_ratio,
    check_breadth_sum,
    check_market_date_consistency,
    check_macro_freshness,
    check_north_scope,
    check_turnover,
]


def run(data_dir: str) -> Report:
    rep = Report(data_dir)
    for fn in CHECKS:
        try:
            fn(rep)
        except Exception as exc:  # 单个校验崩溃不应中断整体
            rep.add(
                f"internal.{fn.__name__}",
                f"校验项内部错误: {fn.__name__}",
                "WARN",
                actual=repr(exc),
                detail="该检查项未能完成，其结果视为未知",
            )
    return rep


def make_payload(rep: Report, data_dir: str) -> dict:
    """把校验结果转成可供报告生成阶段读取的标准载荷。"""
    summary = rep.summary()
    return {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "data_dir": os.path.abspath(data_dir),
        "summary": summary,
        "report_allowed": summary["fail"] == 0,
        "blocking_reasons": [
            r.name for r in rep.results if r.level == "CRITICAL"
        ],
        "warnings": [
            r.name for r in rep.results if r.level in ("WARN", "STALE", "MISSING")
        ],
        "checks": [r.to_dict() for r in rep.results],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="研报数据一致性校验")
    parser.add_argument("data_dir", help="抓取数据目录，如 D:\\codex\\研报\\data\\2026-10-07")
    parser.add_argument("--out", default=None, help="输出路径（默认 <data_dir>/data_quality.json）")
    parser.add_argument("--strict", action="store_true", help="存在 CRITICAL 时返回退出码 1")
    parser.add_argument("--quiet", action="store_true", help="只输出一行摘要")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.data_dir):
        print(f"错误: 目录不存在: {args.data_dir}", file=sys.stderr)
        return 2

    rep = run(args.data_dir)
    summary = rep.summary()

    payload = make_payload(rep, args.data_dir)

    out_path = args.out or os.path.join(args.data_dir, "data_quality.json")
    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"错误: 无法写入 {out_path}: {exc}", file=sys.stderr)
        return 2

    line = (f"Data quality: {summary['pass']} pass / {summary['fail']} fail / "
            f"{summary['stale']} stale / {summary['missing']} missing / {summary['warn']} warn")
    print(line)

    if not args.quiet:
        for r in rep.results:
            if r.level == "PASS":
                continue
            print(f"  [{r.level}] {r.name}")
            if r.actual:
                print(f"        实际: {r.actual}")
            if r.detail:
                print(f"        说明: {r.detail}")
        print(f"  结果已写入: {out_path}")

    if summary["fail"] > 0 and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
