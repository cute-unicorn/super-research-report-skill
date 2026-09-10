"""从 Markdown 研报中提取结构化数据。

设计要点：
- 全文档扫描，不设行数上限。早期版本用 `splitlines()[:N]` 做微优化，
  导致报告内容一变（数据出现在第 N 行之后）就静默失效。
- 标签匹配容忍中英文冒号、空格、全角符号等格式差异。
- `diagnose()` 汇报哪些字段没取到，把静默失败变成显式提示。
"""

import datetime
import os
import re

from .textutil import pnum


def _lines(text):
    return text.splitlines()


# 数值 + 单位（万亿/亿/万/%），符号可选
_AMOUNT = r"([+\-]?[\d,]+(?:\.\d+)?)\s*(万亿|亿|万|%)?"


def _label_amount(text, labels):
    """按标签找首个数值，兼容 '标签：值' / '标签 值' / '标签值为值'。"""
    for line in _lines(text):
        for label in labels:
            # 容忍 "约"、"为"、"：" 等连接词
            m = re.search(re.escape(label) + r"[：:值为\s约]*" + _AMOUNT, line)
            if m:
                return pnum(m.group(1) + (m.group(2) or ""))
    return None


def _to_abs(num, unit):
    scale = {"万亿": 1e12, "亿": 1e8, "万": 1e4, "%": 1.0}.get(unit, 1.0)
    try:
        return float(str(num).replace(",", "")) * scale
    except (TypeError, ValueError):
        return None


# ---------------- 指数 ----------------
_INDEX_NAMES = ("上证指数", "深证成指", "创业板指", "沪深300")


def ext_idx(text):
    ret, seen = [], {}
    for line in _lines(text):
        for name in _INDEX_NAMES:
            if name in seen:
                continue
            m = re.search(re.escape(name) + r".*?([+\-]?\d+\.?\d*)\s*%", line)
            if m:
                try:
                    seen[name] = len(ret)
                    ret.append({"n": name, "v": float(m.group(1)), "p": ""})
                except ValueError:
                    pass
    # 点位
    for line in _lines(text):
        for name in _INDEX_NAMES:
            if name in seen:
                m = re.search(re.escape(name) + r"[：:]\s*([\d,]+\.?\d*)", line)
                if m and not ret[seen[name]]["p"]:
                    ret[seen[name]]["p"] = m.group(1)
    return ret


# ---------------- 市场宽度 ----------------
_BREADTH_KEYS = [
    ("up", ("上涨家数",)),
    ("down", ("下跌家数",)),
    ("lu", ("涨停家数",)),
    ("ld", ("跌停家数",)),
]


def ext_brd(text):
    r = {"up": None, "down": None, "lu": None, "ld": None, "to": None}
    for key, labels in _BREADTH_KEYS:
        v = _label_amount(text, labels)
        if v is not None:
            r[key] = int(round(v))
    to = _label_amount(text, ("成交额", "两市成交额"))
    if to is not None:
        r["to"] = to
    return r


# ---------------- 行业 ----------------
_SEC_HEAD = re.compile(r"^#{1,4}.*?(行业与风格|领涨|涨幅榜|涨居前|领跌|行业)")
_BULLET_PCT = re.compile(r"^[-*]\s+(.+?)\s*([+\-]?\d+\.?\d*)\s*%")
_NUM_PCT = re.compile(r"^\s*\d+[.、]\s+(.+?)\s*([+\-]?\d+\.?\d*)\s*%")


def ext_sec(text, limit=24):
    ret, on = [], False
    for line in _lines(text):
        if _SEC_HEAD.search(line):
            on = True
            continue
        if on and re.match(r"^#{1,4}\s", line) and ret:
            break
        if not on:
            continue
        for m in (_BULLET_PCT.match(line), _NUM_PCT.match(line)):
            if m:
                try:
                    name = m.group(1).strip().split("：")[0].split(":")[0][:14]
                    ret.append({"n": name, "v": float(m.group(2))})
                except ValueError:
                    pass
                break
    return ret[:limit]


# ---------------- 两融 ----------------
def ext_mgn(text):
    return {
        "bal": _label_amount(text, ("两融余额", "融资融券余额")),
        "fin": _label_amount(text, ("融资余额",)),
        "sec": _label_amount(text, ("融券余额",)),
        "net": _label_amount(text, ("融资净买入", "融资净买入额")),
        "chg": _label_amount(text, ("融资余额环比增长率", "融资余额环比", "环比")),
    }


