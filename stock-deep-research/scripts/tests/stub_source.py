#!/usr/bin/env python3
"""离线集成测试用的问财/搜索数据源 stub。

故意只返回 2 个报告期，用于触发个股数据质量门禁的 CRITICAL 路径。
"""

import json
import sys


def build_row(periods, *, single=False):
    data = {
        "股票代码": "000001.SZ",
        "股票简称": "测试公司",
        "最新价": "10.00",
        "最新涨跌幅": -1.0,
    }
    for period in periods:
        if single:
            data[f"单季度_营业收入[{period}]"] = 100.0
            data[f"单季度_归母净利润[{period}]"] = 10.0
            data[f"单季度_扣非净利润[{period}]"] = 9.0
            data[f"单季度_经营活动产生的现金流量净额[{period}]"] = 8.0
            data[f"单季度_销售毛利率[{period}]"] = 20.0
            data[f"单季度_净资产收益率[{period}]"] = 5.0
            data[f"单季度_销售商品和提供劳务收到的现金[{period}]"] = 90.0
        else:
            data[f"营业收入[{period}]"] = 100.0
            data[f"归母净利润[{period}]"] = 10.0
            data[f"扣非归母净利润[{period}]"] = 9.0
            data[f"经营活动产生的现金流量净额[{period}]"] = 8.0
            data[f"销售毛利率[{period}]"] = 20.0
            data[f"净资产收益率[{period}]"] = 5.0
            data[f"销售商品和提供劳务收到的现金[{period}]"] = 90.0
            data[f"合同负债[{period}]"] = 50.0
            data[f"应收账款[{period}]"] = 40.0
            data[f"总资产[{period}]"] = 1000.0
            data[f"负债[{period}]"] = 400.0
    return data


def main():
    args = sys.argv[1:]
    if "--query" in args:
        query = args[args.index("--query") + 1]
    elif args:
        query = args[0]
    else:
        query = ""

    periods = ["20260331", "20260630"]
    if "近12个季度" in query and "单季度" in query:
        rows = [build_row(periods, single=True)]
    elif "近12个季度" in query:
        rows = [build_row(periods)]
    else:
        rows = [{"股票代码": "000001.SZ", "股票简称": "测试公司", "最新价": "10.00"}]
    print(json.dumps({"success": True, "datas": rows}, ensure_ascii=False))


if __name__ == "__main__":
    main()
