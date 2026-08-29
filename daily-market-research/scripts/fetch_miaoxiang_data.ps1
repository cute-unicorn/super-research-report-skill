param(
    [string]$Workspace = "D:\codex\研报",
    [string]$Date = "",
    [string]$MxRoot = "",
    [string[]]$StockNames = @()
)

$ErrorActionPreference = "Stop"

if (-not $Date) {
    $Date = Get-Date -Format "yyyy-MM-dd"
}

$profilePath = "$HOME\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
if (-not $env:MX_APIKEY -and (Test-Path -LiteralPath $profilePath)) {
    . $profilePath
}
if (-not $env:MX_APIKEY) {
    throw "MX_APIKEY is not set. Configure it in the PowerShell profile first."
}

if (-not $MxRoot) {
    $MxRoot = Join-Path $HOME ".codex\skills"
}
if (-not (Test-Path -LiteralPath (Join-Path $MxRoot "mx-data"))) {
    throw "Miaoxiang skills not found under $MxRoot"
}

$OutDir = Join-Path $Workspace ("data\" + $Date + "\mx")
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$env:PYTHONIOENCODING = "utf-8"

function Invoke-Mx {
    param(
        [string]$ScriptPath,
        [string[]]$Arguments,
        [string]$LogName
    )
    if (-not (Test-Path -LiteralPath $ScriptPath)) {
        throw "Miaoxiang script not found: $ScriptPath"
    }
    $log = Join-Path $OutDir $LogName
    $oldEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = & python $ScriptPath @Arguments 2>&1
    $ErrorActionPreference = $oldEAP
    $output | Out-File -LiteralPath $log -Encoding utf8
    $code = $LASTEXITCODE
    Write-Host ("[{0}] exit={1}" -f $LogName, $code)
    if ($code -ne 0) {
        Write-Warning ("Miaoxiang query failed: " + $LogName)
    }
}

# 妙想金融数据
Invoke-Mx (Join-Path $MxRoot "mx-data\mx_data.py") @(
    "上证指数 深证成指 创业板指 沪深300 最新点位 涨跌幅 成交额",
    $OutDir
) "mx_data_indices.log"

# 宏观与汇率目前由 Iwencai 数据源负责；妙想接口暂未支持。
Invoke-Mx (Join-Path $MxRoot "mx-data\mx_data.py") @(
    "黄金 原油 铜 比特币 美元指数 美债收益率 最新",
    $OutDir
) "mx_data_global.log"

# 妙想情绪和资金结构备用数据
Invoke-Mx (Join-Path $MxRoot "mx-data\mx_data.py") @(
    "融资融券余额 北向资金 最新",
    $OutDir
) "mx_data_sentiment.log"

# 妙想两融市场合计口径与近5日趋势备用数据
Invoke-Mx (Join-Path $MxRoot "mx-data\mx_data.py") @(
    "沪深两市 融资融券余额 融资余额 融券余额 最新",
    $OutDir
) "mx_data_margin.log"

Invoke-Mx (Join-Path $MxRoot "mx-data\mx_data.py") @(
    "沪深两市 主力资金净流入 超大单 大单 中单 小单 最新",
    $OutDir
) "mx_data_fundflow.log"

# 妙想资讯搜索
Invoke-Mx (Join-Path $MxRoot "mx-search\mx_search.py") @(
    "今日A股市场重要财经新闻 政策 行业",
    $OutDir
) "mx_search_domestic.log"

Invoke-Mx (Join-Path $MxRoot "mx-search\mx_search.py") @(
    "美股 美联储 全球市场 原油 黄金 比特币 最新",
    $OutDir
) "mx_search_global.log"

# 妙想智能选股
Invoke-Mx (Join-Path $MxRoot "mx-xuangu\mx_xuangu.py") @(
    "--query", "今日涨幅大于5%的A股",
    "--output-dir", $OutDir
) "mx_xuangu_top_gainers.log"

Invoke-Mx (Join-Path $MxRoot "mx-xuangu\mx_xuangu.py") @(
    "--query", "今日主力资金净流入前20的A股",
    "--output-dir", $OutDir
) "mx_xuangu_fundflow.log"

Invoke-Mx (Join-Path $MxRoot "mx-xuangu\mx_xuangu.py") @(
    "--query", "今日涨停的A股",
    "--output-dir", $OutDir
) "mx_xuangu_limit_up.log"

Invoke-Mx (Join-Path $MxRoot "mx-xuangu\mx_xuangu.py") @(
    "--query", "今日最新买入评级的A股",
    "--output-dir", $OutDir
) "mx_xuangu_ratings.log"

# 选定个股的妙想金融数据
if ($StockNames.Count -gt 0) {
    $stockQuery = ($StockNames -join " ") + " 最新价 涨跌幅 市盈率 市净率 主力资金流向"
    Invoke-Mx (Join-Path $MxRoot "mx-data\mx_data.py") @(
        $stockQuery,
        $OutDir
    ) "mx_data_stocks.log"
}

Write-Host "Miaoxiang data fetched to: $OutDir"
