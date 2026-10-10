Set-StrictMode -Version Latest

$script:AiRoot = Split-Path -Parent $PSScriptRoot
$script:ComposeFile = Join-Path $script:AiRoot 'docker-compose.yml'
$script:AiProject = 'local-ai-server'
$script:AiProfiles = @(
    'qwen', 'qwen-q5', 'qwen-vision', 'minicpm', 'spark', 'bonsai',
    'whisper', 'dual-minicpm', 'dual-spark', 'media-tools', 'qwen-image'
)
$script:AiGpuServices = @($script:AiProfiles) + @('llama-swap-gateway')

function Assert-DockerCli {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker CLI is not available on PATH.'
    }
}

function Assert-GatewayNotRunning {
    Assert-DockerCli
    $gatewayState = & docker inspect --format '{{.State.Status}}' 'ai-llama-swap-gateway' 2>$null
    if ($LASTEXITCODE -eq 0 -and $gatewayState -eq 'running') {
        throw 'The unified llama-swap gateway owns the inference slot. Use Open WebUI/API to switch models; do not start a second model service.'
    }
}

function Invoke-AiCompose {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string[]]$Arguments,
        [string[]]$Profiles = @()
    )

    Assert-DockerCli
    $dockerArgs = @('compose', '--project-name', $script:AiProject, '-f', $script:ComposeFile)
    foreach ($profile in $Profiles) {
        $dockerArgs += @('--profile', $profile)
    }

    Push-Location $script:AiRoot
    try {
        & docker @dockerArgs @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

function Get-AiRunningServices {
    $output = @(Invoke-AiCompose -Profiles $script:AiProfiles -Arguments @('ps', '--services', '--status', 'running'))
    return @($output | ForEach-Object { "$_".Trim() } | Where-Object { $_ -and $_ -in $script:AiGpuServices })
}

function Get-GpuMemoryUsedMiB {
    if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
        throw 'nvidia-smi is not available; refusing to assume VRAM was released.'
    }
    $raw = & nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits
    if ($LASTEXITCODE -ne 0) {
        throw 'nvidia-smi could not read GPU memory usage.'
    }
    return [int](("$raw" -split '\s+')[0])
}

function Get-GpuMemoryTotalMiB {
    if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
        throw 'nvidia-smi is not available; refusing to assume VRAM headroom.'
    }
    $raw = & nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits
    if ($LASTEXITCODE -ne 0) { throw 'nvidia-smi could not read total GPU memory.' }
    return [int](("$raw" -split '\s+')[0])
}

function Get-AiGpuIdleBaselineMiB {
    $configured = [Environment]::GetEnvironmentVariable('GPU_IDLE_BASELINE_MIB')
    if ([string]::IsNullOrWhiteSpace($configured)) {
        $line = Get-Content -LiteralPath (Join-Path $script:AiRoot '.env') -ErrorAction SilentlyContinue |
            Where-Object { $_ -match '^GPU_IDLE_BASELINE_MIB=' } | Select-Object -First 1
        if ($line) { $configured = ($line -split '=', 2)[1].Trim() }
    }
    if ([string]::IsNullOrWhiteSpace($configured)) { return 1024 }
    $baseline = 0
    if (-not [int]::TryParse($configured, [ref]$baseline) -or $baseline -lt 0) {
        throw "GPU_IDLE_BASELINE_MIB must be a non-negative integer; found '$configured'."
    }
    return $baseline
}

function Get-AiGpuReleaseToleranceMiB {
    $configured = [Environment]::GetEnvironmentVariable('GPU_RELEASE_TOLERANCE_MIB')
    if ([string]::IsNullOrWhiteSpace($configured)) {
        $line = Get-Content -LiteralPath (Join-Path $script:AiRoot '.env') -ErrorAction SilentlyContinue |
            Where-Object { $_ -match '^GPU_RELEASE_TOLERANCE_MIB=' } | Select-Object -First 1
        if ($line) { $configured = ($line -split '=', 2)[1].Trim() }
    }
    if ([string]::IsNullOrWhiteSpace($configured)) { return 768 }
    $tolerance = 0
    if (-not [int]::TryParse($configured, [ref]$tolerance) -or $tolerance -lt 0) {
        throw "GPU_RELEASE_TOLERANCE_MIB must be a non-negative integer; found '$configured'."
    }
    return $tolerance
}

function Show-GpuStatus {
    Write-Host ''
    Write-Host 'GPU memory and utilization:'
    & nvidia-smi
    if ($LASTEXITCODE -ne 0) {
        throw 'nvidia-smi failed.'
    }
}

function Wait-GpuMemoryReleased {
    param(
        [Parameter(Mandatory)][int]$BaselineMiB,
        [int]$ToleranceMiB = (Get-AiGpuReleaseToleranceMiB),
        [int]$TimeoutSeconds = 120
    )

    $limit = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $used = Get-GpuMemoryUsedMiB
        if ($used -le ($BaselineMiB + $ToleranceMiB)) {
            Write-Host "GPU memory settled at $used MiB (baseline $BaselineMiB MiB)."
            return
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $limit)

    throw "GPU memory did not return near baseline: $used MiB used, baseline $BaselineMiB MiB."
}

