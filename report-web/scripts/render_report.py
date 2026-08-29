#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""炫酷网页版研报渲染器 | 零依赖 | 玻璃拟态 | 自动可视化"""
import argparse, datetime, html, os, re, sys

def esc(t): return html.escape(t, quote=True)
_CS = re.compile(r"`([^`]+)`")

def _inl(t):
    t = esc(t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{esc(m.group(2))}">{m.group(1)}</a>', t)
    return t

def r_inline(t):
    parts, pos = [], 0
    for m in _CS.finditer(t):
        parts.append(_inl(t[pos:m.start()])); parts.append(f"<code>{esc(m.group(1))}</code>"); pos = m.end()
    parts.append(_inl(t[pos:])); return "".join(parts)

_NUM = re.compile(r"([+\-]?)\s*([\d][\d,]*(?:\.\d+)?)\s*(万亿|亿|万|%)?")
_UNIT = re.compile(r"(万亿|亿|万|%)")

def _pnum(v):
    m = _NUM.search(v.strip())
    if not m: return None
    s = -1.0 if m.group(1) == "-" else 1.0
    return s * float(m.group(2).replace(",", "")) * {"万亿":1e12,"亿":1e8,"万":1e4,"%":1.0}.get(m.group(3),1.0)

def _unit(v):
    m = _UNIT.search(v.strip()); return m.group(1) if m else ""

def _fmt(v, uh=""):
    if v is None: return "—"
    a = abs(v)
    if uh == "%": return f"{v:+.2f}%"
    if a >= 1e12: return f"{v/1e12:.2f}万亿"
    if a >= 1e8: return f"{v/1e8:.2f}亿"
    if a >= 1e4: return f"{v/1e4:.1f}万"
    return f"{int(v)}" if v == int(v) else f"{v:.2f}"

def _vcls(v):
    if v is None: return ""
    return "up" if v > 0 else ("down" if v < 0 else "flat")

def ext_idx(text):
    ret, seen = [], set()
    pats = [(r"上证指数.*?([+\-]?\d+\.?\d*)%","上证指数"),(r"深证成指.*?([+\-]?\d+\.?\d*)%","深证成指"),(r"创业板指.*?([+\-]?\d+\.?\d*)%","创业板指"),(r"沪深300.*?([+\-]?\d+\.?\d*)%","沪深300")]
    for line in text.splitlines()[:60]:
        for p, n in pats:
            m = re.search(p, line)
            if m and n not in seen:
                try: seen.add(n); ret.append({"n":n,"v":float(m.group(1)),"p":""})
                except: pass
    for line in text.splitlines()[:60]:
        for p, n in [(r"上证指数[：:]\s*([\d,.]+)","上证指数"),(r"深证成指[：:]\s*([\d,.]+)","深证成指"),(r"创业板指[：:]\s*([\d,.]+)","创业板指"),(r"沪深300[：:]\s*([\d,.]+)","沪深300")]:
            m = re.search(p, line)
            if m:
                for i in ret:
                    if i["n"] == n: i["p"] = m.group(1); break
    return ret

def ext_brd(text):
    r = {"up":None,"down":None,"lu":None,"ld":None,"to":None}
    for line in text.splitlines()[:300]:
        for k, p in [("up",r"上涨家数[：:]\s*([\d,]+)"),("down",r"下跌家数[：:]\s*([\d,]+)"),("lu",r"涨停家数[：:]\s*([\d,]+)"),("ld",r"跌停家数[：:]\s*([\d,]+)")]:
            m = re.search(p, line)
            if m: r[k] = int(m.group(1).replace(",",""))
        m = re.search(r"成交额[：:]\s*约?\s*([\d.]+)\s*(万亿|亿)", line)
        if m: r["to"] = float(m.group(1)) * (1e12 if m.group(2)=="万亿" else 1e8)
    return r

def ext_sec(text):
    ret, on = [], False
    for line in text.splitlines():
        if re.search(r"^#{1,3}.*?(行业与风格|领涨|涨幅|涨居前|领跌)", line): on = True; continue
        if re.search(r"^#{1,3}\s*", line) and on and ret: break
        if on:
            for m in [re.match(r"^[-*]\s+(.+?)\s*([+\-]?\d+\.?\d*)%", line), re.match(r"^\s*\d+[.、]\s+(.+?)\s*([+\-]?\d+\.?\d*)%", line)]:
                if m:
                    try: ret.append({"n":m.group(1).strip().split("：")[0][:14],"v":float(m.group(2))})
                    except: pass
    return ret[:16]

def ext_mgn(text):
    r = {"bal":None,"fin":None,"sec":None,"net":None,"chg":None}
    for line in text.splitlines()[:200]:
        for k, p in [("bal",r"两融余额[：:]?\s*([\d.,]+)\s*(万亿|亿)"),("fin",r"融资余额[：:]?\s*([\d.,]+)\s*(万亿|亿)"),("sec",r"融券余额[：:]?\s*([\d.,]+)\s*(万亿|亿)")]:
            m = re.search(p, line)
            if m and r[k] is None: r[k] = float(m.group(1).replace(",","")) * (1e12 if m.group(2)=="万亿" else 1e8)
        m = re.search(r"融资净买入[：:]?\s*([+\-]?[\d.,]+)\s*(万亿|亿)", line)
        if m and r["net"] is None: r["net"] = (-1 if m.group(1).startswith("-") else 1) * float(m.group(1).lstrip("+-").replace(",","")) * (1e12 if m.group(2)=="万亿" else 1e8)
        m = re.search(r"环比.*?([+\-]?\d+\.?\d*)%", line)
        if m and r["chg"] is None:
            try: r["chg"] = float(m.group(1))
            except: pass
    return r

def ext_title(text, path):
    for l in text.splitlines():
        m = re.match(r"^#\s+(.+)$", l)
        if m: return m.group(1).strip()
    return re.sub(r"\.md$","",os.path.basename(path),flags=re.I)

def ext_date(path):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
    return m.group(1) if m else datetime.date.today().isoformat()

def ext_badges(text, path):
    n = os.path.basename(path); b = ["A股"]
    if "客观评级" in text or "深度研报" in n: b.append("个股深度")
    elif "深度分析与标的策略" in n: b.append("每日·深度版")
    else: b.append("每日·基础版")
    if "两融" in text: b.append("两融")
    if "非共识" in text: b.append("α")
    return b

def ext_toc(text):
    toc, code, sec = [], False, 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("```"): code = not code; continue
        if code: continue
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m: sec += 1; toc.append((len(m.group(1)), m.group(2).strip(), f"sec-{sec}"))
    return toc


# ================ 块级渲染 ================
class Ctx:
    def __init__(self): self.toc, self.sec = [], 0

def _break(line):
    s = line.lstrip()
    return (s.startswith("#") or s.startswith("|") or s.startswith(">") or s.startswith("```")
        or bool(re.match(r"^\s*[-*+]\s+", line)) or bool(re.match(r"^\s*\d+[.、]\s+", line))
        or bool(re.match(r"^\s*([-*_])\s*(\1\s*){2,}$", line)))

def _li_kv(t):
    m = re.match(r"^(.+?)[：:]\s*(.+)$", t)
    if m and re.search(r"\d", m.group(2)):
        k = r_inline(m.group(1).strip()); v = r_inline(m.group(2).strip())
        c = _vcls(_pnum(m.group(2)))
        return f'<span class="kv-k">{k}</span><span class="kv-v {c}">{v}</span>'
    return _r_inline_hl(t)

def _split_row(l):
    l = l.strip()
    if l.startswith("|"): l = l[1:]
    if l.endswith("|"): l = l[:-1]
    return [c.strip() for c in l.split("|")]

def render_blocks(lines, ctx, top=True):
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i].rstrip("\n"); s = line.lstrip()
        if s.startswith("```"):
            buf = []; i += 1
            while i < n and not lines[i].startswith("```"): buf.append(lines[i].rstrip("\n")); i += 1
            i += 1
            out.append(f"<pre><code>{esc(chr(10).join(buf))}</code></pre>"); continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1)); title = m.group(2).strip()
            ctx.sec += 1; anc = f"sec-{ctx.sec}"
            if top: ctx.toc.append((lvl, title, anc))
            out.append(f'<h{lvl} id="{anc}">{r_inline(title)}</h{lvl}>'); i += 1; continue
        if s.startswith("|") and i + 1 < n and re.match(r"^\s*\|?[\s:\-|]+\|?\s*$", lines[i+1]):
            hdr = _split_row(line); i += 2; body = []
            while i < n and lines[i].lstrip().startswith("|"): body.append(_split_row(lines[i])); i += 1
            out.append(_table(hdr, body)); continue
        if re.match(r"^\s*([-*_])\s*(\1\s*){2,}$", line): out.append("<hr>"); i += 1; continue
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].startswith(">"): buf.append(lines[i][1:].lstrip()); i += 1
            out.append("<blockquote>" + render_blocks(buf, ctx, False) + "</blockquote>"); continue
        if re.match(r"^\s*[-*+]\s+", line):
            items = []
            while i < n and re.match(r"^\s*[-*+]\s+", lines[i]): items.append(re.sub(r"^\s*[-*+]\s+","",lines[i].rstrip("\n"))); i += 1
            out.append("<ul>" + "".join(f"<li>{_li_kv(it)}</li>" for it in items) + "</ul>"); continue
        if re.match(r"^\s*\d+[.、]\s+", line):
            items = []
            while i < n and re.match(r"^\s*\d+[.、]\s+", lines[i]): items.append(re.sub(r"^\s*\d+[.、]\s+","",lines[i].rstrip("\n"))); i += 1
            out.append("<ol>" + "".join(f"<li>{_li_kv(it)}</li>" for it in items) + "</ol>"); continue
        buf = [line]; i += 1
        while i < n and lines[i].strip() and not _break(lines[i]): buf.append(lines[i].rstrip("\n")); i += 1
        out.append("<p>" + _r_inline_hl(" ".join(x.strip() for x in buf if x.strip())) + "</p>")
    return "\n".join(out)


