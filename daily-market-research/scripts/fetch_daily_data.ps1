param(
    [string]$Workspace = "D:\codex\研报",
    [string]$Date = "",
    [string]$SkillRoot = "",
    [string[]]$StockNames = @()
)

$ErrorActionPreference = "Stop"

if (-not $Date) {
    $Date = Get-Date -Format "yyyy-MM-dd"
}

$profilePath = "$HOME\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
if (-not $env:IWENCAI_API_KEY -and (Test-Path -LiteralPath $profilePath)) {
    . $profilePath
}
if (-not $env:IWENCAI_BASE_URL) {
    $env:IWENCAI_BASE_URL = "https://openapi.iwencai.com"
}
if (-not $env:IWENCAI_API_KEY) {
    throw "IWENCAI_API_KEY is not set. Configure it in the PowerShell profile first."
}

if (-not $SkillRoot) {
    $candidates = @(
        "D:\codex\研报\skills",
        (Join-Path $HOME ".codex\skills")
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) {
            $SkillRoot = $c
            break
        }
    }
}
if (-not $SkillRoot -or -not (Test-Path -LiteralPath $SkillRoot)) {
    throw "Iwencai skill root not found."
}

$OutDir = Join-Path $Workspace ("data\" + $Date)
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$env:PYTHONIOENCODING = "utf-8"

if ($StockNames.Count -eq 0) {
    Get-ChildItem -LiteralPath $OutDir -Filter "stocks_*.json" -ErrorAction SilentlyContinue | ForEach-Object {
        [System.IO.File]::Delete($_.FullName)
    }
}

function Get-CnDate {
    param([datetime]$D)
    return $D.ToString("yyyy年M月d日")
}

function Invoke-Query {
    param(
        [string]$Skill,
        [string]$Script,
        [string[]]$Arguments,
        [string]$OutFile
    )
    $scriptPath = Join-Path $SkillRoot "$Skill\scripts\$Script"
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        throw "Script not found: $scriptPath"
    }
    & python $scriptPath @Arguments 2>&1 | Out-File -LiteralPath (Join-Path $OutDir $OutFile) -Encoding utf8
    $code = $LASTEXITCODE
    Write-Host ("[{0}] exit={1}" -f $OutFile, $code)
    if ($code -ne 0) {
        Write-Warning ("Query failed: " + $OutFile)
    }
}

function Invoke-Search {
    param(
        [string]$Skill,
        [string]$Script,
        [string]$Query,
        [int]$Size,
        [string]$OutFile
    )
    $scriptPath = Join-Path $SkillRoot "$Skill\scripts\$Script"
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        throw "Script not found: $scriptPath"
    }
    $outPath = Join-Path $OutDir $OutFile
    & python $scriptPath $Query "--size" $Size "--output" $outPath 2>&1 | Out-Null
    $code = $LASTEXITCODE
    Write-Host ("[{0}] exit={1}" -f $OutFile, $code)
    if ($code -ne 0) {
        Write-Warning ("Query failed: " + $OutFile)
    }
}

$prev = (Get-Date $Date).AddDays(-1)
$cnPrev = Get-CnDate $prev
$month = (Get-Date $Date).ToString("yyyy年M月")

# 指数
Invoke-Query "hithink-zhishu-query" "cli.py" @("--query", "上证指数 深证成指 创业板指 沪深300 今日点位 涨跌幅", "--limit", "10") "indices_cn.json"
Invoke-Query "hithink-zhishu-query" "cli.py" @("--query", "纳斯达克指数 道琼斯指数 标普500 恒生指数 恒生科技指数 最新点位 涨跌幅", "--limit", "10") "indices_global.json"

# 市场宽度
Invoke-Query "hithink-market-query" "cli.py" @("--query", "两市成交额", "--limit", "5", "--call-type", "retry") "market_turnover.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "$($cnPrev)上涨家数", "--limit", "5", "--call-type", "retry") "market_breadth_up.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "$($cnPrev)下跌家数", "--limit", "5", "--call-type", "retry") "market_breadth_down.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "涨停家数", "--limit", "5", "--call-type", "retry") "market_limit_up.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "跌停家数", "--limit", "5", "--call-type", "retry") "market_limit_down.json"

# 两融水平（市场合计口径）
Invoke-Query "hithink-market-query" "cli.py" @("--query", "沪深两市 融资余额 融券余额 两融余额 流通市值 合计 最新", "--limit", "10", "--call-type", "retry") "margin_level.json"

# 两融资金流与边际（市场合计口径）
Invoke-Query "hithink-market-query" "cli.py" @("--query", "沪深两市 融资净买入 融资买入额 最新", "--limit", "10", "--call-type", "retry") "margin_flow.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "两市融资余额 合计 最新 变化", "--limit", "10", "--call-type", "retry") "margin_change.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "北向资金 净买入 最新", "--limit", "5", "--call-type", "retry") "sentiment_north.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "昨日涨停股今日表现 连板高度 上涨家数占比", "--limit", "10", "--call-type", "retry") "sentiment_market.json"

# 资金结构
Invoke-Query "hithink-market-query" "cli.py" @("--query", "沪深两市 主力资金净流入 超大单净流入 大单净流入 中单净流入 小单净流入", "--limit", "10", "--call-type", "retry") "fundflow_market.json"
Invoke-Query "hithink-industry-query" "cli.py" @("--query", "行业板块 主力资金净流入排名", "--limit", "10") "fundflow_industry_top.json"
Invoke-Query "hithink-industry-query" "cli.py" @("--query", "行业板块 主力资金净流出排名", "--limit", "10") "fundflow_industry_bottom.json"

