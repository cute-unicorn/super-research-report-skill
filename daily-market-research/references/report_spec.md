# 每日研报规范

## 一、基础研报结构

文件：`每日市场研报_YYYY-MM-DD.md`

1. 市场总览
   - 上证指数、深证成指、创业板指、沪深300、同花顺全A
   - 全A成交额、上涨家数、下跌家数、涨停家数、跌停家数
   - 未取到字段必须注明

2. 行业与风格
   - 领涨行业、领跌行业
   - 风格判断（成长/红利/价值切换）
   - 资金流向若未取到，明确标注

3. 宏观与流动性
   - CPI、PPI、M2、社融、LPR、汇率
   - 每个指标标注报告期

4. 海外市场与全球资产
   - 美股三大指数、港股恒指/恒生科技
   - 美元指数、美债收益率、美元兑日元、欧元兑美元
   - 黄金、原油、铜、比特币

5. 政策与要闻（国内外）
   - 国内监管、产业政策、资本市场政策
   - 国际央行、汇率、地缘、AI 等重大事件
   - 每一条政策/要闻必须逐条展开，包含两段固定结构：
     - `内容解读`：先解释事件是什么，注明主体、时间、关键数字和目标
     - `影响分析`：再分析对 A 股行业、板块、资金、估值或风险的影响
   - 禁止只罗列标题、只写一句话或把多条政策合并成一段

6. 重要公告与事件
   - 回购、增持、业绩预告、半年报、并购重组、风险事件

7. 机构观点
   - 晨会、月度策略、金股、评级
   - 标注机构和日期

8. 关注方向与风险提示
   - 主线持续性、关键变量、风险点

9. 非共识 α 观点
   - 从当日数据挖掘 2-4 条“正确但非共识”的独立判断
   - 每条包含四要素：市场一致预期 / 非共识点 / α 来源与兑现路径 / 证伪条件
   - 禁止复述市场共识，必须给出与盘面或一致预期不同、且可验证的观点
   - 来源必须落在当日数据、政策、资金、估值或情绪背离上

10. 情绪分析
   - 融资融券余额、融资余额（标注报告期）
   - 北向资金净买入（标注报告期，取不到写“未取到”）
   - 上涨家数占比、涨停/跌停家数、连板高度、昨日涨停股今日表现
   - 成交额、换手率、市场情绪温度判断（过热/中性/冰点）
   - 每项数据标注日期，接口为空时明确注明

11. 两融水平及分析
   - 数据必须使用市场合计口径（沪深两市合计），标注报告期日期
   - 水平：两融余额、融资余额、融券余额
   - 边际：融资余额环比增长率（margin_change.json，百分比口径）、融资净买入（正为加杠杆、负为去杠杆）
   - 活跃度：融资买入额、融资买入额占两市成交额比例（可用成交额自行计算）
   - 杠杆率与结构：融资余额占流通市值比例（margin_level.json 返回流通市值、总市值两个口径，优先用流通市值，注明口径）、融券余额占两融余额比例（A股融券占比通常极低）
   - 趋势：近5日两融余额/融资余额方向（妙想近5日表格，取不到写“未取到”）
   - 信号解读（至少三选一结合当日盘面展开）：
     - 两融上升 + 指数上涨：风险偏好扩张，量能支撑确认
     - 两融上升 + 指数滞涨/缩量：杠杆堆积、滞涨风险，警惕情绪过热
     - 两融回落 + 指数下行：去杠杆、情绪降温，防负反馈
   - 风险提示：维持担保比例与强制平仓/去杠杆风险，数据取不到时写“未取到”
   - 数据来源：同花顺问财（margin_level.json / margin_flow.json / margin_change.json），妙想近5日（mx_data_margin.log）作交叉验证

12. 资金分析
   - 机构资金：以超大单净流入近似
   - 主力资金：主力净流入、主力增仓占比
   - 大户资金：以大单净流入近似
   - 散户资金：以中单+小单净流入近似
   - 行业资金流入/流出前列
   - 北向资金、融资余额作为补充
   - 必须注明“机构/主力/大户/散户”为近似口径，并标注日期

13. 风险提示（汇总）
   - 汇总市场、行业、个股、情绪和资金风险

## 二、深度分析与标的策略结构

文件：`每日市场研报_YYYY-MM-DD_深度分析与标的策略.md`

1. 总体分析
2. 海外市场与全球资产
3. 政策与要闻（国内外）
   - 与基础研报相同，每一条必须包含“内容解读”和“影响分析”
   - 内容解读先行，影响分析随后，逐条展开
