[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:8080',
    [string]$Prompt = 'Solve this consistently: explain one practical way to reduce GPU memory use for local inference, including a trade-off.',
    [ValidateRange(16, 4096)][int]$MaxTokens = 256,
    [ValidateRange(1, 20)][int]$Repeats = 3,
    [int]$Seed = -1,
    [string]$ReasoningEffort,
    [ValidateSet('off', 'on')][string]$ThinkingMode,
    [string]$ModelLabel = 'from-api',
    [string]$GGUF = 'from-profile',
    [string]$Quant = 'from-profile',
    [string]$Context = 'from-profile',
    [double]$LoadTimeSeconds = 0,
    [string]$Variant = 'configured-profile',
    [string]$SessionId = ''
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')

function Get-AiMetricSnapshot {
    param([Parameter(Mandatory)][string]$Uri)
    $response = Invoke-WebRequest -Uri "$Uri/metrics" -TimeoutSec 20
    $metricsText = [string]$response.Content
    $names = @(
        'prompt_tokens_total', 'prompt_tokens_cached_total', 'prompt_seconds_total',
        'tokens_predicted_total', 'tokens_predicted_seconds_total',
        'spec_decode_num_draft_tokens_total', 'spec_decode_num_accepted_tokens_total',
        'spec_decode_num_drafts_total'
    )
    $snapshot = @{}
    foreach ($name in $names) {
        $fullName = "llamacpp:$name"
        $pattern = '(?m)^' + [regex]::Escape($fullName) + '(?:\{[^}]*\})?\s+([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*$'
        $match = [regex]::Match($metricsText, $pattern)
        if ($match.Success) {
            $snapshot[$name] = [double]::Parse($match.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture)
        }
        else {
            $snapshot[$name] = 0.0
        }
    }
    return $snapshot
}

function Get-AiStreamCompletion {
    param(
        [Parameter(Mandatory)][string]$Uri,
        [Parameter(Mandatory)][string]$ModelId,
        [Parameter(Mandatory)][string]$Text,
        [Parameter(Mandatory)][int]$TokenLimit,
        [int]$RequestSeed = -1,
        [string]$Effort,
        [ValidateSet('off', 'on')][string]$Thinking
    )

    $payload = @{
        model = $ModelId
        messages = @(@{ role = 'user'; content = $Text })
        max_tokens = $TokenLimit
        temperature = 1.0
        stream = $true
        stream_options = @{ include_usage = $true }
        timings_per_token = $true
        cache_prompt = $false
    }
    if ($RequestSeed -ge 0) { $payload.seed = $RequestSeed }
    if (-not [string]::IsNullOrWhiteSpace($Effort)) { $payload.reasoning_effort = $Effort }
    if (-not [string]::IsNullOrWhiteSpace($Thinking)) {
        $payload.chat_template_kwargs = @{ enable_thinking = ($Thinking -eq 'on') }
    }
    $json = $payload | ConvertTo-Json -Depth 8 -Compress
    $http = [Net.Http.HttpClient]::new()
    $http.Timeout = [TimeSpan]::FromSeconds(1800)
    $request = [Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::Post, "$Uri/v1/chat/completions")
    $request.Content = [Net.Http.StringContent]::new($json, [Text.Encoding]::UTF8, 'application/json')
    $clock = [Diagnostics.Stopwatch]::StartNew()
    try {
        $response = $http.SendAsync($request, [Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            $errorBody = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            throw "Chat API returned HTTP $([int]$response.StatusCode): $errorBody"
        }
        $stream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
        $reader = [IO.StreamReader]::new($stream)
        $answer = [Text.StringBuilder]::new()
        $firstTokenSeconds = $null
        $usagePrompt = 0
        $usageCompletion = 0
        $requestTimings = $null
        while ($null -ne ($line = $reader.ReadLine())) {
            if (-not $line.StartsWith('data: ')) { continue }
            $data = $line.Substring(6).Trim()
            if ($data -eq '[DONE]') { break }
            try { $chunk = $data | ConvertFrom-Json -Depth 16 } catch { continue }
            $usageProperty = $chunk.PSObject.Properties['usage']
            if ($null -ne $usageProperty -and $null -ne $usageProperty.Value) {
                $usage = $usageProperty.Value
                $promptProperty = $usage.PSObject.Properties['prompt_tokens']
                $completionProperty = $usage.PSObject.Properties['completion_tokens']
                if ($null -ne $promptProperty -and $null -ne $promptProperty.Value) { $usagePrompt = [int]$promptProperty.Value }
                if ($null -ne $completionProperty -and $null -ne $completionProperty.Value) { $usageCompletion = [int]$completionProperty.Value }
            }
            $choicesProperty = $chunk.PSObject.Properties['choices']
            $timingsProperty = $chunk.PSObject.Properties['timings']
            if ($null -ne $timingsProperty -and $null -ne $timingsProperty.Value) { $requestTimings = $timingsProperty.Value }
            if ($null -eq $choicesProperty) { continue }
            foreach ($choice in @($choicesProperty.Value | Where-Object { $null -ne $_ })) {
                $deltaProperty = $choice.PSObject.Properties['delta']
                if ($null -eq $deltaProperty -or $null -eq $deltaProperty.Value) { continue }
                $delta = $deltaProperty.Value
                $contentProperty = $delta.PSObject.Properties['content']
                $piece = if ($null -ne $contentProperty -and $null -ne $contentProperty.Value) { [string]$contentProperty.Value } else { '' }
                if (-not [string]::IsNullOrEmpty($piece)) {
                    if ($null -eq $firstTokenSeconds) { $firstTokenSeconds = $clock.Elapsed.TotalSeconds }
                    [void]$answer.Append($piece)
                }
            }
        }
        $clock.Stop()
        return [pscustomobject]@{
            TTFTSeconds = $firstTokenSeconds
            TotalSeconds = $clock.Elapsed.TotalSeconds
            Text = $answer.ToString()
            UsagePromptTokens = $usagePrompt
            UsageCompletionTokens = $usageCompletion
            Timings = $requestTimings
        }
    }
    finally {
        $request.Dispose()
        $http.Dispose()
    }
}

function Get-AiGpuSample {
    $raw = & nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw --format=csv,noheader,nounits
    if ($LASTEXITCODE -ne 0 -or -not $raw) { return $null }
    $parts = ("$raw" -split ',') | ForEach-Object { $_.Trim() }
    if ($parts.Count -lt 3) { return $null }
    return [pscustomobject]@{
        Utilization = [double]::Parse($parts[0], [Globalization.CultureInfo]::InvariantCulture)
        MemoryMiB = [double]::Parse($parts[1], [Globalization.CultureInfo]::InvariantCulture)
        PowerW = [double]::Parse($parts[2], [Globalization.CultureInfo]::InvariantCulture)
    }
}

$modelId = Confirm-OpenAiApi -BaseUrl $BaseUrl
$resultsPath = Join-Path $script:AiRoot 'BENCHMARK_RUNTIME_RESULTS.csv'
$answersPath = Join-Path $script:AiRoot 'BENCHMARK_ANSWERS.jsonl'
for ($run = 1; $run -le $Repeats; $run++) {
    $errors = ''
    $gpuIdle = Get-GpuMemoryUsedMiB
    $metricsBefore = Get-AiMetricSnapshot -Uri $BaseUrl
    $samples = [Collections.Generic.List[object]]::new()
    $sampler = Start-Job -ScriptBlock {
        while ($true) {
            $line = & nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw --format=csv,noheader,nounits 2>$null
            if ($LASTEXITCODE -eq 0 -and $line) {
                $parts = ("$line" -split ',') | ForEach-Object { $_.Trim() }
                if ($parts.Count -ge 3) {
                    [pscustomobject]@{ Utilization = $parts[0]; MemoryMiB = $parts[1]; PowerW = $parts[2] }
                }
            }
            Start-Sleep -Milliseconds 300
        }
    }
    $completion = $null
    try {
        $requestSeed = if ($Seed -ge 0) { $Seed + $run - 1 } else { -1 }
        $completionArgs = @{ Uri = $BaseUrl; ModelId = $modelId; Text = $Prompt; TokenLimit = $MaxTokens; RequestSeed = $requestSeed }
        if (-not [string]::IsNullOrWhiteSpace($ReasoningEffort)) { $completionArgs.Effort = $ReasoningEffort }
        if (-not [string]::IsNullOrWhiteSpace($ThinkingMode)) { $completionArgs.Thinking = $ThinkingMode }
        $completion = Get-AiStreamCompletion @completionArgs
    }
    catch {
        $errors = $_.Exception.Message
    }
    finally {
        Stop-Job -Job $sampler -ErrorAction SilentlyContinue
        foreach ($sample in @(Receive-Job -Job $sampler -ErrorAction SilentlyContinue)) {
            try {
                $samples.Add([pscustomobject]@{
                    Utilization = [double]::Parse([string]$sample.Utilization, [Globalization.CultureInfo]::InvariantCulture)
                    MemoryMiB = [double]::Parse([string]$sample.MemoryMiB, [Globalization.CultureInfo]::InvariantCulture)
                    PowerW = [double]::Parse([string]$sample.PowerW, [Globalization.CultureInfo]::InvariantCulture)
                })
            } catch { }
        }
        Remove-Job -Job $sampler -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 250
    $metricsAfter = Get-AiMetricSnapshot -Uri $BaseUrl
    $deltaPromptTokens = [Math]::Max(0, ($metricsAfter['prompt_tokens_total'] - $metricsBefore['prompt_tokens_total']) + ($metricsAfter['prompt_tokens_cached_total'] - $metricsBefore['prompt_tokens_cached_total']))
    $deltaPromptSeconds = [Math]::Max(0, $metricsAfter['prompt_seconds_total'] - $metricsBefore['prompt_seconds_total'])
    $deltaGenTokens = [Math]::Max(0, $metricsAfter['tokens_predicted_total'] - $metricsBefore['tokens_predicted_total'])
    $deltaGenSeconds = [Math]::Max(0, $metricsAfter['tokens_predicted_seconds_total'] - $metricsBefore['tokens_predicted_seconds_total'])
    $deltaDrafted = [Math]::Max(0, $metricsAfter['spec_decode_num_draft_tokens_total'] - $metricsBefore['spec_decode_num_draft_tokens_total'])
    $deltaAccepted = [Math]::Max(0, $metricsAfter['spec_decode_num_accepted_tokens_total'] - $metricsBefore['spec_decode_num_accepted_tokens_total'])
    $meanUtil = $null
    $meanPower = $null
    $peakVram = $gpuIdle
    if ($samples.Count -gt 0) {
        $meanUtil = [Math]::Round((($samples | Measure-Object -Property Utilization -Average).Average), 2)
        $meanPower = [Math]::Round((($samples | Measure-Object -Property PowerW -Average).Average), 2)
        $peakVram = [Math]::Round((($samples | Measure-Object -Property MemoryMiB -Maximum).Maximum), 0)
    }
    $pp = if ($deltaPromptSeconds -gt 0) { [Math]::Round($deltaPromptTokens / $deltaPromptSeconds, 3) } else { $null }
    $tg = if ($deltaGenSeconds -gt 0) { [Math]::Round($deltaGenTokens / $deltaGenSeconds, 3) } else { $null }
    $acceptance = if ($deltaDrafted -gt 0) { [Math]::Round(100 * $deltaAccepted / $deltaDrafted, 2) } else { $null }
    if ($completion -and $completion.Timings) {
        $timings = $completion.Timings
        $timingPromptCount = $timings.PSObject.Properties['prompt_n']
        $timingCacheCount = $timings.PSObject.Properties['cache_n']
        $timingPromptRate = $timings.PSObject.Properties['prompt_per_second']
        $timingGeneratedCount = $timings.PSObject.Properties['predicted_n']
        $timingGeneratedRate = $timings.PSObject.Properties['predicted_per_second']
        $timingDraftCount = $timings.PSObject.Properties['draft_n']
        $timingAcceptedCount = $timings.PSObject.Properties['draft_n_accepted']
        if ($null -ne $timingPromptCount) {
            $deltaPromptTokens = [int]$timingPromptCount.Value
            if ($null -ne $timingCacheCount) { $deltaPromptTokens += [int]$timingCacheCount.Value }
        }
        if ($null -ne $timingPromptRate -and [double]$timingPromptRate.Value -gt 0) { $pp = [Math]::Round([double]$timingPromptRate.Value, 3) }
        if ($null -ne $timingGeneratedCount) { $deltaGenTokens = [int]$timingGeneratedCount.Value }
        if ($null -ne $timingGeneratedRate -and [double]$timingGeneratedRate.Value -gt 0) { $tg = [Math]::Round([double]$timingGeneratedRate.Value, 3) }
        if ($null -ne $timingDraftCount) { $deltaDrafted = [int]$timingDraftCount.Value }
        if ($null -ne $timingAcceptedCount) { $deltaAccepted = [int]$timingAcceptedCount.Value }
        $acceptance = if ($deltaDrafted -gt 0) { [Math]::Round(100 * $deltaAccepted / $deltaDrafted, 2) } else { $null }
    }
    Write-Host ("Raw metrics: prompt={0} tokens/{1:N6}s; generated={2} tokens/{3:N6}s; drafted={4}; accepted={5}." -f $deltaPromptTokens, $deltaPromptSeconds, $deltaGenTokens, $deltaGenSeconds, $deltaDrafted, $deltaAccepted)
    $excerpt = if ($completion) { $completion.Text -replace '[\r\n]+', ' ' } else { '' }
    if ($excerpt.Length -gt 500) { $excerpt = $excerpt.Substring(0, 500) }
    $row = [pscustomobject][ordered]@{
        TimestampUtc = [DateTime]::UtcNow.ToString('o')
        BenchmarkSession = $SessionId
        Model = $ModelLabel
        GGUF = $GGUF
        Quant = $Quant
        Context = $Context
        Variant = $Variant
        ReasoningEffort = $ReasoningEffort
        ThinkingMode = $ThinkingMode
        LoadTimeSeconds = $LoadTimeSeconds
        Repeat = $run
        TTFTSeconds = if ($completion) { $completion.TTFTSeconds } else { $null }
        TotalSeconds = if ($completion) { [Math]::Round($completion.TotalSeconds, 3) } else { $null }
        PromptTokens = $deltaPromptTokens
        PP_TokPerSec = $pp
        GeneratedTokens = $deltaGenTokens
        TG_TokPerSec = $tg
        DraftTokens = $deltaDrafted
        AcceptedDraftTokens = $deltaAccepted
        AcceptancePercent = $acceptance
        DraftVerificationSteps = [Math]::Max(0, $metricsAfter['spec_decode_num_drafts_total'] - $metricsBefore['spec_decode_num_drafts_total'])
        VRAMIdleMiB = $gpuIdle
        VRAMPeakMiB = $peakVram
        GPUUtilizationAvgPercent = $meanUtil
        PowerAvgW = $meanPower
        Errors = $errors
        QualitySanityCheck = if ($completion -and -not [string]::IsNullOrWhiteSpace($completion.Text)) { 'User-facing content recorded; manual sanity review required' } else { 'No user-facing content returned; review chat template/output fields' }
        ResponseExcerpt = $excerpt
    }
    if (Test-Path -LiteralPath $resultsPath) { $row | Export-Csv -LiteralPath $resultsPath -NoTypeInformation -Append -Encoding utf8 }
    else { $row | Export-Csv -LiteralPath $resultsPath -NoTypeInformation -Encoding utf8 }
    if ($completion) {
        [pscustomobject]@{
            timestamp_utc = $row.TimestampUtc
            model = $ModelLabel
            gguf = $GGUF
            quant = $Quant
            context = $Context
            variant = $Variant
            reasoning_effort = $ReasoningEffort
            thinking_mode = $ThinkingMode
            repeat = $run
            prompt = $Prompt
            response = $completion.Text
        } | ConvertTo-Json -Depth 8 -Compress | Add-Content -LiteralPath $answersPath -Encoding utf8
    }
    Write-Host ("{0} run {1}/{2}: TTFT={3}s PP={4} tok/s TG={5} tok/s accept={6}% VRAM peak={7} MiB errors={8}" -f $ModelLabel, $run, $Repeats, $row.TTFTSeconds, $pp, $tg, $acceptance, $peakVram, $errors)
}
Write-Host "Metrics written to $resultsPath; response samples written to $answersPath."