# ---------------- 个股 ----------------
def ext_stock(text):
    d = {k: None for k in (
        "price", "mcap", "pe", "pe_ttm", "pb", "div", "rev", "rev_chg",
        "profit_chg", "margin", "roe", "debt", "chip_pct", "chip_avg",
        "c90lo", "c90hi", "c70lo", "c70hi", "ma20", "ma60", "rsi")}
    d["rating"] = ""
    d["target"] = ""

    def first(pats, cast=float, key=None):
        for line in _lines(text):
            for pat in pats:
                m = re.search(pat, line)
                if m:
                    try:
                        return cast(m.group(1))
                    except (ValueError, TypeError):
                        pass
        return None

    d["rating"] = first([r"客观评级[：:]\s*([^（(\n]+)"], str) or ""
    m = re.search(r"目标区间\s*([\d.]+)\s*[-~至]\s*([\d.]+)", text)
    if m:
        d["target"] = f"{m.group(1)}-{m.group(2)}"

    d["price"] = _label_amount(text, ("收盘价", "收盘", "现价", "最新价"))
    d["mcap"] = _label_amount(text, ("总市值",))
    d["pe_ttm"] = first([r"PE\s*TTM\s*([\d.]+)"])
    d["pe"] = d["pe_ttm"]
    d["pb"] = first([r"PB\s*([\d.]+)"])
    d["div"] = first([r"股息率[^%\d]*([\d.]+)\s*%"])
    d["rev"] = _label_amount(text, ("营业收入", "营收"))
    # 优先取括号内的同比（如 "营收 17.10 亿（-21.05%）"），再回退到裸百分比
    d["rev_chg"] = first([
        r"营(?:业)?收(?:入)?[^（(\n]*[（(]([+\-]?\d+\.?\d*)\s*%",
        r"营业收入同比增长率[^%\d]*([+\-]?\d+\.?\d*)\s*%",
        r"营收[^%\d]*([+\-]?\d+\.?\d*)\s*%",
    ])
    d["profit_chg"] = first([
        r"归母[^（(\n]*[（(]([+\-]?\d+\.?\d*)\s*%",
        r"归母净利润同比增长率[^%\d]*([+\-]?\d+\.?\d*)\s*%",
        r"归母[^%\d]*([+\-]?\d+\.?\d*)\s*%",
    ])
    d["margin"] = first([r"毛利率\s*([\d.]+)\s*%"])
    d["roe"] = first([r"ROE\s*[（(]?\s*([+\-]?[\d.]+)\s*%"])
    d["debt"] = first([r"负债率\s*([\d.]+)\s*%"])
    d["chip_pct"] = first([r"获利盘\s*([\d.]+)\s*%"])
    d["chip_avg"] = first([r"平均成本\s*([\d.]+)"])
    m = re.search(r"90%\s*成本区间\s*约?\s*([\d.]+)\s*[至\-~]+\s*([\d.]+)", text)
    if m:
        d["c90lo"], d["c90hi"] = float(m.group(1)), float(m.group(2))
    m = re.search(r"70%\s*成本区间\s*约?\s*([\d.]+)\s*[至\-~]+\s*([\d.]+)", text)
    if m:
        d["c70lo"], d["c70hi"] = float(m.group(1)), float(m.group(2))
    d["ma20"] = first([r"MA20\s*[约为]?\s*([\d.]+)"])
    d["ma60"] = first([r"MA60\s*[约为]?\s*([\d.]+)"])
    d["rsi"] = first([r"RSI\s*[约为]?\s*([\d.]+)"])
    return d


# ---------------- 宏观 / 海外 ----------------
_MACRO_KEYS = [
    ("cpi", ("中国CPI同比", "CPI同比增长率", "CPI")),
    ("ppi", ("PPI",)),
    ("m2", ("M2同比增速", "M2",)),
    ("she", ("社会融资规模存量", "社融")),
    ("lpr", ("LPR",)),
    ("usdcny", ("美元兑人民币汇率", "美元兑人民币")),
]


def ext_macro(text):
    r = {}
    for key, labels in _MACRO_KEYS:
        v = _label_amount(text, labels)
        if v is not None:
            r[key] = v
    return r


_OVERSEAS_KEYS = [
    ("nasdaq", ("纳斯达克",)),
    ("dow", ("道琼斯",)),
    ("sp500", ("标普500", "标普")),
    ("hsi", ("恒生指数",)),
    ("gold", ("黄金", "伦敦现货黄金")),
    ("oil", ("布伦特原油", "原油")),
    ("btc", ("比特币",)),
]