# ================ 表格 + SVG 图表 ================
def _table(hdr, body):
    if not hdr: return ""
    th = "".join(f"<th>{r_inline(c)}</th>" for c in hdr)
    rows = []
    for r in body:
        cs = (r + [""] * len(hdr))[:len(hdr)]
        rows.append("<tr>" + "".join(f"<td>{r_inline(c)}</td>" for c in cs) + "</tr>")
    tbl = f"<div class='tw'><table><thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    return tbl + _chart(hdr, body)

def _chart(hdr, body):
    ncols = len(hdr)
    ncs = []
    for c in range(ncols):
        vals, us = [], set()
        for r in body:
            if c < len(r): vals.append(_pnum(r[c])); us.add(_unit(r[c]))
        ok = [v for v in vals if v is not None]
        if len(ok) >= max(2, int(len(vals)*0.7)) and len(us) == 1: ncs.append(c)
    if not ncs: return ""
    c = ncs[-1]; items = []
    for r in body:
        v = _pnum(r[c]) if c < len(r) else None
        lbl = r[0].strip()[:14] if r else ""
        if v is not None and lbl: items.append((lbl, v))
    if len(items) < 2: return ""
    mx = max(abs(v) for _, v in items) or 1
    w, rh, bh, pd = 560, 36, 20, 150
    h = len(items) * rh + 24
    svg = [f'<svg class="cchart" viewBox="0 0 {w} {h}">']
    for idx, (lbl, v) in enumerate(items):
        y = 20 + idx * rh; bw = max(6, abs(v)/mx*(w-pd-48))
        col = "#ef4444" if v >= 0 else "#22c55e"
        svg.append(f'<text class="cl" x="8" y="{y+14}">{esc(lbl)}</text>')
        svg.append(f'<rect class="cbar" x="{pd}" y="{y}" width="{bw:.1f}" height="{bh}" rx="4" fill="{col}"/>')
        svg.append(f'<text class="cv" x="{pd+bw+8:.0f}" y="{y+14}">{esc(_fmt(v))}</text>')
    svg.append("</svg>")
    return f'<div class="tc"><div class="tc-t">自动图表 · {esc(hdr[c].strip())}</div>{"".join(svg)}</div>'


# ================ 仪表盘 SVG ================
def _gauge(value, label, unit, color, radius=70):
    """半圆仪表盘"""
    cx, cy = 100, 95
    if value is None: value = 0
    pct = max(0, min(1, abs(value) / 100))
    angle = 180 * pct
    end_x = cx + radius * -1 * (1 if value < 0 else 1) * (1 - pct) if False else cx + radius * (1 - 2*pct) if value < 0 else cx + radius * pct * 2 - radius
    import math
    ex = cx + radius * math.cos(math.radians(180 - angle))
    ey = cy - radius * math.sin(math.radians(180 - angle))
    large = 1 if angle > 180 else 0
    path = f"M {cx-radius} {cy} A {radius} {radius} 0 {large} 1 {ex:.1f} {ey:.1f}"
    return f'''<svg class="gauge" viewBox="0 0 200 110">
<path d="M {cx-radius} {cy} A {radius} {radius} 0 0 1 {cx+radius} {cy}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="12" stroke-linecap="round"/>
<path class="gauge-arc" d="{path}" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round" style="stroke-dasharray:{3.14159*radius:.0f};stroke-dashoffset:{3.14159*radius*(1-pct):.0f}"/>
<text class="gauge-val" x="{cx}" y="{cy-8}" text-anchor="middle" fill="{color}">{_fmt(value, unit)}</text>
<text class="gauge-lbl" x="{cx}" y="{cy+14}" text-anchor="middle">{esc(label)}</text>
</svg>'''

def _donut(up, down, lu, ld):
    """市场宽度环形图"""
    total = (up or 0) + (down or 0)
    if total == 0: return ""
    up_pct = (up or 0) / total
    cx, cy, r = 80, 80, 60
    circ = 2 * 3.14159 * r
    up_len = circ * up_pct
    down_len = circ * (1 - up_pct)
    up_pct_s = f"{up_pct*100:.1f}%"
    down_pct_s = f"{(1-up_pct)*100:.1f}%"
    lu_s = f"{lu or 0}"
    ld_s = f"{ld or 0}"
    return f'''<svg class="donut" viewBox="0 0 160 160">
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#22c55e" stroke-width="16" stroke-dasharray="{down_len:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})"/>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#ef4444" stroke-width="16" stroke-dasharray="{up_len:.1f} {circ:.1f}" stroke-dashoffset="{-down_len:.1f}" transform="rotate(-90 {cx} {cy})"/>
<text x="{cx}" y="{cy-6}" text-anchor="middle" class="donut-big" fill="#ef4444">{up_pct_s}</text>
<text x="{cx}" y="{cy+14}" text-anchor="middle" class="donut-sm">上涨占比</text>
<text x="{cx}" y="{cy+30}" text-anchor="middle" class="donut-xs" fill="var(--muted)">涨 {up or "—"} / 跌 {down or "—"}</text>
</svg>'''

def _hbar(items, color_up="#ef4444", color_down="#22c55e"):
    """横向条形图（带渐变动画）"""
    if not items: return ""
    mx = max(abs(v) for _, v in items) or 1
    w, rh, bh, pd = 520, 36, 22, 130
    h = len(items) * rh + 20
    svg = [f'<svg class="hbar" viewBox="0 0 {w} {h}">']
    for i, (lbl, v) in enumerate(items):
        y = 16 + i * rh; bw = max(4, abs(v)/mx*(w-pd-60))
        col = color_up if v >= 0 else color_down
        svg.append(f'<text class="cl" x="8" y="{y+15}">{esc(lbl)}</text>')
        svg.append(f'<defs><linearGradient id="g{i}"><stop offset="0%" stop-color="{col}" stop-opacity="0.3"/><stop offset="100%" stop-color="{col}" stop-opacity="0.9"/></linearGradient></defs>')
        svg.append(f'<rect class="cbar" x="{pd}" y="{y}" width="{bw:.1f}" height="{bh}" rx="5" fill="url(#g{i})"/>')
        svg.append(f'<text class="cv" x="{pd+bw+8:.0f}" y="{y+15}" fill="{col}">{v:+.2f}%</text>')
    svg.append("</svg>")
    return "".join(svg)

def _index_cards(indices):
    if not indices: return ""
    cards = []
    for i, ix in enumerate(indices):
        cls = _vcls(ix["v"])
        pt = ix.get("p", "")
        cards.append(f'''<div class="idx-card" style="--d:{i*0.08}s">
<div class="idx-name">{esc(ix["n"])}</div>
<div class="idx-pt">{esc(pt) if pt else "&nbsp;"}</div>
<div class="idx-val {cls}" data-val="{ix["v"]:+.2f}">{ix["v"]:+.2f}%</div>
</div>''')
    return '<div class="idx-grid">' + "".join(cards) + "</div>"

