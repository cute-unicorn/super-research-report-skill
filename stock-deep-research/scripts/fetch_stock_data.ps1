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
if (-not $env:IWENCAI_API_KEY) { throw "IWENCAI_API_KEY is not set. Configure it in the PowerShell profile first." }

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
$env:PYTHONIOENCODING = "utf-8"

$script:Failures = @()
$script:Fallbacks = @()
$script:BuildFailed = $false
$script:QualityFail = 0
$script:QualityReportAllowed = $true
$script:QualityBlocking = @()

# ---------- 工具函数 ----------
function Get-JsonDataCount {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return 0 }
    try {
        $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
        if ([string]::IsNullOrWhiteSpace($raw)) { return 0 }
        $obj = $raw | ConvertFrom-Json
        if ($null -ne $obj.datas) { return @($obj.datas).Count }
        if ($null -ne $obj.data) { return @($obj.data).Count }
        return 0
    } catch { return 0 }
}

function Invoke-Query {
    param(
        [string]$Skill,
        [string]$Script,
        [string[]]$Arguments,
        [string]$OutFile,
        [switch]$AllowEmpty
    )
    $scriptPath = Join-Path $SkillRoot "$Skill\scripts\$Script"
    if (-not (Test-Path -LiteralPath $scriptPath)) { throw "Script not found: $scriptPath" }
    $outPath = Join-Path $OutDir $OutFile
    & python $scriptPath @Arguments 2>&1 | Out-File -LiteralPath $outPath -Encoding utf8
    $count = Get-JsonDataCount $outPath
    Write-Host ("[{0}] rows={1}" -f $OutFile, $count)
    if ($count -eq 0 -and -not $AllowEmpty) { $script:Failures += $OutFile }
    return $count
}

# 问财失败 -> 自动重试 -> 仍失败则标记（由妙想 mx-data 兜底段落补数）
function Invoke-QueryWithRetry {
    param(
        [string]$Skill,
        [string]$Script,
        [string[]]$Arguments,
        [string]$OutFile
    )
    $count = Invoke-Query -Skill $Skill -Script $Script -Arguments $Arguments -OutFile $OutFile -AllowEmpty
    if ($count -gt 0) { return $count }
    Write-Warning ("[retry] {0} empty, retrying with --call-type retry" -f $OutFile)
    $count = Invoke-Query -Skill $Skill -Script $Script -Arguments ($Arguments + @("--call-type", "retry")) -OutFile $OutFile -AllowEmpty
    if ($count -gt 0) { $script:Fallbacks += ("$OutFile(retry)") }
    return $count
}

function Invoke-Search {
    param([string]$Skill, [string]$Script, [string]$Query, [int]$Size, [string]$OutFile)
    $scriptPath = Join-Path $SkillRoot "$Skill\scripts\$Script"
    if (-not (Test-Path -LiteralPath $scriptPath)) { throw "Script not found: $scriptPath" }
    $outPath = Join-Path $OutDir $OutFile
    & python $scriptPath $Query "--size" $Size "--output" $outPath 2>&1 | Out-Null
    $count = Get-JsonDataCount $outPath
    Write-Host ("[{0}] rows={1}" -f $OutFile, $count)
}

if ($StockNames.Count -eq 0) {
    Write-Warning "No stock names provided. Use -StockNames '公司A 公司B'."
    return
}

$stocks = $StockNames -join " "
Write-Host "Fetching stock data for: $stocks"

# 行情 / 估值 / 资金 / 技术 / 筹码
Invoke-QueryWithRetry "hithink-market-query" "cli.py" @("--query", "$stocks 最新价 涨跌幅 换手率 主力资金净流入", "--limit", "10") "stocks_quote.json" | Out-Null
Invoke-QueryWithRetry "hithink-market-query" "cli.py" @("--query", "$stocks 市盈率 市净率 总市值 股息率", "--limit", "10") "stocks_valuation.json" | Out-Null
Invoke-QueryWithRetry "hithink-market-query" "cli.py" @("--query", "$stocks 主力资金净流入 主力增仓占比", "--limit", "10") "stocks_fundflow.json" | Out-Null
Invoke-QueryWithRetry "hithink-market-query" "cli.py" @("--query", "$stocks 20日均线 60日均线 RSI MACD", "--limit", "10") "stocks_tech.json" | Out-Null
Invoke-QueryWithRetry "hithink-market-query" "cli.py" @("--query", "$stocks 获利盘比例 平均成本 90%成本区间 70%成本区间 集中度90", "--limit", "10") "stocks_chips.json" | Out-Null

