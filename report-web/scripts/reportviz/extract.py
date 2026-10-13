"""从 Markdown 研报中提取结构化数据。

设计要点：
- 全文档扫描，不设行数上限。早期版本用 `splitlines()[:N]` 做微优化，
  导致报告内容一变（数据出现在第 N 行之后）就静默失效。
- 标签匹配容忍中英文冒号、空格、全角符号等格式差异。
- `diagnose()` 汇报哪些字段没取到，把静默失败变成显式提示。
"""

import datetime
import json
import os
import re

from .textutil import pnum


def _lines(text):
    return text.splitlines()


# 数值 + 单位（万亿/亿/万/%），符号可选
_AMOUNT = r"([+\-]?[\d,]+(?:\.\d+)?)\s*(万亿|亿|万|%)?"


def _label_amount(text, labels):
    """按标签找首个数值。

    标签与数值之间允许少量修饰词（：/ 约 / 同比 / 增速 等），
    但不得跨越数字或句号，避免匹配到相邻指标。
    优先在表格行中匹配（数值更精确），再回退到正文。
    """
    lines = _lines(text)
    table_lines = [l for l in lines if l.lstrip().startswith("|")]
    # (?![日月周年]) 防止把 "5日" "2026年" 这类期间引用当成数值
    pat_tail = re.compile(r"(?![日月周年])")
    for pool in (table_lines, lines):
        for line in pool:
            for label in labels:
                m = re.search(re.escape(label) + r"[^\d+\-。\n]{0,10}" + _AMOUNT, line)
                if not m:
                    continue
                end = m.end()
                if end < len(line) and line[end] in "日月周年":
                    continue
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
_SEC_MARK = re.compile(r"(行业与风格|领涨行业|领跌行业|涨幅榜|跌幅榜|涨居前)")
_BULLET_PCT = re.compile(r"^[-*]\s+(.+?)\s*([+\-]?\d+\.?\d*)\s*%")
_NUM_PCT = re.compile(r"^\s*\d+[.、]\s+(.+?)\s*([+\-]?\d+\.?\d*)\s*%")
_ANY_PCT = re.compile(r"([+\-]?\d+\.?\d*)\s*%")


def _is_sec_marker(line):
    """判断一行是否为行业段落的起始标记。

    必须避免误匹配正文（例：α 标题里的"从领涨到领跌"），因此要求
    要么是 Markdown 标题，要么是短标签行。
    """
    s = line.strip()
    if "非共识" in s or "观点" in s:
        return False
    if not _SEC_MARK.search(s):
        return False
    if s.startswith("#"):
        return True
    plain = s.strip("*：: ").strip()
    return len(plain) <= 14


def _table_sector(line):
    """从 Markdown 表格行提取 (行业名, 涨跌幅)。"""
    s = line.strip()
    if not s.startswith("|"):
        return None
    cells = [c.strip().strip("*` ") for c in s.strip("|").split("|")]
    if len(cells) < 2:
        return None
    for index, cell in enumerate(cells):
        match = _ANY_PCT.search(cell)
        if not match:
            continue
        name = cells[index - 1] if index > 0 else cells[0]
        name = name.strip()
        if not name or name in {"行业", "板块", "名称", "涨跌幅", "指标"}:
            continue
        try:
            return name[:14], float(match.group(1))
        except ValueError:
            return None
    return None


def ext_sec(text, limit=24):
    """提取行业涨跌幅。

    不依赖标题语法（## / 纯文本 / 加粗均可），改为定位"领涨/领跌"标记后
    解析紧随其后的项目符号列表，遇到非列表内容即停止。
    """
    lines = _lines(text)
    ret = []
    i = 0
    while i < len(lines):
        if not _is_sec_marker(lines[i]):
            i += 1
            continue
        j = i + 1
        while j < len(lines):
            s = lines[j].strip()
            if not s:
                j += 1
                continue
            if s.startswith("#"):
                break
            m = _BULLET_PCT.match(lines[j]) or _NUM_PCT.match(lines[j])
            if m:
                try:
                    name = m.group(1).strip().split("：")[0].split(":")[0][:14]
                    ret.append({"n": name, "v": float(m.group(2))})
                except ValueError:
                    pass
                j += 1
                continue
            table_item = _table_sector(lines[j])
            if table_item:
                ret.append({"n": table_item[0], "v": table_item[1]})
                j += 1
                continue
            j += 1
        i = j

    seen, out = set(), []
    for item in ret:
        if item["n"] not in seen:
            seen.add(item["n"])
            out.append(item)
    return out[:limit]


def _suffixed_value(row, prefix):
    """读取精确字段或带日期后缀的最新字段。"""
    if prefix in row:
        return row.get(prefix)
    values = []
    for key, value in row.items():
        if key == prefix or key.startswith(prefix + "["):
            values.append((key, value))
    if not values:
        return None
    values.sort(key=lambda item: item[0])
    return values[-1][1]


