"""Markdown 块级渲染：标题/列表/表格/引用/代码块，并为表格自动生成条形图。"""

import re

from .textutil import esc, r_inline, r_inline_hl, pnum, unit, fmt, vcls

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
        c = vcls(pnum(m.group(2)))
        return f'<span class="kv-k">{k}</span><span class="kv-v {c}">{v}</span>'
    return r_inline_hl(t)


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
        out.append("<p>" + r_inline_hl(" ".join(x.strip() for x in buf if x.strip())) + "</p>")
    return "\n".join(out)


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
            if c < len(r): vals.append(pnum(r[c])); us.add(unit(r[c]))
        ok = [v for v in vals if v is not None]
        if len(ok) >= max(2, int(len(vals)*0.7)) and len(us) == 1: ncs.append(c)
    if not ncs: return ""
    c = ncs[-1]; items = []
    for r in body:
        v = pnum(r[c]) if c < len(r) else None
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
        svg.append(f'<text class="cv" x="{pd+bw+8:.0f}" y="{y+14}">{esc(fmt(v))}</text>')
    svg.append("</svg>")
    return f'<div class="tc"><div class="tc-t">自动图表 · {esc(hdr[c].strip())}</div>{"".join(svg)}</div>'
