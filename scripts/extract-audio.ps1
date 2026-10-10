[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$VideoPath,
    [string]$OutputPath
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'media-common.ps1')

$video = (Resolve-Path -LiteralPath $VideoPath).Path
$videoContainerPath = ConvertTo-AiContainerMediaPath -Path $video
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path (Split-Path -Parent $video) (([IO.Path]::GetFileNameWithoutExtension($video)) + '-audio.wav')
}
$outputFull = [IO.Path]::GetFullPath($OutputPath)
$outputContainerPath = ConvertTo-AiContainerMediaPath -Path $outputFull
if (Test-Path -LiteralPath $outputFull) { throw "Refusing to overwrite existing audio: $outputFull" }

Invoke-AiMediaTool -Tool ffmpeg -Arguments @(
    '-hide_banner', '-nostdin', '-n', '-i', $videoContainerPath,
    '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', $outputContainerPath
)
Write-Host "Audio written: $outputFull"