def ext_sec_from_data(data_dir, limit=24):
    """从 industry_top/bottom.json 补全行业热力图数据。"""
    if not data_dir or not os.path.isdir(data_dir):
        return []
    rows = []
    for filename in ("industry_top.json", "industry_bottom.json"):
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                payload = json.load(handle)
        except Exception:
            continue
        for row in payload.get("datas", []):
            if not isinstance(row, dict):
                continue
            name = row.get("指数简称") or row.get("行业名称") or row.get("板块名称")
            value = _suffixed_value(row, "涨跌幅")
            if value is None:
                value = _suffixed_value(row, "跌幅")
                if value is not None:
                    value = -abs(pnum(value))
            number = pnum(value)
            if name and number is not None:
                rows.append({"n": str(name)[:14], "v": number})

    seen, out = set(), []
    for item in rows:
        if item["n"] not in seen:
            seen.add(item["n"])
            out.append(item)
    return out[:limit]


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

    # 表格/加粗写法下，标签与数值间会夹着 "|"、"**" 等符号。
    # _SEP 必须排除数字与正负号，否则会把 "-4.11" 的负号吃掉。
    _SEP = r"[^\d+\-\n。]{0,14}"
    # 区间连接符：至 / - / ~ / – / —
    _DASH = r"[至\-~–—]+"

    def val(pats):
        """在 _SEP 容忍下取首个数值。"""
        for line in _lines(text):
            for lab in pats:
                m = re.search(re.escape(lab) + _SEP + r"([+\-]?[\d,]+(?:\.\d+)?)", line)
                if m:
                    try:
                        return float(m.group(1).replace(",", ""))
                    except ValueError:
                        pass
        return None

    d["rating"] = first([r"客观评级[：:]\s*([^（(\n]+)"], str) or ""
    m = re.search(r"目标区间\s*([\d.]+)\s*[-~至]\s*([\d.]+)", text)
    if m:
        d["target"] = f"{m.group(1)}-{m.group(2)}"

    d["price"] = _label_amount(text, ("收盘价", "收盘", "现价", "最新价"))
    d["mcap"] = _label_amount(text, ("总市值",))
    d["pe_ttm"] = val(["PE TTM", "市盈率ttm", "市盈率(TTM)", "PE(TTM)"])
    d["pe"] = d["pe_ttm"]
    d["pb"] = val(["PB"])
    d["div"] = val(["股息率"])
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
    d["margin"] = val(["毛利率"])
    d["roe"] = val(["ROE"])
    d["debt"] = val(["负债率", "资产负债率"])
    d["chip_pct"] = val(["获利盘", "收盘获利"])
    d["chip_avg"] = val(["平均成本"])
    m = re.search(r"90%\s*成本区间" + _SEP + r"([\d.]+)\s*" + _DASH + r"\s*([\d.]+)", text)
    if m:
        d["c90lo"], d["c90hi"] = float(m.group(1)), float(m.group(2))
    m = re.search(r"70%\s*成本区间" + _SEP + r"([\d.]+)\s*" + _DASH + r"\s*([\d.]+)", text)
    if m:
        d["c70lo"], d["c70hi"] = float(m.group(1)), float(m.group(2))
    d["ma20"] = val(["20日MA", "MA20"])
    d["ma60"] = val(["60日MA", "MA60"])
    d["rsi"] = val(["RSI"])
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
    (r"大户.*?净流入\s*约?\s*([+\-]?[\d.,]+)\s*(亿|万)", "large", 1),
    (r"大户.*?净流出\s*约?\s*([\d.,]+)\s*(亿|万)", "large", -1),
    (r"散户.*?净流入\s*约?\s*([+\-]?[\d.,]+)\s*(亿|万)", "retail", 1),
    (r"散户.*?净流出\s*约?\s*([\d.,]+)\s*(亿|万)", "retail", -1),
]


def ext_fundflow(text):
    lines = _lines(text)
    section_lines = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("#") and ("资金分析" in s or "资金结构" in s):
            section_lines = []
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("## "):
                    break
                section_lines.append(lines[j])
            break
    pool = section_lines if section_lines is not None else lines

    r = {}
    # 优先解析资金结构表，避免正文中的板块资金流入被误当成市场主力资金。
    for line in pool:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip().strip("*` ") for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        label, amount = cells[0], cells[1]
        if not amount or amount in {"—", "-", "--"}:
            continue
        value = pnum(amount)
        if value is None:
            continue
        key = None
        if "主力" in label:
            key = "main"
        elif "机构" in label or "超大单" in label:
            key = "xl"
        elif "大户" in label or "大单" in label:
            key = "large"
        elif "散户" in label or "中单+小单" in label:
            key = "retail"
        if key and key not in r:
            r[key] = value

    for line in pool:
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
def is_stock_report(text, path=None):
    """优先按文件名分类，避免深度日报中的“核心判断”导致误判。"""
    name = os.path.basename(path or "")
    if "每日市场研报" in name or "深度分析与标的策略" in name:
        return False
    if "深度研报" in name:
        return True
    head = text[:1200]
    return "客观评级" in head or "核心判断" in head


def extract_for(text, path, data_dir=None):
    """按报告类型抽取，返回 (kind, data)。"""
    if is_stock_report(text, path):
        return "stock", ext_stock(text)
    data = {
        "idx": ext_idx(text),
        "brd": ext_brd(text),
        "sec": ext_sec(text),
        "mgn": ext_mgn(text),
        "macro": ext_macro(text),
        "overseas": ext_overseas(text),
        "trend": ext_margin_trend(text),
        "flow": ext_fundflow(text),
    }
    if not data["sec"]:
        data["sec"] = ext_sec_from_data(data_dir)
    return "daily", data


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
