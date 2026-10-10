param(
    [string]$BaseUrl = 'http://127.0.0.1:8080',
    [string]$Prompt = 'Reply with one short sentence confirming the local model is responding.',
    [int]$MaxTokens = 96
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$model = Confirm-OpenAiApi -BaseUrl $BaseUrl
$body = @{
    model = $model
    messages = @(@{ role = 'user'; content = $Prompt })
    max_tokens = $MaxTokens
    temperature = 0
    seed = 1234
    stream = $false
} | ConvertTo-Json -Depth 8
$timer = [Diagnostics.Stopwatch]::StartNew()
$response = Invoke-RestMethod -Uri "$BaseUrl/v1/chat/completions" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 600
$timer.Stop()
$text = $response.choices[0].message.content
if ([string]::IsNullOrWhiteSpace($text)) { $text = $response.choices[0].message.reasoning_content }
if ([string]::IsNullOrWhiteSpace($text)) {
    throw 'The server returned an empty answer.'
}
Write-Host ("Smoke response ({0:N2} s):" -f $timer.Elapsed.TotalSeconds)
Write-Output $text
Show-GpuStatus
