# 超级研报skill

基于 Codex 技能体系的 A 股研究自动化工具集，把“每日市场研报”和“个股机构级深度研报”做成可复用的 Skill，覆盖三类研报能力：

1. 每日市场研报（基础版）
2. 每日市场研报（深度分析与标的策略）
3. 个股机构级深度研报

数据来自同花顺问财（Iwencai）与东方财富妙想（MX）。报告自动抓取行情、宏观、政策、公告、研报、情绪、资金、两融等维度，内置“非共识 α 观点”模块、板块与个股策略、以及逐层风险提示。

> 本项目仅供学习研究，不构成任何投资建议。

## 功能特性

- 三份报告能力：每日研报基础版、每日研报深度分析与标的策略版、个股机构级深度研报。
- 双数据源交叉验证：同花顺问财为主，东方财富妙想作备用与近 5 日趋势校验。
- 动态选股选板块：板块与个股完全由当日数据决定，无固定备选池，避免“旧名单复读”。
- 非共识 α 观点：每条给出市场一致预期 / 非共识点 / α 来源与兑现路径 / 证伪条件。
- 政策逐条解读：国内外政策与要闻先“内容解读”再“影响分析”。
- 两融水平及分析：沪深两市合计口径，覆盖水平、边际、活跃度、杠杆结构、信号解读、去杠杆风险。
- 情绪与资金结构：北向、涨跌停、连板、机构/主力/大户/散户资金（近似口径）。
- 多期财务序列：个股研报自动抓取 12 个报告期，区分单季度与累计口径，计算收现比、应收账款/营收增速差、合同负债同比、经营现金流/净利润等派生指标。
- 数据质量门禁：日频数据与个股多期数据都有独立校验；存在 CRITICAL 时拒绝生成结论，WARN 必须在报告中解释。
- 报告结构验收：日报和个股研报生成后自动检查固定章节、政策逐条解读、非共识、风险提示、关键财务字段与免责声明。
- 宏观数据补全：CPI、PPI、M2、社融、LPR、汇率独立抓取；黄金、原油、铜拆分查询后合并。
- 风控纪律：每只个股与板块都给出止损、止盈与风险提示；目标价与止损均为示例参数。
- 可接入定时自动化：配合 Codex 定时任务，每日自动产出并保存研报。
- 可选网页可视化：将研报渲染为玻璃拟态风格的自包含 HTML 页面（零依赖，双击打开）。
- 三级数据兜底：问财 → 自动重试 → 东方财富妙想选股，关键数据缺失时拒绝生成报告。

## 目录结构

```text
超级研报skill/
├── daily-market-research/           # 每日市场研报技能
│   ├── SKILL.md                     # 技能主入口与工作流
│   ├── agents/openai.yaml           # 技能界面配置
│   ├── references/report_spec.md    # 基础版 + 深度版研报规范
│   └── scripts/
│       ├── fetch_daily_data.ps1     # 同花顺问财数据抓取（含重试/兜底/校验）
│       ├── fetch_miaoxiang_data.ps1 # 东方财富妙想数据抓取
│       ├── mx_to_iwencai.py         # 妙想结果 → 问财同构结构转换器
│       ├── lib/common.ps1           # 共享工具函数
│       ├── lib/validate_facts.py    # 日频数据一致性校验
│       ├── lib/validate_report.py   # 日报结构验收
│       ├── lib/merge_assets.py      # 全球商品数据合并
│       └── tests/                   # 数据门禁、报告结构、PowerShell 回归与抓取门禁测试
└── stock-deep-research/             # 个股机构级深度研报技能
    ├── SKILL.md
    ├── references/report_spec.md
    └── scripts/
        ├── fetch_stock_data.ps1
        ├── lib/build_timeseries.py       # 单季度/累计财务时间序列
        ├── lib/validate_stock_facts.py   # 个股数据质量门禁
        ├── lib/validate_report.py        # 个股研报结构验收
        └── tests/
            ├── test_timeseries.py        # 27 项离线测试
            ├── test_fetch_gate.ps1       # 严格门禁端到端测试
            └── stub_source.py            # 离线数据源 stub
└── report-web/                      # 可选：网页可视化模块
    ├── SKILL.md
    ├── scripts/
    │   ├── render_report.py         # CLI 入口
    │   └── reportviz/               # 提取/渲染/图表/模板模块
    └── tests/                       # 33 项断言 + 样例研报
```