# 行业
Invoke-Query "hithink-industry-query" "cli.py" @("--query", "行业板块涨幅排名", "--limit", "20") "industry_top.json"
Invoke-Query "hithink-industry-query" "cli.py" @("--query", "行业板块跌幅排名", "--limit", "10") "industry_bottom.json"
Invoke-Query "hithink-industry-query" "cli.py" @("--query", "半导体行业 市盈率 市净率 估值", "--limit", "10") "industry_val.json"
Invoke-Query "hithink-industry-query" "cli.py" @("--query", "电力设备 电网设备 特高压 板块 涨跌幅", "--limit", "20") "industry_grid.json"
Invoke-Query "hithink-industry-query" "cli.py" @("--query", "核电 电力 板块 涨跌幅", "--limit", "20") "industry_nuclear.json"
Invoke-Query "hithink-industry-query" "cli.py" @("--query", "人工智能 算力 板块 涨跌幅", "--limit", "20") "industry_ai.json"

# 宏观与海外
Invoke-Query "hithink-macro-query" "cli.py" @("--query", "最近一期中国CPI PPI 社融 M2增速", "--limit", "10") "macro_cn.json"
Invoke-Query "hithink-macro-query" "cli.py" @("--query", "中国CPI同比 最新", "--limit", "5") "macro_cpi.json"
Invoke-Query "hithink-macro-query" "cli.py" @("--query", "中国M2同比增速 最新", "--limit", "5") "macro_m2.json"
Invoke-Query "hithink-macro-query" "cli.py" @("--query", "社会融资规模存量 最新", "--limit", "5") "macro_she.json"
Invoke-Query "hithink-macro-query" "cli.py" @("--query", "LPR 最新利率", "--limit", "5") "macro_lpr.json"
Invoke-Query "hithink-macro-query" "cli.py" @("--query", "美元兑人民币汇率 最新", "--limit", "5") "macro_usdcny.json"
Invoke-Query "hithink-macro-query" "cli.py" @("--query", "美元指数 美国10年期国债收益率 美元兑日元 欧元兑美元 最新", "--limit", "10") "macro_global.json"
Invoke-Query "hithink-macro-query" "cli.py" @("--query", "伦敦现货黄金 布伦特原油 铜 最新", "--limit", "10") "macro_assets.json"

# 个股详细数据：仅查询当日选定的股票，无固定备选池
if ($StockNames.Count -gt 0) {
    $stocks = $StockNames -join " "
    Invoke-Query "hithink-market-query" "cli.py" @("--query", "$stocks 最新价 涨跌幅 换手率", "--limit", "10") "stocks_quote.json"
    Invoke-Query "hithink-market-query" "cli.py" @("--query", "$stocks 市盈率 市净率 股息率 总市值", "--limit", "10") "stocks_valuation.json"
    Invoke-Query "hithink-market-query" "cli.py" @("--query", "$stocks 主力资金净流入", "--limit", "10", "--call-type", "retry") "stocks_fundflow.json"
    Invoke-Query "hithink-market-query" "cli.py" @("--query", "$stocks 20日均线 60日均线 RSI MACD", "--limit", "10") "stocks_tech.json"
    Invoke-Query "hithink-finance-query" "cli.py" @("--query", "$stocks 最新营收 净利润 同比", "--limit", "10") "stocks_finance.json"
    Invoke-Query "hithink-finance-query" "cli.py" @("--query", "$stocks ROE 毛利率 资产负债率 每股收益", "--limit", "10") "stocks_ratios.json"
    Invoke-Query "hithink-insresearch-query" "cli.py" @("--query", "$stocks 最新评级", "--limit", "10") "stocks_ratings.json"
}
Invoke-Query "hithink-insresearch-query" "cli.py" @("--query", "券商金股 $month", "--limit", "10") "gold_stocks.json"

# ETF
Invoke-Query "hithink-market-query" "cli.py" @("--query", "半导体ETF 通信ETF 医疗ETF 最新价 涨跌幅 成交额", "--limit", "10") "etf_metadata.json"

# 每日动态扫描
Invoke-Query "hithink-market-query" "cli.py" @("--query", "$($cnPrev)涨幅前20股票", "--limit", "20") "scan_top_gainers.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "$($cnPrev)主力资金净流入前20股票", "--limit", "20") "scan_fundflow_top.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "$($cnPrev)涨停股票", "--limit", "20") "scan_limit_up_stocks.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "$($cnPrev)最新评级 买入", "--limit", "20") "scan_ratings_today.json"

# 新闻、公告、研报
Invoke-Search "news-search" "news_search.py" "今日A股市场重要财经新闻 政策 行业" 15 "news_domestic.json"
Invoke-Search "news-search" "news_search.py" "美股 美联储 全球市场 原油 黄金 比特币 最新" 15 "news_global.json"
Invoke-Search "announcement-search" "announcement_search.py" "今日重要公告 回购 增持 重组 业绩预告" 15 "announcements.json"
Invoke-Search "announcement-search" "announcement_search.py" "今日股东增持公告" 10 "announcements_hold.json"
Invoke-Search "announcement-search" "announcement_search.py" "今日业绩预告 半年报" 10 "announcements_forecast.json"
Invoke-Search "report-search" "report_search.py" "A股晨会策略 市场观点 行业配置" 15 "reports.json"

Write-Host "Data fetched to: $OutDir"