4. 重要公告与事件
5. 机构观点
6. 情绪与资金分析
   - 市场情绪：北向资金、涨跌家数、涨停跌停、连板/昨日涨停表现
   - 两融水平及分析（独立小节）：
     - 数据：两融余额、融资余额、融券余额（市场合计，标注日期）；融资余额环比、融资净买入、融资买入额及占成交额比例、融资余额占流通市值比例
     - 分析：绝对水平、边际方向、杠杆结构与交易活跃度、信号解读（与指数同向/背离）、维持担保比例与去杠杆风险
     - 妙想近5日趋势作交叉验证，取不到写“未取到”
   - 资金结构：机构资金（超大单）、主力资金（超大单+大单）、大户资金（大单）、散户资金（中单+小单）
   - 行业资金流入/流出前列
   - 每项标注日期和近似口径
7. 非共识 α 观点
   - 从当日资金、行业、政策、估值或情绪背离中提炼 2-4 条非共识判断
   - 每条包含：市场一致预期 / 非共识点 / α 来源与兑现路径 / 证伪条件
   - 非共识观点必须与当日板块、龙头股或市场结构直接挂钩，避免空泛
   - 若与非共识观点相关，可在第 8 部分个股深度分析中展开验证
8. 板块推荐
   - 市场驱动板块：由当日行业涨幅、资金流向、机构观点动态确定
   - 政策驱动板块：由当日政策、招标、核准、项目事件动态确定
   - 每个板块包含证据、分析、短中长期、止损参考、风险
   - 每个板块必须列出 2-4 只最相关龙头股（名称 + 代码），并标注入选依据（当日涨幅、主力净流入、机构评级、金股、业绩或事件催化）
   - 板块推荐中列出的龙头股必须在第 8 部分逐一完整分析，不能只列不析
9. 个股深度分析
   - 每只个股包含：股票类型、估值、财务、资金、技术、消息催化、短中长期、止损、止盈、风险
   - 候选池动态生成，不固定：优先从当日涨幅居前、主力净流入、机构评级、金股、业绩或事件催化中筛选
   - 禁止固定备选池，个股完全由当日扫描结果和补充查询决定
   - 必须覆盖第 7 部分列出的全部龙头股；每只个股开头标注所属板块与入选证据
10. ETF 关注组合
   - 半导体ETF国联安 512480
   - 通信ETF国泰 515880
   - 医药ETF易方达 512010
   - 若未取到 ETF 精确价格，用板块指数作为证据并注明
11. 组合建议
   - 进攻、均衡、防守、观察比例
   - 止损纪律
12. 风险提示
   - 每个部分都应有独立风险提示
   - 文末汇总全报告风险

## 二点五、动态选择规则

板块切换规则：

- 行业涨幅前 5 且存在资金或政策催化的板块优先进入“市场驱动板块”。
- 有政策文件、重大项目、招标、核准等催化且订单可验证的板块进入“政策驱动板块”。
- 连续多日没有新催化或已经明显透支的板块，应剔除或降级。
- 至少保留 1 个市场驱动板块和 1 个政策驱动板块，但具体板块由当日数据决定。

个股切换规则：

- 优先选择当日主力净流入、涨幅居前、机构评级/金股覆盖、业绩或公告催化的标的。
- 若上一日标的当日无资金、无评级、无催化且技术走弱，必须替换。
- 不要使用任何预设股票名单，所有个股必须来自当日扫描。
- 每个板块从当日数据中选出 2-4 只龙头股；板块推荐列出的龙头股必须全部进入个股深度分析。

动态扫描数据：

- `scan_top_gainers.json`：当日涨幅前 20 股票
- `scan_fundflow_top.json`：当日主力净流入前 20 股票
- `scan_limit_up_stocks.json`：当日涨停股票
- `scan_ratings_today.json`：当日买入评级
- `industry_top.json` / `industry_bottom.json`：行业涨跌幅排名
- `gold_stocks.json`：券商金股
- `news_domestic.json` / `news_global.json`：国内外政策和催化
- `margin_level.json` / `margin_flow.json` / `margin_change.json`：两融水平、净买入/买入额、环比（市场合计口径）
- `sentiment_north.json` / `sentiment_market.json`：北向资金与市场宽度情绪数据
- `mx_data_margin.log`：妙想两融近5日趋势备用数据
- `fundflow_market.json` / `fundflow_industry_top.json` / `fundflow_industry_bottom.json`：资金结构数据
- `mx_data_sentiment.log` / `mx_data_fundflow.log`：妙想情绪和资金结构备用数据

## 三、常用补充查询

### 妙想备用数据源（MX）

当 Iwencai 配额不足或数据缺失时，使用妙想技能补查。

金融数据：

```powershell
python C:\Users\csy\.codex\skills\mx-data\mx_data.py "上证指数 深证成指 创业板指 沪深300 最新点位 涨跌幅 成交额" "D:\codex\研报\data\<date>\mx"
```

资讯搜索：

```powershell
python C:\Users\csy\.codex\skills\mx-search\mx_search.py "今日A股市场重要财经新闻 政策 行业" "D:\codex\研报\data\<date>\mx"
```

