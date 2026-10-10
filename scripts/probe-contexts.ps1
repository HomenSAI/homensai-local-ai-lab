[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('qwen','qwen-q5','qwen-vision','minicpm','spark','bonsai')][string]$ModelKey,
    [ValidateRange(10,1800)][int]$StartTimeoutSeconds=180
)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'common.ps1')

$definitions=@{
    'qwen'=@{Service='qwen';Env='QWEN_CTX';Model='Qwen3.5-9B MTP';GGUF='Qwen3.5-9B-UD-Q4_K_XL.gguf';Quant='UD-Q4_K_XL';Contexts=@(8192,16384,32768,65536)}
    'qwen-q5'=@{Service='qwen-q5';Env='QWEN_Q5_CTX';Model='Qwen3.5-9B Q5 comparison';GGUF='Qwen3.5-9B-Q5_K_S-4.60bpw.gguf';Quant='Q5_K_S';Contexts=@(8192,16384,32768,65536)}
    'qwen-vision'=@{Service='qwen-vision';Env='QWEN_VISION_CTX';Model='Qwen3.5-9B Vision';GGUF='Qwen3.5-9B-UD-Q4_K_XL.gguf + mmproj-F16.gguf';Quant='UD-Q4_K_XL + F16';Contexts=@(8192,16384,32768)}
    'minicpm'=@{Service='minicpm';Env='MINICPM_CTX';Model='MiniCPM5-2B';GGUF='MiniCPM5-2B-Q8_0.gguf';Quant='Q8_0';Contexts=@(8192,16384,32768,65536)}
    'spark'=@{Service='spark';Env='SPARK_CTX';Model='Spark-X2.5-4B';GGUF='Spark-X2.5-4B-Q8_0.gguf';Quant='Q8_0';Contexts=@(8192,16384,32768,65536)}
    'bonsai'=@{Service='bonsai';Env='BONSAI_CTX';Model='Ternary Bonsai 2 27B';GGUF='Ternary-Bonsai-2-27B-PTQ1_0.gguf';Quant='PTQ1_0';Contexts=@(8192,16384,32768)}
}
$def=$definitions[$ModelKey]
$startScript=Join-Path $PSScriptRoot "start-$ModelKey.ps1"
$resultPath=Join-Path $script:AiRoot 'CONTEXT_PROBE_RESULTS.csv'
$oldContext=[Environment]::GetEnvironmentVariable($def.Env,'Process')
$oldTimeout=[Environment]::GetEnvironmentVariable('LLAMA_START_TIMEOUT_SECONDS','Process')
$session=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
try {
    [Environment]::SetEnvironmentVariable('LLAMA_START_TIMEOUT_SECONDS',[string]$StartTimeoutSeconds,'Process')
    foreach($context in $def.Contexts) {
        $status='passed';$errorText='';$startup=$null;$vram=$null;$apiModel='';$answer=''
        [Environment]::SetEnvironmentVariable($def.Env,[string]$context,'Process')
        try {
            $startOutput=@(& $startScript)
            $startInfo=$startOutput | Where-Object {$null -ne $_ -and $_.PSObject.Properties['StartupSeconds']} | Select-Object -Last 1
            if($startInfo){$startup=[double]$startInfo.StartupSeconds}
            $apiModel=Confirm-OpenAiApi -BaseUrl 'http://127.0.0.1:8080'
            $payload=@{model=$apiModel;messages=@(@{role='user';content='Reply with exactly READY.'});max_tokens=128;temperature=0;seed=1234;stream=$false}|ConvertTo-Json -Depth 8
            $response=Invoke-RestMethod -Uri 'http://127.0.0.1:8080/v1/chat/completions' -Method Post -ContentType 'application/json' -Body $payload -TimeoutSec 600
            $answer=[string]$response.choices[0].message.content
            if([string]::IsNullOrWhiteSpace($answer)){$answer=[string]$response.choices[0].message.reasoning_content}
            if([string]::IsNullOrWhiteSpace($answer)){throw 'The model returned an empty smoke response.'}
            $sample=& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits
            if($LASTEXITCODE -eq 0 -and $sample){$vram=[int](($sample -split '\s+')[0])}
        }
        catch {
            $status='failed';$errorText=$_.Exception.Message
        }
        finally {
            $active=@(Get-AiRunningServices)
            if($active -contains $def.Service){Stop-AiServices -ServiceNames @($def.Service) -WaitForGpuRelease}
        }
        $row=[pscustomobject][ordered]@{TimestampUtc=[DateTime]::UtcNow.ToString('o');Session=$session;Model=$def.Model;Profile=$ModelKey;GGUF=$def.GGUF;Quant=$def.Quant;Context=$context;LoadSeconds=$startup;VRAMUsedMiB=$vram;ApiModel=$apiModel;Status=$status;Error=$errorText;SmokeExcerpt=($answer -replace '[\r\n]+',' ')}
        if(Test-Path -LiteralPath $resultPath){$row|Export-Csv -LiteralPath $resultPath -NoTypeInformation -Append -Encoding utf8}else{$row|Export-Csv -LiteralPath $resultPath -NoTypeInformation -Encoding utf8}
        Write-Host ("CONTEXT {0} {1}: {2}{3}" -f $ModelKey,$context,$status,($(if($errorText){" — $errorText"}else{''})))
        if($status -ne 'passed'){Write-Warning "Stopping this model's context ladder at the first failed size; larger contexts are not safe to assume.";break}
    }
    Write-Host "Context probe rows: $resultPath"
}
finally {
    [Environment]::SetEnvironmentVariable($def.Env,$oldContext,'Process')
    [Environment]::SetEnvironmentVariable('LLAMA_START_TIMEOUT_SECONDS',$oldTimeout,'Process')
}
