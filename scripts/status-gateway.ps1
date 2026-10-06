$ErrorActionPreference = 'Stop'
$ContainerName = 'ai-llama-swap-gateway'
$state = docker inspect --format '{{.State.Status}}' $ContainerName 2>$null
if (-not $state) { Write-Output 'GATEWAY=NOT_CREATED'; exit 0 }
Write-Output "GATEWAY=$state"
docker inspect --format 'HEALTH={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} RESTART={{.HostConfig.RestartPolicy.Name}}' $ContainerName
if ($state -eq 'running') {
    try {
        $models = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/v1/models' -TimeoutSec 8
        Write-Output "API=http://localhost:8080/v1 MODEL_COUNT=$($models.data.Count)"
    } catch { Write-Output "API_ERROR=$($_.Exception.Message)" }
    $processRows = @(docker exec $ContainerName ps -eo pid,args 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect gateway model processes.' }
    $rows = @($processRows | Where-Object { $_ -match 'llama-server' })
    if ($rows.Count -eq 0) { Write-Output 'ACTIVE_MODEL=NONE' }
    else { Write-Output "ACTIVE_LLAMA_SERVER_COUNT=$($rows.Count)"; $rows }
}
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader
