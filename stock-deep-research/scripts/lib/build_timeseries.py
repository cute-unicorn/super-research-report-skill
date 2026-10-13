#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把问财的“近 N 个季度”原始返回合并成标准化财务时间序列。

问财对同一组指标可能返回两种口径：
    - 单季度_营业收入[20260630]       单季度流量
    - 营业收入[20260630]             年初至今累计流量

本模块只做确定性的解析、合并和派生计算，不负责预测或投资判断。
输出中的 ``derived`` 字段用于让研报作者检查利润、现金流、应收账款和
合同负债之间的背离，避免把单期数据直接当作趋势。

用法:
    python build_timeseries.py \
        --single-q .../stocks_timeseries_single_q.json \
        --cumulative .../stocks_timeseries_cumulative.json \
        --out .../stocks_timeseries.json \
        --as-of 2026-10-13
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import date, datetime
from typing import Any, Optional


DATE_SUFFIX_RE = re.compile(r"\[(\d{8})\]$")

# 键名必须去掉日期后缀后精确匹配，不能用 startswith，
# 否则“营业收入”会误吞“营业收入同比增长率”。
SINGLE_QUARTER_ALIASES = {
    "revenue": ("单季度_营业收入",),
    "net_profit": ("单季度_归母净利润",),
    "deducted_net_profit": ("单季度_扣非净利润",),
    "operating_cash_flow": (
        "单季度_经营活动产生的现金流量净额",
        "单季度_经营活动现金流",
    ),
    "gross_margin_pct": ("单季度_销售毛利率", "单季度_毛利率"),
    "roe_pct": ("单季度_净资产收益率", "单季度_ROE"),
    "cash_received_from_sales": (
        "单季度_销售商品和提供劳务收到的现金",
        "单季度_销售商品提供劳务收到的现金",
    ),
}

CUMULATIVE_ALIASES = {
    "revenue": ("营业收入",),
    "net_profit": ("归母净利润",),
    "deducted_net_profit": ("扣非归母净利润", "扣非净利润"),
    "operating_cash_flow": (
        "经营活动产生的现金流量净额",
        "经营活动现金流",
    ),
    "gross_margin_pct": ("销售毛利率", "毛利率"),
    "roe_pct": ("净资产收益率", "ROE"),
    "cash_received_from_sales": (
        "销售商品和提供劳务收到的现金",
        "销售商品提供劳务收到的现金",
    ),
}

BALANCE_SHEET_ALIASES = {
    "contract_liabilities": ("合同负债",),
    "accounts_receivable": ("应收账款",),
    "total_assets": ("总资产",),
    "total_liabilities": ("负债",),
}

FLOW_METRICS = (
    "revenue",
    "net_profit",
    "deducted_net_profit",
    "operating_cash_flow",
    "gross_margin_pct",
    "roe_pct",
    "cash_received_from_sales",
)

BALANCE_METRICS = (
    "contract_liabilities",
    "accounts_receivable",
    "total_assets",
    "total_liabilities",
)


def _to_number(value: Any) -> Optional[float]:
    """把接口返回的数值或带单位的字符串转为 float。"""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if not isinstance(value, str):
        return None

    text = value.strip().replace(",", "")
    if not text or text in {"--", "-", "None", "null", "未取到"}:
        return None
    scale = 1.0
    for suffix, factor in (("万亿", 1e12), ("亿", 1e8), ("万", 1e4)):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            scale = factor
            break
    if text.endswith("%"):
        text = text[:-1]
    try:
        number = float(text) * scale
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _round(value: Optional[float], digits: int = 6) -> Optional[float]:
    return None if value is None else round(value, digits)


def _period_label(period: str) -> str:
    return f"{period[:4]}-{period[4:6]}-{period[6:]}"


def _period_type(period: str) -> str:
    month = period[4:6]
    return {"03": "Q1", "06": "Q2", "09": "Q3", "12": "Q4"}.get(month, "OTHER")


def _period_date(period: str) -> date:
    return datetime.strptime(period, "%Y%m%d").date()


def _prior_year_period(periods: list[str], period: str) -> Optional[str]:
    """返回同一报告期的上一年度键，如 20260630 -> 20250630。"""
    target = _period_label(period)
    try:
        current = datetime.strptime(target, "%Y-%m-%d").date()
        previous = current.replace(year=current.year - 1).strftime("%Y%m%d")
    except ValueError:
        return None
    return previous if previous in periods else None


