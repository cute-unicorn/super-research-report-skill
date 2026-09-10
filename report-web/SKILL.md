---
name: report-visualizer
description: 将 Markdown 研报渲染为炫酷的玻璃拟态网页（自包含 HTML）。当用户要求"把研报做成网页"、"可视化研报"、"生成网页版研报"或"渲染 HTML 报告"时使用。可选模块。
---

# 网页版研报渲染

将任意 Markdown 研报转换为单文件自包含 HTML（零依赖，双击即可离线打开）。

## 能力

- 玻璃拟态暗色主题，带渐变光效与动画
- 自动提取指数涨跌、涨跌家数、领涨领跌板块、两融水平生成仪表盘
- 市场宽度环形图、行业横向条形图、关键指标卡片
- 数字滚动动画、滚动揭示、阅读进度条
- 侧边目录导航（支持高亮当前章节）
- 表格自动生成条形图
- 提取诊断：未取到的字段会显式列出，不再静默失败

## 用法

```bash
python "<模块目录>/report-web/scripts/render_report.py" \
    --input "<报告.md>" --output "<报告.html>" \
    [--title "自定义标题"] [--diagnose]
```

`--diagnose` 会打印报告类型与缺失字段清单，用于排查图表为何不显示。

## 结构

```text
report-web/
├── SKILL.md
├── scripts/
│   ├── render_report.py      # CLI 入口
│   └── reportviz/
│       ├── textutil.py       # 转义/数值解析/格式化
│       ├── extract.py        # 从 Markdown 提取结构化数据
│       ├── markdown.py       # 块级 Markdown → HTML
│       ├── charts.py         # SVG 图表构建
│       ├── dashboards.py     # 仪表盘装配
│       ├── template.py       # HTML 外壳
│       └── assets.py         # 内联 CSS/JS
└── tests/
    ├── fixtures/             # 样例研报
    └── test_extract.py       # 26 项断言
```

## 自测

```bash
python report-web/tests/test_extract.py
```

覆盖：数值解析、每日报告提取（指数/宽度/行业/两融/资金/宏观/海外）、
个股报告提取（评级/估值/财务/筹码/技术）、诊断、渲染组件、自包含性。

## 依赖

无。仅需 Python 3 标准库。

## 已知边界

- 提取基于正则匹配 Markdown 文本，报告写法变化时可能漏匹配。
  新增字段后请同步补充 `tests/fixtures/` 与断言。
- 全文档扫描（不设行数上限）。早期版本用 `splitlines()[:N]` 做微优化，
  导致数据位置后移时静默失效，已弃用。
