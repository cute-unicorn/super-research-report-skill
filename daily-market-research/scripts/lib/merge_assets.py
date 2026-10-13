#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把黄金、原油、铜等独立查询结果合并成 macro_assets.json。"""

from __future__ import annotations

import argparse
import json
import os
import sys


def load_rows(path: str) -> list[dict]:
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except Exception:
        return []
    for key in ("datas", "data"):
        rows = payload.get(key) if isinstance(payload, dict) else None
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def merge(paths: list[str], as_of: str = "") -> dict:
    rows: list[dict] = []
    sources: list[str] = []
    seen: set[str] = set()
    stamp = as_of.replace("-", "")
    for path in paths:
        if not path:
            continue
        sources.append(os.path.abspath(path))
        for row in load_rows(path):
            identity = str(
                row.get("合约代码")
                or row.get("品种代码")
                or row.get("品种简称")
                or row.get("指标")
                or ""
            )
            if identity and identity in seen:
                continue
            if identity:
                seen.add(identity)
            item = dict(row)
            if stamp and not item.get("时间"):
                item["时间"] = stamp
            rows.append(item)
    return {
        "success": True,
        "source": "merged-assets",
        "sources": sources,
        "datas": rows,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="合并全球商品查询结果")
    parser.add_argument("--out", required=True)
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--as-of", default="")
    args = parser.parse_args(argv)

    payload = merge(args.input, args.as_of)
    try:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"错误: 无法写入 {args.out}: {exc}", file=sys.stderr)
        return 2
    print(f"Merged assets: {len(payload['datas'])} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