def _prior_quarter_period(periods: list[str], period: str) -> Optional[str]:
    """返回日历上的上一季度键；缺失时不拿更早的报告期冒充环比。"""
    try:
        current = _period_date(period)
    except ValueError:
        return None
    if current.month not in (3, 6, 9, 12):
        return None
    month, day = current.month, current.day
    if month == 3:
        previous = date(current.year - 1, 12, 31)
    elif month == 6:
        previous = date(current.year, 3, 31)
    elif month == 9:
        previous = date(current.year, 6, 30)
    else:
        previous = date(current.year, 9, 30)
    key = previous.strftime("%Y%m%d")
    return key if key in periods else None


def _yoy(
    current: Optional[float],
    previous: Optional[float],
    *,
    positive_base: bool = True,
) -> Optional[float]:
    if current is None or previous is None:
        return None
    if positive_base and previous <= 0:
        return None
    if abs(previous) < 1e-12:
        return None
    return (current / previous - 1.0) * 100.0


def _ratio_pct(
    numerator: Optional[float],
    denominator: Optional[float],
    *,
    positive_denominator: bool = True,
) -> Optional[float]:
    if numerator is None or denominator is None:
        return None
    if positive_denominator and denominator <= 0:
        return None
    if abs(denominator) < 1e-12:
        return None
    return numerator / denominator * 100.0


def _subtract(
    first: Optional[float], second: Optional[float]
) -> Optional[float]:
    if first is None or second is None:
        return None
    return first - second


def _extract_metrics(
    row: dict, aliases: dict[str, tuple[str, ...]]
) -> dict[str, dict[str, float]]:
    """按“日期后缀 + 精确指标名”抽取 {period: {metric: value}}。"""
    extracted: dict[str, dict[str, float]] = {}
    for key, raw_value in row.items():
        if not isinstance(key, str):
            continue
        match = DATE_SUFFIX_RE.search(key)
        if not match:
            continue
        base = key[: match.start()]
        metric = next(
            (name for name, names in aliases.items() if base in names),
            None,
        )
        if metric is None:
            continue
        number = _to_number(raw_value)
        if number is None:
            continue
        extracted.setdefault(match.group(1), {})[metric] = number
    return extracted


