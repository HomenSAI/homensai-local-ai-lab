$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$active = @(Get-AiRunningServices)
if ($active.Count -eq 0) {
    Write-Host 'Active model: none'
}
else {
    Write-Host 'Active local-ai-server services:'
    foreach ($service in $active) {
        $url = Get-AiServiceApiUrl -Service $service
        if ($service -eq 'whisper') {
            Write-Host "  $service — speech API $url/inference"
        }
        elseif ($service -eq 'media-tools') {
            Write-Host "  $service — one-shot ffmpeg/ffprobe utility"
        }
        else {
            Write-Host "  $service — OpenAI API $url/v1"
        }
    }
}
Show-GpuStatus
