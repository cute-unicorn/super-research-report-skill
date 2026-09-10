"""文本与数值工具：转义、行内 Markdown、数值解析与格式化。"""

import html
import re


def esc(t):
    return html.escape(t, quote=True)


_CS = re.compile(r"`([^`]+)`")


def _inl(t):
    t = esc(t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
               lambda m: f'<a href="{esc(m.group(2))}">{m.group(1)}</a>', t)
    return t


def r_inline(t):
    """行内 Markdown → HTML，行内代码优先切分。"""
    parts, pos = [], 0
    for m in _CS.finditer(t):
        parts.append(_inl(t[pos:m.start()]))
        parts.append(f"<code>{esc(m.group(1))}</code>")
        pos = m.end()
    parts.append(_inl(t[pos:]))
    return "".join(parts)


_NUM = re.compile(r"([+\-]?)\s*([\d][\d,]*(?:\.\d+)?)\s*(万亿|亿|万|%)?")
_UNIT = re.compile(r"(万亿|亿|万|%)")

_SCALE = {"万亿": 1e12, "亿": 1e8, "万": 1e4, "%": 1.0}


def pnum(v):
    """解析带单位数值 → 归一化浮点数（万亿/亿/万 → 绝对值）。"""
    if v is None:
        return None
    m = _NUM.search(str(v).strip())
    if not m:
        return None
    sign = -1.0 if m.group(1) == "-" else 1.0
    try:
        num = float(m.group(2).replace(",", ""))
    except ValueError:
        return None
    return sign * num * _SCALE.get(m.group(3), 1.0)


def unit(v):
    m = _UNIT.search(str(v).strip())
    return m.group(1) if m else ""


def fmt(v, uh=""):
    if v is None:
        return "—"
    a = abs(v)
    if uh == "%":
        return f"{v:+.2f}%"
    if a >= 1e12:
        return f"{v / 1e12:.2f}万亿"
    if a >= 1e8:
        return f"{v / 1e8:.2f}亿"
    if a >= 1e4:
        return f"{v / 1e4:.1f}万"
    return f"{int(v)}" if v == int(v) else f"{v:.2f}"


def vcls(v):
    if v is None:
        return ""
    return "up" if v > 0 else ("down" if v < 0 else "flat")


_HL_NUM = re.compile(
    r'(?<!["/>=])([+\-]?[\d,]+\.?\d*\s*(?:%|万亿|亿|万|元|倍|点|家))(?!["</])'
)


def hl_nums(html_text):
    """给正文中的数值加高亮 class。"""
    return _HL_NUM.sub(r'<span class="num">\1</span>', html_text)


def r_inline_hl(t):
    """行内渲染 + 数值高亮。"""
    return hl_nums(r_inline(t))