def _mgn_cards(m):
    if m["bal"] is None and m["net"] is None: return ""
    cards = []
    if m["bal"]: cards.append(f'<div class="mgn-card"><span class="k">两融余额</span><span class="v">{_fmt(m["bal"])}</span></div>')
    if m["net"] is not None: cards.append(f'<div class="mgn-card"><span class="k">融资净买入</span><span class="v {_vcls(m["net"])}">{_fmt(m["net"])}</span></div>')
    if m["chg"] is not None: cards.append(f'<div class="mgn-card"><span class="k">环比</span><span class="v {_vcls(m["chg"])}">{m["chg"]:+.2f}%</span></div>')
    return '<div class="mgn-grid">' + "".join(cards) + "</div>"

def build_dashboard(text):
    """生成仪表盘 HTML 块（如果数据可用）"""
    if "客观评级" in text[:500] or "核心判断" in text[:800]:
        return build_stock_dash(text)
    return build_daily_dash(text)


def ext_stock(text):
    r = {"rating":"","target":"","price":None,"pe":None,"pb":None,"mcap":None,
         "div":None,"rev":None,"rev_chg":None,"profit_chg":None,"margin":None,
         "roe":None,"debt":None,"chip_pct":None,"chip_avg":None,
         "c90lo":None,"c90hi":None,"c70lo":None,"c70hi":None,
         "ma20":None,"ma60":None,"rsi":None}
    for line in text.splitlines()[:300]:
        m = re.search(r"客观评级[：:]\s*(.+?)[（(]", line)
        if m and not r["rating"]: r["rating"] = m.group(1).strip()
        m = re.search(r"目标区间\s*([\d.]+)[-~至]\s*([\d.]+)", line)
        if m and not r["target"]: r["target"] = m.group(1) + "-" + m.group(2)
        m = re.search(r"收盘\s*([\d.]+)\s*元", line)
        if m and r["price"] is None: r["price"] = float(m.group(1))
        m = re.search(r"PE\s*TTM\s*([\d.]+)", line)
        if m and r["pe"] is None: r["pe"] = float(m.group(1))
        m = re.search(r"PB\s*([\d.]+)\s*倍", line)
        if m and r["pb"] is None: r["pb"] = float(m.group(1))
        m = re.search(r"总市值.*?([\d.]+)\s*亿", line)
        if m and r["mcap"] is None: r["mcap"] = float(m.group(1))
        m = re.search(r"股息率.*?([\d.]+)%", line)
        if m and r["div"] is None: r["div"] = float(m.group(1))
        m = re.search(r"营收\s*([\d.]+)\s*亿", line)
        if m and r["rev"] is None: r["rev"] = float(m.group(1))
        m = re.search(r"毛利率\s*([\d.]+)%", line)
        if m and r["margin"] is None: r["margin"] = float(m.group(1))
        m = re.search(r"ROE\s*[（(]?([+\-]?[\d.]+)%", line)
        if m and r["roe"] is None: r["roe"] = float(m.group(1))
        m = re.search(r"负债率\s*([\d.]+)%", line)
        if m and r["debt"] is None: r["debt"] = float(m.group(1))
        m = re.search(r"获利盘\s*([\d.]+)%", line)
        if m and r["chip_pct"] is None: r["chip_pct"] = float(m.group(1))
        m = re.search(r"平均成本\s*([\d.]+)", line)
        if m and r["chip_avg"] is None: r["chip_avg"] = float(m.group(1))
        m = re.search(r"90%\s*成本区间\s*([\d.]+)\s*至\s*([\d.]+)", line)
        if m: r["c90lo"] = float(m.group(1)); r["c90hi"] = float(m.group(2))
        m = re.search(r"70%\s*成本区间\s*([\d.]+)\s*至\s*([\d.]+)", line)
        if m: r["c70lo"] = float(m.group(1)); r["c70hi"] = float(m.group(2))
        m = re.search(r"MA20\s*([\d.]+)", line)
        if m and r["ma20"] is None: r["ma20"] = float(m.group(1))
        m = re.search(r"MA60\s*([\d.]+)", line)
        if m and r["ma60"] is None: r["ma60"] = float(m.group(1))
        m = re.search(r"RSI\s*([\d.]+)", line)
        if m and r["rsi"] is None: r["rsi"] = float(m.group(1))
        m = re.search(r"归母.*?([+\-]?\d+\.?\d*)%", line)
        if m and r["profit_chg"] is None:
            try: r["profit_chg"] = float(m.group(1))
            except: pass
    return r


def _rating_card(d):
    if not d["rating"]: return ""
    tgt = f'<span class="rt-tgt">目标区间 {esc(d["target"])}</span>' if d["target"] else ""
    is_buy = "买入" in d["rating"] or "增持" in d["rating"] or "推荐" in d["rating"]
    cls = "rt-buy" if is_buy else "rt-sell"
    return f'''<div class="rating-banner {cls} reveal on">
<div class="rt-label">客观评级</div>
<div class="rt-val">{esc(d["rating"])}</div>
{tgt}
</div>'''


def _stock_metrics(d):
    items = []
    if d["price"] is not None: items.append(("最新价", f'{d["price"]:.2f} 元', ""))
    if d["mcap"] is not None: items.append(("总市值", f'{d["mcap"]:.1f} 亿', ""))
    if d["pe"] is not None: items.append(("PE TTM", f'{d["pe"]:.1f}', ""))
    if d["pb"] is not None: items.append(("PB", f'{d["pb"]:.2f}', ""))
    if d["div"] is not None: items.append(("股息率", f'{d["div"]:.2f}%', ""))
    if d["rev"] is not None: items.append(("最新营收", f'{d["rev"]:.1f} 亿', ""))
    if d["rev_chg"] is not None: items.append(("营收同比", f'{d["rev_chg"]:+.2f}%', _vcls(d["rev_chg"])))
    if d["profit_chg"] is not None: items.append(("归母同比", f'{d["profit_chg"]:+.2f}%', _vcls(d["profit_chg"])))
    if d["margin"] is not None: items.append(("毛利率", f'{d["margin"]:.1f}%', ""))
    if d["roe"] is not None: items.append(("ROE", f'{d["roe"]:.2f}%', _vcls(d["roe"])))
    if d["debt"] is not None: items.append(("负债率", f'{d["debt"]:.1f}%', ""))
    if d["chip_pct"] is not None: items.append(("获利盘", f'{d["chip_pct"]:.1f}%', ""))
    if not items: return ""
    cards = []
    for i, (k, v, c) in enumerate(items):
        ring = ""
        num = None
        try: num = float(re.search(r'[+\-]?[\d.]+', v).group())
        except: pass
        if num is not None and ("%" in v):
            pct = min(100, abs(num))
            rcol = "#ef4444" if (c == "up" or (c == "" and num > 50)) else ("#22c55e" if c == "down" else "#6366f1")
            ring = _ring(pct, 40, rcol)
            cards.append(f'<div class="sm-card has-ring" style="--d:{i*0.06}s"><div class="sm-ring">{ring}</div><div class="sm-body"><div class="sm-k">{esc(k)}</div><div class="sm-v {c}">{esc(v)}</div></div></div>')
        else:
            cards.append(f'<div class="sm-card" style="--d:{i*0.06}s"><div class="sm-k">{esc(k)}</div><div class="sm-v {c}">{esc(v)}</div></div>')
    return '<div class="sm-grid">' + "".join(cards) + "</div>"


def _price_zone(d):
    lo = d.get("c90lo"); hi = d.get("c90hi")
    price = d.get("price"); avg = d.get("chip_avg")
    ma20 = d.get("ma20"); ma60 = d.get("ma60")
    if lo is None or hi is None or price is None: return ""
    rng = hi - lo
    if rng <= 0: return ""
    def pos(v): return max(0, min(100, (v - lo) / rng * 100))
    markers = []
    markers.append(f'<div class="pz-mark" style="left:{pos(price):.1f}%"><span class="pz-dot" style="background:var(--accent2)"></span><span class="pz-lbl">现价 {price:.2f}</span></div>')
    if avg: markers.append(f'<div class="pz-mark" style="left:{pos(avg):.1f}%"><span class="pz-dot" style="background:var(--warn)"></span><span class="pz-lbl">均成本 {avg:.2f}</span></div>')
    if ma20: markers.append(f'<div class="pz-mark" style="left:{pos(ma20):.1f}%"><span class="pz-dot" style="background:var(--accent)"></span><span class="pz-lbl">MA20 {ma20:.2f}</span></div>')
    if ma60: markers.append(f'<div class="pz-mark" style="left:{pos(ma60):.1f}%"><span class="pz-dot" style="background:#6b7280"></span><span class="pz-lbl">MA60 {ma60:.2f}</span></div>')
    c70 = ""
    if d.get("c70lo") and d.get("c70hi"):
        l = pos(d["c70lo"]); r = pos(d["c70hi"])
        c70 = f'<div class="pz-zone70" style="left:{l:.1f}%;width:{r-l:.1f}%"></div>'
    return f'''<div class="pz-wrap reveal on">
<div class="pz-title">筹码价格带</div>
<div class="pz-bar">
<div class="pz-zone90"></div>{c70}
{"".join(markers)}
</div>
<div class="pz-labels"><span>{lo:.2f}</span><span>{hi:.2f}</span></div>
</div>'''


