[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Prompt,
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9 _.-]*\.(png|webp)$')][string]$OutputName = 'qwen-image.png',
    [ValidateRange(512, 2048)][int]$Width = 1024,
    [ValidateRange(512, 2048)][int]$Height = 1024,
    [ValidateRange(1, 100)][int]$Steps = 20,
    [ValidateRange(0, 2147483647)][int]$Seed = 42,
    [string]$ReferenceImage
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
Assert-GatewayNotRunning

$mediaRoot = [IO.Path]::GetFullPath((Join-Path $script:AiRoot 'media'))
$outputDirectory = Join-Path $mediaRoot 'images'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$outputPath = Join-Path $outputDirectory $OutputName
$containerOutput = "/media/images/$OutputName"

$cliArgs = @(
    'run', '--rm', '--no-deps', 'qwen-image',
    '--diffusion-model', '/models/301_Qwen-Image-2.1/qwen-image-2.1-Q5_K_M.gguf',
    '--vae', '/models/301_Qwen-Image-2.1/vae/qwen_image_2.1_vae_bf16.safetensors',
    '--llm', '/models/015_Qwen3-VL-8B/Qwen3VL-8B-Instruct-Q4_K_M.gguf',
    '-p', $Prompt,
    '--steps', "$Steps",
    '--cfg-scale', '6.0',
    '--sampling-method', 'euler',
    '-W', "$Width",
    '-H', "$Height",
    '--seed', "$Seed",
    '--offload-to-cpu',
    '--params-backend', 'diffusion=disk',
    '--max-vram', '-1',
    '--diffusion-fa',
    '--vae-tiling',
    '--vae-tile-size', '256x256',
    '--vae-tile-overlap', '0.5',
    '-o', $containerOutput
)

if (-not [string]::IsNullOrWhiteSpace($ReferenceImage)) {
    $resolvedReference = (Resolve-Path -LiteralPath $ReferenceImage -ErrorAction Stop).Path
    $relativeReference = [IO.Path]::GetRelativePath($mediaRoot, $resolvedReference)
    if ($relativeReference -eq '..' -or $relativeReference.StartsWith("..$([IO.Path]::DirectorySeparatorChar)") -or [IO.Path]::IsPathRooted($relativeReference)) {
        throw 'ReferenceImage must be inside ai-server/media so the container can read it.'
    }
    $containerReference = '/media/' + ($relativeReference -replace '\\', '/')
    $cliArgs += @(
        '--llm_vision', '/models/015_Qwen3-VL-8B/mmproj/mmproj-Qwen3VL-8B-Instruct-F16.gguf',
        '-r', $containerReference
    )
}

$active = @(Get-AiRunningServices)
if ($active.Count -gt 0) {
    Write-Host "Stopping this project's GPU services before Qwen Image: $($active -join ', ')"
}
Stop-AiServices -ServiceNames $active -WaitForGpuRelease