## 自测

修改抓取脚本后运行：

```powershell
powershell -ExecutionPolicy Bypass -File "daily-market-research\scripts\tests\test_common.ps1"
```

覆盖交易日回退、JSON 解析、妙想转换器、兜底链路（强制问财失败 → 妙想补数）与日频校验门禁。

修改个股多期财务抓取或门禁后运行：

```powershell
python "stock-deep-research\scripts\tests\test_timeseries.py"
```

覆盖时间序列合并、单季度/累计口径、收现比、应收账款/营收增速差、合同负债、经营现金流背离和派生值篡改拦截。

修改报告结构验收器后运行：

```powershell
python "daily-market-research\scripts\tests\test_validate_report.py"
python "daily-market-research\scripts\tests\test_merge_assets.py"
powershell -ExecutionPolicy Bypass -File "daily-market-research\scripts\tests\test_fetch_gate.ps1"
powershell -ExecutionPolicy Bypass -File "stock-deep-research\scripts\tests\test_fetch_gate.ps1"
```

覆盖日报章节完整性、个股研报关键字段、缺失章节拦截、占位符告警、两份验收器同步，以及默认严格门禁的非零退出与 `AllowCritical` 调试旁路。

修改网页渲染器后运行：

```bash
python report-web/tests/test_extract.py
```

覆盖数值解析、每日/个股报告字段提取、提取诊断、渲染组件完整性与自包含性。

## 工作流概览

```text
1. 确定日期与输出目录
2. 运行 fetch_daily_data.ps1 抓取问财数据（行情/宏观/政策/公告/研报/情绪/资金/两融）
3. 可选运行 fetch_miaoxiang_data.ps1 抓取妙想备用数据（交叉验证/近5日趋势/个股补充）
4. 读取 data/YYYY-MM-DD 下的 JSON，动态扫描涨幅榜、资金榜、涨停、评级、金股、政策催化
5. 按当日数据选定板块与龙头股，生成基础版研报
6. 在基础版之上生成深度分析与标的策略版（板块 + 龙头 + 个股五维度）
7. 验证：章节完整性、α 条数、政策逐条解读、板块龙头全覆盖、数据来源与免责声明
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

抓取脚本会额外生成：

- `stocks_timeseries.json`：12 个报告期的单季度、累计、资产负债和派生指标。
- `stock_data_quality.json`：个股数据门禁结果；`summary.fail` 必须为 0。

报告中的财务维度必须展示至少 8 个报告期，并明确区分单季度与年初至今累计。出现“利润为正、经营现金流为负”“应收账款增速显著快于营收”或“合同负债同比大幅下降”时，必须给出原因假设、证据和证伪条件，不能机械地把单期变化写成趋势结论。

### 自动化（可选）

配合 Codex 定时任务（心跳/自动化），可每天早上定时生成研报并保存到指定目录：

```text
每天早上 07:00 使用 daily-market-research 技能，生成今日两份市场研报，保存到 D:\codex\研报
```

### 数据可靠性（可选）

抓取脚本支持自动重试、妙想兜底和完整性校验。默认执行严格门禁：

```powershell
# 默认模式：关键数据缺失、日期错配或数据质量 CRITICAL 时直接中止
powershell -ExecutionPolicy Bypass -File "daily-market-research\scripts\fetch_daily_data.ps1" -Workspace "D:\codex\研报"

