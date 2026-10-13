---
name: report-visualizer
description: 将 Markdown 研报渲染为炫酷的玻璃拟态网页（自包含 HTML）。当用户要求"把研报做成网页"、"可视化研报"、"生成网页版研报"或"渲染 HTML 报告"时使用。可选模块。
---

# 网页版研报渲染

将任意 Markdown 研报转换为单文件自包含 HTML（零依赖，双击即可离线打开）。

## 能力

- 玻璃拟态暗色主题，带渐变光效与动画
- 首屏"今日要点"横幅：领涨/领跌行业、涨跌家数、涨跌停、主力资金、两融余额
- 指数卡片带独立强调色；涨跌用高饱和 HSL 色阶区分强弱
- 图表组件：市场宽度堆叠条、情绪仪表盘、涨跌家数环形图、两融构成环形图、
  两融双轴折线、板块热力图、行业涨跌幅双向条形图、资金流向双向条形图、
  宏观指标芯片、海外市场条形图、风险等级条
- 个股：评级横幅、指标卡（含环形进度）、财务对比条、筹码价格带、技术信号、主力资金条
- 数字滚动动画、滚动揭示、阅读进度条
- 侧边目录导航（支持高亮当前章节）
- 表格自动生成条形图
- 提取诊断：未取到的字段会显式列出，不再静默失败

## 设计约定

- 红涨绿跌（A 股习惯），色相固定：涨 `hsl(354,…)`、跌 `hsl(158,…)`，
  用亮度表达幅度，避免整屏同色。
- 关键组件不依赖入场动画显示：指数卡早期用 `animation ... both` 加延迟，
  静态渲染或无头截图会停在 `opacity:0` 显示空白，已改为纯 transition。
- `.reveal` 仅在 `<html class="js">` 下隐藏，无 JS 时内容始终可见。
- CSS 规则不得带 `+` 前缀（曾被误写入，导致浏览器丢弃整条规则）。

## 用法

```bash
python "<模块目录>/report-web/scripts/render_report.py" \
    --input "<报告.md>" --output "<报告.html>" \
    [--title "自定义标题"] [--data-dir "<报告对应data目录>"] [--diagnose]
```

`--diagnose` 会打印报告类型与缺失字段清单，用于排查图表为何不显示。
若未显式传入 `--data-dir`，渲染器会按文件名日期自动寻找同级 `data/YYYY-MM-DD`。
深度日报会优先按文件名识别为日报，避免其中的“核心判断”被误判为个股报告。

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
    └── test_extract.py       # 33 项断言
```

## 自测

```bash
python report-web/tests/test_extract.py
```

覆盖：数值解析、每日报告提取（指数/宽度/表格行业/两融/资金/宏观/海外）、
深度日报分类、data 目录行业回退、个股报告提取（评级/估值/财务/筹码/技术）、
诊断、渲染组件、自包含性和 CSS/JS 分离。

## 依赖

无。仅需 Python 3 标准库。

## 已知边界

- 提取基于正则匹配 Markdown 文本，报告写法变化时可能漏匹配。
  新增字段后请同步补充 `tests/fixtures/` 与断言。
- 全文档扫描（不设行数上限）。早期版本用 `splitlines()[:N]` 做微优化，
  导致数据位置后移时静默失效，已弃用。
