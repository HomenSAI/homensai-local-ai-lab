$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
Stop-AiServices -ServiceNames @('whisper') -WaitForGpuRelease
