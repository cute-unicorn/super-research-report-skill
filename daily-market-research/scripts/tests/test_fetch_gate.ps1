# 日频抓取门禁的端到端集成测试。
# 使用临时 stub 数据源，不访问真实 API。

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$scriptRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$fetchScript = Join-Path $scriptRoot "fetch_daily_data.ps1"
$tag = [guid]::NewGuid().ToString("N").Substring(0, 8)
$tempRoot = Join-Path $env:TEMP ("daily_gate_" + $tag)
$workspace = Join-Path $tempRoot "workspace"
$skillRoot = Join-Path $tempRoot "skills"

$skills = @(
    "hithink-zhishu-query",
    "hithink-market-query",
    "hithink-industry-query",
    "hithink-macro-query",
    "hithink-finance-query",
    "hithink-insresearch-query",
    "news-search",
    "announcement-search",
    "report-search"
)
foreach ($skill in $skills) {
    New-Item -ItemType Directory -Force -Path (Join-Path $skillRoot "$skill\scripts") | Out-Null
}

$stubSource = Join-Path $PSScriptRoot "stub_source.py"
foreach ($skill in $skills) {
    $name = if ($skill -eq "news-search") { "news_search.py" }
            elseif ($skill -eq "announcement-search") { "announcement_search.py" }
            elseif ($skill -eq "report-search") { "report_search.py" }
            else { "cli.py" }
    Copy-Item -LiteralPath $stubSource -Destination (Join-Path $skillRoot "$skill\scripts\$name") -Force
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
    $dataDir = Join-Path $workspace "data\2026-10-13"
    New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
    $stockTimeseries = Join-Path $dataDir "stocks_timeseries.json"
    '{"datas":[{"sentinel":true}]}' | Set-Content -LiteralPath $stockTimeseries -Encoding utf8

    Write-Host "`n[1] 默认严格模式应非零退出"
    $strictOutput = & powershell -ExecutionPolicy Bypass -File $fetchScript `
        -Workspace $workspace -Date "2026-10-13" -SkillRoot $skillRoot -Strict 2>&1
    $strictExit = $LASTEXITCODE
    Assert-True ($strictExit -ne 0) ("严格模式退出码非零，实际=" + $strictExit)
    Assert-True (($strictOutput -join "`n") -match "数据一致性校验门禁失败") "严格模式输出门禁失败原因"
    Assert-True (Test-Path -LiteralPath $stockTimeseries) "日报抓取不得删除个股时间序列"

    Write-Host "`n[2] AllowCritical 仅用于调试时允许继续"
    $allowOutput = & powershell -ExecutionPolicy Bypass -File $fetchScript `
        -Workspace $workspace -Date "2026-10-13" -SkillRoot $skillRoot -AllowCritical 2>&1
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