def _sentiment_gauge(up, down):
    if up is None or down is None: return ""
    total = up + down
    if total == 0: return ""
    up_ratio = up / total * 100
    if up_ratio > 60: label, color = "偏多", "#ef4444"
    elif up_ratio > 45: label, color = "中性", "#f59e0b"
    else: label, color = "偏空", "#22c55e"
    import math
    cx, cy, rad = 100, 95, 70
    angle = 180 * (up_ratio / 100)
    ex = cx + rad * math.cos(math.radians(180 - angle))
    ey = cy - rad * math.sin(math.radians(180 - angle))
    return f'''<div class="sg-wrap reveal on"><div class="sg-title">市场情绪</div>
<svg class="gauge" viewBox="0 0 200 110">
<path d="M 30 95 A 70 70 0 0 1 170 95" fill="none" stroke="rgba(255,255,255,.06)" stroke-width="14" stroke-linecap="round"/>
<path d="M 30 95 A 70 70 0 0 1 {ex:.1f} {ey:.1f}" fill="none" stroke="{color}" stroke-width="14" stroke-linecap="round" opacity=".85"/>
<text x="100" y="80" text-anchor="middle" class="gauge-val" fill="{color}">{up_ratio:.1f}%</text>
<text x="100" y="100" text-anchor="middle" class="gauge-lbl">{label}</text>
<text x="30" y="108" text-anchor="middle" class="gauge-xs" fill="#22c55e">空</text>
<text x="170" y="108" text-anchor="middle" class="gauge-xs" fill="#ef4444">多</text>
</svg></div>'''


def build_stock_dash(text):
    d = ext_stock(text)
    parts = []
    rc = _rating_card(d)
    if rc: parts.append(rc)
    sm = _stock_metrics(d)
    if sm: parts.append(sm)
    ff = _fundflow_card(text)
    if ff: parts.append(ff)
    fb = _fin_bars(d)
    if fb: parts.append(fb)
    pz = _price_zone(d)
    if pz: parts.append(pz)
    ts = _tech_strip(d)
    if ts: parts.append(ts)
    rb = _risk_bar(6)
    if rb: parts.append(rb)
    return '<div class="dashboard">' + "".join(parts) + "</div>" if parts else ""


def _fundflow_card(text):
    """个股资金流向指示器"""
    main = None; direction = ""
    for line in text.splitlines()[:200]:
        m = re.search(r"主力.*?净流入\s*([\d.,]+)\s*万", line)
        if m:
            try:
                main = float(m.group(1).replace(",", ""))
                direction = "net_in" if "流出" not in line else "net_out"
            except: pass
        m = re.search(r"主力.*?净流出\s*([\d.,]+)\s*万", line)
        if m and main is None:
            try:
                main = -float(m.group(1).replace(",", ""))
                direction = "net_out"
            except: pass
    if main is None: return ""
    col = "#ef4444" if main >= 0 else "#22c55e"
    lbl = "净流入" if main >= 0 else "净流出"
    txt = f"{abs(main)/10000:.0f}万" if abs(main) >= 10000 else f"{abs(main):.0f}万"
    return f'''<div class="ff-wrap reveal on"><div class="ff-title">主力资金</div>
<div class="ff-bar"><div class="ff-fill" style="background:{col}"></div></div>
<div class="ff-val" style="color:{col}">{lbl} {txt}</div></div>'''


def _waterfall(items):
    """资金流向瀑布图"""
    if not items or len(items) < 2: return ""
    w, rh, pd = 480, 44, 120
    h = len(items) * rh + 40
    mx = max(abs(v) for _, v in items) or 1
    running = 0
    bars = []
    for i, (lbl, v) in enumerate(items):
        y = 16 + i * rh
        old = running
        running += v
        start = min(old, running)
        end = max(old, running)
        bar_y1 = h - 30 - (start / mx) * (h - 50)
        bar_y2 = h - 30 - (end / mx) * (h - 50)
        bar_h = max(3, abs(bar_y2 - bar_y1))
        top = min(bar_y1, bar_y2)
        col = "#ef4444" if v >= 0 else "#22c55e"
        bars.append(f'<text class="cl" x="8" y="{y+16}">{esc(lbl)}</text>')
        bars.append(f'<rect x="{pd}" y="{top:.1f}" width="60" height="{bar_h:.1f}" rx="3" fill="{col}" opacity=".7"/>')
        bars.append(f'<text class="cv" x="{pd+68}" y="{y+16}" fill="{col}">{v:+.0f}亿</text>')
    svg = f'<svg class="wf-chart" viewBox="0 0 {w} {h}">{"".join(bars)}</svg>'
    return f'<div class="wf-wrap reveal on"><div class="wf-title">资金流向瀑布</div>{svg}</div>'


def _risk_bar(level):
    """风险水平指示条 (1-10)"""
    if not level: return ""
    pct = min(100, int(level) / 10 * 100)
    if level <= 3: col, lbl = "#22c55e", "低风险"
    elif level <= 6: col, lbl = "#f59e0b", "中等风险"
    else: col, lbl = "#ef4444", "高风险"
    segments = ""
    for i in range(10):
        sc = col if i < level else "rgba(255,255,255,.06)"
        segments += f'<div class="rb-seg" style="background:{sc}"></div>'
    return f'''<div class="rb-wrap"><div class="rb-title">风险等级</div>
<div class="rb-bar">{segments}</div><span class="rb-lbl" style="color:{col}">{lbl} {level}/10</span></div>'''


# ================ 增强可视化 ================
def _ring(pct, size=44, color="#6366f1", stroke=4):
    import math
    pct = max(0, min(100, pct))
    r = (size - stroke) / 2
    c = size / 2
    circ = 2 * math.pi * r
    offset = circ * (1 - pct / 100)
    return (f'<svg class="mring" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="rgba(255,255,255,.06)" stroke-width="{stroke}"/>'
        f'<circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}" '
        f'stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}" stroke-linecap="round" '
        f'transform="rotate(-90 {c} {c})"/></svg>')


def _heatmap(sectors):
    if not sectors: return ""
    tiles = []
    for s in sectors:
        v = s["v"]
        inten = min(1, abs(v) / 8)
        if v >= 0:
            bg = f"rgba(239,68,68,{0.08 + inten * 0.45:.2f})"
            tc = "#fca5a5"
        else:
            bg = f"rgba(34,197,94,{0.08 + inten * 0.45:.2f})"
            tc = "#86efac"
        tiles.append(
            f'<div class="hm-tile" style="background:{bg}">'
            f'<span class="hm-n">{esc(s["n"])}</span>'
            f'<span class="hm-v" style="color:{tc}">{v:+.2f}%</span></div>'
        )
    return f'<div class="hm-wrap"><div class="hm-title">板块热力图</div><div class="hm-grid">{"".join(tiles)}</div></div>'


_HL_NUM = re.compile(
    r'(?<!["/>=])([+\-]?[\d,]+\.?\d*\s*(?:%|万亿|亿|万|元|倍|点|家))(?!["</])'
)

def _hl_nums(html_text):
    return _HL_NUM.sub(r'<span class="num">\1</span>', html_text)


def _r_inline_hl(t):
    return _hl_nums(r_inline(t))


# ================ 更多数据提取 ================
def ext_macro(text):
    r = {}
    for line in text.splitlines()[:120]:
        for k, p in [
            ("cpi", r"CPI.*?([+\-]?\d+\.?\d*)%"),
            ("ppi", r"PPI.*?([+\-]?\d+\.?\d*)%"),
            ("m2", r"M2.*?([+\-]?\d+\.?\d*)%"),
            ("she", r"社融.*?([\d.]+)\s*(万亿|亿)"),
            ("lpr", r"LPR.*?([\d.]+)%"),
            ("usdcny", r"美元兑人民币.*?([\d.]+)"),
        ]:
            if k not in r:
                m = re.search(p, line)
                if m:
                    try: r[k] = m.group(1)
                    except: pass
    return r

