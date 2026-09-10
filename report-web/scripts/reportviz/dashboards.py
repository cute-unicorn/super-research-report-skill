"""仪表盘装配：把提取数据与图表组件拼成首屏可视化区块。"""

from . import extract as ex
from .charts import (
    _index_cards, _donut, _heatmap, _mgn_cards, _waterfall, _risk_bar, _margin_line_chart,
    _macro_chips, _overseas_bars, _rating_card, _stock_metrics, _fin_bars, _price_zone,
    _tech_strip, _sentiment_gauge, _fundflow_card,
    _key_points, _breadth_chart, _margin_composition, _sector_bars,
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
    flow = ex.ext_fundflow(text)
    parts = []

    # 1) 要点横幅：最该被看到的信息
    kp = _key_points(idx, brd, sec, mgn, flow)
    if kp: parts.append(kp)

    # 2) 指数
    if idx: parts.append('<div class="dash-sec"><div class="dash-sec-t">指数表现</div>' + _index_cards(idx) + '</div>')

    # 3) 情绪 + 两融卡片
    sg = _sentiment_gauge(brd["up"], brd["down"])
    dn = _donut(brd["up"], brd["down"], brd["lu"], brd["ld"])
    mc2 = _margin_composition(mgn.get("fin"), mgn.get("sec"), mgn.get("bal"))
    if sg or dn or mc2:
        row = ""
        if dn: row += f'<div class="dash-cell" style="flex:0 0 220px">{dn}</div>'
        if sg: row += f'<div class="dash-cell" style="flex:0 0 260px">{sg}</div>'
        if mc2: row += f'<div class="dash-cell" style="flex:0 0 220px">{mc2}</div>'
        mgn_cards = _mgn_cards(mgn)
        if mgn_cards: row += f'<div style="flex:1;min-width:260px">{mgn_cards}</div>'
        if row: parts.append(f'<div class="dash-row" style="align-items:stretch">{row}</div>')

    # 4) 涨跌家数对比
    bc = _breadth_chart(brd.get("up"), brd.get("down"), brd.get("lu"), brd.get("ld"))
    if bc: parts.append('<div class="dash-sec"><div class="dash-sec-t">市场宽度</div>' + bc + '</div>')

    # 5) 两融走势
    ml = _margin_line_chart(mline_pts)
    if ml: parts.append('<div class="dash-sec"><div class="dash-sec-t">两融走势</div>' + ml + '</div>')

    # 6) 行业：热力图 + 排序条形图
    if sec: parts.append('<div class="dash-sec"><div class="dash-sec-t">板块热力图</div>' + _heatmap(sec) + '</div>')
    sb = _sector_bars(sec)
    if sb: parts.append('<div class="dash-sec"><div class="dash-sec-t">行业排名</div>' + sb + '</div>')

    # 7) 资金流向
    wf_items = []
    for key, label in (("xl", "机构(超大单)"), ("main", "主力"), ("large", "大户"), ("retail", "散户")):
        if flow.get(key) is not None:
            wf_items.append((label, flow[key] / 1e8))
    wf = _waterfall(wf_items)
    if wf:
        parts.append('<div class="dash-sec"><div class="dash-sec-t">资金流向</div>' + wf + '</div>')
    rb = _risk_bar(5)
    if rb: parts.append(rb)
    mc = _macro_chips(macro)
    ob = _overseas_bars(ovs)
    if mc or ob:
        row = ""
        if mc: row += mc
        if ob: row += ob
        parts.append('<div class="dash-sec"><div class="dash-sec-t">宏观与海外</div>' + f'<div class="dash-two">{row}</div>' + '</div>')
    if not parts: return ""
    return '<div class="dashboard">' + "".join(parts) + "</div>"
