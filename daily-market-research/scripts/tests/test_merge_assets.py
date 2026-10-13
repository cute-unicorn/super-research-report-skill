#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merge_assets.py 的离线测试。"""

from __future__ import annotations

import json
import os
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.normpath(os.path.join(HERE, "..", "lib"))
sys.path.insert(0, LIB)

import merge_assets as ma  # noqa: E402

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def write(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


def main():
    global PASS, FAIL
    with tempfile.TemporaryDirectory(prefix="merge_assets_") as root:
        gold = os.path.join(root, "gold.json")
        oil = os.path.join(root, "oil.json")
        missing = os.path.join(root, "missing.json")
        write(gold, {"datas": [{"合约代码": "AU2612.SHF", "价格": 905.32}]})
        write(oil, {"datas": [
            {"合约代码": "AU2612.SHF", "价格": 905.32},
            {"合约代码": "BRN27J.ICE", "价格": 95.64},
        ]})

        payload = ma.merge([gold, oil, missing], "2026-10-13")
        check("合并后保留去重商品", len(payload["datas"]) == 2, str(payload["datas"]))
        check(
            "商品顺序稳定",
            [row["合约代码"] for row in payload["datas"]]
            == ["AU2612.SHF", "BRN27J.ICE"],
        )
        check("来源文件被记录", len(payload["sources"]) == 3)
        check(
            "合并结果补充 as_of 日期",
            all(row.get("时间") == "20261013" for row in payload["datas"]),
        )

        out = os.path.join(root, "macro_assets.json")
        args = ["--out", out, "--as-of", "2026-10-13"]
        for path in (gold, oil):
            args += ["--input", path]
        check("CLI 成功", ma.main(args) == 0)
        with open(out, "r", encoding="utf-8") as handle:
            written = json.load(handle)
        check("CLI 输出可解析", len(written["datas"]) == 2)

    print(f"\n===== RESULT: {PASS} passed, {FAIL} failed =====")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
