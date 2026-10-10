Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'common.ps1')

function Get-AiMediaRoot {
    $configured = [Environment]::GetEnvironmentVariable('MEDIA_DIR')
    if ([string]::IsNullOrWhiteSpace($configured)) {
        $line = Get-Content -LiteralPath (Join-Path $script:AiRoot '.env') |
            Where-Object { $_ -match '^MEDIA_DIR=' } | Select-Object -First 1
        if (-not $line) { throw 'MEDIA_DIR is missing from ai-server/.env.' }
        $configured = ($line -split '=', 2)[1].Trim()
    }
    $root = [IO.Path]::GetFullPath($configured)
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        throw "Media directory does not exist: $root"
    }
    return $root.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
}

function ConvertTo-AiContainerMediaPath {
    param([Parameter(Mandatory)][string]$Path)

    $root = Get-AiMediaRoot
    $full = [IO.Path]::GetFullPath($Path)
    $prefix = $root + [IO.Path]::DirectorySeparatorChar
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Media inputs and outputs must be inside MEDIA_DIR ($root): $full"
    }
    $relative = [IO.Path]::GetRelativePath($root, $full).Replace('\', '/')
    if ($relative -eq '..' -or $relative.StartsWith('../', [StringComparison]::Ordinal)) {
        throw "Path escapes MEDIA_DIR: $full"
    }
    return "/media/$relative"
}

function Invoke-AiMediaTool {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidateSet('ffmpeg', 'ffprobe')][string]$Tool,
        [Parameter(Mandatory)][string[]]$Arguments
    )
    Invoke-AiCompose -Profiles @('media-tools') -Arguments (@(
        'run', '--rm', '--no-deps', '--entrypoint', $Tool, 'media-tools'
    ) + $Arguments)
}
