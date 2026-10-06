param([switch]$NoBuild)
$ErrorActionPreference = 'Stop'
$ProjectDir = Split-Path -Parent $PSScriptRoot
$ContainerName = 'ai-llama-swap-gateway'
Push-Location $ProjectDir
try {
    docker version --format 'Docker Engine {{.Server.Version}}' | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Docker daemon is unavailable; start Docker Desktop and rerun.' }
    $other = @(docker ps --format '{{.Names}}' | Where-Object { $_ -match '^local-ai-server-(qwen|qwen-q5|qwen-vision|minicpm|spark|bonsai|dual-minicpm|dual-spark|whisper|qwen-image)-' })
    if ($other.Count -gt 0) { throw "Independent GPU inference containers are active ($($other -join ', ')); stop the project-owned ones before starting the exclusive gateway." }
    docker compose --profile gateway config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Gateway Compose validation failed.' }
    if ($NoBuild) { docker compose --profile gateway up -d llama-swap-gateway }
    else { docker compose --profile gateway up -d --build llama-swap-gateway }
    if ($LASTEXITCODE -ne 0) { throw 'Gateway startup failed.' }

    $deadline = (Get-Date).AddMinutes(20)
    do {
        $state = docker inspect --format '{{.State.Health.Status}}' $ContainerName 2>$null
        if ($state -eq 'healthy') { break }
        if ((Get-Date) -gt $deadline) { docker logs --tail 100 $ContainerName; throw 'Gateway did not become healthy within 20 minutes.' }
        Start-Sleep -Seconds 3
    } while ($true)

    $models = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/v1/models' -TimeoutSec 15
    $processRows = @(docker exec $ContainerName ps -eo pid,args 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to verify gateway child processes; refusing to report a clean startup.' }
    $llama = @($processRows | Where-Object { $_ -match 'llama-server' })
    if ($llama.Count -ne 0) { throw "Gateway started with $($llama.Count) model server process(es); expected ACTIVE MODEL = NONE." }
    Write-Output 'GATEWAY=HEALTHY'
    Write-Output "MODELS=$($models.data.Count)"
    Write-Output 'ACTIVE MODEL=NONE'
    Write-Output 'LOCAL API=http://localhost:8080/v1'
    Write-Output 'LAN API=http://<your-LAN-IP>:8080/v1 (only if you publish the gateway on the LAN)'
    Write-Output 'OPEN WEBUI=http://localhost:3000'
    nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader
} finally { Pop-Location }