# 财务 / 比率 / 评级
Invoke-QueryWithRetry "hithink-finance-query" "cli.py" @("--query", "$stocks 营业收入 归母净利润 毛利率", "--limit", "10") "stocks_finance.json" | Out-Null
Invoke-QueryWithRetry "hithink-finance-query" "cli.py" @("--query", "$stocks ROE 资产负债率 每股收益 经营现金流", "--limit", "10") "stocks_ratios.json" | Out-Null
Invoke-QueryWithRetry "hithink-finance-query" "cli.py" @("--query", "$stocks 近12个季度 单季度营业收入 单季度归母净利润 单季度扣非净利润 单季度经营活动现金流 单季度销售毛利率 单季度净资产收益率 单季度销售商品和提供劳务收到的现金", "--limit", "20") "stocks_timeseries_single_q.json" | Out-Null
Invoke-QueryWithRetry "hithink-finance-query" "cli.py" @("--query", "$stocks 近12个季度 营业收入 归母净利润 扣非净利润 累计经营活动产生的现金流量净额 销售毛利率 净资产收益率 销售商品和提供劳务收到的现金 合同负债 应收账款 总资产 负债合计", "--limit", "20") "stocks_timeseries_cumulative.json" | Out-Null
Invoke-QueryWithRetry "hithink-insresearch-query" "cli.py" @("--query", "$stocks 最新评级 目标价 研报", "--limit", "10") "stocks_ratings.json" | Out-Null

# 新闻 / 公告 / 研报
Invoke-Search "news-search" "news_search.py" "$stocks 最新 业绩 公告 事件" 12 "stocks_news.json"
Invoke-Search "announcement-search" "announcement_search.py" "$stocks 最新公告 业绩 回购 增持" 10 "stocks_announcements.json"
Invoke-Search "report-search" "report_search.py" "$stocks 深度报告 点评 评级 目标价" 10 "stocks_reports.json"

# 妙想兜底：为缺失字段补数据（行情/财务/搜索）
$prevErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$homeSkills = Join-Path $HOME ".codex\skills"
$mxData = @((Join-Path $SkillRoot "mx-data\mx_data.py"), (Join-Path $homeSkills "mx-data\mx_data.py")) |
    Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$mxSearch = @((Join-Path $SkillRoot "mx-search\mx_search.py"), (Join-Path $homeSkills "mx-search\mx_search.py")) |
    Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (Test-Path -LiteralPath $mxData) {
    & python $mxData "$stocks 最新价 涨跌幅 市盈率 市净率 总市值 毛利率 净利率 经营现金流" $MxDir *> (Join-Path $MxDir "mx_data.log")
    Write-Host ("[mx_data] exit=" + $LASTEXITCODE)
}
if (Test-Path -LiteralPath $mxSearch) {
    & python $mxSearch "$stocks 最新 业绩 公告 产业链 政策 行业景气" $MxDir *> (Join-Path $MxDir "mx_search.log")
    Write-Host ("[mx_search] exit=" + $LASTEXITCODE)
}
$ErrorActionPreference = $prevErrorAction

# ---------- 多期财务时间序列构建与门禁 ----------
$timeseriesSingle = Join-Path $OutDir "stocks_timeseries_single_q.json"
$timeseriesCumulative = Join-Path $OutDir "stocks_timeseries_cumulative.json"
$timeseriesPath = Join-Path $OutDir "stocks_timeseries.json"
$timeseriesBuilder = Join-Path $PSScriptRoot "lib\build_timeseries.py"
$timeseriesValidator = Join-Path $PSScriptRoot "lib\validate_stock_facts.py"
$timeseriesQualityPath = Join-Path $OutDir "stock_data_quality.json"

