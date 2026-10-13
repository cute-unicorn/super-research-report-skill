---
name: stock-deep-research
description: 生成单只 A 股个股的机构级深度研报：基础五维度（估值/财务/资金/技术/消息）+ 产业链拆解 + 政策链分析 + 非共识 α 观点 + 客观评级 + 情景推演 + 详细风险提示。当用户要求“深度分析某只股票”“机构级个股研报”“给个股评级”“拆解个股的产业链与政策”“找出这只股票的非共识机会”时使用。依赖已安装的 Iwencai 与妙想技能。
---

# 个股机构级深度研报

## 目标

针对单只 A 股（可扩展至港股/美股），生成一份机构级深度研报，文件保存到输出目录：

`深度研报_公司简称_YYYY-MM-DD.md`

报告必须包含：客观评级框、核心判断、基础五维度、产业链拆解、政策链分析、非共识 α 观点、情景推演、详细风险提示。

## 前置条件

- `IWENCAI_API_KEY` 已配置（Windows PowerShell profile）。
- `MX_APIKEY` 已配置（东方财富妙想备用数据源）。
- 已安装：`hithink-market-query`、`hithink-finance-query`、`hithink-insresearch-query`、`hithink-industry-query`、`news-search`、`announcement-search`、`report-search`、`mx-data`、`mx-search` 等技能。
- 技能根目录候选：`D:\codex\研报\skills`、`C:\Users\csy\.codex\skills`。

## 工作流

1. 确定标的与日期。
   - 读取用户给出的股票名称/代码；必要时用 `hithink-basicinfo-query` 确认代码。
   - 日期默认取当天，例如 `2026-08-25`。
   - 输出目录默认 `D:\codex\研报`，也可使用当前工作区。

2. 抓取个股与产业数据。
   - 运行：`powershell -ExecutionPolicy Bypass -File "<技能目录>\scripts\fetch_stock_data.ps1" -Workspace "D:\codex\研报" -StockNames "公司A 公司B"`
   - 默认即严格模式：关键数据缺失或质量门禁失败时直接中止。
   - 仅在调试抓取脚本时使用 `-AllowCritical`；正式研报禁止使用该开关。
   - 脚本将行情/估值/财务/资金/技术/筹码/评级/新闻/公告/研报保存到 `<Workspace>\data\<date>\` 与 `<Workspace>\data\<date>\mx\`。
   - 额外抓取单季度与累计口径的 12 个报告期，生成 `stocks_timeseries.json` 和 `stock_data_quality.json`。
   - **自动重试**：每条查询失败时自动加 `--call-type retry` 重试一次。
   - **妙想兜底**：无论是否失败，脚本都会调用 `mx-data` / `mx-search` 写入 `<date>\mx\`，用于补查缺失字段与交叉验证；结果标注“数据来源：东方财富妙想”。

3. 阅读原始数据并补产业/政策研究。
   - 优先读取脚本生成的 JSON/日志。
   - 必须读取 `stocks_timeseries.json`：区分单季度与年初至今累计口径，至少覆盖 8 个报告期；逐期检查营收、净利润、扣非净利润、经营现金流、毛利率、ROE、应收账款、合同负债和资产负债率。
   - 必须读取 `stock_data_quality.json`。`fail` 必须为 0；`warn` 中的每一项都必须在报告财务维度或风险提示中解释，不得忽略。
   - 重点检查四组背离：利润与经营现金流、应收账款增速与营收增速、合同负债同比变化、单季度与累计口径的方向差异。合同负债下降既可能是订单减少，也可能是预收款转为收入，必须寻找订单、回款或收入确认证据区分。
   - 用 `news-search` / `mx-search` 补查：公司所处行业景气、竞争格局、政策方向、上下游关键环节、可比公司。
   - 对关键缺口（如参股投资市值、订单折算、税率安排）单独检索并明确来源。

4. 动态形成观点。
   - 必须给出“正确但非共识”的独立判断，而非复述市场一致预期。
   - 每个 α 观点都要有可验证的数据/事件支撑和证伪条件。

5. 生成研报。
   - 严格按 `references/report_spec.md` 的结构与评级体系生成。
   - 报告开头必须给出客观评级和评级理由。

6. 验证。
   - 先检查抓取脚本末尾的 `STOCK FETCH SUMMARY`：`Empty critical` 必须为 `none`，否则不得生成研报。
   - `Data quality` 必须显示 `0 fail`，且 `stock_data_quality.json` 的 `report_allowed` 必须为 `true`；若为 `false`，不得生成正式研报，只在日志或对话中输出 `blocking_reasons` 与修复动作。
   - 财务维度必须列出至少 8 个报告期的趋势表，并明确标注“单季度”或“年初至今累计”，禁止把累计同比写成单季同比。
   - 必须引用或解释以下派生指标：收现比、经营现金流/净利润、应收账款同比减营收同比、合同负债同比、资产负债率。
   - 文末必须包含“数据溯源与观察清单”，至少列出 8 个关键事实及其来源、报告期和下次更新触发条件。
   - 文件存在且包含全部章节。
   - 生成后必须运行：
     `python "<技能目录>\scripts\lib\validate_report.py" "<报告文件>" --profile stock`；
     `report_valid` 必须为 `true`，否则修正报告后重新验收。
   - 评级框、核心判断、五维度、产业链、政策链、α 观点、情景推演、风险提示齐全。
   - 每个数据标注日期和来源；未取到的字段写“未取到”，禁止编造。
   - 文末注明“数据来源”和“不构成投资建议”。

## 评级体系（客观评级，报告开头必须给出）

- 买入 / 强烈推荐：预期股价相对基准涨幅 20% 以上
- 增持 / 推荐：预期相对基准涨幅 10%~20%
- 持有 / 中性：预期相对基准涨跌幅 -10%~+10%，基本跟随大盘
- 减持 / 回避：预期相对基准跌幅 10% 以上
- 卖出：预期相对基准跌幅更大，建议清仓

评级必须给“理由 + 上调/下调触发条件”，并与情景推演一致。

## 数据纪律

- 只使用接口实际返回的数据；缺失字段写“未取到”，不推测补数。
- 新闻、公告、研报、评级保留来源与日期。
- 评级、止损、止盈、目标价均为分析判断/示例参数，必须声明不构成投资建议。
- 产业链、政策、α 观点等分析要区分“事实”与“判断”，判断要有依据和证伪条件。
- 报告为机构级输出，但必须避免夸大与无依据的断言。

## 参考

- 报告结构与评级规范见 `references/report_spec.md`。
- 数据抓取脚本见 `scripts/fetch_stock_data.ps1`。

## 自测

修改抓取脚本、时间序列或门禁后必须运行：

```powershell
python "<技能目录>\scripts\tests\test_timeseries.py"
powershell -ExecutionPolicy Bypass -File "<技能目录>\scripts\tests\test_fetch_gate.ps1"
python "<技能目录>\scripts\lib\validate_report.py" "<报告文件>" --profile stock
```