def ext_overseas(text):
    r = {}
    for line in text.splitlines()[:150]:
        for k, p in [
            ("nasdaq", r"纳斯达克.*?([+\-]?\d+\.?\d*)%"),
            ("dow", r"道琼斯.*?([+\-]?\d+\.?\d*)%"),
            ("sp500", r"标普.*?([+\-]?\d+\.?\d*)%"),
            ("hsi", r"恒生指数.*?([+\-]?\d+\.?\d*)%"),
            ("gold", r"黄金.*?([+\-]?\d+\.?\d*)%"),
            ("oil", r"原油.*?([+\-]?\d+\.?\d*)%"),
            ("btc", r"比特币.*?([+\-]?\d+\.?\d*)%"),
        ]:
            if k not in r:
                m = re.search(p, line)
                if m:
                    try: r[k] = float(m.group(1))
                    except: pass
    return r

def ext_fundflow(text):
    r = {}
    for line in text.splitlines()[:200]:
        m = re.search(r"主力.*?净流入.*?([+\-]?[\d.,]+)\s*(亿|万)", line)
        if m and "main" not in r:
            sign = -1 if m.group(1).startswith("-") else 1
            r["main"] = sign * float(m.group(1).replace(",","").lstrip("+-")) * (1e8 if m.group(2)=="亿" else 1e4)
        m = re.search(r"超大单.*?净流入.*?([+\-]?[\d.,]+)\s*(亿|万)", line)
        if m and "xl" not in r:
            sign = -1 if m.group(1).startswith("-") else 1
            r["xl"] = sign * float(m.group(1).replace(",","").lstrip("+-")) * (1e8 if m.group(2)=="亿" else 1e4)
    return r

def ext_margin_trend(text):
    """提取两融历史数据点用于折线图"""
    points = []
    for line in text.splitlines():
        m = re.search(r"(\d{2}-\d{2})\s*[|│]?\s*([\d.]+)亿\s*[|│]?\s*([\d.]+)万亿", line)
        if m:
            try:
                points.append({"date": m.group(1), "sec": float(m.group(2)), "fin": float(m.group(3))})
            except: pass
    return points

def _margin_line_chart(points):
    """两融余额折线图（带面积填充）"""
    if len(points) < 2: return ""
    w, h = 480, 180
    pad_l, pad_r, pad_t, pad_b = 50, 20, 20, 30
    fin_vals = [p["fin"] for p in points]
    sec_vals = [p["sec"] for p in points]
    all_vals = fin_vals + sec_vals
    vmin, vmax = min(all_vals) * 0.95, max(all_vals) * 1.05
    vrng = vmax - vmin or 1
    def x(i): return pad_l + (w - pad_l - pad_r) * i / (len(points) - 1)
    def y(v): return pad_t + (h - pad_t - pad_b) * (1 - (v - vmin) / vrng)
    fin_pts = " ".join(f"{x(i):.1f},{y(p['fin']):.1f}" for i, p in enumerate(points))
    sec_pts = " ".join(f"{x(i):.1f},{y(p['sec']):.1f}" for i, p in enumerate(points))
    area = f"M {x(0):.1f},{y(fin_vals[0]):.1f} " + " ".join(f"L {x(i):.1f},{y(p['fin']):.1f}" for i, p in enumerate(points)) + f" L {x(len(points)-1):.1f},{h-pad_b} L {x(0):.1f},{h-pad_b} Z"
    dots = "".join(f'<circle cx="{x(i):.1f}" cy="{y(p["fin"]):.1f}" r="4" fill="#6366f1" stroke="#0a0e1a" stroke-width="2"/>' for i, p in enumerate(points))
    labels = "".join(f'<text class="ax-lbl" x="{x(i):.1f}" y="{h-8}" text-anchor="middle">{p["date"]}</text>' for i, p in enumerate(points))
    ylabels = "".join(f'<text class="ax-lbl" x="{pad_l-6}" y="{y(v)+4:.1f}" text-anchor="end">{v:.1f}万亿</text>' for v in [vmin + vrng*0.25, vmin + vrng*0.5, vmin + vrng*0.75, vmax])
    return f'''<div class="ml-wrap reveal on"><div class="ml-title">两融余额走势</div>
<svg class="mlchart" viewBox="0 0 {w} {h}">
<defs><linearGradient id="mlg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#6366f1" stop-opacity=".3"/><stop offset="100%" stop-color="#6366f1" stop-opacity="0"/></linearGradient></defs>
<path d="{area}" fill="url(#mlg)"/>
<polyline class="ml-line" points="{fin_pts}" fill="none" stroke="#6366f1" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
<polyline points="{sec_pts}" fill="none" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="4 3" opacity=".6"/>
{dots}{labels}{ylabels}
</svg>
<div class="ml-legend"><span class="ml-dot" style="background:#6366f1"></span>融资余额 <span class="ml-dot" style="background:#f59e0b"></span>融券余额</div>
</div>'''


def _macro_chips(data):
    if not data: return ""
    labels = {"cpi":"CPI","ppi":"PPI","m2":"M2","she":"社融","lpr":"LPR","usdcny":"USDCNY"}
    chips = []
    for k, lbl in labels.items():
        if k in data:
            v = data[k]
            chips.append(f'<div class="mc-chip"><span class="mc-k">{lbl}</span><span class="mc-v">{esc(str(v))}</span></div>')
    return f'<div class="mc-wrap"><div class="mc-title">宏观指标</div><div class="mc-grid">{"".join(chips)}</div></div>'


def _overseas_bars(data):
    if not data: return ""
    labels = {"nasdaq":"纳斯达克","dow":"道琼斯","sp500":"标普500","hsi":"恒生指数","gold":"黄金","oil":"原油","btc":"比特币"}
    items = [(labels[k], v) for k, v in data.items() if v is not None]
    if not items: return ""
    bars = []
    mx = max(abs(v) for _, v in items) or 1
    for name, v in items:
        pct = abs(v) / mx * 100
        col = "#ef4444" if v >= 0 else "#22c55e"
        bars.append(f'''<div class="ob-row"><span class="ob-n">{name}</span>
<div class="ob-track"><div class="ob-fill" style="width:{pct:.0f}%;background:{col}"></div></div>
<span class="ob-v" style="color:{col}">{v:+.2f}%</span></div>''')
    return f'<div class="ob-wrap"><div class="ob-title">海外市场</div>{"".join(bars)}</div>'


def _fin_bars(d):
    """个股财务指标进度条"""
    bars = []
    metrics = [
        ("毛利率", d.get("margin"), 100, "%"),
        ("ROE", d.get("roe"), 30, "%"),
        ("负债率", d.get("debt"), 100, "%"),
        ("获利盘", d.get("chip_pct"), 100, "%"),
    ]
    for lbl, val, mx, unit in metrics:
        if val is None: continue
        pct = min(100, abs(val) / mx * 100)
        col = "#6366f1" if val >= 0 else "#22c55e"
        bars.append(f'''<div class="fb-row"><span class="fb-k">{lbl}</span>
<div class="fb-track"><div class="fb-fill" style="width:{pct:.0f}%;background:linear-gradient(90deg,{col}44,{col})"></div></div>
<span class="fb-v">{val:+.1f}{unit}</span></div>''')
    return f'<div class="fb-wrap"><div class="fb-title">财务概览</div>{"".join(bars)}</div>' if bars else ""


def _tech_strip(d):
    """技术信号指示器"""
    price = d.get("price"); ma20 = d.get("ma20"); ma60 = d.get("ma60"); rsi = d.get("rsi")
    if price is None: return ""
    signals = []
    if ma20:
        above = price > ma20
        signals.append(("MA20", "上方" if above else "下方", "#ef4444" if above else "#22c55e"))
    if ma60:
        above = price > ma60
        signals.append(("MA60", "上方" if above else "下方", "#ef4444" if above else "#22c55e"))
    if rsi:
        if rsi > 70: sig, col = "超买", "#ef4444"
        elif rsi < 30: sig, col = "超卖", "#22c55e"
        else: sig, col = "中性", "#f59e0b"
        signals.append(("RSI", f"{rsi:.0f} {sig}", col))
    if not signals: return ""
    pills = "".join(f'<div class="ts-pill" style="border-color:{col}33"><span class="ts-k">{k}</span><span class="ts-v" style="color:{col}">{v}</span></div>' for k, v, col in signals)
    return f'<div class="ts-wrap"><div class="ts-title">技术信号</div><div class="ts-grid">{pills}</div></div>'


