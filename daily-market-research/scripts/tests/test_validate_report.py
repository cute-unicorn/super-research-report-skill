#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告结构验收器测试。"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.normpath(os.path.join(HERE, "..", "lib"))
sys.path.insert(0, LIB)

import validate_report as vr  # noqa: E402

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def write(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def daily_basic_fixture() -> str:
    sections = [
        "市场总览",
        "行业与风格",
        "宏观与流动性",
        "海外市场与全球资产",
        "政策与要闻",
        "重要公告与事件",
        "机构观点",
        "关注方向与风险提示",
        "非共识 α 观点",
        "情绪分析",
        "两融水平及分析",
        "资金分析",
        "风险提示（汇总）",
    ]
    lines = ["# 每日市场研报", ""]
    for index, section in enumerate(sections, 1):
        lines.append(f"## {index}、{section}")
        lines.append(f"{section}正文。")
        if section == "政策与要闻":
            lines.append("内容解读：事件A。")
            lines.append("影响分析：影响A。")
            lines.append("内容解读：事件B。")
            lines.append("影响分析：影响B。")
        lines.append("")
    lines.extend(
        [
            "风险提示一。",
            "风险提示二。",
            "风险提示三。",
            "数据来源：同花顺问财。",
            "官方来源：中国人民银行 https://www.pbc.gov.cn。",
            "本报告不构成投资建议。",
        ]
    )
    return "\n".join(lines)


def stock_fixture() -> str:
    return """# 深度研报：测试公司（000001.SZ）

> 客观评级：增持 / 推荐

## 核心判断
核心判断正文。

## 基础五维度
估值：PE 10 倍。
财务：单季度营收 1 亿元，累计营收 2 亿元，收现比 90%，应收账款同比 10%，合同负债同比 20%，资产负债率 40%。
资金：主力净流入。
技术：站上 MA20。
消息与催化：订单增长。

## 产业链拆解
产业链正文。

## 政策链分析
政策正文。

## 非共识 α 观点
市场一致预期 / 非共识点 / α 来源与兑现路径 / 证伪条件。

## 情景推演与关键变量
乐观/中性/悲观。
事实：数据来自 2026-10-13 财报。
推理：基于历史区间判断。
假设：行业景气不变。
止损：跌破支撑位。
止盈：达到目标区间。

## 风险提示
风险提示一。
风险提示二。
风险提示三。

## 数据溯源与观察清单
触发条件：财报、订单或现金流变化时复核。

数据来源：同花顺问财。
官方来源：上海证券交易所公告 https://www.sse.com.cn。
本报告不构成投资建议。
"""


def daily_deep_fixture() -> str:
    sections = [
        "总体分析",
        "海外市场与全球资产",
        "政策与要闻",
        "重要公告与事件",
        "机构观点",
        "情绪与资金分析",
        "非共识 α 观点",
        "板块推荐",
        "市场驱动板块",
        "政策驱动板块",
        "个股深度分析",
        "ETF 关注组合",
        "组合建议",
        "风险提示（汇总）",
    ]
    lines = ["# 每日市场研报：深度分析与标的策略", ""]
    for index, section in enumerate(sections, 1):
        lines.append(f"## {index}、{section}")
        lines.append(f"{section}正文，测试公司（000001）。")
        if section == "政策与要闻":
            lines.append("内容解读：事件A。")
            lines.append("影响分析：影响A。")
            lines.append("内容解读：事件B。")
            lines.append("影响分析：影响B。")
        lines.append("")
    lines.extend(
        [
            "风险提示一。",
            "风险提示二。",
            "风险提示三。",
            "风险提示四。",
            "风险提示五。",
            "次日观察：观察指数和资金。",
            "复盘：收盘后核对。",
            "触发条件：若破位则降低仓位。",
            "数据来源：同花顺问财。",
            "官方来源：中国人民银行 https://www.pbc.gov.cn；国家统计局 https://www.stats.gov.cn。",
            "本报告不构成投资建议。",
        ]
    )
    return "\n".join(lines)


def main():
    global PASS, FAIL
    with tempfile.TemporaryDirectory(prefix="vr_test_") as root:
        basic_path = os.path.join(root, "daily_basic.md")
        write(basic_path, daily_basic_fixture())
        print("\n[1] 基础日报结构")
        report = vr.validate_report(basic_path, "daily-basic")
        payload = vr.make_payload(report)
        check("基础日报通过", payload["report_valid"] is True, str(payload["blocking_reasons"]))

        deep_path = os.path.join(root, "daily_deep.md")
        write(deep_path, daily_deep_fixture())
        report = vr.validate_report(deep_path, "daily-deep")
        payload = vr.make_payload(report)
        check("深度日报通过", payload["report_valid"] is True, str(payload["blocking_reasons"]))

        print("\n[2] 缺失章节必须拦截")
        broken = daily_basic_fixture().replace("## 5、政策与要闻", "## 无政策")
        broken_path = os.path.join(root, "broken.md")
        write(broken_path, broken)
        report = vr.validate_report(broken_path, "daily-basic")
        payload = vr.make_payload(report)
        check("缺失政策章节 -> report_valid=false", payload["report_valid"] is False)
        check(
            any("政策与要闻" in item for item in payload["blocking_reasons"]),
            "blocking_reasons 指出缺失章节",
        )

        print("\n[3] 个股研报结构")
        stock_path = os.path.join(root, "stock.md")
        write(stock_path, stock_fixture())
        report = vr.validate_report(stock_path, "stock")
        payload = vr.make_payload(report)
        check("个股研报通过", payload["report_valid"] is True, str(payload["blocking_reasons"]))
        no_official_path = os.path.join(root, "stock_no_official.md")
        write(
            no_official_path,
            stock_fixture().replace(
                "官方来源：上海证券交易所公告 https://www.sse.com.cn。\n",
                "",
            ),
        )
        report = vr.validate_report(no_official_path, "stock")
        check(
            "缺少官方来源 -> report_valid=false",
            vr.make_payload(report)["report_valid"] is False,
        )

        print("\n[4] 占位符告警")
        placeholder_path = os.path.join(root, "placeholder.md")
        write(placeholder_path, stock_fixture() + "\nTODO: 补充\n")
        report = vr.validate_report(placeholder_path, "stock")
        payload = vr.make_payload(report)
        check("TODO 触发 WARN", payload["summary"]["warn"] >= 1)

        print("\n[5] 关键词堆砌不能伪装成完整个股报告")
        keyword_report = (
            "# 测试报告\n\n"
            "客观评级 核心判断 五维度 估值 财务 资金 技术 消息 产业链 政策链 "
            "非共识 情景 数据来源 单季度 累计 收现比 应收账款 合同负债 资产负债率 "
            "风险提示 风险提示 风险提示 不构成投资建议\n"
        )
        keyword_path = os.path.join(root, "keyword.md")
        write(keyword_path, keyword_report)
        report = vr.validate_report(keyword_path, "stock")
        payload = vr.make_payload(report)
        check("无实际章节的关键词堆砌 -> report_valid=false", payload["report_valid"] is False)

        print("\n[6] 两份拷贝同步")
        daily_file = os.path.join(LIB, "validate_report.py")
        stock_file = os.path.normpath(
            os.path.join(HERE, "..", "..", "..", "stock-deep-research", "scripts", "lib", "validate_report.py")
        )
        if os.path.exists(stock_file):
            def digest(path):
                return hashlib.sha256(open(path, "rb").read()).hexdigest()

            check("日报/个股验收器内容一致", digest(daily_file) == digest(stock_file))
        else:
            check("个股验收器存在", False, stock_file)

    print(f"\n===== RESULT: {PASS} passed, {FAIL} failed =====")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
