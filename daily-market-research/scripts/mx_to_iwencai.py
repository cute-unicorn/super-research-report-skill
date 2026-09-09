#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把妙想选股(mx-xuangu)原始 JSON 转成问财同构结构，供下游统一消费。

用法:
    python mx_to_iwencai.py <mx_raw.json> <out.json> [--query "原始查询"]

输出结构与问财接口保持一致:
    {"success": bool, "query": str, "code_count": int, "returned_count": int,
     "datas": [ {中文列名: 值, ...}, ... ], "source": "mx-xuangu"}
"""

import argparse
import json
import sys


def load_mx(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    # 妙想返回层级: {data: {data: {allResults: {result: {columns, dataList}}}}}
    node = raw
    for key in ("data", "data", "allResults", "result"):
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return [], []
    if not isinstance(node, dict):
        return [], []
    columns = node.get("columns") or []
    rows = node.get("dataList") or []
    return columns, rows


def normalize_columns(columns):
    """列 key -> 可读中文名。同名列用日期后缀区分。"""
    mapping = {}
    used = {}
    for col in columns:
        key = col.get("key")
        if not key:
            continue
        title = (col.get("title") or key).strip()
        date_msg = col.get("dateMsg")
        if date_msg:
            title = f"{title}[{str(date_msg).replace('.', '')}]"
        # 去重
        if title in used:
            used[title] += 1
            title = f"{title}_{used[title]}"
        else:
            used[title] = 0
        mapping[key] = title
    return mapping


def convert(columns, rows):
    mapping = normalize_columns(columns)
    datas = []
    for row in rows:
        item = {}
        for key, value in row.items():
            name = mapping.get(key, key)
            if value is None or value == "" or value == "--":
                continue
            item[name] = value
        if item:
            datas.append(item)
    return datas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--query", default="")
    args = ap.parse_args()

    columns, rows = load_mx(args.input)
    datas = convert(columns, rows)
    payload = {
        "success": bool(datas),
        "query": args.query,
        "code_count": len(datas),
        "returned_count": len(datas),
        "datas": datas,
        "source": "mx-xuangu",
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"converted {len(datas)} rows -> {args.output}")
    return 0 if datas else 1


if __name__ == "__main__":
    sys.exit(main())