def build_daily_dash(text):
    idx = ext_idx(text)
    brd = ext_brd(text)
    sec = ext_sec(text)
    mgn = ext_mgn(text)
    macro = ext_macro(text)
    ovs = ext_overseas(text)
    mline_pts = ext_margin_trend(text)
    parts = []
    if idx: parts.append(_index_cards(idx))
    mgn_cards = _mgn_cards(mgn)
    sg = _sentiment_gauge(brd["up"], brd["down"])
    if mgn_cards or sg:
        row = ""
        if sg: row += f'<div class="dash-cell">{sg}</div>'
        if mgn_cards: row += mgn_cards
        if row: parts.append(f'<div class="dash-row">{row}</div>')
    dn = _donut(brd["up"], brd["down"], brd["lu"], brd["ld"])
    if dn:
        parts.append(f'<div class="dash-row"><div class="dash-cell">{dn}</div></div>')
    ml = _margin_line_chart(mline_pts)
    if ml: parts.append(ml)
    if sec: parts.append(_heatmap(sec))
    ff_data = ext_fundflow(text)
    wf_items = []
    if ff_data.get("main") is not None:
        wf_items.append(("main", ff_data["main"] / 1e8))
    if ff_data.get("xl") is not None:
        wf_items.append(("xl", ff_data["xl"] / 1e8))
    wf = _waterfall(wf_items)
    if wf: parts.append(wf)
    rb = _risk_bar(5)
    if rb: parts.append(rb)
    if mgn["bal"] or mgn["net"]: parts.append(_mgn_cards(mgn))
    mc = _macro_chips(macro)
    ob = _overseas_bars(ovs)
    if mc or ob:
        row = ""
        if mc: row += mc
        if ob: row += ob
        parts.append(f'<div class="dash-two">{row}</div>')
    if not parts: return ""
    return '<div class="dashboard">' + "".join(parts) + "</div>"


