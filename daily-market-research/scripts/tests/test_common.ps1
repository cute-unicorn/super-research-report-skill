# 辅助函数与兜底链路测试
# 用法: powershell -ExecutionPolicy Bypass -File scripts\tests\test_common.ps1

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$scriptRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script:SkillRoot = Join-Path $HOME ".codex\skills"
$script:MxRoot = Join-Path $HOME ".codex\skills"
$script:Failures = @()
$script:Fallbacks = @()
$script:Critical = @()

$tmp = Join-Path $env:TEMP ("dmr_test_" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$script:OutDir = Join-Path $tmp "out"
$script:MxDir = Join-Path $tmp "mx"
New-Item -ItemType Directory -Force -Path $script:OutDir, $script:MxDir | Out-Null

. (Join-Path $scriptRoot "lib\common.ps1")

$pass = 0
$fail = 0

function Assert-Equal {
    param($Actual, $Expected, [string]$Name)
    if ("$Actual" -eq "$Expected") {
        Write-Host ("  PASS  {0}" -f $Name) -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host ("  FAIL  {0}: expected [{1}] got [{2}]" -f $Name, $Expected, $Actual) -ForegroundColor Red
        $script:fail++
    }
}

function Assert-True {
    param($Condition, [string]$Name)
    if ($Condition) {
        Write-Host ("  PASS  {0}" -f $Name) -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host ("  FAIL  {0}" -f $Name) -ForegroundColor Red
        $script:fail++
    }
}

Write-Host "`n[1] Get-LastTradingDay" -ForegroundColor Cyan
Assert-Equal (Get-LastTradingDay ([datetime]"2026-09-07")).ToString("yyyy-MM-dd") "2026-09-04" "周一 -> 上周五"
Assert-Equal (Get-LastTradingDay ([datetime]"2026-09-08")).ToString("yyyy-MM-dd") "2026-09-07" "周二 -> 周一"
Assert-Equal (Get-LastTradingDay ([datetime]"2026-09-12")).ToString("yyyy-MM-dd") "2026-09-11" "周六 -> 周五"
Assert-Equal (Get-LastTradingDay ([datetime]"2026-09-13")).ToString("yyyy-MM-dd") "2026-09-11" "周日 -> 周五"

Write-Host "`n[2] Get-JsonDataCount" -ForegroundColor Cyan
$missing = Join-Path $script:OutDir "nope.json"
Assert-Equal (Get-JsonDataCount $missing) 0 "缺失文件 -> 0"

$emptyFile = Join-Path $script:OutDir "empty.json"
'{ "success": true, "datas": [] }' | Set-Content -LiteralPath $emptyFile -Encoding UTF8
Assert-Equal (Get-JsonDataCount $emptyFile) 0 "空 datas -> 0"

$okFile = Join-Path $script:OutDir "ok.json"
'{ "success": true, "datas": [ {"a":1}, {"a":2} ] }' | Set-Content -LiteralPath $okFile -Encoding UTF8
Assert-Equal (Get-JsonDataCount $okFile) 2 "有效 datas -> 2"

$dataFile = Join-Path $script:OutDir "data.json"
'{ "status_msg": "OK", "data": [ {"a":1}, {"a":2}, {"a":3} ] }' | Set-Content -LiteralPath $dataFile -Encoding UTF8
Assert-Equal (Get-JsonDataCount $dataFile) 3 "搜索型 data -> 3"

$badFile = Join-Path $script:OutDir "bad.json"
'not json at all' | Set-Content -LiteralPath $badFile -Encoding UTF8
Assert-Equal (Get-JsonDataCount $badFile) 0 "非法 JSON -> 0"

Write-Host "`n[3] mx_to_iwencai.py 转换器" -ForegroundColor Cyan
$converter = Join-Path $scriptRoot "mx_to_iwencai.py"
$fixture = Join-Path $PSScriptRoot "fixture_mx_raw.json"
$convOut = Join-Path $script:OutDir "converted.json"
if (Test-Path -LiteralPath $fixture) {
    & python $converter $fixture $convOut --query "测试查询" 2>&1 | Out-Null
    $count = Get-JsonDataCount $convOut
    Assert-Equal $count 2 "转换 fixture -> 2 条"
    $conv = Get-Content -LiteralPath $convOut -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-Equal $conv.source "mx-xuangu" "输出带 source 标记"
    Assert-True ($null -ne $conv.datas[0].'名称') "中文列名保留"
} else {
    Write-Host "  SKIP  fixture 不存在" -ForegroundColor Yellow
}

Write-Host "`n[4] 兜底链路（强制问财失败 -> 妙想补数）" -ForegroundColor Cyan
$mxScript = Join-Path $script:MxRoot "mx-xuangu\mx_xuangu.py"
if (Test-Path -LiteralPath $mxScript) {
    # 逻辑自相矛盾的条件，问财必然返回 0，用于触发 retry + mx 兜底
    $impossible = "市盈率小于0且大于100的股票"
    $n = Invoke-QueryWithFallback -Skill "hithink-market-query" -Script "cli.py" `
        -Arguments @("--query", $impossible, "--limit", "5") `
        -OutFile "fallback_probe.json" -MxQuery "2026年9月4日涨幅前20的A股"
    Assert-True ($n -gt 0) "兜底后取得数据（rows=$n）"
    Assert-True ($script:Fallbacks -contains "fallback_probe.json") "记录为 fallback 来源"
    $probe = Get-Content -LiteralPath (Join-Path $script:OutDir "fallback_probe.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-Equal $probe.source "mx-xuangu" "兜底文件标注 source=mx-xuangu"
} else {
    Write-Host "  SKIP  妙想技能未安装" -ForegroundColor Yellow
}

Write-Host "`n[5] 校验门禁逻辑" -ForegroundColor Cyan
$crit = @("ok.json", "nope.json")
$empty = @()
foreach ($c in $crit) { if ((Get-JsonDataCount (Join-Path $script:OutDir $c)) -eq 0) { $empty += $c } }
Assert-Equal $empty.Count 1 "识别出 1 个空关键文件"
Assert-Equal $empty[0] "nope.json" "空文件名单正确"

Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ("`n===== RESULT: {0} passed, {1} failed =====" -f $script:pass, $script:fail) -ForegroundColor Cyan
if ($script:fail -gt 0) { exit 1 }
exit 0
