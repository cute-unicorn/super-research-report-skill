# 权威信息来源规范

## 目标

研报中的政策、宏观、监管、交易所、公司公告和海外利率数据，必须优先引用原始发布方。
新闻检索工具只用于发现线索，不能替代原始来源。

## 来源优先级

1. 官方统计机构、中央银行、监管机构、交易所、政府部门的原始公告或数据页面。
2. 交易所公告、公司年报/季报、招股书、问询函回复等法定披露文件。
3. 国际组织、国家级研究机构和央行工作论文。
4. 数据供应商（同花顺问财、东方财富妙想等），用于结构化数据和交叉核验。
5. 主流财经媒体，仅用于补充事实，必须标注为二手来源。

## 中国官方来源

| 领域 | 来源 | 站点 |
|---|---|---|
| 货币政策、流动性 | 中国人民银行 | https://www.pbc.gov.cn |
| CPI、PPI、工业、消费 | 国家统计局 | https://www.stats.gov.cn |
| 证券监管、行政处罚 | 中国证监会 | https://www.csrc.gov.cn |
| 财政政策、国债、贴息 | 财政部 | https://www.mof.gov.cn |
| 产业政策、重大项目 | 国家发展改革委 | https://www.ndrc.gov.cn |
| 工信产业、制造业 | 工业和信息化部 | https://www.miit.gov.cn |
| 外汇、跨境资金 | 国家外汇管理局 | https://www.safe.gov.cn |
| 上交所公告 | 上海证券交易所 | https://www.sse.com.cn |
| 深交所公告 | 深圳证券交易所 | https://www.szse.cn |
| 北交所公告 | 北京证券交易所 | https://www.bse.cn |
| 法定信息披露 | 巨潮资讯 | https://www.cninfo.com.cn |
| 债券与货币市场 | 中国货币网 | https://www.chinamoney.com.cn |

## 国际官方来源

| 领域 | 来源 | 站点 |
|---|---|---|
| 美国货币政策 | Federal Reserve | https://www.federalreserve.gov |
| 美债、财政数据 | U.S. Treasury | https://home.treasury.gov |
| 美国通胀、就业 | BLS | https://www.bls.gov |
| 美国 GDP、收入 | BEA | https://www.bea.gov |
| 美国上市公司申报 | SEC EDGAR | https://www.sec.gov/edgar |
| 欧元区政策 | ECB | https://www.ecb.europa.eu |
| 英国政策 | Bank of England | https://www.bankofengland.co.uk |
| 日本政策 | Bank of Japan | https://www.boj.or.jp |
| 全球宏观 | IMF | https://www.imf.org |
| 全球发展数据 | World Bank | https://www.worldbank.org |
| 国际比较 | OECD | https://www.oecd.org |
| 国际金融稳定 | BIS | https://www.bis.org |
| 能源数据 | EIA | https://www.eia.gov |
| 原油市场 | OPEC | https://www.opec.org |
| ENSO/厄尔尼诺 | NOAA CPC | https://www.cpc.ncep.noaa.gov |
| 基本金属 | LME | https://www.lme.com |

## 检索方式

先使用已安装的 `news-search`、`mx-search`、`report-search` 发现线索，再打开原始页面核验。
查询示例：

- `中国人民银行 货币政策 公告`
- `国家统计局 PPI 最新数据`
- `证监会 监管 处罚 最新`
- `上交所 公告 问询函`
- `Federal Reserve FOMC statement`
- `U.S. Treasury yield curve`
- `IMF World Economic Outlook`

如果搜索工具没有返回原文链接，必须在报告中写明“未核验到原始来源”，不得把二手标题写成官方文件事实。

## 引用格式

- 政策：`来源：中国人民银行《公告标题》，发布日期，原始链接`
- 数据：`来源：国家统计局，指标名，报告期，原始链接`
- 公告：`来源：上交所/深交所/巨潮，公司代码，公告编号，日期`
- 海外：`Source: Federal Reserve, FOMC statement, date, URL`

## 最低要求

- 每日基础版至少引用 1 个官方来源。
- 每日深度版至少引用 2 个官方来源，其中至少 1 个用于政策或宏观判断。
- 个股深度研报至少引用 1 个交易所/监管/公司法定披露来源；财务序列使用问财数据时必须同时给出报告期和原始数据文件。
- 任何“监管处罚、回购、增持、重组、业绩预告”结论都必须能回溯到公告原文。