# ================ CSS ================
CSS = r"""
:root{--bg:#080c1a;--panel:rgba(255,255,255,.05);--panel2:rgba(255,255,255,.08);
--ink:#e8ecf1;--muted:#7a8699;--line:rgba(255,255,255,.07);--accent:#6366f1;
--accent2:#a78bfa;--up:#ef4444;--down:#22c55e;--warn:#f59e0b;
--side:rgba(8,12,26,.85);--grad:linear-gradient(135deg,#667eea,#764ba2);
--glow:0 0 30px rgba(99,102,241,.15);--glow2:0 0 60px rgba(118,75,162,.1)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:"Microsoft YaHei","PingFang SC","Noto Sans SC",-apple-system,sans-serif;background:var(--bg);color:var(--ink);line-height:1.8;letter-spacing:0;overflow-x:hidden;font-size:17px}
body::before{content:"";position:fixed;inset:0;background:radial-gradient(ellipse at 20% 20%,rgba(99,102,241,.08) 0%,transparent 50%),radial-gradient(ellipse at 80% 80%,rgba(118,75,162,.06) 0%,transparent 50%),radial-gradient(ellipse at 50% 50%,rgba(99,102,241,.04) 0%,transparent 70%);pointer-events:none;z-index:0}
a{color:var(--accent2);text-decoration:none;transition:.2s}
a:hover{color:#c4b5fd;text-shadow:0 0 8px rgba(167,139,250,.4)}
code{font-family:"Cascadia Code","Fira Code",monospace;font-size:.88em;background:rgba(99,102,241,.1);color:#c4b5fd;padding:2px 7px;border-radius:5px;border:1px solid rgba(99,102,241,.15)}
pre{background:rgba(0,0,0,.4);border:1px solid var(--line);border-radius:12px;padding:16px 18px;overflow:auto;font-size:.85em;line-height:1.6;backdrop-filter:blur(10px)}
pre code{background:none;border:none;padding:0;color:#a5b4fc}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:rgba(255,255,255,.03)}
::-webkit-scrollbar-thumb{background:rgba(99,102,241,.3);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:rgba(99,102,241,.5)}

.progress{position:fixed;top:0;left:0;height:3px;width:0;background:linear-gradient(90deg,#6366f1,#a78bfa,#ec4899);z-index:999;border-radius:0 3px 3px 0;box-shadow:0 0 12px rgba(99,102,241,.5)}
.reveal{opacity:0;transform:translateY(24px);transition:opacity .6s cubic-bezier(.22,1,.36,1),transform .6s cubic-bezier(.22,1,.36,1)}
.reveal.on{opacity:1;transform:translateY(0)}

.sidebar{position:fixed;top:0;left:0;bottom:0;width:280px;background:var(--side);backdrop-filter:blur(24px);border-right:1px solid rgba(255,255,255,.1);z-index:100;overflow-y:auto;display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:14px;padding:22px 22px 18px;border-bottom:1px solid var(--line)}
.brand-mark{width:38px;height:38px;border-radius:10px;background:var(--grad);display:flex;align-items:center;justify-content:center;flex:none;box-shadow:0 4px 16px rgba(99,102,241,.4)}
.brand-mark svg{width:20px;height:20px}
.brand-name{font-weight:700;font-size:17px;color:#fff}
.brand-sub{font-size:11px;color:var(--muted)}
.toc-title{padding:18px 22px 8px;font-size:10px;letter-spacing:3px;color:var(--muted);text-transform:uppercase}
.toc{list-style:none;margin:0;padding:0 12px 20px;flex:1;overflow-y:auto}
.toc li{margin:2px 0}
.toc a{display:block;padding:10px 16px;border-radius:8px;color:#b0bac8;font-size:16px;line-height:1.5;border-left:2px solid transparent;transition:.2s}
.toc a:hover{background:rgba(99,102,241,.08);color:#fff;padding-left:18px;box-shadow:inset 0 0 16px rgba(99,102,241,.06)}
.toc a.active{background:rgba(99,102,241,.14);color:#c4b5fd;border-left-color:var(--accent2);box-shadow:inset 0 0 24px rgba(99,102,241,.06)}
.toc .l3{padding-left:28px;font-size:13px}
.toc .l4{padding-left:40px;font-size:12px;color:var(--muted)}
.side-foot{margin-top:auto;padding:16px 20px;font-size:11px;color:var(--muted);border-top:1px solid var(--line)}

.main{margin-left:280px;position:relative;z-index:1}
.hero{padding:48px 56px 34px;border-bottom:1px solid var(--line)}
.hero-tags{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px}
.tag{font-size:13px;color:#c4b5fd;background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.25);padding:4px 12px;border-radius:20px;font-weight:500;letter-spacing:1px}
.tag.hi{background:var(--grad);color:#fff;border:none;box-shadow:0 2px 12px rgba(99,102,241,.3)}
.hero h1{margin:0 0 14px;font-size:36px;font-weight:800;line-height:1.3;background:linear-gradient(135deg,#fff 40%,#a5b4fc 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-meta{color:var(--muted);font-size:15px;display:flex;flex-wrap:wrap;gap:8px 28px}
.hero-meta b{color:#a5b4fc;font-weight:600}

.dashboard{max-width:1100px;margin:0 auto;padding:24px 56px 0}
.idx-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin:20px 0}
.idx-card{background:var(--panel);border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:24px 26px;backdrop-filter:blur(16px);transition:.3s;animation:fadeUp .6s both;animation-delay:var(--d,0s);position:relative;overflow:hidden}
.idx-card::before{content:"";position:absolute;top:0;left:0;right:0;height:2px;background:var(--grad);opacity:.6}
.idx-card:hover{background:var(--panel2);border-color:rgba(99,102,241,.25);box-shadow:var(--glow);transform:translateY(-3px)}
.idx-name{font-size:12px;color:var(--muted);margin-bottom:6px;letter-spacing:1px}
.idx-pt{font-size:26px;font-weight:700;font-family:monospace;color:#fff}
.idx-val{font-size:32px;font-weight:800;font-family:monospace}
.idx-val.up{color:var(--up)}.idx-val.down{color:var(--down)}

.dash-row{display:flex;justify-content:center;margin:16px 0}
.dash-cell{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px;backdrop-filter:blur(12px)}
.donut text{font-family:inherit}
.donut-big{font-size:24px;font-weight:800}
.donut-sm{font-size:11px;fill:var(--muted)}
.donut-xs{font-size:10px}

.sec-block{margin:14px 0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;backdrop-filter:blur(12px)}
.sec-t{font-size:12px;color:var(--muted);margin-bottom:8px;letter-spacing:2px}
.hbar,.cchart{width:100%;height:auto;display:block}
.hbar text,.cchart text{font-family:inherit}
.cl{font-size:12px;fill:#8a94a6}
.cv{font-size:12px;fill:#e8ecf1;font-weight:600}
.cbar{transition:width .8s cubic-bezier(.22,1,.36,1)}

.mgn-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:16px 0}
.mgn-card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:4px;backdrop-filter:blur(12px)}
.mgn-card .k{font-size:11px;color:var(--muted)}
.mgn-card .v{font-size:22px;font-weight:700;font-family:monospace;color:#fff}
.mgn-card .v.up{color:var(--up)}.mgn-card .v.down{color:var(--down)}

.content{max-width:1100px;margin:0 auto;padding:32px 56px 48px}
.content h2{font-size:24px;margin:48px 0 22px;padding:16px 24px;background:var(--panel);border:1px solid var(--line);border-radius:12px;border-left:4px solid var(--accent);backdrop-filter:blur(14px)}
.content h3{font-size:20px;margin:28px 0 12px;padding-bottom:10px;border-bottom:1px solid var(--line);color:#c4b5fd}
.content h4{font-size:17px;margin:20px 0 8px;color:var(--accent2)}
.content h2[id^="risk"],.content h2[id^="sec-12"],.content h2[id^="sec-13"]{border-left-color:var(--up);background:rgba(239,68,68,.06)}
p{margin:14px 0;line-height:1.85;max-width:860px}
ul,ol{margin:12px 0;padding-left:28px;max-width:860px}
li{margin:7px 0;line-height:1.75}
li .kv-k{color:var(--muted);margin-right:10px;font-size:.95em}
li .kv-v{font-weight:700;font-family:monospace;color:#fff;font-size:1.25em;padding:2px 6px;border-radius:5px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.04)}
li .kv-v.up{color:var(--up)}.li .kv-v.down{color:var(--down)}

.tw{overflow-x:auto;margin:14px 0;border:1px solid var(--line);border-radius:12px;backdrop-filter:blur(10px)}
table{border-collapse:collapse;width:100%;font-size:15px;background:rgba(0,0,0,.25)}
th{background:rgba(99,102,241,.08);color:#a5b4fc;text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);white-space:nowrap;font-weight:600;font-size:12px;letter-spacing:1px}
td{padding:9px 14px;border-bottom:1px solid rgba(255,255,255,.03);white-space:nowrap}
tbody tr:hover{background:rgba(99,102,241,.05)}
tbody tr:last-child td{border-bottom:none}

.tc{margin:14px 0 20px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;backdrop-filter:blur(12px)}
.tc-t{font-size:11px;color:var(--muted);margin-bottom:8px;letter-spacing:2px}
.gauge{width:100%;max-width:220px;height:auto;display:block;margin:0 auto}
.gauge-val{font-size:26px;font-weight:800;font-family:monospace}
.gauge-lbl{font-size:11px;fill:var(--muted)}

blockquote{margin:20px 0;padding:18px 24px;background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.15);border-left:4px solid var(--warn);border-radius:0 12px 12px 0;color:#fde68a;backdrop-filter:blur(10px)}
blockquote p{margin:6px 0}
hr{border:none;height:1px;background:linear-gradient(90deg,transparent,var(--line),transparent);margin:24px 0}

.foot{max-width:1020px;margin:0 auto;padding:20px 48px 50px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);margin-top:20px}
#top{position:fixed;right:24px;bottom:24px;width:48px;height:48px;border-radius:12px;border:1px solid var(--line);background:var(--panel);color:#fff;cursor:pointer;display:none;align-items:center;justify-content:center;box-shadow:0 4px 20px rgba(0,0,0,.4);backdrop-filter:blur(10px);transition:.2s;z-index:100}
#top:hover{background:rgba(99,102,241,.15);border-color:var(--accent);box-shadow:var(--glow)}
#top svg{width:20px;height:20px}

@media(max-width:920px){
.sidebar{position:static;width:auto;height:auto}
.toc{display:flex;flex-wrap:nowrap;overflow-x:auto;gap:4px;padding:4px 12px 12px}
.toc li{flex:none}.toc a{border-left:none;border-bottom:2px solid transparent;white-space:nowrap;border-radius:0}
.toc a.active{border-bottom-color:var(--accent2)}
.toc .l3,.toc .l4{padding-left:10px}.toc-title{display:none}.side-foot{display:none}
.main{margin-left:0}.hero{padding:28px 20px}.hero h1{font-size:22px}
.dashboard{padding:16px 16px 0}.content{padding:20px 16px}.foot{padding:16px 20px 30px}
}
@keyframes fadeUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{box-shadow:0 0 20px rgba(99,102,241,.1)}50%{box-shadow:0 0 40px rgba(99,102,241,.25)}}
.idx-card:hover{animation:pulse 2s infinite}
.rating-banner{display:flex;align-items:center;gap:20px;padding:24px 32px;border-radius:16px;margin:0 0 18px;backdrop-filter:blur(16px)}
.rating-banner.rt-buy{background:linear-gradient(135deg,rgba(239,68,68,.12),rgba(239,68,68,.04));border:1px solid rgba(239,68,68,.25);box-shadow:0 4px 24px rgba(239,68,68,.08)}
.rating-banner.rt-sell{background:linear-gradient(135deg,rgba(34,197,94,.12),rgba(34,197,94,.04));border:1px solid rgba(34,197,94,.25)}
.rt-label{font-size:12px;color:var(--muted);letter-spacing:3px;text-transform:uppercase}
.rt-val{font-size:40px;font-weight:800;background:linear-gradient(135deg,#ef4444,#f97316);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.rt-buy .rt-val{background:linear-gradient(135deg,#ef4444,#f97316);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.rt-sell .rt-val{background:linear-gradient(135deg,#22c55e,#14b8a6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.rt-tgt{margin-left:auto;font-size:18px;font-weight:700;color:var(--warn);font-family:monospace}
.sm-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.sm-card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;backdrop-filter:blur(12px);transition:.3s;animation:fadeUp .5s both;animation-delay:var(--d,0s)}
.sm-card:hover{background:var(--panel2);border-color:rgba(99,102,241,.3);transform:translateY(-2px);box-shadow:var(--glow)}
.sm-k{font-size:10px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:4px}
.sm-v{font-size:28px !important;font-weight:700;font-family:monospace;color:#fff}
.sm-v.up{color:var(--up)}.sm-v.down{color:var(--down)}
.pz-wrap{margin:16px 0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 20px;backdrop-filter:blur(12px)}
.pz-title{font-size:12px;color:var(--muted);letter-spacing:2px;margin-bottom:12px}
.pz-bar{position:relative;height:24px;border-radius:12px;overflow:visible;background:rgba(255,255,255,.03)}
.pz-zone90{position:absolute;top:0;left:0;right:0;height:100%;border-radius:12px;background:linear-gradient(90deg,rgba(34,197,94,.15),rgba(255,255,255,.05),rgba(239,68,68,.15))}
.pz-zone70{position:absolute;top:2px;height:calc(100% - 4px);border-radius:10px;background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.2)}
.pz-mark{position:absolute;top:-6px;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:4px;z-index:2}
.pz-dot{width:10px;height:10px;border-radius:50%;border:2px solid rgba(255,255,255,.3);box-shadow:0 0 8px rgba(255,255,255,.2)}
.pz-lbl{font-size:10px;color:var(--muted);white-space:nowrap;font-family:monospace}
.pz-labels{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-top:8px;font-family:monospace}
.sg-wrap{text-align:center;padding:8px}
.sg-title{font-size:12px;color:var(--muted);letter-spacing:2px;margin-bottom:6px}
.gauge-xs{font-size:9px}
.dash-row{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin:16px 0}
.dash-cell{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:12px;backdrop-filter:blur(12px);min-width:200px}
.content h2{position:relative;overflow:hidden}
.content h2::after{content:"";position:absolute;bottom:0;left:0;right:0;height:1px;background:linear-gradient(90deg,rgba(99,102,241,.4),transparent 70%)}
.content strong{color:#c4b5fd;font-weight:700}
.content h2 + p, .content h2 + ul {margin-top:12px}
.hm-wrap{margin:14px 0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;backdrop-filter:blur(12px)}
.hm-title{font-size:11px;color:var(--muted);letter-spacing:2px;margin-bottom:10px;text-transform:uppercase}
.hm-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px}
.hm-tile{border-radius:12px;padding:18px 14px;text-align:center;transition:.2s;cursor:default;border:1px solid rgba(255,255,255,.06);backdrop-filter:blur(8px)}
.hm-tile:hover{transform:scale(1.04);border-color:rgba(255,255,255,.1)}
.hm-n{display:block;font-size:12px;color:#c0cad6;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hm-v{display:block;font-size:19px;font-weight:800;font-family:monospace}
.num{font-family:monospace;font-weight:700;color:#a5b4fc;font-size:1.2em;padding:2px 6px;border-radius:5px;background:rgba(99,102,241,.1);text-shadow:0 0 12px rgba(165,180,252,.2)}
.sm-card.has-ring{display:flex;align-items:center;gap:10px}
.sm-ring{flex:none}
.sm-body{flex:1;min-width:0}
.mring{display:block}
.idx-val{font-size:26px !important;font-weight:800 !important;text-shadow:0 0 20px rgba(255,255,255,.08)}
.idx-card .idx-name{font-size:11px;letter-spacing:1px;text-transform:uppercase}
.idx-card .idx-pt{font-size:17px;font-family:monospace;color:#a5b4fc;font-weight:600}
.sm-v{font-size:22px !important}
.content li .kv-v{font-size:1.1em !important;padding:1px 4px;border-radius:4px;background:rgba(255,255,255,.03)}
.content .num{padding:1px 3px;border-radius:4px;background:rgba(99,102,241,.08)}
.dash-two{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0}
.mc-wrap,.ob-wrap,.ml-wrap,.fb-wrap,.ts-wrap{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;backdrop-filter:blur(12px);margin:10px 0}
.mc-title,.ob-title,.ml-title,.fb-title,.ts-title{font-size:11px;color:var(--muted);letter-spacing:2px;margin-bottom:12px;text-transform:uppercase}
.mc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:8px}
.mc-chip{background:rgba(99,102,241,.06);border:1px solid rgba(99,102,241,.12);border-radius:8px;padding:8px 10px;text-align:center}
.mc-k{display:block;font-size:10px;color:var(--muted);margin-bottom:2px}
.mc-v{display:block;font-size:18px;font-weight:700;font-family:monospace;color:#a5b4fc}
.ob-row{display:flex;align-items:center;gap:10px;margin:6px 0}
.ob-n{width:60px;font-size:12px;color:var(--muted);flex:none}
.ob-track{flex:1;height:8px;background:rgba(255,255,255,.04);border-radius:4px;overflow:hidden}
.ob-fill{height:100%;border-radius:4px;transition:width .8s cubic-bezier(.22,1,.36,1)}
.ob-v{width:70px;text-align:right;font-size:15px;font-family:monospace;font-weight:600;flex:none}
.mlchart{width:100%;height:auto;display:block}
.ml-line{filter:drop-shadow(0 0 6px rgba(99,102,241,.4))}
.ml-legend{display:flex;gap:16px;align-items:center;font-size:11px;color:var(--muted);margin-top:8px}
.ml-dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;vertical-align:middle}
.ax-lbl{font-size:9px;fill:var(--muted);font-family:monospace}
.fb-row{display:flex;align-items:center;gap:12px;margin:8px 0}
.fb-k{width:56px;font-size:12px;color:var(--muted);flex:none}
.fb-track{flex:1;height:10px;background:rgba(255,255,255,.04);border-radius:5px;overflow:hidden}
.fb-fill{height:100%;border-radius:5px;transition:width .8s cubic-bezier(.22,1,.36,1)}
.fb-v{width:70px;text-align:right;font-size:16px;font-family:monospace;font-weight:600;color:#a5b4fc;flex:none}
.ts-grid{display:flex;flex-wrap:wrap;gap:8px}
.ts-pill{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 14px;display:flex;align-items:center;gap:8px}
.ts-k{font-size:11px;color:var(--muted)}
.ts-v{font-size:14px;font-weight:700;font-family:monospace}
@media(max-width:768px){.dash-two{grid-template-columns:1fr}}

+.ff-wrap{margin:14px 0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 20px;backdrop-filter:blur(12px)}
+.ff-title{font-size:11px;color:var(--muted);letter-spacing:2px;margin-bottom:10px;text-transform:uppercase}
+.ff-bar{height:10px;background:rgba(255,255,255,.04);border-radius:5px;overflow:hidden;margin:8px 0}
+.ff-fill{height:100%;border-radius:5px;width:65%;transition:width 1s cubic-bezier(.22,1,.36,1)}
+.ff-val{font-size:24px;font-weight:700;font-family:monospace;text-align:center}

+.wf-wrap{margin:14px 0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;backdrop-filter:blur(12px)}
+.wf-title{font-size:11px;color:var(--muted);letter-spacing:2px;margin-bottom:10px;text-transform:uppercase}
+.wf-chart{width:100%;height:auto;display:block}
+.rb-wrap{display:flex;align-items:center;gap:12px;padding:10px 0}
+.rb-title{font-size:11px;color:var(--muted);letter-spacing:1px;flex:none}
+.rb-bar{display:flex;gap:3px;flex:1;max-width:200px}
+.rb-seg{height:10px;flex:1;border-radius:2px}
+.rb-lbl{font-size:13px;font-weight:700;font-family:monospace;flex:none}
+"""


