[CmdletBinding()]
param(
    [string]$Prompt = 'Explain a practical way to diagnose a deadlock in a Python service. Give the steps and one short code example.',
    [ValidateRange(32, 4096)][int]$MaxTokens = 256,
    [ValidateRange(1, 10)][int]$Repeats = 3,
    [switch]$SkipDual,
    [switch]$DualOnly
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')

$resultsPath = Join-Path $script:AiRoot 'BENCHMARK_RUNTIME_RESULTS.csv'
$answersPath = Join-Path $script:AiRoot 'BENCHMARK_ANSWERS.jsonl'
$stressPath = Join-Path $script:AiRoot 'DUAL_STRESS_RESULTS.jsonl'
$sessionId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$script:AiBenchmarkSession = $sessionId
$startQwen = Join-Path $PSScriptRoot 'start-qwen.ps1'
$startMini = Join-Path $PSScriptRoot 'start-minicpm.ps1'
$startSpark = Join-Path $PSScriptRoot 'start-spark.ps1'
$startBonsai = Join-Path $PSScriptRoot 'start-bonsai.ps1'
$startDual = Join-Path $PSScriptRoot 'start-dual.ps1'
$benchmark = Join-Path $PSScriptRoot 'benchmark-model.ps1'

function Get-ProjectEnvValue {
    param([Parameter(Mandatory)][string]$Name, [string]$Default = '')
    $processValue = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if (-not [string]::IsNullOrWhiteSpace($processValue)) { return $processValue }
    $line = Get-Content -LiteralPath (Join-Path $script:AiRoot '.env') | Where-Object {
        $_ -match ('^' + [regex]::Escape($Name) + '=')
    } | Select-Object -First 1
    if ($line) { return ($line -split '=', 2)[1].Trim() }
    return $Default
}

function Add-BenchmarkFailure {
    param([string]$Model, [string]$GGUF, [string]$Quant, [string]$Context, [string]$Variant, [string]$ErrorText)
    $row = [pscustomobject][ordered]@{
        TimestampUtc = [DateTime]::UtcNow.ToString('o'); BenchmarkSession = $script:AiBenchmarkSession
        Model = $Model; GGUF = $GGUF; Quant = $Quant; Context = $Context; Variant = $Variant
        ReasoningEffort = ''; ThinkingMode = ''; LoadTimeSeconds = ''; Repeat = ''; TTFTSeconds = ''; TotalSeconds = ''
        PromptTokens = ''; PP_TokPerSec = ''; GeneratedTokens = ''; TG_TokPerSec = ''
        DraftTokens = ''; AcceptedDraftTokens = ''; AcceptancePercent = ''; DraftVerificationSteps = ''
        VRAMIdleMiB = ''; VRAMPeakMiB = ''; GPUUtilizationAvgPercent = ''; PowerAvgW = ''
        Errors = $ErrorText; QualitySanityCheck = 'Not completed'; ResponseExcerpt = ''
    }
    if (Test-Path -LiteralPath $resultsPath) { $row | Export-Csv -LiteralPath $resultsPath -NoTypeInformation -Append -Encoding utf8 }
    else { $row | Export-Csv -LiteralPath $resultsPath -NoTypeInformation -Encoding utf8 }
    Write-Warning "$Variant failed: $ErrorText"
}

function Invoke-BenchmarkCase {
    param(
        [Parameter(Mandatory)][string]$Model, [Parameter(Mandatory)][string]$GGUF,
        [Parameter(Mandatory)][string]$Quant, [Parameter(Mandatory)][string]$Context,
        [Parameter(Mandatory)][string]$Variant, [Parameter(Mandatory)][string]$StartScript,
        [hashtable]$Environment = @{}, [string]$BaseUrl = 'http://127.0.0.1:8080',
        [string]$ReasoningEffort = '', [ValidateSet('off', 'on')][string]$ThinkingMode
    )
    $saved = @{}
    foreach ($name in $Environment.Keys) {
        $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, [string]$Environment[$name], 'Process')
    }
    $watch = [Diagnostics.Stopwatch]::StartNew()
    try {
        $startResults = @(& $StartScript | Where-Object { $null -ne $_.PSObject.Properties['StartupSeconds'] })
        $watch.Stop()
        $startupInfo = @($startResults | Select-Object -Last 1)
        $loadSeconds = if ($startupInfo.Count -gt 0) { [double]$startupInfo[0].StartupSeconds } else { $watch.Elapsed.TotalSeconds }
        $benchParams = @{
            BaseUrl = $BaseUrl; Prompt = $Prompt; MaxTokens = $MaxTokens; Repeats = $Repeats; Seed = 8128
            ModelLabel = $Model; GGUF = $GGUF; Quant = $Quant; Context = $Context
            LoadTimeSeconds = $loadSeconds; Variant = $Variant; SessionId = $sessionId
        }
        if (-not [string]::IsNullOrWhiteSpace($ReasoningEffort)) { $benchParams.ReasoningEffort = $ReasoningEffort }
        if (-not [string]::IsNullOrWhiteSpace($ThinkingMode)) { $benchParams.ThinkingMode = $ThinkingMode }
        & $benchmark @benchParams
    }
    catch {
        Add-BenchmarkFailure -Model $Model -GGUF $GGUF -Quant $Quant -Context $Context -Variant $Variant -ErrorText $_.Exception.Message
    }
    finally {
        foreach ($name in $Environment.Keys) {
            [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process')
        }
    }
}

function Get-AverageTg {
    param([Parameter(Mandatory)][string]$Model)
    if (-not (Test-Path -LiteralPath $resultsPath)) { return $null }
      $values = @(Import-Csv -LiteralPath $resultsPath | Where-Object {
        $_.BenchmarkSession -eq $sessionId -and $_.Model -eq $Model -and
        [string]::IsNullOrWhiteSpace($_.Errors) -and $_.TG_TokPerSec -match '^[0-9]+([.,][0-9]+)?$'
    } | ForEach-Object {
        $value = 0.0
        if ([double]::TryParse($_.TG_TokPerSec, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::CurrentCulture, [ref]$value)) { $value }
    })
    if ($values.Count -eq 0) { return $null }
    return [double](($values | Measure-Object -Average).Average)
}

function Get-MaxPeakVram {
    param([Parameter(Mandatory)][string[]]$Models)
    if (-not (Test-Path -LiteralPath $resultsPath)) { return $null }
    $values = @(Import-Csv -LiteralPath $resultsPath | Where-Object {
        $_.BenchmarkSession -eq $sessionId -and $Models -contains $_.Model -and
        [string]::IsNullOrWhiteSpace($_.Errors) -and $_.VRAMPeakMiB -match '^[0-9.]+$'
    } | ForEach-Object { [double]::Parse($_.VRAMPeakMiB, [Globalization.CultureInfo]::InvariantCulture) })
    if ($values.Count -eq 0) { return $null }
    return [double](($values | Measure-Object -Maximum).Maximum)
}

function Invoke-DualStress {
    $bodyMini = @{ model = 'minicpm5-2b-dual'; messages = @(@{ role = 'user'; content = $Prompt }); max_tokens = 96; temperature = 0; seed = 8128 } | ConvertTo-Json -Depth 8 -Compress
    $bodySpark = @{ model = 'spark-x2.5-4b-dual'; messages = @(@{ role = 'user'; content = $Prompt }); max_tokens = 96; temperature = 0; seed = 8128 } | ConvertTo-Json -Depth 8 -Compress
    $jobs = @(
        Start-Job -ArgumentList 'http://127.0.0.1:8083/v1/chat/completions', $bodyMini -ScriptBlock {
            param($Uri, $Body)
            try { $r = Invoke-RestMethod -Uri $Uri -Method Post -ContentType 'application/json' -Body $Body -TimeoutSec 300; [pscustomobject]@{ Endpoint = $Uri; Error = ''; Text = [string]$r.choices[0].message.content } }
            catch { [pscustomobject]@{ Endpoint = $Uri; Error = $_.Exception.Message; Text = '' } }
        }
        Start-Job -ArgumentList 'http://127.0.0.1:8084/v1/chat/completions', $bodySpark -ScriptBlock {
            param($Uri, $Body)
            try { $r = Invoke-RestMethod -Uri $Uri -Method Post -ContentType 'application/json' -Body $Body -TimeoutSec 300; [pscustomobject]@{ Endpoint = $Uri; Error = ''; Text = [string]$r.choices[0].message.content } }
            catch { [pscustomobject]@{ Endpoint = $Uri; Error = $_.Exception.Message; Text = '' } }
        }
    )
    $samples = [Collections.Generic.List[object]]::new()
    $watch = [Diagnostics.Stopwatch]::StartNew()
    try {
        while (@($jobs | Where-Object { $_.State -eq 'Running' }).Count -gt 0 -and $watch.Elapsed.TotalSeconds -lt 300) {
            $raw = & nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw --format=csv,noheader,nounits
            if ($LASTEXITCODE -eq 0 -and $raw) {
                $parts = ("$raw" -split ',') | ForEach-Object { $_.Trim() }
                if ($parts.Count -ge 3) {
                    $samples.Add([pscustomobject]@{
                        Utilization = [double]::Parse($parts[0], [Globalization.CultureInfo]::InvariantCulture)
                        MemoryMiB = [double]::Parse($parts[1], [Globalization.CultureInfo]::InvariantCulture)
                        PowerW = [double]::Parse($parts[2], [Globalization.CultureInfo]::InvariantCulture)
                    })
                }
            }
            Start-Sleep -Milliseconds 300
        }
        $timedOut = @($jobs | Where-Object { $_.State -eq 'Running' }).Count -gt 0
        if ($timedOut) { $jobs | Stop-Job -ErrorAction SilentlyContinue }
        $results = @($jobs | Receive-Job -ErrorAction SilentlyContinue)
        $watch.Stop()
        $logs = @(Invoke-AiCompose -Profiles @('dual-minicpm', 'dual-spark') -Arguments @('logs', '--tail', '300', 'dual-minicpm', 'dual-spark')) -join [Environment]::NewLine
        $runtimeErrors = [bool]($logs -match '(?i)out of memory|cuda error|failed to allocate|illegal memory access|device-side assert')
        $healthy = $true
        foreach ($url in @('http://127.0.0.1:8083', 'http://127.0.0.1:8084')) {
            try { Wait-ForHttpEndpoint -Uri "$url/health" -TimeoutSeconds 5 } catch { $healthy = $false }
        }
        $peak = if ($samples.Count -gt 0) { [double](($samples | Measure-Object -Property MemoryMiB -Maximum).Maximum) } else { $null }
        $freeAtPeak = if ($null -ne $peak) { (Get-GpuMemoryTotalMiB) - $peak } else { $null }
        $requestErrors = @($results | Where-Object { -not [string]::IsNullOrWhiteSpace($_.Error) }).Count -gt 0
        $passed = (-not $timedOut) -and (-not $requestErrors) -and (-not $runtimeErrors) -and $healthy -and ($null -ne $freeAtPeak) -and ($freeAtPeak -ge 1024)
        $entry = [pscustomobject]@{
            timestamp_utc = [DateTime]::UtcNow.ToString('o'); session = $sessionId
            result = if ($passed) { 'PASS' } else { 'FAIL' }
            elapsed_seconds = [Math]::Round($watch.Elapsed.TotalSeconds, 3)
            peak_vram_mib = $peak; free_at_peak_mib = $freeAtPeak
            gpu_utilization_avg_percent = if ($samples.Count -gt 0) { [Math]::Round((($samples | Measure-Object -Property Utilization -Average).Average), 2) } else { $null }
            power_avg_w = if ($samples.Count -gt 0) { [Math]::Round((($samples | Measure-Object -Property PowerW -Average).Average), 2) } else { $null }
            timed_out = $timedOut; runtime_errors = $runtimeErrors; endpoints_healthy = $healthy; request_results = $results
        }
        $entry | ConvertTo-Json -Depth 8 -Compress | Add-Content -LiteralPath $stressPath -Encoding utf8
        Write-Host "Dual simultaneous stress: $($entry.result); peak VRAM=$peak MiB; free at peak=$freeAtPeak MiB."
        return $passed
    }
    finally { $jobs | Stop-Job -ErrorAction SilentlyContinue; $jobs | Remove-Job -Force -ErrorAction SilentlyContinue }
}

$qwenContext = Get-ProjectEnvValue -Name 'QWEN_CTX' -Default '65536'
$miniContext = Get-ProjectEnvValue -Name 'MINICPM_CTX' -Default '65536'
$sparkContext = Get-ProjectEnvValue -Name 'SPARK_CTX' -Default '65536'
$bonsaiContext = Get-ProjectEnvValue -Name 'BONSAI_CTX' -Default '8192'
$qwenFile = 'Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf'
$miniFile = 'MiniCPM5/MiniCPM5-2B-Q8_0.gguf'
$sparkFile = 'Spark/Spark-X2.5-4B-Q8_0.gguf'
$bonsaiFile = 'Ternary-Bonsai-2-27B-PTQ1_0.gguf'

if (-not $DualOnly) {
foreach ($variant in @(
    @{ Name = 'MTP OFF'; Type = 'none'; N = '' },
    @{ Name = 'MTP n-max=2'; Type = 'draft-mtp'; N = '2' },
    @{ Name = 'MTP n-max=4'; Type = 'draft-mtp'; N = '4' },
    @{ Name = 'MTP n-max=6'; Type = 'draft-mtp'; N = '6' }
)) {
    Invoke-BenchmarkCase -Model 'Qwen3.5-9B' -GGUF $qwenFile -Quant 'UD-Q4_K_XL' -Context $qwenContext -Variant $variant.Name -StartScript $startQwen -Environment @{ QWEN_SPEC_TYPE = $variant.Type; QWEN_SPEC_N_MAX = $variant.N } -ThinkingMode 'off'
}

foreach ($variant in @(
    @{ Name = 'DSpark OFF'; Type = 'none'; N = '' },
    @{ Name = 'DSpark n-max=4'; Type = 'draft-dspark'; N = '4' },
    @{ Name = 'DSpark n-max=7'; Type = 'draft-dspark'; N = '7' }
)) {
    Invoke-BenchmarkCase -Model 'MiniCPM5-2B' -GGUF $miniFile -Quant 'Q8_0' -Context $miniContext -Variant $variant.Name -StartScript $startMini -Environment @{ MINICPM_SPEC_TYPE = $variant.Type; MINICPM_SPEC_N_MAX = $variant.N }
}

foreach ($kv in @('f16', 'q8_0')) {
    foreach ($thinking in @('off', 'on')) {
        Invoke-BenchmarkCase -Model 'Spark-X2.5-4B' -GGUF $sparkFile -Quant 'Q8_0' -Context $sparkContext -Variant "thinking $thinking; KV $kv" -StartScript $startSpark -Environment @{ SPARK_KV = $kv } -ThinkingMode $thinking
    }
}
Invoke-BenchmarkCase -Model 'Ternary-Bonsai-2-27B' -GGUF $bonsaiFile -Quant 'PTQ1_0' -Context $bonsaiContext -Variant 'Prism baseline' -StartScript $startBonsai
}

if (-not $SkipDual) {
    Invoke-BenchmarkCase -Model 'MiniCPM5 single dual-context' -GGUF $miniFile -Quant 'Q8_0' -Context '8192' -Variant 'single baseline for dual' -StartScript $startMini -Environment @{ MINICPM_CTX = '8192'; MINICPM_SPEC_TYPE = 'none'; MINICPM_SPEC_N_MAX = '' }
    Invoke-BenchmarkCase -Model 'Spark single dual-context' -GGUF $sparkFile -Quant 'Q8_0' -Context '16384' -Variant 'single q8 KV baseline for dual' -StartScript $startSpark -Environment @{ SPARK_CTX = '16384'; SPARK_KV = 'q8_0' }
    $dualReady = $false
    $dualLoadSeconds = 0.0
    try {
        $dualStartResults = @(& $startDual | Where-Object { $null -ne $_.PSObject.Properties['StartupSeconds'] })
        if ($dualStartResults.Count -gt 0) { $dualLoadSeconds = [double]$dualStartResults[-1].StartupSeconds }
        $dualReady = $true
    }
    catch {
        Add-BenchmarkFailure -Model 'MiniCPM5-2B + Spark-X2.5-4B' -GGUF "$miniFile + $sparkFile" -Quant 'Q8_0 + Q8_0' -Context '8192 + 16384' -Variant 'dual-resident startup' -ErrorText $_.Exception.Message
        Write-Warning 'Dual mode is disabled for this run; single-mode benchmarks are complete.'
    }
    if ($dualReady) {
        try {
            & $benchmark -BaseUrl 'http://127.0.0.1:8083' -Prompt $Prompt -MaxTokens $MaxTokens -Repeats $Repeats -ModelLabel 'MiniCPM5 dual' -GGUF $miniFile -Quant 'Q8_0' -Context '8192' -Variant 'MiniCPM+Spark resident' -LoadTimeSeconds $dualLoadSeconds -SessionId $sessionId
            & $benchmark -BaseUrl 'http://127.0.0.1:8084' -Prompt $Prompt -MaxTokens $MaxTokens -Repeats $Repeats -ModelLabel 'Spark dual' -GGUF $sparkFile -Quant 'Q8_0' -Context '16384 q8_0 KV' -Variant 'MiniCPM+Spark resident' -LoadTimeSeconds $dualLoadSeconds -SessionId $sessionId
            $miniSingleTg = Get-AverageTg -Model 'MiniCPM5 single dual-context'
            $sparkSingleTg = Get-AverageTg -Model 'Spark single dual-context'
            $miniDualTg = Get-AverageTg -Model 'MiniCPM5 dual'
            $sparkDualTg = Get-AverageTg -Model 'Spark dual'
            $dualPeak = Get-MaxPeakVram -Models @('MiniCPM5 dual', 'Spark dual')
            $freeAtPeak = if ($null -ne $dualPeak) { (Get-GpuMemoryTotalMiB) - $dualPeak } else { $null }
            $miniPass = ($null -ne $miniSingleTg) -and ($null -ne $miniDualTg) -and ($miniDualTg -ge ($miniSingleTg * 0.90))
            $sparkPass = ($null -ne $sparkSingleTg) -and ($null -ne $sparkDualTg) -and ($sparkDualTg -ge ($sparkSingleTg * 0.90))
            $noErrors = @(Import-Csv -LiteralPath $resultsPath | Where-Object { $_.BenchmarkSession -eq $sessionId -and $_.Model -in @('MiniCPM5 dual', 'Spark dual') -and -not [string]::IsNullOrWhiteSpace($_.Errors) }).Count -eq 0
            $safeVram = ($null -ne $freeAtPeak) -and ($freeAtPeak -ge 1024)
            $dualPass = $miniPass -and $sparkPass -and $noErrors -and $safeVram
            Write-Host "Dual policy: MiniCPM TG $miniSingleTg single -> $miniDualTg dual; Spark TG $sparkSingleTg single -> $sparkDualTg dual; free at peak $freeAtPeak MiB."
            if ($dualPass) {
                if (-not (Invoke-DualStress)) { Write-Warning 'Dual mode failed simultaneous stress checks and must be marked DISABLED.' }
            }
            else { Write-Warning 'Dual mode failed speed, error, or VRAM criteria and must be marked DISABLED; simultaneous stress was skipped.' }
        }
        catch {
            Add-BenchmarkFailure -Model 'MiniCPM5-2B + Spark-X2.5-4B' -GGUF "$miniFile + $sparkFile" -Quant 'Q8_0 + Q8_0' -Context '8192 + 16384' -Variant 'dual-resident benchmark' -ErrorText $_.Exception.Message
        }
    }
}

try { Stop-AiServices -WaitForGpuRelease } catch { Write-Warning "Could not stop local AI services cleanly: $($_.Exception.Message)" }
Write-Host "Benchmark session $sessionId complete. Results: $resultsPath; answers: $answersPath; dual stress: $stressPath."
