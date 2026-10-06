$ErrorActionPreference = 'Stop'
$ProjectDir = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectDir
try {
    docker compose --profile gateway stop --timeout 100 llama-swap-gateway
    if ($LASTEXITCODE -ne 0) { throw 'Graceful gateway stop failed.' }
    Write-Output 'Gateway stopped gracefully; container and logs were retained.'
    nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader
} finally { Pop-Location }
