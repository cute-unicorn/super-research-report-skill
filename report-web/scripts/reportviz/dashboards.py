"""仪表盘装配：把提取数据与图表组件拼成首屏可视化区块。"""

from . import extract as ex
from .charts import (
    _index_cards, _donut, _heatmap, _mgn_cards, _waterfall, _risk_bar, _margin_line_chart,
    _macro_chips, _overseas_bars, _rating_card, _stock_metrics, _fin_bars, _price_zone,
    _tech_strip, _sentiment_gauge, _fundflow_card,
)

def build_dashboard(text):
    """生成仪表盘 HTML 块（如果数据可用）"""
    if "客观评级" in text[:500] or "核心判断" in text[:800]:
        return build_stock_dash(text)
    return build_daily_dash(text)


def build_stock_dash(text):
    d = ex.ext_stock(text)
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


def build_daily_dash(text):
    idx = ex.ext_idx(text)
    brd = ex.ext_brd(text)
    sec = ex.ext_sec(text)
    mgn = ex.ext_mgn(text)
    macro = ex.ext_macro(text)
    ovs = ex.ext_overseas(text)
    mline_pts = ex.ext_margin_trend(text)
    parts = []
    if idx: parts.append('<div class="dash-sec"><div class="dash-sec-t">指数表现</div>' + _index_cards(idx) + '</div>')
    sg = _sentiment_gauge(brd["up"], brd["down"])
    dn = _donut(brd["up"], brd["down"], brd["lu"], brd["ld"])
    if sg or dn:
        row = ""
        if dn: row += f'<div class="dash-cell" style="flex:0 0 220px">{dn}</div>'
        if sg: row += f'<div class="dash-cell" style="flex:0 0 260px">{sg}</div>'
        mgn_cards = _mgn_cards(mgn)
        if mgn_cards: row += f'<div style="flex:1;min-width:260px">{mgn_cards}</div>'
        if row: parts.append(f'<div class="dash-row" style="align-items:stretch">{row}</div>')
    ml = _margin_line_chart(mline_pts)
    if ml: parts.append('<div class="dash-sec"><div class="dash-sec-t">两融走势</div>' + ml + '</div>')
    if sec: parts.append('<div class="dash-sec"><div class="dash-sec-t">板块热力图</div>' + _heatmap(sec) + '</div>')
    ff_data = ex.ext_fundflow(text)
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
        parts.append('<div class="dash-sec"><div class="dash-sec-t">宏观与海外</div>' + f'<div class="dash-two">{row}</div>' + '</div>')
    if not parts: return ""
    return '<div class="dashboard">' + "".join(parts) + "</div>"
