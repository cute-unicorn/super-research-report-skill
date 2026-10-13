#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""财务时间序列构建器与个股数据门禁的离线测试。

用法:
    python stock-deep-research/scripts/tests/test_timeseries.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = SCRIPT_ROOT / "lib"
sys.path.insert(0, str(LIB_ROOT))

import build_timeseries as bt  # noqa: E402
import validate_stock_facts as vf  # noqa: E402


PASS = 0
FAIL = 0


def check(condition: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}" + (f": {detail}" if detail else ""))


def write_json(path: Path, payload: dict, *, bom: bool = False) -> None:
    encoding = "utf-8-sig" if bom else "utf-8"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding=encoding,
    )


def make_fixture(
    *,
    period_count: int = 12,
    latest_revenue: float = 200.0,
    latest_previous_revenue: float = 100.0,
    latest_cash: float = 150.0,
    latest_ocf: float = 20.0,
    latest_net_profit: float = 25.0,
    latest_ar: float = 240.0,
    previous_ar: float = 100.0,
    latest_cl: float = 60.0,
    previous_cl: float = 100.0,
    latest_assets: float = 1000.0,
    latest_liabilities: float = 400.0,
) -> tuple[dict, dict]:
    periods = [
        "20230930",
        "20231231",
        "20240331",
        "20240630",
        "20240930",
        "20241231",
        "20250331",
        "20250630",
        "20250930",
        "20251231",
        "20260331",
        "20260630",
    ][:period_count]
    if len(periods) < 2:
        periods = ["20260331", "20260630"]

    single_row = {"股票代码": "000001.SZ", "股票简称": "测试公司", "最新价": "10.5", "最新涨跌幅": "-1.2"}
    cumulative_row = {
        "股票代码": "000001.SZ",
        "股票简称": "测试公司",
        "最新价": "10.5",
        "最新涨跌幅": "-1.2",
    }
    latest_period = periods[-1]
    prior_year_period = (
        str(int(latest_period[:4]) - 1) + latest_period[4:]
    )
    for index, period in enumerate(periods):
        if period == latest_period:
            revenue = latest_revenue
            cash = latest_cash
            ocf = latest_ocf
            net_profit = latest_net_profit
            ar = latest_ar
            cl = latest_cl
            assets = latest_assets
            liabilities = latest_liabilities
        elif period == prior_year_period:
            revenue = latest_previous_revenue
            cash = 80.0
            ocf = 10.0
            net_profit = 10.0
            ar = previous_ar
            cl = previous_cl
            assets = 900.0
            liabilities = 300.0
        else:
            revenue = 100.0 + index
            cash = 80.0 + index
            ocf = 10.0
            net_profit = 10.0
            ar = 100.0 + index
            cl = 100.0
            assets = 900.0
            liabilities = 300.0
        single_row[f"单季度_营业收入[{period}]"] = revenue
        single_row[f"单季度_归母净利润[{period}]"] = net_profit
        single_row[f"单季度_扣非净利润[{period}]"] = net_profit - 1.0
        single_row[f"单季度_经营活动产生的现金流量净额[{period}]"] = ocf
        single_row[f"单季度_销售毛利率[{period}]"] = 20.0
        single_row[f"单季度_净资产收益率[{period}]"] = 5.0
        single_row[f"单季度_销售商品和提供劳务收到的现金[{period}]"] = cash

        cumulative_row[f"营业收入[{period}]"] = revenue * 2
        cumulative_row[f"归母净利润[{period}]"] = net_profit * 2
        cumulative_row[f"扣非归母净利润[{period}]"] = (net_profit - 1.0) * 2
        cumulative_row[f"经营活动产生的现金流量净额[{period}]"] = ocf
        cumulative_row[f"销售毛利率[{period}]"] = 20.0
        cumulative_row[f"净资产收益率[{period}]"] = 5.0
        cumulative_row[f"销售商品和提供劳务收到的现金[{period}]"] = cash
        cumulative_row[f"合同负债[{period}]"] = cl
        cumulative_row[f"应收账款[{period}]"] = ar
        cumulative_row[f"总资产[{period}]"] = assets
        cumulative_row[f"负债[{period}]"] = liabilities
    return (
        {"success": True, "datas": [single_row]},
        {"success": True, "datas": [cumulative_row]},
    )