function Stop-AiServices {
    [CmdletBinding()]
    param(
        [string[]]$ServiceNames = @(),
        [switch]$WaitForGpuRelease
    )

    $baseline = Get-AiGpuIdleBaselineMiB
    if ($ServiceNames.Count -eq 0) {
        $ServiceNames = @(Get-AiRunningServices)
    }
    $ServiceNames = @($ServiceNames | Where-Object { $_ -in $script:AiGpuServices })
    if ($ServiceNames.Count -eq 0) {
        Write-Host 'No local-ai-server services are running.'
    }
    else {
        Write-Host "Stopping managed services: $($ServiceNames -join ', ')"
        $composeArgs = @('stop', '--timeout', '120') + $ServiceNames
        Invoke-AiCompose -Profiles $script:AiProfiles -Arguments $composeArgs
    }

    if ($WaitForGpuRelease) {
        Wait-GpuMemoryReleased -BaselineMiB $baseline
    }
    Show-GpuStatus
}

function Wait-ForHttpEndpoint {
    param(
        [Parameter(Mandatory)][string]$Uri,
        [int]$TimeoutSeconds = 900
    )

    $limit = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Uri -TimeoutSec 5 -SkipHttpErrorCheck
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                return
            }
        }
        catch {
            # The service may still be loading its model.
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $limit)

    throw "Timed out waiting for endpoint $Uri."
}

function Confirm-OpenAiApi {
    param([Parameter(Mandatory)][string]$BaseUrl)

    $models = Invoke-RestMethod -Uri "$BaseUrl/v1/models" -TimeoutSec 20
    if (-not $models.data -or $models.data.Count -lt 1) {
        throw "The model list at $BaseUrl/v1/models is empty."
    }
    Write-Host "OpenAI API: $BaseUrl/v1 (model $($models.data[0].id))"
    return $models.data[0].id
}

function Start-AiModel {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Service,
        [Parameter(Mandatory)][string]$Profile,
        [Parameter(Mandatory)][string]$BaseUrl,
        [int]$TimeoutSeconds = 900
    )

    Assert-GatewayNotRunning
    $timeoutOverride = [Environment]::GetEnvironmentVariable('LLAMA_START_TIMEOUT_SECONDS', 'Process')
    if (-not [string]::IsNullOrWhiteSpace($timeoutOverride)) {
        $parsedTimeout = 0
        if ([int]::TryParse($timeoutOverride, [ref]$parsedTimeout) -and $parsedTimeout -ge 10 -and $parsedTimeout -le 1800) {
            $TimeoutSeconds = $parsedTimeout
        }
        else { throw "LLAMA_START_TIMEOUT_SECONDS must be an integer from 10 to 1800; found '$timeoutOverride'." }
    }

    $active = @(Get-AiRunningServices)
    if ($active.Count -gt 0) {
        Write-Host "Active local-ai-server services: $($active -join ', ')"
    }
    else {
        Write-Host 'No local-ai-server model service is active.'
    }
    Stop-AiServices -ServiceNames $active -WaitForGpuRelease

    $loadStarted = [Diagnostics.Stopwatch]::StartNew()
    Invoke-AiCompose -Profiles @($Profile) -Arguments @('up', '-d', '--no-build', $Service)
    Wait-ForHttpEndpoint -Uri "$BaseUrl/health" -TimeoutSeconds $TimeoutSeconds
    $null = Confirm-OpenAiApi -BaseUrl $BaseUrl
    $loadStarted.Stop()
    Write-Host ("Model ready; startup and health check: {0:N1} s" -f $loadStarted.Elapsed.TotalSeconds)
    Show-GpuStatus
    [pscustomobject]@{
        Service = $Service
        ApiUrl = "$BaseUrl/v1"
        StartupSeconds = [Math]::Round($loadStarted.Elapsed.TotalSeconds, 3)
        Context = $null
    }
}

function Start-AiDual {
    throw 'Dual-resident launch is disabled by the current single-model policy. Start the llama-swap gateway and choose one model through Open WebUI.'
}

function Start-AiWhisper {
    Assert-GatewayNotRunning
    $active = @(Get-AiRunningServices)
    if ($active.Count -gt 0) {
        Write-Host "Active local-ai-server services: $($active -join ', ')"
    }
    Stop-AiServices -ServiceNames $active -WaitForGpuRelease
    $loadStarted = [Diagnostics.Stopwatch]::StartNew()
    Invoke-AiCompose -Profiles @('whisper') -Arguments @('up', '-d', '--no-build', 'whisper')
    Wait-ForHttpEndpoint -Uri 'http://127.0.0.1:8082/' -TimeoutSeconds 900
    $loadStarted.Stop()
    Write-Host 'Whisper is ready; multipart STT endpoint: http://127.0.0.1:8082/inference'
    Write-Host ("Startup and readiness check: {0:N1} s" -f $loadStarted.Elapsed.TotalSeconds)
    Show-GpuStatus
    [pscustomobject]@{
        Service = 'whisper'
        ApiUrl = 'http://127.0.0.1:8082/inference'
        StartupSeconds = [Math]::Round($loadStarted.Elapsed.TotalSeconds, 3)
    }
}

function Get-AiServiceApiUrl {
    param([Parameter(Mandatory)][string]$Service)
    switch ($Service) {
        'dual-minicpm' { return 'http://127.0.0.1:8083' }
        'dual-spark' { return 'http://127.0.0.1:8084' }
        'whisper' { return 'http://127.0.0.1:8082' }
        default { return 'http://127.0.0.1:8080' }
    }
}
