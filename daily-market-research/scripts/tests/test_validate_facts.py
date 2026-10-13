#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_facts.py 的测试。

覆盖三类场景:
    1. 负向测试 —— 构造"应该被拦下"的数据，验证校验器真的会报错
    2. 误报测试 —— 构造"正常"的数据，验证不会被误判
    3. 边界测试 —— 容差边界、缺字段、BOM 编码

用法:
    python test_validate_facts.py
退出码 0 全部通过，1 存在失败。
"""

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.normpath(os.path.join(HERE, "..", "lib"))
sys.path.insert(0, LIB)

import validate_facts as vf  # noqa: E402

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


def write_json(path, payload, bom=False):
    encoding = "utf-8-sig" if bom else "utf-8"
    with open(path, "w", encoding=encoding) as fh:
        json.dump(payload, fh, ensure_ascii=False)


def base_fixture(root):
    """构造一套内部自洽的正常数据。

    数值取自 2026-10-12 的真实抓取结果——该日数据通过了全部勾稽校验：
    融资净买入 / 融资余额 = -0.2321%，接口报 -0.2315%，偏差 1.00x；
    两融 / 流通市值 = 2.592%，落在合理区间。
    """
    financing = 2_390_776_445_326.0
    securities = 21_841_413_119.0
    total = financing + securities
    float_cap = 93_063_201_000_000.0

    write_json(os.path.join(root, "margin_level.json"), {"datas": [{
        "融资余额[20260930]": financing,
        "融券余额[20260930]": securities,
        "两融余额[20260930]": total,
        "流通市值[20260930]": float_cap,
        "融资净买入额[20260930]": -5_548_165_669.0,
    }]}, bom=True)

    # 正确口径: -55.48亿 / 2.391万亿 = -0.2321%
    write_json(os.path.join(root, "margin_change.json"), {"datas": [{
        "融资余额环比增长率[20260930]": -0.2315,
    }]}, bom=True)

    write_json(os.path.join(root, "margin_flow.json"), {"datas": [{
        "融资净买入额[20260930]": -5_548_165_669.0,
    }]}, bom=True)

    write_json(os.path.join(root, "market_breadth_up.json"),
               {"datas": [{"上涨家数[20260930]": 2568.0}]}, bom=True)
    write_json(os.path.join(root, "market_breadth_down.json"),
               {"datas": [{"下跌家数[20260930]": 2822.0}]}, bom=True)
    write_json(os.path.join(root, "market_turnover.json"),
               {"datas": [{"成交额[20260930]": 1.4378e12}]}, bom=True)
    write_json(os.path.join(root, "indices_cn.json"),
               {"datas": [{"收盘价[20260930]": 3842.19}]}, bom=True)

    # 新鲜的宏观数据（用今天日期，确保不触发 STALE）
    from datetime import date
    today = date.today().strftime("%Y%m%d")
    write_json(os.path.join(root, "macro_she.json"),
               {"datas": [{"时间": today, "指标值": 4.42e14}]}, bom=True)
    write_json(os.path.join(root, "macro_cpi.json"),
               {"datas": [{"时间": today, "指标值": 0.8}]}, bom=True)
    write_json(os.path.join(root, "macro_m2.json"),
               {"datas": [{"时间": today, "指标值": 7.5}]}, bom=True)
    write_json(os.path.join(root, "macro_lpr.json"),
               {"datas": [{"时间": today, "指标值": 3.0}]}, bom=True)
    write_json(os.path.join(root, "macro_ppi.json"),
               {"datas": [{"时间": today, "指标值": -1.2}]}, bom=True)
    write_json(os.path.join(root, "macro_usdcny.json"),
               {"datas": [{"时间": today, "指标值": 7.1}]}, bom=True)
    write_json(os.path.join(root, "macro_global.json"),
               {"datas": [{"时间": today, "指标值": 4.2}]}, bom=True)
    write_json(os.path.join(root, "macro_assets.json"),
               {"datas": [{"时间": today, "指标值": 100.0}]}, bom=True)

    # 市场合计口径的北向资金
    write_json(os.path.join(root, "sentiment_north.json"),
               {"datas": [{"净买入额[20260930]": 1.2e9}]}, bom=True)


def level_of(rep, check_id):
    for r in rep.results:
        if r.check_id == check_id:
            return r.level
    return None


def result_of(rep, check_id):
    for r in rep.results:
        if r.check_id == check_id:
            return r
    return None


def main():
    print("\n[1] 正常数据不应误报")
    root = tempfile.mkdtemp(prefix="vf_ok_")
    try:
        base_fixture(root)
        rep = vf.run(root)
        s = rep.summary()
        check("无 CRITICAL", s["fail"] == 0, f"实际 fail={s['fail']}")
        check("无 STALE", s["stale"] == 0, f"实际 stale={s['stale']}")
        check("无 MISSING", s["missing"] == 0, f"实际 missing={s['missing']}")
        check("两融恒等式通过",
              level_of(rep, "margin.identity") == "PASS",
              f"实际={level_of(rep, 'margin.identity')}")
        check("环比一致性通过",
              level_of(rep, "margin.change_consistency") == "PASS",
              f"实际={level_of(rep, 'margin.change_consistency')}")
        check("两融/流通市值比例通过",
              level_of(rep, "margin.ratio") == "PASS",
              f"实际={level_of(rep, 'margin.ratio')}")
        check("北向口径正常识别",
              level_of(rep, "sentiment.north_scope") == "PASS",
              f"实际={level_of(rep, 'sentiment.north_scope')}")
        payload = vf.make_payload(rep, root)
        check("正常数据 report_allowed=true",
              payload["report_allowed"] is True,
              f"实际={payload['report_allowed']}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("\n[2] 负向测试: 复现 2026-09-30 的余额字段污染（37 倍偏差）")
    root = tempfile.mkdtemp(prefix="vf_bad_")
    try:
        base_fixture(root)
        # 09-30 实测: 融资余额字段约为真值一半，接口环比 -50.68%
        write_json(os.path.join(root, "margin_level.json"), {"datas": [{
            "融资余额[20260930]": 1_204_088_797_128.0,
            "融券余额[20260930]": 12_007_781_016.77,
            "两融余额[20260930]": 1_216_096_578_144.77,
            "流通市值[20260930]": 96_139_668_496_540.34,
            "融资净买入额[20260930]": -16_487_765_639.0,
        }]}, bom=True)
        write_json(os.path.join(root, "margin_change.json"), {"datas": [{
            "融资余额环比增长率[20260930]": -50.681605,
        }]}, bom=True)
        write_json(os.path.join(root, "margin_flow.json"), {"datas": [{
            "融资净买入额[20260930]": -16_487_765_639.0,
        }]}, bom=True)
        rep = vf.run(root)
        lvl = level_of(rep, "margin.change_consistency")
        check("矛盾口径被判为 CRITICAL", lvl == "CRITICAL", f"实际={lvl}")
        detail = result_of(rep, "margin.change_consistency")
        check("记录了倍数偏差", detail is not None and "37.0x" in detail.actual,
              f"实际={detail.actual if detail else None}")
        check("提示不要假定哪一方正确",
              detail is not None and "不要假定哪一个是对的" in detail.detail)
        # 同一份数据里，比例校验也应独立识别出余额字段异常
        ratio_lvl = level_of(rep, "margin.ratio")
        check("比例校验独立识别出余额污染", ratio_lvl == "CRITICAL",
              f"实际={ratio_lvl}")
        ratio_detail = result_of(rep, "margin.ratio")
        check("比例校验记录实际占比",
              ratio_detail is not None and "1.265%" in ratio_detail.actual,
              f"实际={ratio_detail.actual if ratio_detail else None}")
        check("summary 计入 fail", rep.summary()["fail"] == 2,
              f"实际={rep.summary()['fail']}")
        payload = vf.make_payload(rep, root)
        check("污染数据 report_allowed=false",
              payload["report_allowed"] is False,
              f"实际={payload['report_allowed']}")
        check("污染数据记录 blocking_reasons",
              len(payload["blocking_reasons"]) >= 2,
              f"实际={payload['blocking_reasons']}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("\n[3] 负向测试: 破坏两融恒等式")
    root = tempfile.mkdtemp(prefix="vf_ident_")
    try:
        base_fixture(root)
        # 只把两融余额抬高 5%（>1% 容差），其余保持正常，
        # 确保这一条只触发恒等式检查，不干扰比例检查
        write_json(os.path.join(root, "margin_level.json"), {"datas": [{
            "融资余额[20260930]": 2_390_776_445_326.0,
            "融券余额[20260930]": 21_841_413_119.0,
            "两融余额[20260930]": 2_533_248_751_367.0,  # 人为抬高 5%
            "流通市值[20260930]": 93_063_201_000_000.0,
            "融资净买入额[20260930]": -5_548_165_669.0,
        }]}, bom=True)
        rep = vf.run(root)
        lvl = level_of(rep, "margin.identity")
        check("恒等式破坏被判为 CRITICAL", lvl == "CRITICAL", f"实际={lvl}")
        check("比例检查未被干扰",
              level_of(rep, "margin.ratio") == "PASS",
              f"实际={level_of(rep, 'margin.ratio')}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("\n[4] 负向测试: 过期宏观数据应标记 STALE")
    root = tempfile.mkdtemp(prefix="vf_stale_")
    try:
        base_fixture(root)
        write_json(os.path.join(root, "macro_she.json"),
                   {"datas": [{"时间": "20251231", "指标值": 4.42e14}]}, bom=True)
        rep = vf.run(root)
        lvl = level_of(rep, "macro.macro_she.json")
        check("286 天前的数据标记 STALE", lvl == "STALE", f"实际={lvl}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("\n[5] 负向测试: 北向资金个股级口径应告警")
    root = tempfile.mkdtemp(prefix="vf_north_")
    try:
        base_fixture(root)
        write_json(os.path.join(root, "sentiment_north.json"), {"datas": [
            {"股票代码": "000560.SZ", "股票简称": "我爱我家",
             "净买入额合计值[20260930]": 1.2e8},
            {"股票代码": "000002.SZ", "股票简称": "万科A",
             "净买入额合计值[20260930]": 9.1e7},
        ]}, bom=True)
        rep = vf.run(root)
        lvl = level_of(rep, "sentiment.north_scope")
        check("个股级口径被判为 WARN", lvl == "WARN", f"实际={lvl}")
        r = result_of(rep, "sentiment.north_scope")
        check("提示了不得表述为全市场净买入",
              r is not None and "龙虎榜" in r.detail)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("\n[6] 边界: 关键文件缺失应报 CRITICAL")
    root = tempfile.mkdtemp(prefix="vf_missing_")
    try:
        # 只放一个文件，其余全部缺失
        write_json(os.path.join(root, "indices_cn.json"), {"datas": [{"a": 1}]})
        rep = vf.run(root)
        s = rep.summary()
        check("缺失文件产生 CRITICAL", s["fail"] >= 5, f"实际 fail={s['fail']}")
        check("margin_level 缺失被记录",
              level_of(rep, "file.margin_level.json") == "CRITICAL")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("\n[7] 边界: 带 BOM 的文件能被正确解析")
    root = tempfile.mkdtemp(prefix="vf_bom_")
    try:
        base_fixture(root)  # base_fixture 全部用 bom=True 写入
        rep = vf.run(root)
        raw = open(os.path.join(root, "margin_level.json"), "rb").read(3)
        check("fixture 确实带 BOM", raw == b"\xef\xbb\xbf", f"实际前3字节={raw!r}")
        check("BOM 文件解析成功",
              level_of(rep, "file.margin_level.json") == "PASS",
              f"实际={level_of(rep, 'file.margin_level.json')}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("\n[8] 边界: 污染文件（非 JSON）应报 CRITICAL 而非静默通过")
    root = tempfile.mkdtemp(prefix="vf_pollute_")
    try:
        base_fixture(root)
        with open(os.path.join(root, "margin_flow.json"), "w", encoding="utf-8") as fh:
            fh.write("Traceback (most recent call last):\n  Error: API quota exceeded\n")
        rep = vf.run(root)
        lvl = level_of(rep, "file.margin_flow.json")
        check("被错误信息污染的文件判为 CRITICAL", lvl == "CRITICAL", f"实际={lvl}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("\n[9] 负向测试: 市场类文件跨交易日错配")
    root = tempfile.mkdtemp(prefix="vf_dates_")
    try:
        base_fixture(root)
        write_json(
            os.path.join(root, "market_turnover.json"),
            {"datas": [{"成交额[20200101]": 1.0e12}]},
            bom=True,
        )
        rep = vf.run(root)
        lvl = level_of(rep, "market.date_consistency")
        check("跨 6 年日期错配判为 CRITICAL", lvl == "CRITICAL", f"实际={lvl}")
        check(
            "日期错配使 report_allowed=false",
            vf.make_payload(rep, root)["report_allowed"] is False,
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(f"\n===== RESULT: {PASS} passed, {FAIL} failed =====")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
