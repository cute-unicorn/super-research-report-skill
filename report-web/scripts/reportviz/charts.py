"""SVG 图表构建：仪表盘、环形图、条形图、折线图、热力图、价格带、进度条等。"""

import html
import math
import re

from .textutil import esc, pnum, unit, fmt, vcls, r_inline

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
<text class="gauge-val" x="{cx}" y="{cy-8}" text-anchor="middle" fill="{color}">{fmt(value, unit)}</text>
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
        cls = vcls(ix["v"])
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
    if m["bal"]: cards.append(f'<div class="mgn-card"><span class="k">两融余额</span><span class="v">{fmt(m["bal"])}</span></div>')
    if m["net"] is not None: cards.append(f'<div class="mgn-card"><span class="k">融资净买入</span><span class="v {vcls(m["net"])}">{fmt(m["net"])}</span></div>')
    if m["chg"] is not None: cards.append(f'<div class="mgn-card"><span class="k">环比</span><span class="v {vcls(m["chg"])}">{m["chg"]:+.2f}%</span></div>')
    return '<div class="mgn-grid">' + "".join(cards) + "</div>"


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
    if d["rev_chg"] is not None: items.append(("营收同比", f'{d["rev_chg"]:+.2f}%', vcls(d["rev_chg"])))
    if d["profit_chg"] is not None: items.append(("归母同比", f'{d["profit_chg"]:+.2f}%', vcls(d["profit_chg"])))
    if d["margin"] is not None: items.append(("毛利率", f'{d["margin"]:.1f}%', ""))
    if d["roe"] is not None: items.append(("ROE", f'{d["roe"]:.2f}%', vcls(d["roe"])))
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
