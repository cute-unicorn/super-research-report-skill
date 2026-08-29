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

if ($StockNames.Count -eq 0) {
    Write-Warning "No stock names provided. Use -StockNames '公司A 公司B'."
    return
}

$stocks = $StockNames -join " "
Write-Host "Fetching stock data for: $stocks"

# 行情 / 估值 / 资金 / 技术 / 筹码
Invoke-Query "hithink-market-query" "cli.py" @("--query", "$stocks 最新价 涨跌幅 换手率 主力资金净流入", "--limit", "10") "stocks_quote.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "$stocks 市盈率 市净率 总市值 股息率", "--limit", "10") "stocks_valuation.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "$stocks 主力资金净流入 主力增仓占比", "--limit", "10", "--call-type", "retry") "stocks_fundflow.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "$stocks 20日均线 60日均线 RSI MACD", "--limit", "10") "stocks_tech.json"
Invoke-Query "hithink-market-query" "cli.py" @("--query", "$stocks 获利盘比例 平均成本 90%成本区间 70%成本区间 集中度90", "--limit", "10") "stocks_chips.json"

# 财务 / 比率 / 评级
Invoke-Query "hithink-finance-query" "cli.py" @("--query", "$stocks 营业收入 归母净利润 毛利率", "--limit", "10") "stocks_finance.json"
Invoke-Query "hithink-finance-query" "cli.py" @("--query", "$stocks ROE 资产负债率 每股收益 经营现金流", "--limit", "10") "stocks_ratios.json"
Invoke-Query "hithink-insresearch-query" "cli.py" @("--query", "$stocks 最新评级 目标价 研报", "--limit", "10") "stocks_ratings.json"
# 新闻 / 公告 / 研报
Invoke-Search "news-search" "news_search.py" "$stocks 最新 业绩 公告 事件" 12 "stocks_news.json"
Invoke-Search "announcement-search" "announcement_search.py" "$stocks 最新公告 业绩 回购 增持" 10 "stocks_announcements.json"
Invoke-Search "report-search" "report_search.py" "$stocks 深度报告 点评 评级 目标价" 10 "stocks_reports.json"

# 妙想备用数据（行情 / 财务 / 行业与政策搜索）
$mxDir = Join-Path $OutDir "mx"
New-Item -ItemType Directory -Force -Path $mxDir | Out-Null
$prevErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$homeSkills = Join-Path $HOME ".codex\skills"
$mxData = @((Join-Path $SkillRoot "mx-data\mx_data.py"), (Join-Path $homeSkills "mx-data\mx_data.py")) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$mxSearch = @((Join-Path $SkillRoot "mx-search\mx_search.py"), (Join-Path $homeSkills "mx-search\mx_search.py")) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (Test-Path -LiteralPath $mxData) {
    & python $mxData "$stocks 最新价 涨跌幅 市盈率 市净率 总市值 毛利率 净利率 经营现金流" $mxDir *> (Join-Path $mxDir "mx_data.log")
    Write-Host ("[mx_data] exit=" + $LASTEXITCODE)
}
if (Test-Path -LiteralPath $mxSearch) {
    & python $mxSearch "$stocks 最新 业绩 公告 产业链 政策 行业景气" $mxDir *> (Join-Path $mxDir "mx_search.log")
    Write-Host ("[mx_search] exit=" + $LASTEXITCODE)
}
$ErrorActionPreference = $prevErrorAction

Write-Host "Stock data fetched to: $OutDir"