$sampleJob = Start-Job -ArgumentList $script:AiProject -ScriptBlock {
    param($ProjectName)
    while ($true) {
        $gpuLine = & nvidia-smi --query-gpu=memory.used,utilization.gpu,power.draw --format=csv,noheader,nounits 2>$null
        if ($LASTEXITCODE -eq 0 -and $gpuLine) {
            $gpuParts = ("$gpuLine" -split ',') | ForEach-Object { $_.Trim() }
            if ($gpuParts.Count -ge 3) {
                $ramMiB = 0.0
                $containerIds = & docker ps --filter "label=com.docker.compose.project=$ProjectName" --filter 'label=com.docker.compose.service=qwen-image' --format '{{.ID}}' 2>$null
                foreach ($containerId in $containerIds) {
                    $usage = & docker stats --no-stream --format '{{.MemUsage}}' $containerId 2>$null
                    if ($usage -match '^\s*([\d.]+)\s*(B|KB|KiB|MB|MiB|GB|GiB)') {
                        $amount = [double]::Parse($matches[1], [Globalization.CultureInfo]::InvariantCulture)
                        $ramMiB += switch ($matches[2].ToLowerInvariant()) {
                            'b' { $amount / 1MB }
                            { $_ -in @('kb', 'kib') } { $amount / 1024 }
                            'mb' { $amount * 0.953674 }
                            'mib' { $amount }
                            'gb' { $amount * 953.674 }
                            'gib' { $amount * 1024 }
                        }
                    }
                }
                [pscustomobject]@{
                    vram_mib = [double]::Parse($gpuParts[0], [Globalization.CultureInfo]::InvariantCulture)
                    gpu_percent = [double]::Parse($gpuParts[1], [Globalization.CultureInfo]::InvariantCulture)
                    power_w = [double]::Parse($gpuParts[2], [Globalization.CultureInfo]::InvariantCulture)
                    container_ram_mib = [Math]::Round($ramMiB, 1)
                }
            }
        }
        Start-Sleep -Seconds 1
    }
}
$started = [Diagnostics.Stopwatch]::StartNew()
$runError = ''
$telemetryRows = @()
try {
    Invoke-AiCompose -Profiles @('qwen-image') -Arguments $cliArgs
}
catch {
    $runError = $_.Exception.Message
}
finally {
    $started.Stop()
    Stop-Job -Job $sampleJob -ErrorAction SilentlyContinue
    $telemetryRows = @(Receive-Job -Job $sampleJob -ErrorAction SilentlyContinue)
    Remove-Job -Job $sampleJob -Force -ErrorAction SilentlyContinue
}
$peakVram = if ($telemetryRows.Count -gt 0) { [Math]::Round((($telemetryRows | Measure-Object -Property vram_mib -Maximum).Maximum), 0) } else { $null }
$peakContainerRam = if ($telemetryRows.Count -gt 0) { [Math]::Round((($telemetryRows | Measure-Object -Property container_ram_mib -Maximum).Maximum), 1) } else { $null }
$avgGpu = if ($telemetryRows.Count -gt 0) { [Math]::Round((($telemetryRows | Measure-Object -Property gpu_percent -Average).Average), 2) } else { $null }
$avgPower = if ($telemetryRows.Count -gt 0) { [Math]::Round((($telemetryRows | Measure-Object -Property power_w -Average).Average), 2) } else { $null }
$telemetry = [pscustomobject][ordered]@{
    timestamp_utc = [DateTime]::UtcNow.ToString('o'); output = $outputPath; prompt = $Prompt; seed = $Seed
    width = $Width; height = $Height; steps = $Steps; elapsed_seconds = [Math]::Round($started.Elapsed.TotalSeconds, 3)
    status = if ($runError) { 'error' } else { 'complete' }; error = $runError
    peak_vram_mib = $peakVram; peak_container_ram_mib = $peakContainerRam
    gpu_utilization_avg_percent = $avgGpu; power_avg_w = $avgPower; sample_count = $telemetryRows.Count
}
$telemetryPath = Join-Path $outputDirectory "$OutputName.telemetry.json"
$telemetry | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $telemetryPath -Encoding utf8
if ($runError) { throw "Qwen Image command failed: $runError. Telemetry: $telemetryPath" }
Wait-GpuMemoryReleased -BaselineMiB (Get-AiGpuIdleBaselineMiB)
Show-GpuStatus
$outputPath = Join-Path $outputDirectory $OutputName
if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
    throw "Qwen Image command ended without creating $outputPath."
}
Write-Host ("Generated {0} in {1:N1} s (seed {2}, {3}x{4}, {5} steps). Peak GPU {6} MiB; peak container RAM {7} MiB. Telemetry: {8}" -f $outputPath, $started.Elapsed.TotalSeconds, $Seed, $Width, $Height, $Steps, $peakVram, $peakContainerRam, $telemetryPath)
