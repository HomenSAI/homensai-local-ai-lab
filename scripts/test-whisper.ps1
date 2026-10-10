[CmdletBinding()]
param(
    [string]$AudioPath=(Join-Path $PSScriptRoot '..\media\test-assets\whisper-smoke.wav'),
    [string]$BaseUrl='http://127.0.0.1:8082'
)
$ErrorActionPreference='Stop'
$file=Get-Item -LiteralPath $AudioPath -ErrorAction Stop
if($file.Length -le 44 -or $file.Length -gt 256MB){throw 'Audio file must be a non-empty WAV/audio file no larger than 256 MiB.'}
$sha=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$form=@{file=$file}
$timer=[Diagnostics.Stopwatch]::StartNew()
$response=Invoke-RestMethod -Uri "$BaseUrl/inference" -Method Post -Form $form -TimeoutSec 900
$timer.Stop()
$transcript=[string]$response.text
if([string]::IsNullOrWhiteSpace($transcript)){$transcript=[string]$response.transcription}
if([string]::IsNullOrWhiteSpace($transcript)){throw "Whisper returned no transcript: $($response|ConvertTo-Json -Depth 8 -Compress)"}
$row=[ordered]@{timestamp_utc=[DateTime]::UtcNow.ToString('o');model='ggml-large-v3-turbo-q8_0';audio=$file.FullName;audio_sha256=$sha;audio_bytes=$file.Length;elapsed_seconds=[Math]::Round($timer.Elapsed.TotalSeconds,3);transcript=$transcript;raw=$response}
$output=Join-Path $PSScriptRoot '..\benchmark-output\multimodal\whisper-smoke.jsonl'
$output=[IO.Path]::GetFullPath($output)
New-Item -ItemType Directory -Path (Split-Path -Parent $output) -Force|Out-Null
Add-Content -LiteralPath $output -Value ($row|ConvertTo-Json -Depth 12 -Compress) -Encoding utf8
Write-Host ("Whisper passed in {0:N2}s; audio SHA256 {1}" -f $timer.Elapsed.TotalSeconds,$sha)
Write-Output $transcript
Write-Host "Raw result: $output"
