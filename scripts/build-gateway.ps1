$ErrorActionPreference = 'Stop'
$ProjectDir = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectDir
try {
    docker version --format 'Docker Engine {{.Server.Version}}' | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Docker daemon is unavailable.' }
    docker compose --profile gateway config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Gateway Compose validation failed.' }
    docker compose --profile gateway build llama-swap-gateway
    if ($LASTEXITCODE -ne 0) { throw 'Gateway image build failed.' }
    docker image inspect local/ai-server-llama-swap:260 --format 'IMAGE={{.Id}} SIZE={{.Size}}'
} finally { Pop-Location }
