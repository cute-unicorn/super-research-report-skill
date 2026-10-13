param(
    [string]$Workspace = "D:\codex\研报",
    [string]$Date = "",
    [string]$SkillRoot = "",
    [string[]]$StockNames = @(),
    [switch]$Strict,
    [switch]$AllowCritical
)

$ErrorActionPreference = "Stop"

if (-not $Date) { $Date = Get-Date -Format "yyyy-MM-dd" }
$script:StrictMode = -not $AllowCritical
if ($Strict) { $script:StrictMode = $true }

$profilePath = "$HOME\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
if (-not $env:IWENCAI_API_KEY -and (Test-Path -LiteralPath $profilePath)) { . $profilePath }
if (-not $env:IWENCAI_BASE_URL) { $env:IWENCAI_BASE_URL = "https://openapi.iwencai.com" }
if (-not $env:IWENCAI_API_KEY) { throw "IWENCAI_API_KEY is not set." }

if (-not $SkillRoot) {
    foreach ($c in @("D:\codex\研报\skills", (Join-Path $HOME ".codex\skills"))) {
        if (Test-Path -LiteralPath $c) { $SkillRoot = $c; break }
    }
}
if (-not $SkillRoot -or -not (Test-Path -LiteralPath $SkillRoot)) { throw "Iwencai skill root not found." }

$OutDir = Join-Path $Workspace ("data\" + $Date)
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$MxDir = Join-Path $OutDir "mx"
New-Item -ItemType Directory -Force -Path $MxDir | Out-Null
$MxRoot = Join-Path $HOME ".codex\skills"
$env:PYTHONIOENCODING = "utf-8"

# ---------- 工具函数（见 lib/common.ps1） ----------
$script:Failures = @()
$script:Fallbacks = @()
$script:Critical = @()
. (Join-Path $PSScriptRoot "lib\common.ps1")

$prev = Get-LastTradingDay (Get-Date $Date)
$cnPrev = Get-CnDate $prev
$month = (Get-Date $Date).ToString("yyyy年M月")
Write-Host ("Trading day anchor: {0}" -f $cnPrev)

# ---------- 指数 ----------
Invoke-QueryWithFallback "hithink-zhishu-query" "cli.py" @("--query", "上证指数 深证成指 创业板指 沪深300 今日点位 涨跌幅", "--limit", "10") "indices_cn.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-zhishu-query" "cli.py" @("--query", "纳斯达克指数 道琼斯指数 标普500 恒生指数 恒生科技指数 最新点位 涨跌幅", "--limit", "10") "indices_global.json" $null | Out-Null

# ---------- 市场宽度 ----------
Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "两市成交额", "--limit", "5", "--call-type", "retry") "market_turnover.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$cnPrev 上涨家数", "--limit", "5", "--call-type", "retry") "market_breadth_up.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$cnPrev 下跌家数", "--limit", "5", "--call-type", "retry") "market_breadth_down.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$cnPrev 涨停家数", "--limit", "5", "--call-type", "retry") "market_limit_up.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$cnPrev 跌停家数", "--limit", "5", "--call-type", "retry") "market_limit_down.json" $null | Out-Null

# ---------- 两融（市场合计口径，关键） ----------
Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "沪深两市 融资余额 融券余额 两融余额 流通市值 合计 最新", "--limit", "10", "--call-type", "retry") "margin_level.json" "沪深两市 融资融券余额 融资余额 融券余额 最新" | Out-Null
Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "沪深两市 融资净买入 融资买入额 最新", "--limit", "10", "--call-type", "retry") "margin_flow.json" "沪深两市 融资净买入 融资买入额 最新" | Out-Null
Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "两市融资余额 合计 最新 变化", "--limit", "10", "--call-type", "retry") "margin_change.json" "沪深两市 融资余额 环比变化" | Out-Null

# ---------- 情绪 ----------
Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "北向资金 净买入 最新", "--limit", "5", "--call-type", "retry") "sentiment_north.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$cnPrev 昨日涨停股今日表现 连板高度 上涨家数占比", "--limit", "10", "--call-type", "retry") "sentiment_market.json" $null | Out-Null

