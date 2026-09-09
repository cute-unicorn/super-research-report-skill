# 通用抓取辅助函数（供 fetch_daily_data.ps1 复用）
# 依赖调用方预先设置: $script:SkillRoot, $script:OutDir, $script:MxDir, $script:MxRoot, $script:Failures, $script:Fallbacks

function Get-CnDate { param([datetime]$D) return $D.ToString("yyyy年M月d日") }

# 跳过周末；节假日由接口自身回退到最近交易日
function Get-LastTradingDay {
    param([datetime]$D)
    $d = $D.AddDays(-1)
    while ($d.DayOfWeek -eq 'Saturday' -or $d.DayOfWeek -eq 'Sunday') { $d = $d.AddDays(-1) }
    return $d
}

# 读取 JSON 的 datas/data 条数，文件缺失或解析失败返回 0
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
    $scriptPath = Join-Path $script:SkillRoot "$Skill\scripts\$Script"
    if (-not (Test-Path -LiteralPath $scriptPath)) { throw "Script not found: $scriptPath" }
    $outPath = Join-Path $script:OutDir $OutFile
    & python $scriptPath @Arguments 2>&1 | Out-File -LiteralPath $outPath -Encoding utf8
    $count = Get-JsonDataCount $outPath
    Write-Host ("[{0}] rows={1}" -f $OutFile, $count)
    if ($count -eq 0 -and -not $AllowEmpty) { $script:Failures += $OutFile }
    return $count
}

# 问财失败 -> 重试 -> 妙想选股兜底 -> 转成问财同构结构
function Invoke-QueryWithFallback {
    param(
        [string]$Skill,
        [string]$Script,
        [string[]]$Arguments,
        [string]$OutFile,
        [string]$MxQuery
    )
    $count = Invoke-Query -Skill $Skill -Script $Script -Arguments $Arguments -OutFile $OutFile -AllowEmpty
    if ($count -gt 0) { return $count }

    Write-Warning ("[retry] {0} empty, retrying with --call-type retry" -f $OutFile)
    $count = Invoke-Query -Skill $Skill -Script $Script -Arguments ($Arguments + @("--call-type", "retry")) -OutFile $OutFile -AllowEmpty
    if ($count -gt 0) { return $count }

    if (-not $MxQuery) { return 0 }
    $mxScript = Join-Path $script:MxRoot "mx-xuangu\mx_xuangu.py"
    $converter = Join-Path $PSScriptRoot "..\mx_to_iwencai.py"
    if (-not (Test-Path -LiteralPath $mxScript) -or -not (Test-Path -LiteralPath $converter)) {
        Write-Warning ("[fallback] mx unavailable for {0}" -f $OutFile); return 0
    }
    Write-Warning ("[fallback] {0} -> mx-xuangu: {1}" -f $OutFile, $MxQuery)
    & python $mxScript --query $MxQuery --output-dir $script:MxDir 2>&1 | Out-Null
    $rawFile = Get-ChildItem -LiteralPath $script:MxDir -Filter "*_raw.json" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $rawFile) { Write-Warning ("[fallback] no mx raw json for {0}" -f $OutFile); return 0 }

    $outPath = Join-Path $script:OutDir $OutFile
    & python $converter $rawFile.FullName $outPath --query $MxQuery 2>&1 | Out-Null
    $count = Get-JsonDataCount $outPath
    Write-Host ("[{0}] fallback rows={1} source=mx-xuangu" -f $OutFile, $count)
    if ($count -gt 0) { $script:Fallbacks += $OutFile } else { $script:Failures += $OutFile }
    return $count
}

function Invoke-Search {
    param([string]$Skill, [string]$Script, [string]$Query, [int]$Size, [string]$OutFile)
    $scriptPath = Join-Path $script:SkillRoot "$Skill\scripts\$Script"
    if (-not (Test-Path -LiteralPath $scriptPath)) { throw "Script not found: $scriptPath" }
    $outPath = Join-Path $script:OutDir $OutFile
    & python $scriptPath $Query "--size" $Size "--output" $outPath 2>&1 | Out-Null
    $count = Get-JsonDataCount $outPath
    Write-Host ("[{0}] rows={1}" -f $OutFile, $count)
}