def ext_overseas(text):
    r = {}
    for key, labels in _OVERSEAS_KEYS:
        for line in _lines(text):
            for label in labels:
                m = re.search(re.escape(label) + r".*?([+\-]?\d+\.?\d*)\s*%", line)
                if m:
                    try:
                        r[key] = float(m.group(1))
                    except ValueError:
                        pass
                    break
            if key in r:
                break
    return r


# ---------------- 资金流 ----------------
_FLOW_PATS = [
    (r"主力.*?净流入.*?([+\-]?[\d.,]+)\s*(亿|万)", "main", 1),
    (r"主力.*?净流出.*?([\d.,]+)\s*(亿|万)", "main", -1),
    (r"主力净买入[：:]?\s*([+\-]?[\d.,]+)\s*(亿|万)", "main", 1),
    (r"超大单.*?净流入.*?([+\-]?[\d.,]+)\s*(亿|万)", "xl", 1),
    (r"超大单.*?净流出.*?([\d.,]+)\s*(亿|万)", "xl", -1),
    (r"超大单净买入[：:]?\s*([+\-]?[\d.,]+)\s*(亿|万)", "xl", 1),
]


def ext_fundflow(text):
    r = {}
    for line in _lines(text):
        for pat, key, sign in _FLOW_PATS:
            if key in r:
                continue
            m = re.search(pat, line)
            if m:
                raw = m.group(1).replace(",", "").lstrip("+-")
                try:
                    val = float(raw) * (1e8 if m.group(2) == "亿" else 1e4)
                except ValueError:
                    continue
                if m.group(1).startswith("-"):
                    sign = -1
                r[key] = sign * val
    return r


# ---------------- 两融趋势（表格） ----------------
_TREND_ROW = re.compile(
    r"(\d{2}-\d{2})\s*[|│]?\s*([\d.]+)\s*亿\s*[|│]?\s*([\d.]+)\s*万亿")


def ext_margin_trend(text):
    pts = []
    for line in _lines(text):
        m = _TREND_ROW.search(line)
        if m:
            try:
                pts.append({"date": m.group(1),
                            "sec": float(m.group(2)),
                            "fin": float(m.group(3))})
            except ValueError:
                pass
    return pts


# ---------------- 元信息 ----------------
def ext_title(text, path):
    for line in _lines(text):
        m = re.match(r"^#\s+(.+)$", line)
        if m:
            return m.group(1).strip()
    return re.sub(r"\.md$", "", os.path.basename(path), flags=re.I)


def ext_date(path):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
    return m.group(1) if m else datetime.date.today().isoformat()


def ext_badges(text, path):
    name = os.path.basename(path)
    badges = ["A股"]
    if "客观评级" in text or "深度研报" in name:
        badges.append("个股深度")
    elif "深度分析与标的策略" in name:
        badges.append("每日·深度版")
    else:
        badges.append("每日·基础版")
    if "两融" in text:
        badges.append("两融")
    if "非共识" in text:
        badges.append("α")
    return badges


def ext_toc(text):
    toc, in_code, sec = [], False, 0
    for line in _lines(text):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            sec += 1
            toc.append((len(m.group(1)), m.group(2).strip(), f"sec-{sec}"))
    return toc


# ---------------- 诊断 ----------------
def is_stock_report(text):
    head = text[:1200]
    return "客观评级" in head or "核心判断" in head


def extract_for(text, path):
    """按报告类型抽取，返回 (kind, data)。"""
    if is_stock_report(text):
        return "stock", ext_stock(text)
    return "daily", {
        "idx": ext_idx(text),
        "brd": ext_brd(text),
        "sec": ext_sec(text),
        "mgn": ext_mgn(text),
        "macro": ext_macro(text),
        "overseas": ext_overseas(text),
        "trend": ext_margin_trend(text),
        "flow": ext_fundflow(text),
    }


def diagnose(kind, data):
    """返回未取到的字段列表，用于把静默失败变成显式提示。"""
    missing = []
    if kind == "stock":
        for key, val in data.items():
            if val in (None, "", [], {}):
                missing.append(f"stock.{key}")
    else:
        for key, val in data.items():
            if isinstance(val, dict):
                for sub, sv in val.items():
                    if sv in (None, "", [], {}):
                        missing.append(f"{key}.{sub}")
            elif not val:
                missing.append(key)
    return missing
