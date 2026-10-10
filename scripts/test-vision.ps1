[CmdletBinding()]
param(
    [string]$ImagePath=(Join-Path $PSScriptRoot '..\media\test-assets\vision-smoke.png'),
    [string]$BaseUrl='http://127.0.0.1:8080'
)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$file=Get-Item -LiteralPath $ImagePath -ErrorAction Stop
if($file.Length -le 0 -or $file.Length -gt 10MB){throw 'Vision test image must be between 1 byte and 10 MiB.'}
$models=Invoke-RestMethod -Uri "$BaseUrl/v1/models" -TimeoutSec 20
if($models.data.Count -ne 1 -or $models.data[0].id -notmatch 'qwen3\.5-9b-vision'){throw 'API identity guard failed; expected the isolated Qwen Vision profile.'}
$sha=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$mime=switch($file.Extension.ToLowerInvariant()){'.png'{'image/png'}'.jpg'{'image/jpeg'}'.jpeg'{'image/jpeg'}'.webp'{'image/webp'}default{throw 'Use PNG, JPEG or WebP for the vision smoke.'}}
$data='data:{0};base64,{1}' -f $mime,[Convert]::ToBase64String([IO.File]::ReadAllBytes($file.FullName))
$payload=@{
    model=$models.data[0].id
    messages=@(@{role='user';content=@(
        @{type='text';text='Describe the main shapes and their colors in this image in one short sentence.'},
        @{type='image_url';image_url=@{url=$data}}
    )})
    max_tokens=192
    temperature=0
    seed=1234
    stream=$false
    chat_template_kwargs=@{enable_thinking=$false}
}
$timer=[Diagnostics.Stopwatch]::StartNew()
$response=Invoke-RestMethod -Uri "$BaseUrl/v1/chat/completions" -Method Post -ContentType 'application/json' -Body ($payload|ConvertTo-Json -Depth 12) -TimeoutSec 900
$timer.Stop()
$choice=$response.choices[0]
$message=$choice.message
$answer=[string]$message.content
if([string]::IsNullOrWhiteSpace($answer)){$answer=[string]$message.reasoning_content}
if([string]::IsNullOrWhiteSpace($answer)){throw 'Vision API returned an empty answer.'}
$row=[ordered]@{timestamp_utc=[DateTime]::UtcNow.ToString('o');model=$models.data[0].id;image=$file.FullName;image_sha256=$sha;image_bytes=$file.Length;context=$models.data[0].meta.n_ctx;elapsed_seconds=[Math]::Round($timer.Elapsed.TotalSeconds,3);prompt_tokens=$response.usage.prompt_tokens;completion_tokens=$response.usage.completion_tokens;finish_reason=$choice.finish_reason;response=$answer;raw=$response}
$output=Join-Path $script:AiRoot 'benchmark-output\multimodal\vision-smoke.jsonl'
New-Item -ItemType Directory -Path (Split-Path -Parent $output) -Force|Out-Null
Add-Content -LiteralPath $output -Value ($row|ConvertTo-Json -Depth 20 -Compress) -Encoding utf8
Write-Host ("Qwen Vision passed in {0:N2}s at context {1}; image SHA256 {2}" -f $timer.Elapsed.TotalSeconds,$row.context,$sha)
Write-Output $answer
Write-Host "Raw result: $output"
