param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$modelRoot = '<ROOT>\Qwen-Image-2.1'
$assets = @(
    @{ Repo='unsloth/Qwen-Image-2.1-GGUF'; Revision='2c31ccd392b367a6637841a143813320a02dff55'; File='qwen-image-2.1-Q5_K_M.gguf'; LocalDir=$modelRoot },
    @{ Repo='Qwen/Qwen3-VL-8B-Instruct-GGUF'; Revision='f982a07559d4a2f6c8744d840bf6fccab30eea96'; File='Qwen3VL-8B-Instruct-Q4_K_M.gguf'; LocalDir=(Join-Path $modelRoot 'text_encoder') },
    @{ Repo='Qwen/Qwen3-VL-8B-Instruct-GGUF'; Revision='f982a07559d4a2f6c8744d840bf6fccab30eea96'; File='mmproj-Qwen3VL-8B-Instruct-F16.gguf'; LocalDir=(Join-Path $modelRoot 'text_encoder') },
    @{ Repo='Comfy-Org/Qwen-Image-2.1'; Revision='9a44dbdb47cefd046be9c0a13476192f34c8db8e'; File='vae/qwen_image_2.1_vae_bf16.safetensors'; LocalDir=$modelRoot }
)
$hf = Get-Command hf -ErrorAction Stop
New-Item -ItemType Directory -Path $modelRoot,(Join-Path $modelRoot 'text_encoder'),(Join-Path $modelRoot 'vae') -Force | Out-Null

# Keep HF Xet's per-file buffers modest on this 16 GiB host; this script downloads serially.
$env:HF_XET_RECONSTRUCTION_DOWNLOAD_BUFFER_SIZE = '536870912'
$env:HF_XET_RECONSTRUCTION_DOWNLOAD_BUFFER_PERFILE_SIZE = '268435456'
$env:HF_XET_RECONSTRUCTION_DOWNLOAD_BUFFER_LIMIT = '536870912'
$env:HF_XET_NUM_CONCURRENT_RANGE_GETS = '4'
$env:HF_XET_CLIENT_AC_INITIAL_DOWNLOAD_CONCURRENCY = '1'
$env:HF_XET_CLIENT_AC_MAX_DOWNLOAD_CONCURRENCY = '2'

foreach ($asset in $assets) {
    $destination = Join-Path $asset.LocalDir $asset.File
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        Write-Host "PRESERVE existing asset; skip download: $destination"
        continue
    }
    Write-Host "Downloading pinned $($asset.Repo)/$($asset.File)@$($asset.Revision) with bounded, serial HF Xet concurrency"
    & $hf.Source download $asset.Repo $asset.File --revision $asset.Revision --local-dir $asset.LocalDir
    if ($LASTEXITCODE -ne 0) { throw "hf download failed for $($asset.Repo)/$($asset.File), exit $LASTEXITCODE" }
    if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) { throw "hf returned success but asset is missing: $destination" }
    Get-Item -LiteralPath $destination | Select-Object FullName,Length
}
Write-Host 'All absent Qwen Image assets downloaded from their pinned revisions; verify sizes, GGUF metadata and SHA256 next.'