智能选股：

```powershell
python C:\Users\csy\.codex\skills\mx-xuangu\mx_xuangu.py --query "今日涨幅大于5%的A股" --output-dir "D:\codex\研报\data\<date>\mx"
```

动态扫描也可使用：

- `mx_xuangu_top_gainers.log`：当日涨幅榜
- `mx_xuangu_fundflow.log`：当日资金流入榜
- `mx_xuangu_limit_up.log`：当日涨停
- `mx_xuangu_ratings.log`：当日买入评级

说明：`mx-zixuan`、`mx-moni`、`mx-poster` 属于自选股、模拟交易和社区功能，不用于每日研报生成。

指数：

```powershell
python D:\codex\研报\skills\hithink-zhishu-query\scripts\cli.py --query "上证指数 深证成指 创业板指 沪深300 今日点位 涨跌幅" --limit 10
```

个股行情（股票名替换为当日扫描结果）：

```powershell
python D:\codex\研报\skills\hithink-market-query\scripts\cli.py --query "股票A 股票B 最新价 涨跌幅 换手率" --limit 10
```

估值：

```powershell
python D:\codex\研报\skills\hithink-market-query\scripts\cli.py --query "股票A 股票B 市盈率 市净率 股息率 总市值" --limit 10
```

财务：

```powershell
python D:\codex\研报\skills\hithink-finance-query\scripts\cli.py --query "股票A 股票B ROE 毛利率 资产负债率 每股收益" --limit 10
```

资金：

```powershell
python D:\codex\研报\skills\hithink-market-query\scripts\cli.py --query "股票A 股票B 主力资金净流入" --limit 10 --call-type retry
```

技术：

```powershell
python D:\codex\研报\skills\hithink-market-query\scripts\cli.py --query "股票A 股票B 20日均线 60日均线 RSI MACD" --limit 10
```

研报搜索：

```powershell
python D:\codex\研报\skills\report-search\scripts\report_search.py "A股晨会策略 市场观点 行业配置" --size 15 --output out.json
```

情绪补充查询：

```powershell
python D:\codex\研报\skills\hithink-market-query\scripts\cli.py --query "北向资金 净买入 最新" --limit 5 --call-type retry
python D:\codex\研报\skills\hithink-market-query\scripts\cli.py --query "昨日涨停股今日表现 连板高度 上涨家数占比" --limit 10 --call-type retry
```

两融水平补充查询（市场合计口径）：

```powershell
python D:\codex\研报\skills\hithink-market-query\scripts\cli.py --query "沪深两市 融资余额 融券余额 两融余额 流通市值 合计 最新" --limit 10 --call-type retry
python D:\codex\研报\skills\hithink-market-query\scripts\cli.py --query "沪深两市 融资净买入 融资买入额 最新" --limit 10 --call-type retry
python D:\codex\研报\skills\hithink-market-query\scripts\cli.py --query "两市融资余额 合计 最新 变化" --limit 10 --call-type retry
```

资金结构补充查询：

```powershell
python D:\codex\研报\skills\hithink-market-query\scripts\cli.py --query "沪深两市 主力资金净流入 超大单净流入 大单净流入 中单净流入 小单净流入" --limit 10 --call-type retry
python D:\codex\研报\skills\hithink-industry-query\scripts\cli.py --query "行业板块 主力资金净流入排名" --limit 10
python D:\codex\研报\skills\hithink-industry-query\scripts\cli.py --query "行业板块 主力资金净流出排名" --limit 10
```

妙想备用：

```powershell
python C:\Users\csy\.codex\skills\mx-data\mx_data.py "沪深两市 主力资金净流入 超大单 大单 中单 小单 最新" "D:\codex\研报\data\<date>\mx"
python C:\Users\csy\.codex\skills\mx-data\mx_data.py "融资融券余额 北向资金 最新" "D:\codex\研报\data\<date>\mx"
python C:\Users\csy\.codex\skills\mx-data\mx_data.py "沪深两市 融资融券余额 融资余额 融券余额 最新" "D:\codex\研报\data\<date>\mx"
```

## 四、数据纪律

- 所有数据必须来自接口实际返回。
- 缺失字段写“未取到”，不补造数据。
- 新闻、研报、评级必须保留来源机构、日期和标题。
- 止盈止损是示例参数，必须声明不构成投资建议。
- 情绪和资金数据必须标注日期；机构/主力/大户/散户资金口径必须注明近似关系。
- 两融数据必须使用沪深两市合计口径并标注日期；个股级两融余额不能当作市场两融水平使用。
- 融资买入额占成交额比例、融资余额占流通市值比例若接口未直接给出，可用成交额、流通市值自行计算并注明。
- 两融分析必须落到“水平、边际、活跃度、杠杆结构、信号解读、去杠杆风险”六个维度，不能只罗列数字。