def load_rows(path: Optional[str]) -> list[dict]:
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    for key in ("datas", "data"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def _new_stock(row: dict) -> dict:
    return {
        "code": str(row.get("股票代码") or "").strip(),
        "name": str(row.get("股票简称") or "").strip(),
        "latest_price": _to_number(row.get("最新价")),
        "latest_pct": _to_number(row.get("最新涨跌幅")),
        "periods": {},
    }


def _ensure_period(stock: dict, period: str) -> dict:
    periods = stock["periods"]
    if period not in periods:
        periods[period] = {
            "period": _period_label(period),
            "report_date": period,
            "report_type": _period_type(period),
            "single_quarter": {},
            "cumulative": {},
            "balance_sheet": {},
            "derived": {},
        }
    return periods[period]


def _merge_rows(
    stocks: dict[str, dict],
    rows: list[dict],
    aliases: dict[str, tuple[str, ...]],
    target: str,
) -> None:
    for row in rows:
        code = str(row.get("股票代码") or "").strip()
        name = str(row.get("股票简称") or "").strip()
        key = code or name
        if not key:
            continue
        if key not in stocks:
            stocks[key] = _new_stock(row)
        stock = stocks[key]
        for field in ("code", "name"):
            if not stock.get(field):
                stock[field] = str(row.get("股票代码" if field == "code" else "股票简称") or "").strip()
        for field in ("latest_price", "latest_pct"):
            if stock.get(field) is None:
                source_key = "最新价" if field == "latest_price" else "最新涨跌幅"
                stock[field] = _to_number(row.get(source_key))

        extracted = _extract_metrics(row, aliases)
        for period, values in extracted.items():
            _ensure_period(stock, period)[target].update(values)


def _derive_periods(stock: dict) -> None:
    period_keys = sorted(stock["periods"].keys())
    by_period = stock["periods"]
    for period in period_keys:
        item = by_period[period]
        single = item["single_quarter"]
        cumulative = item["cumulative"]
        balance = item["balance_sheet"]

        prior_year = _prior_year_period(period_keys, period)
        prior_year_item = by_period.get(prior_year, {}) if prior_year else {}
        prior_single = prior_year_item.get("single_quarter", {}) if prior_year_item else {}
        prior_cumulative = prior_year_item.get("cumulative", {}) if prior_year_item else {}
        prior_balance = prior_year_item.get("balance_sheet", {}) if prior_year_item else {}

        previous_key = _prior_quarter_period(period_keys, period)
        previous_item = by_period.get(previous_key, {}) if previous_key else {}
        previous_balance = previous_item.get("balance_sheet", {}) if previous_item else {}

        single_revenue = single.get("revenue")
        single_net_profit = single.get("net_profit")
        single_ocf = single.get("operating_cash_flow")
        single_cash = single.get("cash_received_from_sales")
        cumulative_revenue = cumulative.get("revenue")
        cumulative_net_profit = cumulative.get("net_profit")
        cumulative_ocf = cumulative.get("operating_cash_flow")
        cumulative_cash = cumulative.get("cash_received_from_sales")

        derived = {
            "single_quarter_revenue_yoy_pct": _yoy(
                single_revenue, prior_single.get("revenue")
            ),
            "single_quarter_net_profit_yoy_pct": _yoy(
                single_net_profit, prior_single.get("net_profit")
            ),
            "single_quarter_ocf_yoy_pct": _yoy(
                single_ocf, prior_single.get("operating_cash_flow")
            ),
            "cash_to_revenue_pct": _ratio_pct(single_cash, single_revenue),
            "ocf_to_net_profit_pct": _ratio_pct(
                single_ocf, single_net_profit, positive_denominator=True
            ),
            "cumulative_cash_to_revenue_pct": _ratio_pct(
                cumulative_cash, cumulative_revenue
            ),
            "cumulative_ocf_to_net_profit_pct": _ratio_pct(
                cumulative_ocf, cumulative_net_profit, positive_denominator=True
            ),
            "revenue_yoy_pct": _yoy(
                cumulative_revenue, prior_cumulative.get("revenue")
            ),
            "receivable_yoy_pct": _yoy(
                balance.get("accounts_receivable"),
                prior_balance.get("accounts_receivable"),
            ),
            "contract_liabilities_yoy_pct": _yoy(
                balance.get("contract_liabilities"),
                prior_balance.get("contract_liabilities"),
            ),
            "contract_liabilities_qoq_pct": _yoy(
                balance.get("contract_liabilities"),
                previous_balance.get("contract_liabilities"),
            ),
            "debt_ratio_pct": _ratio_pct(
                balance.get("total_liabilities"), balance.get("total_assets")
            ),
        }
        derived["receivable_growth_minus_revenue_growth_pct"] = _subtract(
            derived["receivable_yoy_pct"], derived["revenue_yoy_pct"]
        )
        item["derived"] = {
            key: _round(value) for key, value in derived.items()
        }


def build(
    single_q_path: Optional[str],
    cumulative_path: Optional[str],
    as_of: Optional[str] = None,
) -> dict:
    stocks: dict[str, dict] = {}
    single_rows = load_rows(single_q_path)
    cumulative_rows = load_rows(cumulative_path)

    _merge_rows(stocks, single_rows, SINGLE_QUARTER_ALIASES, "single_quarter")
    _merge_rows(stocks, cumulative_rows, CUMULATIVE_ALIASES, "cumulative")
    _merge_rows(stocks, cumulative_rows, BALANCE_SHEET_ALIASES, "balance_sheet")

    for stock in stocks.values():
        _derive_periods(stock)
        periods = sorted(stock["periods"].keys())
        stock["periods_count"] = len(periods)
        stock["latest_period"] = periods[-1] if periods else None
        stock["latest_period_label"] = (
            _period_label(periods[-1]) if periods else None
        )

    datas = sorted(
        stocks.values(),
        key=lambda item: (item.get("code") or "", item.get("name") or ""),
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "as_of": as_of or date.today().isoformat(),
        "sources": {
            "single_q": os.path.abspath(single_q_path) if single_q_path else None,
            "cumulative": os.path.abspath(cumulative_path) if cumulative_path else None,
        },
        "summary": {
            "stocks_count": len(datas),
            "periods_min": min(
                (item.get("periods_count", 0) for item in datas), default=0
            ),
            "periods_max": max(
                (item.get("periods_count", 0) for item in datas), default=0
            ),
        },
        "datas": datas,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="合并问财单季度与累计财务数据为时间序列"
    )
    parser.add_argument("--single-q", default=None, help="单季度原始 JSON")
    parser.add_argument("--cumulative", default=None, help="累计/资产负债原始 JSON")
    parser.add_argument("--out", required=True, help="输出文件")
    parser.add_argument(
        "--as-of",
        default=None,
        help="数据基准日，格式 YYYY-MM-DD；默认今天",
    )
    args = parser.parse_args(argv)

    payload = build(args.single_q, args.cumulative, args.as_of)
    try:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"错误: 无法写入 {args.out}: {exc}", file=sys.stderr)
        return 2

    summary = payload["summary"]
    print(
        f"Timeseries: {summary['stocks_count']} stocks, "
        f"{summary['periods_min']}~{summary['periods_max']} periods"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
