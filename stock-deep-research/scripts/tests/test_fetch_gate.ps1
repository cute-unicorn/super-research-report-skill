# 个股抓取门禁的端到端集成测试。
# 使用临时 stub 数据源，不访问真实 API。
#
# 用法:
#   powershell -ExecutionPolicy Bypass -File scripts\tests\test_fetch_gate.ps1

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$scriptRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$fetchScript = Join-Path $scriptRoot "fetch_stock_data.ps1"
$tag = [guid]::NewGuid().ToString("N").Substring(0, 8)
$tempRoot = Join-Path $env:TEMP ("stock_gate_" + $tag)
$workspace = Join-Path $tempRoot "workspace"
$skillRoot = Join-Path $tempRoot "skills"

foreach ($relative in @(
    "hithink-market-query\scripts",
    "hithink-finance-query\scripts",
    "hithink-insresearch-query\scripts",
    "news-search\scripts",
    "announcement-search\scripts",
    "report-search\scripts"
)) {
    New-Item -ItemType Directory -Force -Path (Join-Path $skillRoot $relative) | Out-Null
}

$stubSource = Join-Path $PSScriptRoot "stub_source.py"

$targets = @(
    "hithink-market-query\scripts\cli.py",
    "hithink-finance-query\scripts\cli.py",
    "hithink-insresearch-query\scripts\cli.py",
    "news-search\scripts\news_search.py",
    "announcement-search\scripts\announcement_search.py",
    "report-search\scripts\report_search.py"
)
foreach ($target in $targets) {
    Copy-Item -LiteralPath $stubSource -Destination (Join-Path $skillRoot $target) -Force
}

$oldHome = $env:HOME
$oldKey = $env:IWENCAI_API_KEY
$oldBase = $env:IWENCAI_BASE_URL
$pass = 0
$fail = 0

function Assert-True {
    param([bool]$Condition, [string]$Name)
    if ($Condition) {
        Write-Host ("  PASS  {0}" -f $Name) -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host ("  FAIL  {0}" -f $Name) -ForegroundColor Red
        $script:fail++
    }
}

try {
    $oldErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $env:HOME = $tempRoot
    $env:IWENCAI_API_KEY = "dummy"
    $env:IWENCAI_BASE_URL = "https://example.invalid"

    Write-Host "`n[1] 默认严格模式应非零退出"
    $strictOutput = & powershell -ExecutionPolicy Bypass -File $fetchScript `
        -Workspace $workspace -Date "2026-10-13" -SkillRoot $skillRoot `
        -StockNames "测试公司" -Strict 2>&1
    $strictExit = $LASTEXITCODE
    Assert-True ($strictExit -ne 0) ("严格模式退出码非零，实际=" + $strictExit)
    Assert-True (($strictOutput -join "`n") -match "个股数据质量门禁失败") "严格模式输出门禁失败原因"

    Write-Host "`n[2] AllowCritical 仅用于调试时允许继续"
    $allowOutput = & powershell -ExecutionPolicy Bypass -File $fetchScript `
        -Workspace $workspace -Date "2026-10-13" -SkillRoot $skillRoot `
        -StockNames "测试公司" -AllowCritical 2>&1
    $allowExit = $LASTEXITCODE
    Assert-True ($allowExit -eq 0) ("AllowCritical 退出码为 0，实际=" + $allowExit)
    Assert-True (($allowOutput -join "`n") -match "report_allowed=False") "AllowCritical 仍显示 report_allowed=False"
} finally {
    $ErrorActionPreference = $oldErrorAction
    $env:HOME = $oldHome
    $env:IWENCAI_API_KEY = $oldKey
    $env:IWENCAI_BASE_URL = $oldBase
}

Write-Host ("`n===== RESULT: {0} passed, {1} failed =====" -f $pass, $fail) -ForegroundColor Cyan
if ($fail -gt 0) { exit 1 }
exit 0