# 仅在调试时使用；正式报告禁止绕过门禁
powershell -ExecutionPolicy Bypass -File "daily-market-research\scripts\fetch_daily_data.ps1" -Workspace "D:\codex\研报" -AllowCritical
```

脚本末尾会输出摘要：

```text
===== FETCH SUMMARY =====
Fallbacks used: none
Empty critical: none
Other empty: none
```

`Empty critical` 非 `none` 时说明核心数据缺失，此时不应生成研报。

个股抓取的门禁摘要示例：

```text
Data quality: Stock data quality: 5 pass / 0 fail / 3 warn / 0 missing
```

`fail` 大于 0 时不得生成涉及财务趋势、订单前瞻或估值的结论；`warn` 可以生成报告，但必须在正文中逐项解释。

报告生成后运行结构验收：

```powershell
python "daily-market-research\scripts\lib\validate_report.py" "每日市场研报_YYYY-MM-DD.md" --profile daily-basic
python "daily-market-research\scripts\lib\validate_report.py" "每日市场研报_YYYY-MM-DD_深度分析与标的策略.md" --profile daily-deep
python "stock-deep-research\scripts\lib\validate_report.py" "深度研报_公司简称_YYYY-MM-DD.md" --profile stock
```

验收器返回非零或 `report_valid=false` 时，必须先修正报告，不能直接交付。

### 网页可视化（可选）

```bash
python report-web/scripts/render_report.py --input "每日市场研报_2026-08-25.md" --output "daily_report.html" --diagnose
# 可选：显式指定数据目录；不传时会自动寻找 data/YYYY-MM-DD
python report-web/scripts/render_report.py --input "报告.md" --output "报告.html" --data-dir "data/2026-08-25"
```

输出单文件 HTML，双击即可在浏览器中离线打开。内置玻璃拟态暗色主题、市场仪表盘（指数卡片、涨跌环形图、行业热力图/条形图）、数字动画与阅读进度条。行业表格和深度日报会自动使用同级 `data/YYYY-MM-DD` 的行业数据补全可视化。

加 `--diagnose` 可打印提取诊断（报告类型 + 未取到的字段），便于排查图表缺失原因。

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

## 常见问题

- 为什么仓库名叫 `super-research-report-skill` 而不是“超级研报skill”？GitHub 仓库名只允许 ASCII，中文会被服务端剥除；中文名保留在 README 标题与仓库描述中。
- 直连 GitHub 失败怎么办？部分网络需要代理：`git config http.proxy http://127.0.0.1:7897`（按本机代理端口调整）。
- 问财接口配额不足或字段缺失？报告会写“未取到”并优先用妙想数据交叉验证，不补造数据。
- 两融环比数字看起来像百分比？`margin_change.json` 的字段名为“融资余额环比增长率”，按百分比口径解读；与妙想近 5 日口径不一致时需交叉说明。
- 报告里的目标价/止损可靠吗？均为示例风控参数，不构成投资建议；实际交易请独立决策。

## 示例

以下示例为节选与示意，展示三类报告的形态与深度；完整报告由技能在对应日期自动生成。

### 示例 1：每日市场研报（基础版）· 市场总览

节选自《每日市场研报（2026-08-25）》：

```text
- 上证指数：3876.38 点，-0.15%
- 深证成指：13687.06 点，-0.78%
- 创业板指：3382.81 点，-1.43%
- 沪深300：4542.25 点，-0.46%
- 同花顺全A（沪深京）：1837.42 点，+0.66%
- 两市成交额：约 1.15 万亿元
- 上涨家数：1460 家 / 下跌家数：3965 家
- 涨停家数：48 家 / 跌停家数：4 家

说明：指数与个股分化，全A +0.66% 但上涨占比仅约 26.9%，呈“权重与题材搭台、普跌”结构。
```

### 示例 2：每日市场研报（深度版）· 个股深度分析

节选自《每日市场研报（2026-08-25）深度分析与标的策略》中贵州茅台（600519）：