def run_tests() -> int:
    global PASS, FAIL
    PASS = 0
    FAIL = 0

    with tempfile.TemporaryDirectory(prefix="stock_ts_test_") as tmp:
        tmp_path = Path(tmp)
        single_payload, cumulative_payload = make_fixture()
        single_path = tmp_path / "single.json"
        cumulative_path = tmp_path / "cumulative.json"
        output_path = tmp_path / "stocks_timeseries.json"
        write_json(single_path, single_payload, bom=True)
        write_json(cumulative_path, cumulative_payload)

        print("\n[1] 时间序列构建")
        payload = bt.build(str(single_path), str(cumulative_path), "2026-10-13")
        check(payload["summary"]["stocks_count"] == 1, "识别 1 只股票")
        check(payload["summary"]["periods_min"] == 12, "保留 12 个报告期")
        stock = payload["datas"][0]
        latest = stock["periods"]["20260630"]
        check(latest["period"] == "2026-06-30", "标准化报告期")
        check(latest["report_type"] == "Q2", "识别 Q2")
        check(latest["single_quarter"]["revenue"] == 200.0, "单季度营收")
        check(latest["derived"]["cash_to_revenue_pct"] == 75.0, "收现比=75%")
        check(
            latest["derived"]["receivable_yoy_pct"] == 140.0,
            "应收账款同比=140%",
        )
        check(
            latest["derived"]["receivable_growth_minus_revenue_growth_pct"]
            == 40.0,
            "应收-营收增速差=40pp",
        )
        check(
            latest["derived"]["contract_liabilities_yoy_pct"] == -40.0,
            "合同负债同比=-40%",
        )
        check(
            latest["derived"]["debt_ratio_pct"] == 40.0,
            "资产负债率=40%",
        )
        check(
            latest["derived"]["single_quarter_revenue_yoy_pct"] == 100.0,
            "单季营收同比=100%",
        )

        print("\n[2] 字段缺失不崩溃")
        partial_single = {"success": True, "datas": [{"股票代码": "000001.SZ", "股票简称": "测试公司"}]}
        partial_path = tmp_path / "partial.json"
        write_json(partial_path, partial_single)
        partial_payload = bt.build(str(partial_path), None, "2026-10-13")
        check(partial_payload["summary"]["stocks_count"] == 1, "保留股票行")
        check(partial_payload["summary"]["periods_max"] == 0, "无报告期不伪造数据")

        print("\n[3] 数据门禁正常样本")
        write_json(output_path, payload)
        report = vf.run(str(tmp_path), "2026-10-13")
        summary = report.summary()
        check(summary["fail"] == 0, "正常样本无 CRITICAL", str(summary))
        check(summary["warn"] >= 2, "识别应收/合同负债异常", str(summary))
        quality_payload = vf.make_payload(report, str(tmp_path))
        check(
            quality_payload["report_allowed"] is True,
            "正常样本 report_allowed=true",
            str(quality_payload["report_allowed"]),
        )

        print("\n[4] 篡改派生值必须被拦截")
        tampered = json.loads(json.dumps(payload))
        tampered["datas"][0]["periods"]["20260630"]["derived"]["cash_to_revenue_pct"] = 1.0
        write_json(output_path, tampered)
        report = vf.run(str(tmp_path), "2026-10-13")
        check(report.summary()["fail"] >= 1, "收现比被篡改 -> CRITICAL")
        quality_payload = vf.make_payload(report, str(tmp_path))
        check(
            quality_payload["report_allowed"] is False,
            "篡改样本 report_allowed=false",
        )
        check(
            len(quality_payload["blocking_reasons"]) >= 1,
            "篡改样本记录 blocking_reasons",
        )
        trend_tampered = json.loads(json.dumps(payload))
        latest_tampered = trend_tampered["datas"][0]["periods"]["20260630"]
        latest_tampered["derived"]["receivable_yoy_pct"] = 0.0
        latest_tampered["derived"]["contract_liabilities_yoy_pct"] = 0.0
        write_json(output_path, trend_tampered)
        report = vf.run(str(tmp_path), "2026-10-13")
        check(
            report.summary()["fail"] >= 1,
            "应收/合同负债同比被篡改 -> CRITICAL",
        )

        print("\n[5] 报告期不足必须被拦截")
        short_single, short_cumulative = make_fixture(period_count=4)
        short_single_path = tmp_path / "short_single.json"
        short_cumulative_path = tmp_path / "short_cumulative.json"
        write_json(short_single_path, short_single)
        write_json(short_cumulative_path, short_cumulative)
        short_payload = bt.build(str(short_single_path), str(short_cumulative_path))
        write_json(output_path, short_payload)
        report = vf.run(str(tmp_path), "2026-10-13")
        check(report.summary()["fail"] >= 1, "少于 8 期 -> CRITICAL", str(report.summary()))

        print("\n[6] 连续两季利润与现金流背离")
        negative_ocf_single, negative_ocf_cumulative = make_fixture(
            latest_ocf=-5.0
        )
        # 把上一期单季度经营现金流也改成负数。
        negative_ocf_single["datas"][0][
            "单季度_经营活动产生的现金流量净额[20260331]"
        ] = -6.0
        negative_ocf_cumulative["datas"][0][
            "经营活动产生的现金流量净额[20260630]"
        ] = -5.0
        ns_path = tmp_path / "neg_single.json"
        nc_path = tmp_path / "neg_cumulative.json"
        write_json(ns_path, negative_ocf_single)
        write_json(nc_path, negative_ocf_cumulative)
        neg_payload = bt.build(str(ns_path), str(nc_path))
        write_json(output_path, neg_payload)
        report = vf.run(str(tmp_path), "2026-10-13")
        checks = [item.check_id for item in report.results]
        check(
            any(item.endswith("consecutive_cash_divergence") for item in checks),
            "识别连续两季现金流背离",
        )

        print("\n[7] 资产负债率过高")
        risky_single, risky_cumulative = make_fixture(
            latest_assets=100.0, latest_liabilities=130.0
        )
        rs_path = tmp_path / "risk_single.json"
        rc_path = tmp_path / "risk_cumulative.json"
        write_json(rs_path, risky_single)
        write_json(rc_path, risky_cumulative)
        risky_payload = bt.build(str(rs_path), str(rc_path))
        write_json(output_path, risky_payload)
        report = vf.run(str(tmp_path), "2026-10-13")
        check(report.summary()["fail"] >= 1, "负债率超过 100% -> CRITICAL")

        print("\n[8] 关键经营现金流字段缺失必须硬拦截")
        missing_ocf = json.loads(json.dumps(payload))
        missing_latest = missing_ocf["datas"][0]["periods"]["20260630"]
        missing_latest["single_quarter"].pop("operating_cash_flow", None)
        missing_latest["cumulative"].pop("operating_cash_flow", None)
        write_json(output_path, missing_ocf)
        report = vf.run(str(tmp_path), "2026-10-13")
        check(report.summary()["fail"] >= 1, "核心现金流缺失 -> CRITICAL")
        check(
            vf.make_payload(report, str(tmp_path))["report_allowed"] is False,
            "核心现金流缺失 -> report_allowed=false",
        )

        print("\n[9] 未来报告期必须被拦截")
        write_json(output_path, payload)
        report = vf.run(str(tmp_path), "2025-01-01")
        check(report.summary()["fail"] >= 1, "报告期晚于 as_of -> CRITICAL")

        print("\n[10] 缺失日历季度不能冒充环比")
        gap_single = {
            "success": True,
            "datas": [{
                "股票代码": "000001.SZ",
                "股票简称": "测试公司",
                "单季度_营业收入[20250331]": 100.0,
                "单季度_营业收入[20251231]": 100.0,
            }],
        }
        gap_cumulative = {
            "success": True,
            "datas": [{
                "股票代码": "000001.SZ",
                "股票简称": "测试公司",
                "合同负债[20250331]": 100.0,
                "合同负债[20251231]": 60.0,
            }],
        }
        gap_single_path = tmp_path / "gap_single.json"
        gap_cumulative_path = tmp_path / "gap_cumulative.json"
        write_json(gap_single_path, gap_single)
        write_json(gap_cumulative_path, gap_cumulative)
        gap_payload = bt.build(str(gap_single_path), str(gap_cumulative_path))
        gap_qoq = gap_payload["datas"][0]["periods"]["20251231"]["derived"][
            "contract_liabilities_qoq_pct"
        ]
        check(gap_qoq is None, "缺失 2025Q2/Q3 时 QoQ 应为 None", str(gap_qoq))

    print(f"\n===== RESULT: {PASS} passed, {FAIL} failed =====")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(run_tests())
