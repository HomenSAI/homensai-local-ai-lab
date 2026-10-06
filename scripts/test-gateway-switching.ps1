param([int]$MaxTokens = 40)
$ErrorActionPreference = 'Stop'
$ProjectDir = Split-Path -Parent $PSScriptRoot
$OutputDir = Join-Path $ProjectDir 'benchmark\gateway-acceptance'
$ApiBase = 'http://127.0.0.1:8080/v1'
$ContainerName = 'ai-llama-swap-gateway'
$RunId = Get-Date -Format 'yyyyMMdd-HHmmss'
$JsonlPath = Join-Path $OutputDir "model-switching-$RunId.jsonl"
$StreamPath = Join-Path $OutputDir "streaming-sse-$RunId.txt"
$SummaryPath = Join-Path $OutputDir "model-switching-summary-$RunId.json"
$Models = @(
    'Qwen3.5-9B-MTP-Q4_K_XL',
    'Spark-X2.5-4B-Q8_0',
    'MiniCPM5-2B-Q8_0',
    'Ternary-Bonsai-2-27B-PTQ1_0',
    'Qwen3.5-9B-MTP-Q4_K_XL-Vision',
    'Qwen3-VL-8B-Instruct-Q4_K_M',
    'Qwen3.5-9B-Q5_K_S'
)
$ExpectedModelFiles = @{
    'Qwen3.5-9B-MTP-Q4_K_XL' = '/models/Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf'
    'Qwen3.5-9B-MTP-Q4_K_XL-Vision' = '/models/Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf'
    'Qwen3.5-9B-Q5_K_S' = '/models/Qwen3/Qwen3.5-9B-Q5_K_S-4.60bpw.gguf'
    'MiniCPM5-2B-Q8_0' = '/models/MiniCPM5/MiniCPM5-2B-Q8_0.gguf'
    'Spark-X2.5-4B-Q8_0' = '/models/Spark/Spark-X2.5-4B-Q8_0.gguf'
    'Ternary-Bonsai-2-27B-PTQ1_0' = '/models/Ternary-Bonsai-2-27B-PTQ1_0.gguf'
    'Qwen3-VL-8B-Instruct-Q4_K_M' = '/models/Qwen-Image-2.1/text_encoder/Qwen3VL-8B-Instruct-Q4_K_M.gguf'
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$rows = [System.Collections.Generic.List[object]]::new()

function Get-GpuSample {
    $line = nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader,nounits 2>$null | Select-Object -First 1
    return $line
}
function Get-LlamaProcesses {
    $lines = @(docker exec $ContainerName ps -eo pid,args 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect gateway child processes with ps -eo pid,args.' }
    return @($lines | Where-Object { $_ -match 'llama-server' })
}

foreach ($model in $Models) {
    $before = Get-GpuSample
    $body = @{
        model = $model
        messages = @(@{ role = 'user'; content = 'Reply with one short sentence: what is 2 + 2?' })
        max_tokens = $MaxTokens
        temperature = 0
        stream = $false
    } | ConvertTo-Json -Depth 8 -Compress
    $clock = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $response = Invoke-RestMethod -Uri "$ApiBase/chat/completions" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 1800
        $clock.Stop()
        $message = $response.choices[0].message
        $text = [string]$message.content
        if (-not $text -and $message.PSObject.Properties.Name -contains 'reasoning_content') { $text = [string]$message.reasoning_content }
        $proc = Get-LlamaProcesses
        $fileLoaded = (($proc -join ' ') -like "*$($ExpectedModelFiles[$model])*")
        $ok = ($proc.Count -eq 1 -and $fileLoaded -and -not [string]::IsNullOrWhiteSpace($text))
        $row = [pscustomobject]@{
            model = $model; status = if ($ok) { 'PASS' } else { 'FAIL' }
            seconds = [math]::Round($clock.Elapsed.TotalSeconds, 2)
            prompt_tokens = $response.usage.prompt_tokens; output_tokens = $response.usage.completion_tokens
            response = $text; gpu_before = $before; gpu_after = Get-GpuSample
            llama_server_process_count = $proc.Count; active_command = ($proc -join ' ')
            error = if ($ok) { $null } else { 'Unexpected active server count or empty model response' }
        }
    } catch {
        $clock.Stop()
        $row = [pscustomobject]@{ model=$model; status='FAIL'; seconds=[math]::Round($clock.Elapsed.TotalSeconds,2); error=$_.Exception.Message; gpu_before=$before; gpu_after=Get-GpuSample; llama_server_process_count=(Get-LlamaProcesses).Count }
    }
    $rows.Add($row)
    $row | ConvertTo-Json -Depth 8 -Compress | Add-Content -LiteralPath $JsonlPath -Encoding utf8
    Write-Output "MODEL=$model STATUS=$($row.status) TIME=$($row.seconds)s LLAMA_PROCESSES=$($row.llama_server_process_count)"
    if ($row.status -ne 'PASS') { Write-Warning "Model acceptance failed for $model; continuing the remaining models." }
}
$rows | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SummaryPath -Encoding utf8

# Exercise SSE through the same public model ID after all switch directions ran.
$streamModel = 'Spark-X2.5-4B-Q8_0'
$streamBody = @{ model=$streamModel; messages=@(@{role='user';content='Count from one to five.'}); max_tokens=48; temperature=0; stream=$true } | ConvertTo-Json -Depth 8 -Compress
try {
    $stream = Invoke-WebRequest -Uri "$ApiBase/chat/completions" -Method Post -ContentType 'application/json' -Body $streamBody -TimeoutSec 1800 -UseBasicParsing
    $streamPassed = ($stream.Content -match 'data: \[DONE\]' -and $stream.Content -match 'data: \{')
    $stream.Content | Set-Content -LiteralPath $StreamPath -Encoding utf8
    if (-not $streamPassed) { $rows.Add([pscustomobject]@{model=$streamModel;status='FAIL';error='SSE response missing data chunks or [DONE]'}) }
    else { Write-Output "STREAMING=PASS MODEL=$streamModel CHUNKS=$(([regex]::Matches($stream.Content,'data: \{')).Count)" }
} catch {
    $rows.Add([pscustomobject]@{model=$streamModel;status='FAIL';error=$_.Exception.Message})
    Write-Warning "Streaming check failed; gateway restart verification will continue."
}

# Unknown public IDs must be rejected without loading an arbitrary runtime.
$unknownBody = @{ model='not-an-installed-model'; messages=@(@{role='user';content='test'}); max_tokens=1 } | ConvertTo-Json -Depth 5 -Compress
try {
    $null = Invoke-RestMethod -Uri "$ApiBase/chat/completions" -Method Post -ContentType 'application/json' -Body $unknownBody -TimeoutSec 30
    $rows.Add([pscustomobject]@{model='not-an-installed-model';status='FAIL';error='Unknown model unexpectedly accepted'})
    Write-Warning 'Unknown model ID unexpectedly returned success.'
} catch {
    Write-Output 'UNKNOWN_MODEL=PASS (rejected)'
}

# Leave the service running, but restart its manager to prove no model is preloaded on restart.
docker restart --timeout 100 $ContainerName | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Gateway restart failed.' }
$deadline=(Get-Date).AddMinutes(20)
do { $health=docker inspect --format '{{.State.Health.Status}}' $ContainerName 2>$null; if($health -eq 'healthy'){break}; if((Get-Date) -gt $deadline){throw 'Gateway did not recover after restart.'}; Start-Sleep -Seconds 3 } while($true)
$afterRestart = @(Get-LlamaProcesses)
if ($afterRestart.Count -ne 0) { throw 'An LLM was loaded automatically after gateway restart.' }
$modelsAfterRestart = Invoke-RestMethod -Uri "$ApiBase/models" -TimeoutSec 15
if ($modelsAfterRestart.data.Count -ne $Models.Count) { throw 'Model catalog did not survive gateway restart.' }
Write-Output "RESTART=PASS MODEL_PRELOAD=NONE CATALOG=$($modelsAfterRestart.data.Count)"
$rows | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SummaryPath -Encoding utf8
$failed = @($rows | Where-Object { $_.status -eq 'FAIL' })
if ($failed.Count -gt 0) { throw "$($failed.Count) gateway acceptance check(s) failed; see $SummaryPath and $JsonlPath." }
Write-Output "ACCEPTANCE=PASS RESULTS=$SummaryPath"
