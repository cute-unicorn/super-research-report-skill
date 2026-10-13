#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提取器与渲染器测试。

运行:
    python -m unittest discover -s report-web/tests -v
或:
    python report-web/tests/test_extract.py
"""

import os
import json
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)

from reportviz import extract as ex          # noqa: E402
from reportviz.assets import CSS, JS         # noqa: E402
from reportviz.template import build_html    # noqa: E402
from reportviz.textutil import pnum, fmt     # noqa: E402


def load_fixture(name):
    path = os.path.join(HERE, "fixtures", name)
    with open(path, encoding="utf-8") as f:
        return f.read(), path


class TestTextUtil(unittest.TestCase):
    def test_pnum_units(self):
        # 大数存在浮点误差，用相对误差比较
        self.assertAlmostEqual(pnum("1.28万亿") / 1.28e12, 1.0, places=9)
        self.assertAlmostEqual(pnum("135.92亿") / 135.92e8, 1.0, places=9)
        self.assertAlmostEqual(pnum("-35.64亿") / -35.64e8, 1.0, places=9)
        self.assertAlmostEqual(pnum("-49.47%"), -49.47, places=9)

    def test_pnum_none(self):
        self.assertIsNone(pnum("无数据"))
        self.assertIsNone(pnum(""))

    def test_fmt(self):
        self.assertEqual(fmt(1.28e12), "1.28万亿")
        self.assertEqual(fmt(-49.47, "%"), "-49.47%")


class TestDailyExtract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text, cls.path = load_fixture("daily_sample.md")

    def test_kind(self):
        self.assertEqual(ex.extract_for(self.text, self.path)[0], "daily")

    def test_indices(self):
        idx = {i["n"]: i["v"] for i in ex.ext_idx(self.text)}
        self.assertEqual(idx["上证指数"], -0.11)
        self.assertEqual(idx["创业板指"], -1.41)
        self.assertEqual(idx["沪深300"], -0.46)
        self.assertEqual(len(idx), 4)

    def test_index_points(self):
        pts = {i["n"]: i["p"] for i in ex.ext_idx(self.text)}
        self.assertEqual(pts["上证指数"], "3952.18")

    def test_breadth(self):
        b = ex.ext_brd(self.text)
        self.assertEqual(b["up"], 1200)
        self.assertEqual(b["down"], 4200)
        self.assertEqual(b["lu"], 82)
        self.assertEqual(b["ld"], 2)
        self.assertAlmostEqual(b["to"], 2.10e12, places=-8)

    def test_sectors(self):
        secs = {s["n"]: s["v"] for s in ex.ext_sec(self.text)}
        self.assertEqual(secs["氮肥"], 7.91)
        self.assertEqual(secs["疫苗"], -4.19)

    def test_sectors_no_prose_leak(self):
        """行业提取不得从"非共识 α"正文里误抓数据。

        α 标题含"从领涨到领跌"字样，早期实现会把它当成行业段落，
        把"市场一致预期"/"非共识点"也当成行业名。
        """
        names = [s["n"] for s in ex.ext_sec(self.text)]
        for bad in ("市场一致预期", "非共识点", "证伪条件"):
            self.assertNotIn(bad, names, f"行业列表混入正文标签: {bad}")
        # 样本中只有 5 个行业（3 涨 + 2 跌）
        self.assertEqual(len(names), 5, f"行业数量异常: {names}")
        self.assertNotIn("农业化肥链", names)

    def test_sector_markdown_tables(self):
        text = (
            "## 领涨行业\n\n"
            "| 行业 | 涨跌幅 |\n|---|---|\n"
            "| 疫苗 | +4.82% |\n"
            "| 半导体 | -2.92% |\n"
        )
        sectors = {item["n"]: item["v"] for item in ex.ext_sec(text)}
        self.assertEqual(sectors["疫苗"], 4.82)
        self.assertEqual(sectors["半导体"], -2.92)

    def test_deep_daily_is_not_stock(self):
        text = "# 深度分析与标的策略\n\n## 核心判断\n市场判断。\n"
        kind, _ = ex.extract_for(
            text,
            "每日市场研报_2026-10-07_深度分析与标的策略.md",
        )
        self.assertEqual(kind, "daily")

    def test_sector_data_dir_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            payload = {"datas": [
                {"指数简称": "印制电路板", "涨跌幅[20261013]": 6.389},
                {"指数简称": "元件", "涨跌幅[20261013]": 5.0135},
            ]}
            with open(os.path.join(root, "industry_top.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            sectors = {item["n"]: item["v"] for item in ex.ext_sec_from_data(root)}
            self.assertEqual(sectors["印制电路板"], 6.389)
            self.assertEqual(sectors["元件"], 5.0135)

    def test_margin(self):
        m = ex.ext_mgn(self.text)
        self.assertAlmostEqual(m["bal"], 12766.58e8, places=-6)
        self.assertAlmostEqual(m["fin"], 12655.30e8, places=-6)
        self.assertAlmostEqual(m["sec"], 111.27e8, places=-4)
        self.assertAlmostEqual(m["net"], -35.64e8, places=-6)
        self.assertAlmostEqual(m["chg"], -49.47, places=2)

    def test_margin_trend(self):
        pts = ex.ext_margin_trend(self.text)
        self.assertEqual(len(pts), 2)
        self.assertEqual(pts[0]["date"], "08-27")
        self.assertAlmostEqual(pts[1]["fin"], 1.266)

    def test_fundflow(self):
        f = ex.ext_fundflow(self.text)
        self.assertAlmostEqual(f["main"], -315.96e8, places=-6)
        self.assertAlmostEqual(f["xl"], -131.68e8, places=-6)

    def test_fundflow_section_scoped(self):
        text = (
            "# 每日市场研报\n\n"
            "## 行业资金流入\n"
            "银行主力净流入24.25亿元。\n\n"
            "## 十二、资金分析\n"
            "| 资金类别 | 净买入额 | 口径 |\n|---|---|---|\n"
            "| 机构资金（超大单） | -31.47亿元 | 超大单 |\n"
            "| 主力资金（超大单+大单） | -56.50亿元 | 主力 |\n"
            "| 散户资金（中单+小单） | +84.33亿元 | 中单+小单 |\n"
        )
        f = ex.ext_fundflow(text)
        self.assertAlmostEqual(f["main"], -56.50e8, places=-6)
        self.assertAlmostEqual(f["xl"], -31.47e8, places=-6)
        self.assertAlmostEqual(f["retail"], 84.33e8, places=-6)

    def test_macro(self):
        m = ex.ext_macro(self.text)
        self.assertAlmostEqual(m["cpi"], 0.5, places=2)

    def test_overseas(self):
        o = ex.ext_overseas(self.text)
        self.assertAlmostEqual(o["hsi"], 0.07, places=2)

    def test_toc_and_badges(self):
        self.assertTrue(len(ex.ext_toc(self.text)) >= 5)
        self.assertIn("每日·基础版", ex.ext_badges(self.text, "每日市场研报_2026-09-07.md"))


class TestStockExtract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text, cls.path = load_fixture("stock_sample.md")

    def test_kind(self):
        self.assertEqual(ex.extract_for(self.text, self.path)[0], "stock")

    def test_rating_and_target(self):
        d = ex.ext_stock(self.text)
        self.assertIn("增持", d["rating"])
        self.assertEqual(d["target"], "10.0-11.0")

    def test_valuation(self):
        d = ex.ext_stock(self.text)
        self.assertAlmostEqual(d["price"], 9.25, places=2)
        self.assertAlmostEqual(d["mcap"], 135.92e8, places=-6)
        self.assertAlmostEqual(d["pe_ttm"], 238.48, places=1)
        self.assertAlmostEqual(d["pb"], 2.06, places=2)

    def test_financials(self):
        d = ex.ext_stock(self.text)
        self.assertAlmostEqual(d["rev"], 17.10e8, places=-6)
        self.assertAlmostEqual(d["rev_chg"], -21.05, places=2)
        self.assertAlmostEqual(d["profit_chg"], -66.41, places=2)
        self.assertAlmostEqual(d["margin"], 39.05, places=2)
        self.assertAlmostEqual(d["roe"], -4.11, places=2)
        self.assertAlmostEqual(d["debt"], 59.12, places=2)

    def test_chips_and_tech(self):
        d = ex.ext_stock(self.text)
        self.assertAlmostEqual(d["chip_pct"], 60.7, places=1)
        self.assertAlmostEqual(d["c90lo"], 7.77, places=2)
        self.assertAlmostEqual(d["c90hi"], 10.47, places=2)
        self.assertAlmostEqual(d["c70lo"], 8.10, places=2)
        self.assertAlmostEqual(d["c70hi"], 9.75, places=2)
        self.assertAlmostEqual(d["ma20"], 8.46, places=2)
        self.assertAlmostEqual(d["ma60"], 8.15, places=2)
        self.assertAlmostEqual(d["rsi"], 60.0, places=0)


class TestDiagnostics(unittest.TestCase):
    """诊断必须能识别缺失字段，避免静默失败。"""

    def test_clean_report_has_no_missing_daily_fields(self):
        text, path = load_fixture("daily_sample.md")
        kind, data = ex.extract_for(text, path)
        missing = ex.diagnose(kind, data)
        self.assertEqual(missing, [], f"每日报告不应有缺失字段: {missing}")

    def test_empty_report_reports_missing(self):
        kind, data = ex.extract_for("# 空报告\n", "空报告_2026-01-01.md")
        missing = ex.diagnose(kind, data)
        self.assertTrue(len(missing) > 5, "空报告应报出大量缺失字段")


class TestRender(unittest.TestCase):
    """渲染产物必须包含关键可视化组件，且不得残留模板占位。"""

    def _render(self, fixture):
        text, path = load_fixture(fixture)
        return build_html(text, path)

    def test_daily_components(self):
        html = self._render("daily_sample.md")
        for token in ("idx-card", "hm-tile", "mgn-card", "dash-sec-t", "<svg"):
            self.assertIn(token, html, f"缺少组件: {token}")
        self.assertEqual(html.count("板块热力图"), 1, "板块热力图标题不应重复")

    def test_stock_components(self):
        html = self._render("stock_sample.md")
        for token in ("rating-banner", "sm-card", "pz-wrap", "ff-wrap", "ts-wrap"):
            self.assertIn(token, html, f"缺少组件: {token}")

    def test_no_placeholder_leak(self):
        for fixture in ("daily_sample.md", "stock_sample.md"):
            html = self._render(fixture)
            self.assertNotIn("{title}", html)
            self.assertNotIn("None", html.replace("NoneType", ""))

    def test_html_wellformed(self):
        for fixture in ("daily_sample.md", "stock_sample.md"):
            html = self._render(fixture)
            self.assertTrue(html.startswith("<!DOCTYPE html>"))
            self.assertEqual(html.count("<html"), 1)
            self.assertEqual(html.count("</html>"), 1)

    def test_self_contained(self):
        """自包含：不得引用外部 JS/CSS。"""
        for fixture in ("daily_sample.md", "stock_sample.md"):
            html = self._render(fixture)
            self.assertNotIn("<script src=", html)
            self.assertNotIn('rel="stylesheet"', html)

    def test_css_not_embedded_in_script(self):
        self.assertNotIn(".dash-sec{", JS, "CSS 不应混入 JavaScript 字符串")
        self.assertIn(".dash-sec{", CSS, "dash-sec 样式应存在于 CSS")

    def test_deep_daily_uses_data_dir_for_heatmap(self):
        text = "# 每日深度分析与标的策略\n\n## 核心判断\n市场判断。\n"
        path = "每日市场研报_2026-10-13_深度分析与标的策略.md"
        with tempfile.TemporaryDirectory() as root:
            payload = {"datas": [{"指数简称": "印制电路板", "涨跌幅[20261013]": 6.389}]}
            with open(os.path.join(root, "industry_top.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            html = build_html(text, path, data_dir=root)
            self.assertIn("hm-tile", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
