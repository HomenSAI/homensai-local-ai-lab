$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
Assert-DockerCli
Write-Host 'Building the pinned CUDA images one at a time to stay within host RAM.'
foreach ($service in @('qwen', 'bonsai', 'whisper', 'qwen-image')) {
    Write-Host "Building service image: $service"
    Invoke-AiCompose -Profiles @($service) -Arguments @('build', $service)
}
