# 超级研报skill

基于 Codex 技能体系的 A 股研究自动化工具集，把“每日市场研报”和“个股机构级深度研报”做成可复用的 Skill，覆盖三类研报能力：

1. 每日市场研报（基础版）
2. 每日市场研报（深度分析与标的策略）
3. 个股机构级深度研报

数据来自同花顺问财（Iwencai）与东方财富妙想（MX）。报告自动抓取行情、宏观、政策、公告、研报、情绪、资金、两融等维度，内置“非共识 α 观点”模块、板块与个股策略、以及逐层风险提示。

> 本项目仅供学习研究，不构成任何投资建议。

## 目录结构

```text
超级研报skill/
├── daily-market-research/           # 每日市场研报技能
│   ├── SKILL.md                     # 技能主入口与工作流
│   ├── agents/openai.yaml           # 技能界面配置
│   ├── references/report_spec.md    # 基础版 + 深度版研报规范
│   └── scripts/
│       ├── fetch_daily_data.ps1     # 同花顺问财数据抓取
│       └── fetch_miaoxiang_data.ps1 # 东方财富妙想数据抓取
└── stock-deep-research/             # 个股机构级深度研报技能
    ├── SKILL.md
    ├── references/report_spec.md
    └── scripts/fetch_stock_data.ps1
```

## 环境要求

- Windows + PowerShell
- Python 3
- Codex（技能默认目录 `%USERPROFILE%\.codex\skills`）
- 已安装依赖技能：
  - Iwencai 系列：`hithink-market-query`、`hithink-industry-query`、`hithink-macro-query`、`hithink-finance-query`、`hithink-insresearch-query`、`hithink-zhishu-query`、`announcement-search`、`news-search`、`report-search`
  - 妙想系列：`mx-data`、`mx-search`、`mx-xuangu`

## 环境变量

在 PowerShell profile 中配置（请勿提交真实密钥）：

```powershell
$env:IWENCAI_BASE_URL = "https://openapi.iwencai.com"
$env:IWENCAI_API_KEY = "<你的问财 API Key>"
$env:MX_APIKEY = "<你的妙想 API Key>"
```

## 安装

将本仓库克隆或复制到 Codex 技能根目录：

```powershell
git clone https://github.com/cute-unicorn/super-research-report-skill.git
Copy-Item -LiteralPath "超级研报skill\daily-market-research" -Destination "$env:USERPROFILE\.codex\skills" -Recurse
Copy-Item -LiteralPath "超级研报skill\stock-deep-research" -Destination "$env:USERPROFILE\.codex\skills" -Recurse
```

技能中的 `D:\codex\研报` 为作者本地默认输出目录，可通过抓取脚本的 `-Workspace` 参数与 Codex 提示语自行替换。

## 使用方法

### 每日市场研报

在 Codex 中直接要求：

```text
使用 daily-market-research 生成今日两份市场研报
```

手动抓取数据：

```powershell
powershell -ExecutionPolicy Bypass -File "<技能目录>\daily-market-research\scripts\fetch_daily_data.ps1" -Workspace "D:\codex\研报"
powershell -ExecutionPolicy Bypass -File "<技能目录>\daily-market-research\scripts\fetch_miaoxiang_data.ps1" -Workspace "D:\codex\研报"
```

产出：

- `每日市场研报_YYYY-MM-DD.md`
- `每日市场研报_YYYY-MM-DD_深度分析与标的策略.md`

### 个股机构级深度研报

```text
使用 stock-deep-research 深度分析 <股票名称>
```

产出：

- `深度研报_公司简称_YYYY-MM-DD.md`

## 研报能力

### 每日市场研报（基础版）

1. 市场总览
2. 行业与风格
3. 宏观与流动性
4. 海外市场与全球资产
5. 政策与要闻（逐条“内容解读 + 影响分析”）
6. 重要公告与事件
7. 机构观点
8. 关注方向与风险提示
9. 非共识 α 观点
10. 情绪分析
11. 两融水平及分析
12. 资金分析
13. 风险提示（汇总）

### 每日市场研报（深度分析与标的策略）

总体分析、海外市场与全球资产、政策与要闻、重要公告、机构观点、情绪与资金分析（含两融水平及分析）、非共识 α 观点、板块推荐（市场驱动 + 政策驱动，每个板块带龙头股）、个股深度分析（估值/财务/资金/技术/消息五维度 + 短中长期 + 止盈止损 + 风险）、风险提示汇总。

### 个股机构级深度研报

客观评级框、核心判断、基础五维度、产业链拆解、政策链分析、非共识 α 观点、情景推演、详细风险提示。

## 数据来源与纪律

- 所有数据来自接口实际返回，缺失字段写“未取到”，禁止编造。
- 两融水平使用沪深两市合计口径（融资余额、融券余额、两融余额、融资净买入、融资买入额、环比）。
- 机构/主力/大户/散户资金为近似口径：超大单、超大单+大单、大单、中单+小单。
- 止盈止损、目标价均为示例风控参数，不构成保证。
- 板块与个股动态选择，不以固定备选池生成。
- 报告末尾注明数据来源与“不构成投资建议”。

## 许可

[MIT](LICENSE)
