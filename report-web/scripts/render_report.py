#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Markdown 研报渲染为自包含 HTML 网页版研报。

用法:
    python render_report.py --input 报告.md --output 报告.html [--diagnose]

零第三方依赖。渲染逻辑见 reportviz 包。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportviz import extract as ex          # noqa: E402
from reportviz.template import build_html    # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Markdown 研报 → 自包含 HTML")
    ap.add_argument("--input", "-i", required=True, help="输入 Markdown 路径")
    ap.add_argument("--output", "-o", required=True, help="输出 HTML 路径")
    ap.add_argument("--title", default=None, help="自定义标题")
    ap.add_argument("--diagnose", action="store_true",
                    help="打印提取诊断（哪些字段没取到）")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        text = f.read()

    page = build_html(text, args.input, title=args.title)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"written: {args.output} ({len(page)} chars)")

    if args.diagnose:
        kind, data = ex.extract_for(text, args.input)
        missing = ex.diagnose(kind, data)
        print(f"report kind: {kind}")
        if missing:
            print(f"missing fields ({len(missing)}): " + ", ".join(missing))
        else:
            print("missing fields: none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
