$ErrorActionPreference = 'Stop'
$ProjectDir = Split-Path -Parent $PSScriptRoot
$OutputDir = Join-Path $ProjectDir 'benchmark\gateway-acceptance'
$ContainerName = 'ai-llama-swap-gateway'
$ApiBase = 'http://127.0.0.1:8080/v1'
$Model = 'Ternary-Bonsai-2-27B-PTQ1_0'
$ExpectedPath = '/models/Ternary-Bonsai-2-27B-PTQ1_0.gguf'
$RunId = Get-Date -Format 'yyyyMMdd-HHmmss'
$ResultPath = Join-Path $OutputDir "bonsai-prism-runtime-$RunId.json"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

function Get-GpuSample {
    nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader,nounits 2>$null | Select-Object -First 1
}
function Get-LlamaProcesses {
    $lines = @(docker exec $ContainerName ps -eo pid,args 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect gateway child processes with ps -eo pid,args.' }
    return @($lines | Where-Object { $_ -match 'llama-server' })
}

$before = Get-GpuSample
$clock = [System.Diagnostics.Stopwatch]::StartNew()
try {
    $body = @{
        model = $Model
        messages = @(@{ role = 'user'; content = 'Reply with the exact text BONSAI_TEST_OK and nothing else.' })
        max_tokens = 24
        temperature = 0
        stream = $false
    } | ConvertTo-Json -Depth 8 -Compress
    $response = Invoke-RestMethod -Uri "$ApiBase/chat/completions" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 1800
    $clock.Stop()
    $message = $response.choices[0].message
    $text = [string]$message.content
    if (-not $text -and $message.PSObject.Properties.Name -contains 'reasoning_content') { $text = [string]$message.reasoning_content }
    $proc = Get-LlamaProcesses
    $pathLoaded = (($proc -join ' ') -like "*$ExpectedPath*")
    $ok = ($proc.Count -eq 1 -and $pathLoaded -and -not [string]::IsNullOrWhiteSpace($text))
    $row = [pscustomobject]@{
        model = $Model; runtime = 'PrismML'; status = if ($ok) { 'PASS' } else { 'FAIL' }
        seconds = [math]::Round($clock.Elapsed.TotalSeconds, 2)
        prompt_tokens = $response.usage.prompt_tokens; output_tokens = $response.usage.completion_tokens
        response = $text; gpu_before = $before; gpu_after = Get-GpuSample
        llama_server_process_count = $proc.Count; active_command = ($proc -join ' ')
        expected_model_path_loaded = $pathLoaded
        error = if ($ok) { $null } else { 'Unexpected model path/process count or empty response' }
    }
} catch {
    $clock.Stop()
    $row = [pscustomobject]@{
        model = $Model; runtime = 'PrismML'; status = 'FAIL'
        seconds = [math]::Round($clock.Elapsed.TotalSeconds, 2)
        error = $_.Exception.Message; gpu_before = $before; gpu_after = Get-GpuSample
        llama_server_process_count = (Get-LlamaProcesses).Count
    }
}
$row | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ResultPath -Encoding utf8
Write-Output "BONSAI_STATUS=$($row.status) TIME=$($row.seconds)s PROCESSES=$($row.llama_server_process_count)"
Write-Output "RESULT=$ResultPath"
if ($row.status -ne 'PASS') { throw 'Bonsai PrismML runtime smoke test failed; see result JSON and gateway logs.' }
