[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$VideoPath,
    [ValidateSet('qwen', 'minicpm', 'spark', 'bonsai')][string]$FinalModel = 'qwen',
    [ValidateSet('auto', 'ru', 'uk', 'de', 'en')][string]$Language = 'auto',
    [ValidateRange(1, 24)][int]$MaxFrames = 12,
    [string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'media-common.ps1')

$video = (Resolve-Path -LiteralPath $VideoPath).Path
$null = ConvertTo-AiContainerMediaPath -Path $video
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path (Split-Path -Parent $video) (([IO.Path]::GetFileNameWithoutExtension($video)) + '-analysis')
}
$outputRoot = [IO.Path]::GetFullPath($OutputDirectory)
$null = ConvertTo-AiContainerMediaPath -Path (Join-Path $outputRoot 'result.txt')
if (Test-Path -LiteralPath $outputRoot) {
    if (@(Get-ChildItem -LiteralPath $outputRoot -Force).Count -gt 0) {
        throw "Refusing to overwrite an existing analysis directory: $outputRoot"
    }
}
else {
    $null = New-Item -ItemType Directory -Path $outputRoot
}

$audioPath = Join-Path $outputRoot 'audio-16khz-mono.wav'
$framesPath = Join-Path $outputRoot 'frames'
$transcriptPath = Join-Path $outputRoot 'transcript.txt'
$frameAnalysisPath = Join-Path $outputRoot 'frame-descriptions.txt'
$resultPath = Join-Path $outputRoot 'result.txt'

try {
    & (Join-Path $PSScriptRoot 'extract-audio.ps1') -VideoPath $video -OutputPath $audioPath
    & (Join-Path $PSScriptRoot 'extract-keyframes.ps1') -VideoPath $video -OutputDirectory $framesPath -MaxFrames $MaxFrames

    Start-AiWhisper
    try {
        $form = @{
            file = Get-Item -LiteralPath $audioPath
            response_format = 'json'
            language = $Language
        }
        $transcription = Invoke-RestMethod -Uri 'http://127.0.0.1:8082/inference' -Method Post -Form $form -TimeoutSec 3600
        $transcript = [string]$transcription.text
        if ([string]::IsNullOrWhiteSpace($transcript)) { throw 'Whisper returned an empty transcript.' }
        Set-Content -LiteralPath $transcriptPath -Value $transcript -Encoding utf8
    }
    finally {
        Stop-AiServices -ServiceNames @('whisper') -WaitForGpuRelease
    }

    Start-AiModel -Service 'qwen-vision' -Profile 'qwen-vision' -BaseUrl 'http://127.0.0.1:8080'
    $frameFiles = @(Get-ChildItem -LiteralPath $framesPath -Filter '*.jpg' -File | Sort-Object Name)
    if ($frameFiles.Count -eq 0) { throw 'No representative frames were extracted.' }
    $content = [Collections.Generic.List[object]]::new()
    $content.Add(@{ type = 'text'; text = 'Describe the video frames in order. For each, report visible actions, objects, text, and meaningful changes. Do not infer events outside the images.' })
    foreach ($frame in $frameFiles) {
        $encoded = [Convert]::ToBase64String([IO.File]::ReadAllBytes($frame.FullName))
        $content.Add(@{
            type = 'image_url'
            image_url = @{ url = "data:image/jpeg;base64,$encoded"; detail = 'low' }
        })
    }
    $modelId = Confirm-OpenAiApi -BaseUrl 'http://127.0.0.1:8080'
    $visionBody = @{
        model = $modelId
        messages = @(@{ role = 'user'; content = $content.ToArray() })
        max_tokens = 1800
        temperature = 0
        reasoning_effort = 'none'
    } | ConvertTo-Json -Depth 12
    $visionResponse = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/v1/chat/completions' -Method Post -ContentType 'application/json' -Body $visionBody -TimeoutSec 900
    $frameDescriptions = [string]$visionResponse.choices[0].message.content
    if ([string]::IsNullOrWhiteSpace($frameDescriptions)) { throw 'Qwen Vision returned no frame descriptions.' }
    Set-Content -LiteralPath $frameAnalysisPath -Value $frameDescriptions -Encoding utf8

    switch ($FinalModel) {
        'qwen' { Start-AiModel -Service 'qwen' -Profile 'qwen' -BaseUrl 'http://127.0.0.1:8080' }
        'minicpm' { Start-AiModel -Service 'minicpm' -Profile 'minicpm' -BaseUrl 'http://127.0.0.1:8080' }
        'spark' { Start-AiModel -Service 'spark' -Profile 'spark' -BaseUrl 'http://127.0.0.1:8080' }
        'bonsai' { Start-AiModel -Service 'bonsai' -Profile 'bonsai' -BaseUrl 'http://127.0.0.1:8080' -TimeoutSeconds 1200 }
    }
    $finalModelId = Confirm-OpenAiApi -BaseUrl 'http://127.0.0.1:8080'
    $combinedPrompt = @"
Produce a concise but complete video analysis. Clearly distinguish what the transcript says from what is visible in the frames. Note timestamps only when supported by the frame order or transcript. Avoid adding details that are not present.

TRANSCRIPT:
$transcript

FRAME DESCRIPTIONS:
$frameDescriptions
"@
    $finalBody = @{
        model = $finalModelId
        messages = @(@{ role = 'user'; content = $combinedPrompt })
        max_tokens = 2400
        temperature = 0
    } | ConvertTo-Json -Depth 8
    $finalResponse = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/v1/chat/completions' -Method Post -ContentType 'application/json' -Body $finalBody -TimeoutSec 1200
    $finalText = [string]$finalResponse.choices[0].message.content
    if ([string]::IsNullOrWhiteSpace($finalText)) { throw 'The final model returned an empty analysis.' }
    Set-Content -LiteralPath $resultPath -Value $finalText -Encoding utf8
    Write-Host "Video analysis saved to $outputRoot"
    Write-Output $finalText
}
finally {
    try { Stop-AiServices -WaitForGpuRelease } catch { Write-Warning "Could not stop local AI services cleanly: $($_.Exception.Message)" }
}
