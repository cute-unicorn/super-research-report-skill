#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""个股数据质量门禁。

独立读取 ``stocks_timeseries.json``，检查报告生成前最容易出错的事实：
    1. 是否真的有足够长的报告期序列；
    2. 最新报告期是否过旧；
    3. 本地派生指标能否由原始字段复算；
    4. 利润、经营现金流、应收账款和合同负债是否出现需要解释的背离。

输出 ``stock_data_quality.json``。CRITICAL 表示不应直接生成结论；
WARN 表示可以生成报告，但必须在正文中解释该异常。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Optional


MIN_PERIODS = 8
PERIODS_FULL = 12
MAX_LATEST_AGE_DAYS = 220
AR_DIVERGENCE_PP = 20.0
AR_GROWTH_WARN_PCT = 20.0
CONTRACT_LIABILITY_DECLINE_PCT = -30.0
DEBT_RATIO_WARN_PCT = 80.0
DEBT_RATIO_CRITICAL_PCT = 100.0
DERIVED_TOLERANCE_PP = 0.5


@dataclass
class CheckResult:
    check_id: str
    name: str
    level: str
    expected: str = ""
    actual: str = ""
    detail: str = ""
    sources: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class Report:
    def __init__(self) -> None:
        self.results: list[CheckResult] = []

    def add(
        self,
        check_id: str,
        name: str,
        level: str,
        expected: str = "",
        actual: str = "",
        detail: str = "",
        sources=None,
    ) -> None:
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
        result = {"pass": 0, "fail": 0, "warn": 0, "missing": 0}
        for item in self.results:
            if item.level == "PASS":
                result["pass"] += 1
            elif item.level == "CRITICAL":
                result["fail"] += 1
            elif item.level == "WARN":
                result["warn"] += 1
            elif item.level == "MISSING":
                result["missing"] += 1
        return result


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _load_timeseries(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _periods(stock: dict) -> list[dict]:
    periods = stock.get("periods")
    if isinstance(periods, dict):
        values = list(periods.values())
    elif isinstance(periods, list):
        values = periods
    else:
        return []
    return [item for item in values if isinstance(item, dict)]


def _latest(items: list[dict]) -> Optional[dict]:
    if not items:
        return None
    return max(
        items,
        key=lambda item: str(item.get("report_date") or item.get("period") or ""),
    )


def _check_periods(report: Report, stock: dict) -> None:
    items = _periods(stock)
    count = len(items)
    prefix = stock.get("code") or stock.get("name") or "unknown"

    if count >= PERIODS_FULL:
        level = "PASS"
    elif count >= MIN_PERIODS:
        level = "WARN"
    else:
        level = "CRITICAL"
    report.add(
        f"{prefix}.periods",
        "财务报告期数量",
        level,
        expected=f">= {PERIODS_FULL} 个报告期，底线 {MIN_PERIODS} 个",
        actual=f"{count} 个报告期",
        detail=(
            ""
            if level == "PASS"
            else "少于 12 个报告期时同比与季节性判断可信度下降；少于 8 个报告期不得据此做趋势结论。"
        ),
        sources=["stocks_timeseries.json"],
    )

    latest = _latest(items)
    if latest is None:
        return
    stamp = str(latest.get("report_date") or "").replace("-", "")
    as_of = str(stock.get("_as_of") or date.today().isoformat()).replace("-", "")
    if len(stamp) != 8 or len(as_of) != 8:
        report.add(
            f"{prefix}.period_freshness",
            "最新报告期新鲜度",
            "WARN",
            actual=f"report_date={stamp}, as_of={as_of}",
            detail="日期格式异常，无法自动判断是否过期。",
            sources=["stocks_timeseries.json"],
        )
        return
    try:
        age = (
            datetime.strptime(as_of, "%Y%m%d").date()
            - datetime.strptime(stamp, "%Y%m%d").date()
        ).days
    except ValueError:
        return
    if age < 0:
        level = "CRITICAL"
        detail = "报告期晚于数据基准日，数据分区或 as_of 参数可能错配。"
    elif age <= MAX_LATEST_AGE_DAYS:
        level = "PASS"
        detail = ""
    else:
        level = "CRITICAL"
        detail = "最新报告期明显滞后，可能漏掉新财报；不得把该数据表述为最新。"
    report.add(
        f"{prefix}.period_freshness",
        "最新报告期新鲜度",
        level,
        expected=f"距今 <= {MAX_LATEST_AGE_DAYS} 天",
        actual=f"{stamp}，距今 {age} 天",
        detail=detail,
        sources=["stocks_timeseries.json"],
    )


def _check_latest_coverage(report: Report, stock: dict) -> None:
    prefix = stock.get("code") or stock.get("name") or "unknown"
    latest = _latest(_periods(stock))
    if latest is None:
        report.add(
            f"{prefix}.coverage",
            "最新期字段覆盖",
            "CRITICAL",
            actual="无报告期数据",
            sources=["stocks_timeseries.json"],
        )
        return

    single = latest.get("single_quarter") or {}
    cumulative = latest.get("cumulative") or {}
    balance = latest.get("balance_sheet") or {}
    required = {
        "single_quarter.revenue": single.get("revenue"),
        "single_quarter.net_profit": single.get("net_profit"),
        "single_quarter.operating_cash_flow": single.get("operating_cash_flow"),
        "single_quarter.cash_received_from_sales": single.get("cash_received_from_sales"),
        "cumulative.revenue": cumulative.get("revenue"),
        "cumulative.net_profit": cumulative.get("net_profit"),
        "cumulative.operating_cash_flow": cumulative.get("operating_cash_flow"),
        "balance_sheet.accounts_receivable": balance.get("accounts_receivable"),
        "balance_sheet.contract_liabilities": balance.get("contract_liabilities"),
        "balance_sheet.total_assets": balance.get("total_assets"),
        "balance_sheet.total_liabilities": balance.get("total_liabilities"),
    }
    # 缺失这些字段时，利润质量、现金流和杠杆结论无法成立，必须阻断。
    critical_keys = {
        "single_quarter.revenue",
        "single_quarter.net_profit",
        "single_quarter.operating_cash_flow",
        "cumulative.revenue",
        "cumulative.net_profit",
        "cumulative.operating_cash_flow",
        "balance_sheet.total_assets",
        "balance_sheet.total_liabilities",
    }
    missing = [key for key, value in required.items() if _number(value) is None]
    missing_critical = [key for key in missing if key in critical_keys]
    missing_optional = [key for key in missing if key not in critical_keys]
    if missing_critical:
        level = "CRITICAL"
        detail = (
            "关键财务字段缺失，利润质量、现金流或杠杆结论不可生成。"
            "缺失字段必须写入 blocking_reasons，修复数据后重跑。"
        )
    elif missing_optional:
        level = "WARN"
        detail = "非关键字段缺失，报告中必须写“未取到”，不得用上一期或推测值补数。"
    else:
        level = "PASS"
        detail = ""
    report.add(
        f"{prefix}.coverage",
        "最新期核心字段覆盖",
        level,
        expected="核心财务字段全部存在",
        actual="全部存在" if not missing else "缺失: " + ", ".join(missing),
        detail=detail,
        sources=["stocks_timeseries.json"],
    )


def _period_key(item: dict) -> str:
    return str(item.get("report_date") or item.get("period") or "").replace("-", "")


def _prior_year_key(period: str) -> Optional[str]:
    try:
        current = datetime.strptime(period, "%Y%m%d").date()
        previous = current.replace(year=current.year - 1)
    except ValueError:
        return None
    return previous.strftime("%Y%m%d")


def _prior_quarter_key(period: str) -> Optional[str]:
    try:
        current = datetime.strptime(period, "%Y%m%d").date()
    except ValueError:
        return None
    if current.month == 3:
        previous = date(current.year - 1, 12, 31)
    elif current.month == 6:
        previous = date(current.year, 3, 31)
    elif current.month == 9:
        previous = date(current.year, 6, 30)
    elif current.month == 12:
        previous = date(current.year, 9, 30)
    else:
        return None
    return previous.strftime("%Y%m%d")


def _yoy(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous is None or previous <= 0:
        return None
    return (current / previous - 1.0) * 100.0


def _ratio_pct(
    numerator: Optional[float], denominator: Optional[float]
) -> Optional[float]:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator * 100.0


def _expected_derived(item: dict, by_key: dict) -> dict:
    period = _period_key(item)
    prior_year = by_key.get(_prior_year_key(period), {}) if period else {}
    prior_quarter = by_key.get(_prior_quarter_key(period), {}) if period else {}
    single = item.get("single_quarter") or {}
    cumulative = item.get("cumulative") or {}
    balance = item.get("balance_sheet") or {}
    prior_single = prior_year.get("single_quarter") or {}
    prior_cumulative = prior_year.get("cumulative") or {}
    prior_balance = prior_year.get("balance_sheet") or {}
    previous_balance = prior_quarter.get("balance_sheet") or {}

    derived = {
        "single_quarter_revenue_yoy_pct": _yoy(
            _number(single.get("revenue")),
            _number(prior_single.get("revenue")),
        ),
        "single_quarter_net_profit_yoy_pct": _yoy(
            _number(single.get("net_profit")),
            _number(prior_single.get("net_profit")),
        ),
        "single_quarter_ocf_yoy_pct": _yoy(
            _number(single.get("operating_cash_flow")),
            _number(prior_single.get("operating_cash_flow")),
        ),
        "cash_to_revenue_pct": _ratio_pct(
            _number(single.get("cash_received_from_sales")),
            _number(single.get("revenue")),
        ),
        "ocf_to_net_profit_pct": _ratio_pct(
            _number(single.get("operating_cash_flow")),
            _number(single.get("net_profit")),
        ),
        "cumulative_cash_to_revenue_pct": _ratio_pct(
            _number(cumulative.get("cash_received_from_sales")),
            _number(cumulative.get("revenue")),
        ),
        "cumulative_ocf_to_net_profit_pct": _ratio_pct(
            _number(cumulative.get("operating_cash_flow")),
            _number(cumulative.get("net_profit")),
        ),
        "revenue_yoy_pct": _yoy(
            _number(cumulative.get("revenue")),
            _number(prior_cumulative.get("revenue")),
        ),
        "receivable_yoy_pct": _yoy(
            _number(balance.get("accounts_receivable")),
            _number(prior_balance.get("accounts_receivable")),
        ),
        "contract_liabilities_yoy_pct": _yoy(
            _number(balance.get("contract_liabilities")),
            _number(prior_balance.get("contract_liabilities")),
        ),
        "contract_liabilities_qoq_pct": _yoy(
            _number(balance.get("contract_liabilities")),
            _number(previous_balance.get("contract_liabilities")),
        ),
        "debt_ratio_pct": _ratio_pct(
            _number(balance.get("total_liabilities")),
            _number(balance.get("total_assets")),
        ),
    }
    ar_yoy = derived["receivable_yoy_pct"]
    revenue_yoy = derived["revenue_yoy_pct"]
    derived["receivable_growth_minus_revenue_growth_pct"] = (
        ar_yoy - revenue_yoy
        if ar_yoy is not None and revenue_yoy is not None
        else None
    )
    return derived


def _check_derived_recompute(report: Report, stock: dict) -> None:
    prefix = stock.get("code") or stock.get("name") or "unknown"
    items = _periods(stock)
    if not items:
        return
    by_key = {
        _period_key(item): item
        for item in items
        if _period_key(item)
    }
    mismatches: list[str] = []
    for item in items:
        period = _period_key(item)
        if not period:
            continue
        expected = _expected_derived(item, by_key)
        actual_derived = item.get("derived") or {}
        for name, expected_value in expected.items():
            actual_value = _number(actual_derived.get(name))
            if expected_value is None:
                if actual_value is not None:
                    mismatches.append(f"{period}.{name}=None预期,实际={actual_value}")
                continue
            if (
                actual_value is None
                or abs(actual_value - expected_value) > DERIVED_TOLERANCE_PP
            ):
                mismatches.append(
                    f"{period}.{name}预期={expected_value:.4f},实际={actual_value}"
                )

    if mismatches:
        report.add(
            f"{prefix}.derived_recompute",
            "逐期派生指标复算",
            "CRITICAL",
            expected="全部派生指标可由原始字段精确复算",
            actual=f"{len(mismatches)} 处不一致: " + "; ".join(mismatches[:5]),
            detail="时间序列文件可能被污染，必须重新构建后再生成报告。",
            sources=["stocks_timeseries.json"],
        )
    else:
        report.add(
            f"{prefix}.derived_recompute",
            "逐期派生指标复算",
            "PASS",
            actual="全部通过",
            sources=["stocks_timeseries.json"],
        )


def _check_anomalies(report: Report, stock: dict) -> None:
    prefix = stock.get("code") or stock.get("name") or "unknown"
    items = sorted(
        _periods(stock),
        key=lambda item: str(item.get("report_date") or item.get("period") or ""),
    )
    latest = _latest(items)
    if latest is None:
        return

    single = latest.get("single_quarter") or {}
    cumulative = latest.get("cumulative") or {}
    balance = latest.get("balance_sheet") or {}
    derived = latest.get("derived") or {}

    net_profit = _number(cumulative.get("net_profit"))
    ocf = _number(cumulative.get("operating_cash_flow"))
    if net_profit is not None and ocf is not None and net_profit > 0 and ocf < 0:
        report.add(
            f"{prefix}.profit_cash_divergence",
            "利润与经营现金流背离",
            "WARN",
            expected="利润为正时经营现金流通常同步为正",
            actual=f"累计归母净利润={net_profit:,.0f}, 累计经营现金流={ocf:,.0f}",
            detail=(
                "可能存在回款滞后、项目垫资、收入确认前置或利润质量下降。"
                "报告必须解释背离来源，并检查应收账款和合同负债；不得只引用净利润。"
            ),
            sources=["stocks_timeseries.json"],
        )
    else:
        report.add(
            f"{prefix}.profit_cash_divergence",
            "利润与经营现金流背离",
            "PASS",
            actual="未触发“利润为正、经营现金流为负”规则",
            sources=["stocks_timeseries.json"],
        )

    last_two = items[-2:]
    if len(last_two) == 2:
        negatives = 0
        for item in last_two:
            single_item = item.get("single_quarter") or {}
            item_profit = _number(single_item.get("net_profit"))
            item_ocf = _number(single_item.get("operating_cash_flow"))
            if item_profit is not None and item_profit > 0 and item_ocf is not None and item_ocf < 0:
                negatives += 1
        if negatives == 2:
            report.add(
                f"{prefix}.consecutive_cash_divergence",
                "连续两个季度利润与现金流背离",
                "WARN",
                actual="连续两季单季度净利润为正、经营现金流为负",
                detail="连续性比单季异常更值得警惕，报告中必须单独讨论。",
                sources=["stocks_timeseries.json"],
            )

    ar_yoy = _number(derived.get("receivable_yoy_pct"))
    revenue_yoy = _number(derived.get("revenue_yoy_pct"))
    divergence = _number(derived.get("receivable_growth_minus_revenue_growth_pct"))
    if (
        ar_yoy is not None
        and revenue_yoy is not None
        and ar_yoy > AR_GROWTH_WARN_PCT
        and divergence is not None
        and divergence > AR_DIVERGENCE_PP
    ):
        report.add(
            f"{prefix}.receivable_divergence",
            "应收账款增速与营收增速背离",
            "WARN",
            expected=f"应收账款同比增速 - 营收同比增速 <= {AR_DIVERGENCE_PP:.0f}pp",
            actual=f"应收同比={ar_yoy:.2f}%, 营收同比={revenue_yoy:.2f}%, 差值={divergence:.2f}pp",
            detail="需检查回款政策、账龄、坏账准备和收入确认节奏。",
            sources=["stocks_timeseries.json"],
        )
    else:
        report.add(
            f"{prefix}.receivable_divergence",
            "应收账款增速与营收增速背离",
            "PASS",
            actual="未触发阈值",
            sources=["stocks_timeseries.json"],
        )

    cl_yoy = _number(derived.get("contract_liabilities_yoy_pct"))
    cl_qoq = _number(derived.get("contract_liabilities_qoq_pct"))
    if cl_yoy is not None and cl_yoy < CONTRACT_LIABILITY_DECLINE_PCT:
        report.add(
            f"{prefix}.contract_liability_decline",
            "合同负债同比大幅下降",
            "WARN",
            expected=f"同比 >= {CONTRACT_LIABILITY_DECLINE_PCT:.0f}%",
            actual=f"同比={cl_yoy:.2f}%, 环比={cl_qoq}",
            detail=(
                "合同负债下降既可能来自订单减少，也可能来自预收款转为收入。"
                "必须结合订单、收入确认和现金流证据区分，不能机械地判定为利空。"
            ),
            sources=["stocks_timeseries.json"],
        )
    else:
        report.add(
            f"{prefix}.contract_liability_decline",
            "合同负债同比大幅下降",
            "PASS",
            actual="未触发阈值",
            sources=["stocks_timeseries.json"],
        )

    debt_ratio = _number(derived.get("debt_ratio_pct"))
    if debt_ratio is not None and debt_ratio >= DEBT_RATIO_CRITICAL_PCT:
        report.add(
            f"{prefix}.debt_ratio",
            "资产负债率",
            "CRITICAL",
            expected=f"< {DEBT_RATIO_CRITICAL_PCT:.0f}%",
            actual=f"{debt_ratio:.2f}%",
            detail="总负债已达到或超过总资产，必须核实数据口径和持续经营风险。",
            sources=["stocks_timeseries.json"],
        )
    elif debt_ratio is not None and debt_ratio >= DEBT_RATIO_WARN_PCT:
        report.add(
            f"{prefix}.debt_ratio",
            "资产负债率",
            "WARN",
            expected=f"< {DEBT_RATIO_WARN_PCT:.0f}%",
            actual=f"{debt_ratio:.2f}%",
            detail="杠杆偏高，需结合有息负债、现金流和融资成本分析。",
            sources=["stocks_timeseries.json"],
        )
    else:
        report.add(
            f"{prefix}.debt_ratio",
            "资产负债率",
            "PASS",
            actual=f"{debt_ratio:.2f}%" if debt_ratio is not None else "未取到",
            sources=["stocks_timeseries.json"],
        )


def _stock_label(stock: dict) -> str:
    code = stock.get("code") or ""
    name = stock.get("name") or ""
    return " ".join(item for item in (code, name) if item) or "unknown"


def run(data_dir: str, as_of: Optional[str] = None) -> Report:
    report = Report()
    path = os.path.join(data_dir, "stocks_timeseries.json")
    payload = _load_timeseries(path)
    if payload is None:
        report.add(
            "timeseries.file",
            "财务时间序列文件",
            "CRITICAL",
            expected="存在且可为合法 JSON",
            actual="缺失或解析失败",
            detail="没有时间序列时，不得生成涉及财务趋势和订单前瞻的结论。",
            sources=["stocks_timeseries.json"],
        )
        return report

    if not payload.get("summary"):
        report.add(
            "timeseries.summary",
            "时间序列摘要",
            "WARN",
            actual="缺少 summary 字段",
            sources=["stocks_timeseries.json"],
        )

    datas = payload.get("datas")
    if not isinstance(datas, list) or not datas:
        report.add(
            "timeseries.data",
            "时间序列数据",
            "CRITICAL",
            actual="datas 为空",
            sources=["stocks_timeseries.json"],
        )
        return report

    effective_as_of = as_of or payload.get("as_of") or date.today().isoformat()
    for stock in datas:
        if not isinstance(stock, dict):
            continue
        stock = dict(stock)
        stock["_as_of"] = effective_as_of
        try:
            _check_periods(report, stock)
            _check_latest_coverage(report, stock)
            _check_derived_recompute(report, stock)
            _check_anomalies(report, stock)
        except Exception as exc:
            report.add(
                f"{_stock_label(stock)}.internal",
                "个股校验内部错误",
                "WARN",
                actual=repr(exc),
                detail="该个股的检查未完整执行，其结果视为未知。",
                sources=["stocks_timeseries.json"],
            )
    return report


def make_payload(report: Report, data_dir: str) -> dict:
    """把校验结果转成报告生成阶段可读取的标准载荷。"""
    summary = report.summary()
    return {
        "schema_version": 1,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "data_dir": os.path.abspath(data_dir),
        "summary": summary,
        "report_allowed": summary["fail"] == 0,
        "blocking_reasons": [
            item.name for item in report.results if item.level == "CRITICAL"
        ],
        "warnings": [
            item.name
            for item in report.results
            if item.level in ("WARN", "MISSING")
        ],
        "checks": [item.to_dict() for item in report.results],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="个股数据质量门禁")
    parser.add_argument("data_dir", help="包含 stocks_timeseries.json 的目录")
    parser.add_argument("--out", default=None, help="默认 <data_dir>/stock_data_quality.json")
    parser.add_argument("--as-of", default=None, help="数据基准日 YYYY-MM-DD")
    parser.add_argument("--strict", action="store_true", help="存在 CRITICAL 时返回 1")
    parser.add_argument("--quiet", action="store_true", help="只输出一行摘要")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.data_dir):
        print(f"错误: 目录不存在: {args.data_dir}", file=sys.stderr)
        return 2

    report = run(args.data_dir, args.as_of)
    summary = report.summary()
    payload = make_payload(report, args.data_dir)
    out_path = args.out or os.path.join(args.data_dir, "stock_data_quality.json")
    try:
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"错误: 无法写入 {out_path}: {exc}", file=sys.stderr)
        return 2

    print(
        f"Stock data quality: {summary['pass']} pass / {summary['fail']} fail / "
        f"{summary['warn']} warn / {summary['missing']} missing"
    )
    if not args.quiet:
        for item in report.results:
            if item.level == "PASS":
                continue
            print(f"  [{item.level}] {item.name}")
            if item.actual:
                print(f"        实际: {item.actual}")
            if item.detail:
                print(f"        说明: {item.detail}")
        print(f"  结果已写入: {out_path}")

    if summary["fail"] > 0 and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