if (Test-Path -LiteralPath $timeseriesBuilder) {
    $buildLines = & python $timeseriesBuilder `
        --single-q $timeseriesSingle `
        --cumulative $timeseriesCumulative `
        --out $timeseriesPath `
        --as-of $Date 2>&1
    $buildExit = $LASTEXITCODE
    $buildLines | Out-File -LiteralPath (Join-Path $OutDir "stocks_timeseries_build.log") -Encoding utf8
    if ($buildExit -ne 0) {
        $script:Failures += "stocks_timeseries(build)"
        $script:BuildFailed = $true
    }
} else {
    $script:Failures += "build_timeseries.py(missing)"
    $script:BuildFailed = $true
}

$qualitySummary = "not checked"
if (Test-Path -LiteralPath $timeseriesValidator) {
    $qualityLines = & python $timeseriesValidator `
        $OutDir `
        --out $timeseriesQualityPath `
        --as-of $Date `
        --strict 2>&1
    $qualityExit = $LASTEXITCODE
    $qualityLines | Out-File -LiteralPath (Join-Path $OutDir "stock_data_quality.log") -Encoding utf8
    $qualitySummary = ($qualityLines | Select-Object -First 1)
    if ($qualityExit -ne 0) {
        $script:Failures += "stock_data_quality(critical)"
        $script:QualityFail = 1
    }
} else {
    $script:Failures += "validate_stock_facts.py(missing)"
    $script:QualityFail = 1
    $script:QualityReportAllowed = $false
    $script:QualityBlocking = @("validate_stock_facts.py missing")
}

if (Test-Path -LiteralPath $timeseriesQualityPath) {
    try {
        $qualityJson = Get-Content -LiteralPath $timeseriesQualityPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $script:QualityReportAllowed = [bool]$qualityJson.report_allowed
        if ($null -ne $qualityJson.summary -and [int]$qualityJson.summary.fail -gt 0) {
            $script:QualityFail = 1
        }
        $script:QualityBlocking = @($qualityJson.blocking_reasons)
    } catch {
        $script:QualityFail = 1
        $script:QualityReportAllowed = $false
        $script:QualityBlocking = @("stock_data_quality.json parse failed: " + $_.Exception.Message)
    }
}

# ---------- 校验门禁 ----------
$criticalFiles = @("stocks_quote.json","stocks_valuation.json","stocks_finance.json","stocks_ratios.json","stocks_timeseries.json")
$emptyCritical = @()
foreach ($cf in $criticalFiles) {
    if ((Get-JsonDataCount (Join-Path $OutDir $cf)) -eq 0) { $emptyCritical += $cf }
}
if (-not (Test-Path -LiteralPath $timeseriesQualityPath)) {
    $emptyCritical += "stock_data_quality.json"
}

Write-Host ""
Write-Host "===== STOCK FETCH SUMMARY ====="
Write-Host ("Output: {0}" -f $OutDir)
$retryText = if ($script:Fallbacks.Count) { ($script:Fallbacks | Select-Object -Unique) -join ", " } else { "none" }
$critText = if ($emptyCritical.Count) { $emptyCritical -join ", " } else { "none" }
$otherText = if ($script:Failures.Count) { ($script:Failures | Select-Object -Unique) -join ", " } else { "none" }
Write-Host ("Retry succeeded: {0}" -f $retryText)
Write-Host ("Empty critical: {0}" -f $critText)
Write-Host ("Other empty: {0}" -f $otherText)
Write-Host ("Data quality: {0}" -f $qualitySummary)
Write-Host ("Quality gate: report_allowed={0}; blocking={1}" -f $script:QualityReportAllowed, (($script:QualityBlocking | Select-Object -Unique) -join "; "))

$gateMessages = @()
if ($emptyCritical.Count -gt 0) {
    $gateMessages += "个股关键数据缺失: " + ($emptyCritical -join ", ")
}
if ($script:BuildFailed) {
    $gateMessages += "财务时间序列构建失败"
}
if ($script:QualityFail -gt 0 -or -not $script:QualityReportAllowed) {
    $gateMessages += "个股数据质量门禁失败: " + (($script:QualityBlocking | Select-Object -Unique) -join "; ")
}
if ($gateMessages.Count -gt 0) {
    $msg = ($gateMessages -join " | ") + "。请勿在门禁失败时生成个股研报。"
    if ($script:StrictMode) { throw $msg } else { Write-Warning $msg }
}
Write-Host "Stock data fetched to: $OutDir"
