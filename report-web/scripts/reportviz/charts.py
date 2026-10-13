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
    # 每个指数一套独立强调色，避免整屏同色
    accents = ["#22d3ee", "#a78bfa", "#fbbf24", "#f472b6", "#34d399"]
    for i, ix in enumerate(indices):
        cls = vcls(ix["v"])
        pt = ix.get("p", "")
        acc = accents[i % len(accents)]
        cards.append(f'''<div class="idx-card" style="--d:{i*0.08}s;--acc:{acc}">
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
    """资金流向横向条形图（从零轴左右展开，红=净流入，绿=净流出）。"""
    if not items or len(items) < 2:
        return ""
    w, rh, bh = 520, 42, 20
    pad_l, pad_r = 110, 78
    h = len(items) * rh + 16
    mx = max(abs(v) for _, v in items) or 1
    zero = pad_l + (w - pad_l - pad_r) / 2
    half = (w - pad_l - pad_r) / 2

    parts = [
        f'<line x1="{zero:.1f}" y1="6" x2="{zero:.1f}" y2="{h-6}" '
        f'stroke="rgba(255,255,255,.12)" stroke-width="1"/>'
    ]
    for i, (lbl, v) in enumerate(items):
        y = 8 + i * rh
        bw = max(3.0, abs(v) / mx * half)
        col = "#ef4444" if v >= 0 else "#22c55e"
        if v >= 0:
            bx, tx, anchor = zero, zero + bw + 8, "start"
        else:
            bx, tx, anchor = zero - bw, zero - bw - 8, "end"
        parts.append(f'<text class="cl" x="8" y="{y+bh-3}" text-anchor="start">{esc(lbl)}</text>')
        parts.append(f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="{bh}" rx="4" fill="{col}" opacity=".8"/>')
        parts.append(f'<text class="cv" x="{tx:.1f}" y="{y+bh-3}" text-anchor="{anchor}" fill="{col}">{v:+,.0f}亿</text>')
    svg = f'<svg class="wf-chart" viewBox="0 0 {w} {h}">{"".join(parts)}</svg>'
    return f'<div class="wf-wrap reveal on">{svg}</div>'


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


# 涨跌配色：中国习惯红涨绿跌。用高饱和 HSL 让深浅区分更鲜明
GAIN_HUE = 354
LOSS_HUE = 158


def _flow_color(v, strong=True):
    """按数值正负与强度返回鲜明色。"""
    hue = GAIN_HUE if v >= 0 else LOSS_HUE
    return f"hsl({hue}, 92%, 58%)" if strong else f"hsl({hue}, 80%, 46%)"


def _heat_tone(v, maxabs=8.0):
    """热力图色阶：亮度随幅度变化，返回 (背景, 数值色, 左边框色)。"""
    inten = min(1.0, abs(v) / maxabs) if maxabs else 0
    if v >= 0:
        light = 26 + inten * 30
        return (f"hsl({GAIN_HUE}, 78%, {light:.0f}%)",
                f"hsl({GAIN_HUE}, 100%, {min(light + 26, 88):.0f}%)",
                f"hsl({GAIN_HUE}, 95%, 62%)")
    light = 24 + inten * 28
    return (f"hsl({LOSS_HUE}, 72%, {light:.0f}%)",
            f"hsl({LOSS_HUE}, 95%, {min(light + 28, 86):.0f}%)",
            f"hsl({LOSS_HUE}, 90%, 58%)")


def _heatmap(sectors):
    if not sectors: return ""
    maxabs = max((abs(s["v"]) for s in sectors), default=8.0) or 8.0
    tiles = []
    for s in sectors:
        v = s["v"]
        bg, tc, edge = _heat_tone(v, maxabs)
        tiles.append(
            f'<div class="hm-tile" style="background:{bg};border-left:3px solid {edge}">'
            f'<span class="hm-n">{esc(s["n"])}</span>'
            f'<span class="hm-v" style="color:{tc}">{v:+.2f}%</span></div>'
        )
    return f'<div class="hm-wrap"><div class="hm-grid">{"".join(tiles)}</div></div>'


def _key_points(idx, brd, sec, mgn, flow):
    """首屏要点横幅：把当日最该被看到的 4-5 个数拎出来。"""
    cards = []
    if sec:
        top = max(sec, key=lambda s: s["v"])
        bot = min(sec, key=lambda s: s["v"])
        cards.append(("领涨行业", top["n"], f'{top["v"]:+.2f}%', "gain"))
        cards.append(("领跌行业", bot["n"], f'{bot["v"]:+.2f}%', "loss"))
    if brd.get("up") is not None and brd.get("down") is not None:
        total = brd["up"] + brd["down"]
        ratio = brd["up"] / total * 100 if total else 0
        tone = "gain" if ratio >= 50 else "loss"
        cards.append(("涨跌家数", f'{brd["up"]} / {brd["down"]}', f"上涨占比 {ratio:.0f}%", tone))
    if brd.get("lu") is not None and brd.get("ld") is not None:
        tone = "gain" if brd["lu"] >= brd["ld"] * 3 else "loss"
        cards.append(("涨停 / 跌停", f'{brd["lu"]} / {brd["ld"]}', "情绪强度", tone))
    if flow.get("main") is not None:
        v = flow["main"] / 1e8
        cards.append(("主力资金", f"{v:+,.0f}亿", "净流入" if v >= 0 else "净流出",
                      "gain" if v >= 0 else "loss"))
    if mgn.get("bal"):
        cards.append(("两融余额", f'{mgn["bal"]/1e12:.2f}万亿', "杠杆水平", "neutral"))
    if not cards:
        return ""
    html = "".join(
        f'<div class="kp-card kp-{tone}"><span class="kp-k">{esc(k)}</span>'
        f'<span class="kp-v">{esc(v)}</span><span class="kp-sub">{esc(sub)}</span></div>'
        for k, v, sub, tone in cards
    )
    return f'<div class="kp-wrap"><div class="kp-title">今日要点</div><div class="kp-grid">{html}</div></div>'


def _breadth_chart(up, down, lu, ld):
    """涨跌家数对比（100% 堆叠条）+ 涨跌停对比。"""
    if up is None or down is None:
        return ""
    total = up + down
    if total == 0:
        return ""
    up_pct = up / total * 100
    parts = [f'''<div class="bc-wrap"><div class="bc-title">涨跌家数对比</div>
<div class="bc-stack">
  <div class="bc-seg bc-up" style="width:{up_pct:.1f}%"><span>涨 {up}</span></div>
  <div class="bc-seg bc-down" style="width:{100-up_pct:.1f}%"><span>跌 {down}</span></div>
</div>
<div class="bc-axis"><span>0%</span><span>上涨占比 {up_pct:.1f}%</span><span>100%</span></div>''']
    if lu is not None and ld is not None:
        mx = max(lu, ld, 1)
        parts.append(f'''<div class="bc-limits">
  <div class="bc-limit"><span class="bc-lk">涨停</span>
    <div class="bc-lt"><div class="bc-lf bc-up" style="width:{lu/mx*100:.0f}%"></div></div>
    <span class="bc-lv bc-upv">{lu}</span></div>
  <div class="bc-limit"><span class="bc-lk">跌停</span>
    <div class="bc-lt"><div class="bc-lf bc-down" style="width:{ld/mx*100:.0f}%"></div></div>
    <span class="bc-lv bc-downv">{ld}</span></div>
</div>''')
    parts.append("</div>")
    return "".join(parts)


def _margin_composition(fin, sec, total):
    """两融构成环形图：直观看融券占比极低。"""
    if not fin or not total:
        return ""
    sec = sec or 0
    fin_pct = fin / total * 100
    sec_pct = 100 - fin_pct
    r = 54
    circ = 2 * 3.14159 * r
    fin_len = circ * fin_pct / 100
    sec_len = circ - fin_len
    return f'''<div class="mc2-wrap"><div class="mc2-title">两融构成</div>
<svg class="mc2-donut" viewBox="0 0 160 160">
  <circle cx="80" cy="80" r="{r}" fill="none" stroke="hsl({LOSS_HUE},80%,50%)" stroke-width="18"
          stroke-dasharray="{sec_len:.1f} {circ:.1f}" transform="rotate(-90 80 80)"/>
  <circle cx="80" cy="80" r="{r}" fill="none" stroke="hsl({GAIN_HUE},88%,56%)" stroke-width="18"
          stroke-dasharray="{fin_len:.1f} {circ:.1f}" stroke-dashoffset="{-sec_len:.1f}" transform="rotate(-90 80 80)"/>
  <text x="80" y="74" text-anchor="middle" class="mc2-big">{total/1e12:.2f}万亿</text>
  <text x="80" y="94" text-anchor="middle" class="mc2-sm">两融余额</text>
</svg>
<div class="mc2-legend">
  <span><i class="mc2-dot" style="background:hsl({GAIN_HUE},88%,56%)"></i>融资 {fin_pct:.2f}%</span>
  <span><i class="mc2-dot" style="background:hsl({LOSS_HUE},80%,50%)"></i>融券 {sec_pct:.2f}%</span>
</div></div>'''


def _sector_bars(sectors, limit=12):
    """行业涨跌幅双向条形图（比色块更利于精确比较幅度）。"""
    if not sectors:
        return ""
    items = sorted(sectors, key=lambda s: s["v"], reverse=True)[:limit]
    if len(items) < 3:
        return ""
    w, rh, bh = 560, 30, 16
    pad_l, pad_r = 118, 64
    h = len(items) * rh + 14
    mx = max(abs(s["v"]) for s in items) or 1
    zero = pad_l + (w - pad_l - pad_r) / 2
    half = (w - pad_l - pad_r) / 2
    parts = [f'<line x1="{zero:.1f}" y1="4" x2="{zero:.1f}" y2="{h-4}" '
             f'stroke="rgba(255,255,255,.14)" stroke-width="1"/>']
    for i, s in enumerate(items):
        v = s["v"]
        y = 8 + i * rh
        bw = max(3.0, abs(v) / mx * half)
        col = _flow_color(v)
        if v >= 0:
            bx, tx, anc = zero, zero + bw + 7, "start"
        else:
            bx, tx, anc = zero - bw, zero - bw - 7, "end"
        parts.append(f'<text class="sb-n" x="6" y="{y+bh-3}">{esc(s["n"])}</text>')
        parts.append(f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="{bh}" rx="3" fill="{col}"/>')
        parts.append(f'<text class="sb-v" x="{tx:.1f}" y="{y+bh-3}" text-anchor="{anc}" fill="{col}">{v:+.2f}%</text>')
    return f'<div class="sb-wrap"><div class="sb-title">行业涨跌幅排名</div><svg class="sb-chart" viewBox="0 0 {w} {h}">{"".join(parts)}</svg></div>'


def _margin_line_chart(points):
    """两融余额折线图（双轴：融资余额用万亿，融券余额用亿）。

    两个序列量级相差百倍（融资约 2.5 万亿，融券约 200 亿），
    单轴绘制会让其中一条压成直线，且坐标单位会混淆，因此使用左右双轴。
    """
    if len(points) < 2: return ""
    w, h = 520, 190
    pad_l, pad_r, pad_t, pad_b = 56, 56, 24, 34
    fin_vals = [p["fin"] for p in points]
    sec_vals = [p["sec"] for p in points]

    def scale(vals):
        lo, hi = min(vals), max(vals)
        pad = (hi - lo) * 0.6 or max(abs(hi) * 0.02, 0.01)
        return lo - pad, hi + pad

    fmin, fmax = scale(fin_vals)
    smin, smax = scale(sec_vals)
    frng = fmax - fmin or 1
    srng = smax - smin or 1

    def x(i): return pad_l + (w - pad_l - pad_r) * i / (len(points) - 1)
    def yf(v): return pad_t + (h - pad_t - pad_b) * (1 - (v - fmin) / frng)
    def ys(v): return pad_t + (h - pad_t - pad_b) * (1 - (v - smin) / srng)

    fin_pts = " ".join(f"{x(i):.1f},{yf(p['fin']):.1f}" for i, p in enumerate(points))
    sec_pts = " ".join(f"{x(i):.1f},{ys(p['sec']):.1f}" for i, p in enumerate(points))
    area = (f"M {x(0):.1f},{yf(fin_vals[0]):.1f} "
            + " ".join(f"L {x(i):.1f},{yf(p['fin']):.1f}" for i, p in enumerate(points))
            + f" L {x(len(points)-1):.1f},{h-pad_b} L {x(0):.1f},{h-pad_b} Z")
    dots = "".join(
        f'<circle cx="{x(i):.1f}" cy="{yf(p["fin"]):.1f}" r="4" fill="#6366f1" '
        f'stroke="#0a0e1a" stroke-width="2"/>' for i, p in enumerate(points))
    labels = "".join(f'<text class="ax-lbl" x="{x(i):.1f}" y="{h-8}" text-anchor="middle">{p["date"]}</text>' for i, p in enumerate(points))
    # 左轴：融资余额（万亿）；右轴：融券余额（亿）
    yl = "".join(
        f'<text class="ax-lbl" x="{pad_l-6}" y="{yf(v)+4:.1f}" text-anchor="end">{v:.2f}万亿</text>'
        for v in [fmin, fmin + frng / 2, fmax])
    yr = "".join(
        f'<text class="ax-lbl" x="{w-pad_r+6}" y="{ys(v)+4:.1f}" text-anchor="start">{v:.0f}亿</text>'
        for v in [smin, smin + srng / 2, smax])
    vrules = "".join(
        f'<line x1="{pad_l}" y1="{pad_t + (h-pad_t-pad_b)*k:.1f}" x2="{w-pad_r}" '
        f'y2="{pad_t + (h-pad_t-pad_b)*k:.1f}" stroke="rgba(255,255,255,.05)" stroke-width="1"/>'
        for k in (0, 0.5, 1))
    return f'''<div class="ml-wrap reveal on"><div class="ml-title">两融余额走势</div>
<svg class="mlchart" viewBox="0 0 {w} {h}">
<defs><linearGradient id="mlg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#6366f1" stop-opacity=".3"/><stop offset="100%" stop-color="#6366f1" stop-opacity="0"/></linearGradient></defs>
{vrules}
<path d="{area}" fill="url(#mlg)"/>
<polyline class="ml-line" points="{fin_pts}" fill="none" stroke="#6366f1" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
<polyline points="{sec_pts}" fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="5 4" opacity=".85"/>
{dots}{labels}{yl}{yr}
</svg>
<div class="ml-legend"><span class="ml-dot" style="background:#6366f1"></span>融资余额（左轴/万亿） <span class="ml-dot" style="background:#f59e0b"></span>融券余额（右轴/亿）</div>
</div>'''


def _macro_chips(data):
    if not data: return ""
    # 每个指标独立配色，并给出量纲提示
    spec = {
        "cpi": ("CPI", "%", "#fbbf24"),
        "ppi": ("PPI", "", "#f472b6"),
        "m2": ("M2", "%", "#22d3ee"),
        "she": ("社融", "亿", "#a78bfa"),
        "lpr": ("LPR", "%", "#34d399"),
        "usdcny": ("USDCNY", "", "#fb923c"),
    }
    chips = []
    for k, (lbl, u, col) in spec.items():
        if k in data and data[k] is not None:
            v = data[k]
            if k == "she":
                disp = f"{v/1e12:.2f}万亿" if v > 1e10 else f"{v:.0f}{u}"
            elif k == "ppi":
                disp = f"{v:.1f}{u}"          # PPI 是指数，保留一位小数
            else:
                disp = f"{v:g}{u}"
            chips.append(
                f'<div class="mc-chip" style="--acc:{col}">'
                f'<span class="mc-k">{lbl}</span>'
                f'<span class="mc-v" style="color:{col}">{esc(disp)}</span></div>')
    return f'<div class="mc-wrap"><div class="mc-title">宏观指标</div><div class="mc-grid">{"".join(chips)}</div></div>'


def _overseas_bars(data):
    if not data: return ""
    labels = {"nasdaq":"纳斯达克","dow":"道琼斯","sp500":"标普500","hsi":"恒生指数","gold":"黄金","oil":"原油","btc":"比特币"}
    items = [(labels[k], v) for k, v in data.items() if v is not None]
    if not items: return ""
    items.sort(key=lambda kv: kv[1])
    bars = []
    mx = max(abs(v) for _, v in items) or 1
    for name, v in items:
        pct = abs(v) / mx * 100
        col = _flow_color(v)
        bars.append(f'''<div class="ob-row"><span class="ob-n">{name}</span>
<div class="ob-track"><div class="ob-fill" style="width:{pct:.0f}%;background:linear-gradient(90deg,{col}55,{col})"></div></div>
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
    # mcap / rev 在提取阶段已归一化为绝对值，展示时需换算回"亿"
    if d["mcap"] is not None: items.append(("总市值", f'{d["mcap"] / 1e8:,.0f} 亿', ""))
    if d["pe"] is not None: items.append(("PE TTM", f'{d["pe"]:.1f}', ""))
    if d["pb"] is not None: items.append(("PB", f'{d["pb"]:.2f}', ""))
    if d["div"] is not None: items.append(("股息率", f'{d["div"]:.2f}%', ""))
    if d["rev"] is not None: items.append(("最新营收", f'{d["rev"] / 1e8:,.1f} 亿', ""))
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
