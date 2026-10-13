"""HTML 外壳与目录导航。"""

import datetime

from . import extract as ex
from .assets import CSS, JS
from .dashboards import build_dashboard
from .markdown import Ctx, render_blocks
from .textutil import esc

_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6"/></svg>'


_ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>'


def _toc_html(toc):
    items = []
    for lvl, t, anc in toc:
        cls = "l" + str(lvl)
        items.append(f'<li><a class="{cls}" href="#{anc}">{esc(t)}</a></li>')
    return '<ul class="toc">' + "".join(items) + "</ul>"


def build_html(text, path, title=None, data_dir=None):
    title = title or ex.ext_title(text, path)
    date = ex.ext_date(path)
    badges = ex.ext_badges(text, path)
    toc = ex.ext_toc(text)
    ctx = Ctx()
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    body = render_blocks(lines, ctx)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    dash = build_dashboard(text, path, data_dir)
    tag_html = "".join(
        f'<span class="tag{" hi" if i == 0 else ""}">{esc(b)}</span>'
        for i, b in enumerate(badges)
    )
    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style>
<script>document.documentElement.classList.add("js");</script></head><body>
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