# ---------- 资金结构 ----------
Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "沪深两市 主力资金净流入 超大单净流入 大单净流入 中单净流入 小单净流入", "--limit", "10", "--call-type", "retry") "fundflow_market.json" "沪深两市 主力资金净流入 超大单 大单 中单 小单 最新" | Out-Null
Invoke-QueryWithFallback "hithink-industry-query" "cli.py" @("--query", "行业板块 主力资金净流入排名", "--limit", "10", "--call-type", "retry") "fundflow_industry_top.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-industry-query" "cli.py" @("--query", "行业板块 主力资金净流出排名", "--limit", "10", "--call-type", "retry") "fundflow_industry_bottom.json" $null | Out-Null

# ---------- 行业（全部动态，无固定名单） ----------
Invoke-QueryWithFallback "hithink-industry-query" "cli.py" @("--query", "行业板块涨幅排名", "--limit", "20", "--call-type", "retry") "industry_top.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-industry-query" "cli.py" @("--query", "行业板块跌幅排名", "--limit", "10", "--call-type", "retry") "industry_bottom.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-industry-query" "cli.py" @("--query", "行业板块 市盈率 市净率 估值排名", "--limit", "15", "--call-type", "retry") "industry_val.json" $null | Out-Null

# 用当日领涨行业动态补充估值，替代原先硬编码的半导体/电网/核电/AI
$topIndustryPath = Join-Path $OutDir "industry_top.json"
if (Test-Path -LiteralPath $topIndustryPath) {
    try {
        $topObj = Get-Content -LiteralPath $topIndustryPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $topNames = @($topObj.datas | Select-Object -First 5 | ForEach-Object {
            if ($_.'指数简称') { $_.'指数简称' } elseif ($_.'行业名称') { $_.'行业名称' } else { $null }
        }) | Where-Object { $_ }
        if ($topNames.Count -gt 0) {
            $dynQuery = ($topNames -join " ") + " 板块 涨跌幅 市盈率"
            Invoke-QueryWithFallback "hithink-industry-query" "cli.py" @("--query", $dynQuery, "--limit", "20", "--call-type", "retry") "industry_dynamic_top.json" $null | Out-Null
            Write-Host ("[dynamic] sector valuation query: {0}" -f ($topNames -join ", "))
        }
    } catch { Write-Warning "Failed to derive dynamic sectors: $_" }
}