JS = r"""
(()=> {
  const io=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting)e.target.classList.add("on")})},{threshold:.08});
  document.querySelectorAll(".reveal").forEach(el=>io.observe(el));
  const links=[...document.querySelectorAll(".toc a")];
  const map=new Map(links.map(a=>[a.getAttribute("href").slice(1),a]));
  const sio=new IntersectionObserver(es=>{
    let cur=null;for(const e of es){if(e.isIntersecting)cur=e.target}
    if(cur){links.forEach(a=>a.classList.remove("active"));const m=map.get(cur.id);if(m)m.classList.add("active")}
  },{rootMargin:"-10% 0px -80% 0px"});
  document.querySelectorAll("h2[id],h3[id]").forEach(h=>sio.observe(h));
  document.querySelectorAll(".cbar").forEach(r=>{
    const w=r.dataset.w;if(w){requestAnimationFrame(()=>{setTimeout(()=>r.style.width=w+"px",200)})}
  });
  document.querySelectorAll(".idx-val[data-val]").forEach(el=>{
    const target=parseFloat(el.dataset.val);const dur=800;const st=performance.now();
    const step=(now)=>{const p=Math.min(1,(now-st)/dur);const v=target*p;
      el.textContent=(v>=0?"+":"")+v.toFixed(2)+"%";if(p<1)requestAnimationFrame(step)};
    requestAnimationFrame(step);
  });
  const bar=document.querySelector(".progress"),topBtn=document.querySelector("#top");
  const onScroll=()=>{const h=document.documentElement;
    if(bar)bar.style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight)*100)+"%";
    if(topBtn)topBtn.style.display=h.scrollTop>600?"flex":"none"};
  window.addEventListener("scroll",onScroll,{passive:true});
  if(topBtn)topBtn.addEventListener("click",()=>window.scrollTo({top:0,behavior:"smooth"}));
  onScroll();
})();
"""

_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6"/></svg>'
_ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>'


def _toc_html(toc):
    items = []
    for lvl, t, anc in toc:
        cls = "l" + str(lvl)
        items.append(f'<li><a class="{cls}" href="#{anc}">{esc(t)}</a></li>')
    return '<ul class="toc">' + "".join(items) + "</ul>"


def build_html(text, path, title=None):
    title = title or ext_title(text, path)
    date = ext_date(path)
    badges = ext_badges(text, path)
    toc = ext_toc(text)
    ctx = Ctx()
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    body = render_blocks(lines, ctx)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    dash = build_dashboard(text)
    tag_html = "".join(
        f'<span class="tag{" hi" if i == 0 else ""}">{esc(b)}</span>'
        for i, b in enumerate(badges)
    )
    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body>
<div class="progress"></div>
<aside class="sidebar"><div class="brand"><div class="brand-mark">{_ICON}</div>
<div><div class="brand-name">超级研报</div><div class="brand-sub">Report Visualizer</div></div></div>
<div class="toc-title">目录</div>{_toc_html(toc)}
<div class="side-foot">生成于 {esc(now)}<br>不构成投资建议</div></aside>
<main class="main"><header class="hero"><div class="hero-tags">{tag_html}</div>
<h1>{esc(title)}</h1>
<div class="hero-meta"><span>数据日期 <b>{esc(date)}</b></span><span>生成时间 <b>{esc(now)}</b></span><span>模块 <b>report-web</b></span></div>
</header>
{dash}
<div class="content">
{body}
</div>
<footer class="foot">本页面由 report-web 从 Markdown 研报自动生成。数据来源：同花顺问财 / 东方财富妙想。本报告不构成投资建议。</footer>
</main>
<button id="top" title="回到顶部">{_ARROW}</button>
<script>{JS}</script></body></html>'''


def main():
    ap = argparse.ArgumentParser(description="炫酷网页版研报渲染器")
    ap.add_argument("--input", "-i", required=True)
    ap.add_argument("--output", "-o", required=True)
    ap.add_argument("--title", default=None)
    args = ap.parse_args()
    with open(args.input, encoding="utf-8") as f:
        text = f.read()
    page = build_html(text, args.input, title=args.title)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"written: {args.output} ({len(page)} chars)")


if __name__ == "__main__":
    main()