```text
股票类型：高端白酒龙头，消费价值股。
估值：08-25 收盘 1305.15 元，PE TTM 20.04 倍，PB 6.49 倍，总市值约 1.63 万亿元，股息率约 3.77%。
财务（2026 中报）：营收 907.03 亿元（+1.47%），归母净利 445.17 亿元（-1.95%），毛利率 89.56%。
资金：08-25 盘中主力一度净流入居前（约 6.3 亿），收盘口径小幅净流出；换手率约 0.10%。
技术：现价低于 MA20、高于 MA60，RSI 48.75；筹码获利盘 53%，平均成本 1301.15 元。
消息催化：消费板块低位补涨、外资调研、促内需政策预期。
止损/止盈：跌破 1208.40 元（70% 成本下限）减仓；第一目标 MA20 1322.68 元，放量突破看 1428.35 元。
风险提示：中报归母转负，估值消化需时间；白酒需求疲软是核心变量。
```

### 示例 3：个股机构级深度研报 · 评级框与非共识

节选自《深度研报（完整版）：隆平高科（000998.SZ）》：

```text
> 客观评级：增持 / 推荐（预期相对基准涨幅 +10%~20%）
> 数据日期：行情 2026-08-25 收盘；中报 2026-08-21 披露。本报告不构成投资建议。

核心判断（非共识）：
- 市场把隆平当成“中报亏损、靠题材上涨的种业股”；实际是“基本面正在筑底 + 政策与转基因期权未被定价”的种业国家队龙头。
- 非共识一：中报亏损扩大看着吓人，但 Q2 营收转正（+5.92%）、亏损环比收窄、毛利率 +2.76pct，市场对“扭亏拐点”定价不足。
- 非共识二：海外收入首次超过半壁（>50%），公司已是全球种业第七，市场仍按“国内种企”估值。
- 非共识三：转基因玉米商业化是最大期权，当前 PB 1.98、动态 PE 为负，市场没有给这个期权溢价。

情景推演（节选）：
- 乐观：放量突破 9.75 元确认右侧，上看 10.47 元至 11.82 元。
- 中性：8.5-9.8 元区间震荡，跌破 8.10 元减仓。
- 悲观：跌破 8.10 元坚决止损，不接飞刀；单票仓位不超过组合 5%。
```

### 示例 4：两融水平及分析（示意，基于 2026-08-28 真实抓取数据）

两融模块为后续新增模块，以下为该模块的输出形态示例（数据来自实际抓取的 `margin_level.json` / `margin_flow.json` / `margin_change.json` 与妙想近 5 日）：

```text
## 两融水平及分析（数据日期 2026-08-28，沪深两市合计口径）
- 水平：两融余额 12,766.58 亿元（约 1.28 万亿）；融资余额 12,655.30 亿元；融券余额 111.27 亿元。
- 边际：融资余额环比增长率 -49.47%；融资净买入 -35.64 亿元，杠杆资金明显撤离。
- 活跃度：融资买入额 829.99 亿元，占两市成交额约 3.95%，杠杆交易参与度收缩。
- 杠杆率与结构：融资余额占流通市值约 1.27%；融券余额占两融余额约 0.87%（A股融券占比极低）。
- 近5日趋势（妙想口径）：08-24~08-27 融资余额约 2.49~2.51 万亿，08-28 骤降至 1.27 万亿，为极端去杠杆。
- 信号解读：两融骤降 + 融资净买入为负 = 去杠杆、情绪降温，防负反馈；需结合指数、涨跌家数与成交额判断是否到位。
- 风险提示：极端去杠杆若叠加指数破位会放大抛压；维持担保比例数据未取到，强制平仓风险无法量化，需保持警惕。
```

这些示例仅用于说明报告形态，不构成投资建议。

## 许可

本项目保留所有权利（All Rights Reserved）：允许查看、复制与二次开发，但任何衍生或再分发必须保留版权声明，并注明原始出处与原作者（cute-unicorn）。详见 [LICENSE](LICENSE)。
