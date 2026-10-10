[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('minicpm','spark')][string]$ModelKey,
    [ValidateRange(1, 131072)][int]$Context = 8192,
    [ValidateSet('technical_smoke','german_practical','goethe_c1_15min','goethe_c2_15min','scientific_c2','math_10min','goethe_c1_official')][string[]]$Suite = @()
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'common.ps1')

$service = $ModelKey
$startScript = Join-Path $PSScriptRoot "start-$ModelKey.ps1"
$runner = Join-Path $PSScriptRoot 'run-protocol.py'
$savedContext = [Environment]::GetEnvironmentVariable("$($ModelKey.ToUpperInvariant())_CTX", 'Process')
$savedThreads = [Environment]::GetEnvironmentVariable('LLAMA_THREADS', 'Process')
$savedBatchThreads = [Environment]::GetEnvironmentVariable('LLAMA_THREADS_BATCH', 'Process')
[Environment]::SetEnvironmentVariable("$($ModelKey.ToUpperInvariant())_CTX", [string]$Context, 'Process')
[Environment]::SetEnvironmentVariable('LLAMA_THREADS', '4', 'Process')
[Environment]::SetEnvironmentVariable('LLAMA_THREADS_BATCH', '8', 'Process')

try {
    Write-Host "GPU protocol: model=$ModelKey context=$Context; canonical prompts are sent sequentially, with no seed and no CPU fallback."
    $startOutput = @(& $startScript)
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "Model start script failed with exit code $LASTEXITCODE." }
    $startInfo = $startOutput | Where-Object { $null -ne $_ -and $_.PSObject.Properties['StartupSeconds'] } | Select-Object -Last 1

    $composeArgs = @('compose','--project-name',$script:AiProject,'-f',$script:ComposeFile,'--profile',$ModelKey,'ps','-q',$service)
    Push-Location $script:AiRoot
    try { $containerId = (& docker @composeArgs | Select-Object -First 1).Trim() }
    finally { Pop-Location }
    if (-not $containerId) { throw "Could not identify this project's running $service container for telemetry." }

    $runnerArgs = @($runner, '--model-key', $ModelKey, '--base-url', 'http://127.0.0.1:8080', '--container-id', $containerId, '--context', "$Context")
    if ($startInfo) { $runnerArgs += @('--load-seconds', "$($startInfo.StartupSeconds)") }
    foreach ($suiteName in $Suite) { $runnerArgs += @('--suite', $suiteName) }
    & python @runnerArgs
    if ($LASTEXITCODE -ne 0) { throw "Protocol runner failed with exit code $LASTEXITCODE; raw partial results are preserved." }
}
finally {
    try {
        $active = @(Get-AiRunningServices)
        if ($active -contains $service) {
            Invoke-AiCompose -Profiles @($ModelKey) -Arguments @('stop','--timeout','120',$service)
            Wait-GpuMemoryReleased -BaselineMiB (Get-AiGpuIdleBaselineMiB)
        }
        Show-GpuStatus
    }
    finally {
        [Environment]::SetEnvironmentVariable("$($ModelKey.ToUpperInvariant())_CTX", $savedContext, 'Process')
        [Environment]::SetEnvironmentVariable('LLAMA_THREADS', $savedThreads, 'Process')
        [Environment]::SetEnvironmentVariable('LLAMA_THREADS_BATCH', $savedBatchThreads, 'Process')
    }
}