# ---------- 宏观与海外 ----------
Invoke-QueryWithFallback "hithink-macro-query" "cli.py" @("--query", "最近一期中国CPI PPI 社融 M2增速", "--limit", "10", "--call-type", "retry") "macro_cn.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-macro-query" "cli.py" @("--query", "中国CPI同比 最新", "--limit", "5", "--call-type", "retry") "macro_cpi.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-macro-query" "cli.py" @("--query", "中国PPI同比 最新", "--limit", "5", "--call-type", "retry") "macro_ppi.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-macro-query" "cli.py" @("--query", "中国M2同比增速 最新", "--limit", "5", "--call-type", "retry") "macro_m2.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-macro-query" "cli.py" @("--query", "社会融资规模存量 最新", "--limit", "5", "--call-type", "retry") "macro_she.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-macro-query" "cli.py" @("--query", "LPR 最新利率", "--limit", "5", "--call-type", "retry") "macro_lpr.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-macro-query" "cli.py" @("--query", "美元兑人民币汇率 最新", "--limit", "5", "--call-type", "retry") "macro_usdcny.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-macro-query" "cli.py" @("--query", "美元指数 美国10年期国债收益率 美元兑日元 欧元兑美元 最新", "--limit", "10", "--call-type", "retry") "macro_global.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-macro-query" "cli.py" @("--query", "沪金 主力合约 最新价", "--limit", "5", "--call-type", "retry") "macro_assets_gold.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-macro-query" "cli.py" @("--query", "布伦特原油 最新价", "--limit", "5", "--call-type", "retry") "macro_assets_oil.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-macro-query" "cli.py" @("--query", "沪铜 主力合约 最新价", "--limit", "5", "--call-type", "retry") "macro_assets_copper.json" $null | Out-Null
$mergeAssets = Join-Path $PSScriptRoot "lib\merge_assets.py"
if (Test-Path -LiteralPath $mergeAssets) {
    & python $mergeAssets `
        --out (Join-Path $OutDir "macro_assets.json") `
        --as-of $Date `
        --input (Join-Path $OutDir "macro_assets_gold.json") `
        --input (Join-Path $OutDir "macro_assets_oil.json") `
        --input (Join-Path $OutDir "macro_assets_copper.json") 2>&1 | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { $script:Failures += "macro_assets(merge)" }
} else {
    $script:Failures += "merge_assets.py(missing)"
}

# ---------- 个股（仅当日选定，无固定池） ----------
if ($StockNames.Count -gt 0) {
    $stocks = $StockNames -join " "
    Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$stocks 最新价 涨跌幅 换手率", "--limit", "10", "--call-type", "retry") "stocks_quote.json" $null | Out-Null
    Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$stocks 市盈率 市净率 股息率 总市值", "--limit", "10", "--call-type", "retry") "stocks_valuation.json" $null | Out-Null
    Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$stocks 主力资金净流入", "--limit", "10", "--call-type", "retry") "stocks_fundflow.json" $null | Out-Null
    Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$stocks 20日均线 60日均线 RSI MACD", "--limit", "10", "--call-type", "retry") "stocks_tech.json" $null | Out-Null
    Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$stocks 获利盘比例 平均成本 90%成本区间 70%成本区间", "--limit", "10", "--call-type", "retry") "stocks_chips.json" $null | Out-Null
    Invoke-QueryWithFallback "hithink-finance-query" "cli.py" @("--query", "$stocks 最新营收 净利润 同比", "--limit", "10", "--call-type", "retry") "stocks_finance.json" $null | Out-Null
    Invoke-QueryWithFallback "hithink-finance-query" "cli.py" @("--query", "$stocks ROE 毛利率 资产负债率 每股收益", "--limit", "10", "--call-type", "retry") "stocks_ratios.json" $null | Out-Null
    Invoke-QueryWithFallback "hithink-insresearch-query" "cli.py" @("--query", "$stocks 最新评级", "--limit", "10", "--call-type", "retry") "stocks_ratings.json" $null | Out-Null
}

# ---------- 关键扫描（动态选股数据源，带妙想兜底） ----------
$script:Critical += Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$cnPrev 涨幅前20股票", "--limit", "20") "scan_top_gainers.json" "$cnPrev 涨幅前20的A股"
$script:Critical += Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$cnPrev 主力资金净流入前20股票", "--limit", "20") "scan_fundflow_top.json" "$cnPrev 主力资金净流入前20的A股"
$script:Critical += Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$cnPrev 涨停股票", "--limit", "20") "scan_limit_up_stocks.json" "$cnPrev 涨停的A股"
$script:Critical += Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "$cnPrev 最新评级 买入", "--limit", "20") "scan_ratings_today.json" "$cnPrev 最新买入评级的A股"
Invoke-QueryWithFallback "hithink-insresearch-query" "cli.py" @("--query", "券商金股 $month", "--limit", "10", "--call-type", "retry") "gold_stocks.json" $null | Out-Null
Invoke-QueryWithFallback "hithink-market-query" "cli.py" @("--query", "半导体ETF 通信ETF 医疗ETF 最新价 涨跌幅 成交额", "--limit", "10", "--call-type", "retry") "etf_metadata.json" $null | Out-Null

# ---------- 新闻 / 公告 / 研报 ----------
Invoke-Search "news-search" "news_search.py" "今日A股市场重要财经新闻 政策 行业" 15 "news_domestic.json"
Invoke-Search "news-search" "news_search.py" "美股 美联储 全球市场 原油 黄金 比特币 最新" 15 "news_global.json"
Invoke-Search "news-search" "news_search.py" "中国人民银行 国家统计局 证监会 财政部 发改委 最新 政策 公告" 15 "news_official_cn.json"
Invoke-Search "news-search" "news_search.py" "美联储 美国财政部 美国劳工统计局 欧洲央行 日本央行 最新 政策 数据" 15 "news_official_global.json"
Invoke-Search "announcement-search" "announcement_search.py" "今日重要公告 回购 增持 重组 业绩预告" 15 "announcements.json"
Invoke-Search "announcement-search" "announcement_search.py" "今日股东增持公告" 10 "announcements_hold.json"
Invoke-Search "announcement-search" "announcement_search.py" "今日业绩预告 半年报" 10 "announcements_forecast.json"
Invoke-Search "report-search" "report_search.py" "A股晨会策略 市场观点 行业配置" 15 "reports.json"

# ---------- 校验门禁 ----------
$criticalFiles = @("indices_cn.json","market_turnover.json","margin_level.json","margin_flow.json",
                   "fundflow_market.json","industry_top.json","industry_bottom.json",
                   "scan_top_gainers.json","scan_fundflow_top.json","scan_limit_up_stocks.json")
$emptyCritical = @()
foreach ($cf in $criticalFiles) {
    if ((Get-JsonDataCount (Join-Path $OutDir $cf)) -eq 0) { $emptyCritical += $cf }
}

# ---------- 数据一致性校验（勾稽校验，捕获"文件非空但数值自相矛盾"） ----------
$script:QualityFail = 0
$script:QualityLine = "not run"
$script:QualityReportAllowed = $true
$script:QualityBlocking = @()
$validator = Join-Path $PSScriptRoot "lib\validate_facts.py"
if (Test-Path -LiteralPath $validator) {
    $qualityArgs = @($validator, $OutDir)
    if ($script:StrictMode) { $qualityArgs += "--strict" }
    $qualityOut = & python @qualityArgs 2>&1
    $qualityExit = $LASTEXITCODE
    $lines = @($qualityOut | ForEach-Object { $_.ToString() })
    if ($lines.Count -gt 0) {
        # 校验器首行自带 "Data quality: " 前缀，这里剥离以免汇总行重复
        $script:QualityLine = $lines[0] -replace '^Data quality:\s*', ''
        foreach ($ln in $lines) { Write-Host $ln }
    }
    if ($qualityExit -ne 0) {
        $script:QualityFail = 1
        $script:QualityLine = "validator failed with exit code $qualityExit"
    }
} else {
    Write-Warning ("[quality] validator not found: {0}" -f $validator)
    $script:QualityLine = "validator missing"
    $script:QualityFail = 1
    $script:QualityReportAllowed = $false
    $script:QualityBlocking = @("validate_facts.py missing")
}
$qualityPath = Join-Path $OutDir "data_quality.json"
if (Test-Path -LiteralPath $qualityPath) {
    try {
        $qualityJson = Get-Content -LiteralPath $qualityPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $script:QualityReportAllowed = [bool]$qualityJson.report_allowed
        if ($null -ne $qualityJson.summary -and [int]$qualityJson.summary.fail -gt 0) {
            $script:QualityFail = 1
        }
        $script:QualityBlocking = @($qualityJson.blocking_reasons)
    } catch {
        $script:QualityFail = 1
        $script:QualityReportAllowed = $false
        $script:QualityBlocking = @("data_quality.json parse failed: " + $_.Exception.Message)
    }
}

Write-Host ""
Write-Host "===== FETCH SUMMARY ====="
Write-Host ("Output: {0}" -f $OutDir)
$fallbackText = if ($script:Fallbacks.Count) { ($script:Fallbacks | Select-Object -Unique) -join ", " } else { "none" }
$criticalText = if ($emptyCritical.Count) { $emptyCritical -join ", " } else { "none" }
$otherText = if ($script:Failures.Count) { ($script:Failures | Select-Object -Unique) -join ", " } else { "none" }
Write-Host ("Fallbacks used: {0}" -f $fallbackText)
Write-Host ("Empty critical: {0}" -f $criticalText)
Write-Host ("Other empty: {0}" -f $otherText)
Write-Host ("Data quality: {0}" -f $script:QualityLine)
Write-Host ("Quality gate: report_allowed={0}; blocking={1}" -f $script:QualityReportAllowed, (($script:QualityBlocking | Select-Object -Unique) -join "; "))

$gateMessages = @()
if ($emptyCritical.Count -gt 0) {
    $gateMessages += "关键数据缺失: " + ($emptyCritical -join ", ")
}
if ($script:QualityFail -gt 0 -or -not $script:QualityReportAllowed) {
    $gateMessages += "数据一致性校验门禁失败: " + (($script:QualityBlocking | Select-Object -Unique) -join "; ")
}
if ($gateMessages.Count -gt 0) {
    $msg = ($gateMessages -join " | ") + "。请勿在门禁失败时生成报告。"
    if ($script:StrictMode) { throw $msg } else { Write-Warning $msg }
}
Write-Host "Data fetched to: $OutDir"
