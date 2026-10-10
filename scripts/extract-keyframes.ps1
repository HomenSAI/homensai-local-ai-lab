[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$VideoPath,
    [string]$OutputDirectory,
    [ValidateRange(1, 500)][int]$MaxFrames = 24,
    [ValidateRange(1, 3600)][int]$MinIntervalSeconds = 1,
    [ValidateRange(160, 4096)][int]$MaxWidth = 1024
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'media-common.ps1')

$video = (Resolve-Path -LiteralPath $VideoPath).Path
$videoContainerPath = ConvertTo-AiContainerMediaPath -Path $video
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path (Split-Path -Parent $video) (([IO.Path]::GetFileNameWithoutExtension($video)) + '-frames')
}
$outputFull = [IO.Path]::GetFullPath($OutputDirectory)
$null = ConvertTo-AiContainerMediaPath -Path (Join-Path $outputFull 'frame_0001.jpg')
if (Test-Path -LiteralPath $outputFull) {
    if (@(Get-ChildItem -LiteralPath $outputFull -Force).Count -gt 0) {
        throw "Refusing to overwrite files in keyframe directory: $outputFull"
    }
}
else {
    $null = New-Item -ItemType Directory -Path $outputFull
}

$probe = @(Invoke-AiMediaTool -Tool ffprobe -Arguments @(
    '-v', 'error', '-show_entries', 'format=duration',
    '-of', 'default=noprint_wrappers=1:nokey=1', $videoContainerPath
))
$duration = 0.0
$durationText = ($probe | Select-Object -Last 1).ToString().Trim()
if (-not [double]::TryParse($durationText, [Globalization.NumberStyles]::Float,
    [Globalization.CultureInfo]::InvariantCulture, [ref]$duration) -or $duration -le 0) {
    throw "Could not read a positive video duration from ffprobe: '$durationText'"
}
$interval = [Math]::Max($MinIntervalSeconds, [int][Math]::Ceiling($duration / $MaxFrames))
$pattern = ConvertTo-AiContainerMediaPath -Path (Join-Path $outputFull 'frame_%04d.jpg')
$filter = "fps=1/$interval,scale=$($MaxWidth):-2:force_original_aspect_ratio=decrease"
Invoke-AiMediaTool -Tool ffmpeg -Arguments @(
    '-hide_banner', '-nostdin', '-n', '-i', $videoContainerPath,
    '-vf', $filter, '-frames:v', "$MaxFrames", '-q:v', '3', $pattern
)
Write-Host "Extracted representative frames to $outputFull (interval about $interval s, maximum $MaxFrames)."
