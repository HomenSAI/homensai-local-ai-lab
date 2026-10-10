# Local AI Lab - (c) 2026 Serhii Khomenko - https://homensai.com/
<#
.SYNOPSIS
  Installer / doctor for Local AI Lab on Windows with Docker Desktop only: no Python, Git or Node on the host.
  The same steps as scripts/install.py; works in the Windows PowerShell 5.1 that comes with Windows.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install.ps1 doctor     # Docker, GPU in Docker, ports, free disk
  powershell -ExecutionPolicy Bypass -File scripts\install.ps1 init       # .env, folders, placeholders, Docker network and model volume
  powershell -ExecutionPolicy Bypass -File scripts\install.ps1 build      # base images and gateway (15-40 min the first time)
  powershell -ExecutionPolicy Bypass -File scripts\install.ps1 up         # console, report, Git and the gateway
  powershell -ExecutionPolicy Bypass -File scripts\install.ps1 git        # local Git server for the report versions
  powershell -ExecutionPolicy Bypass -File scripts\install.ps1 verify     # HTTP checks of every part
  powershell -ExecutionPolicy Bypass -File scripts\install.ps1 all        # doctor + init + build + up + git + verify
  Flags: -Pull (doctor downloads the 5.6 GB CUDA test image; ask the owner first), -NoGpu (PC without an NVIDIA GPU).
#>
param(
  [Parameter(Position = 0)][ValidateSet("doctor", "init", "build", "up", "git", "verify", "all")][string]$Command,
  [switch]$Pull,
  [switch]$NoGpu
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$EnvFile = Join-Path $Root ".env"
$EnvExample = Join-Path $Root ".env.example"
$CudaImage = "nvidia/cuda:12.8.1-runtime-ubuntu24.04"
$Ports = [ordered]@{ "console/report" = 8766; "gateway API" = 8080; "report redirect" = 8765; "Gitea web" = 3010; "Gitea ssh" = 2222 }

if (-not $Command) { Get-Help $PSCommandPath -Examples; exit 2 }

function Say([string]$Mark, [string]$Text) { Write-Host ("[{0}] {1}" -f $Mark, $Text) }

# Runs docker with the given arguments; returns @{ Code; Out } (stdout and stderr together).
function Invoke-DockerCli([string[]]$Arguments, [switch]$Check) {
  $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  try { $out = (& docker @Arguments 2>&1 | Out-String) } finally { $ErrorActionPreference = $old }
  $code = $LASTEXITCODE
  if ($Check -and $code -ne 0) { throw ("command failed ({0}): docker {1}`n{2}" -f $code, ($Arguments -join " "), $out.Trim()) }
  return @{ Code = $code; Out = $out.Trim() }
}

function Invoke-Compose([string[]]$Arguments) {
  $prefix = @("compose")
  if ($NoGpu) { $prefix += @("-f", "docker-compose.yml", "-f", "docker-compose.nogpu.yml") }
  return Invoke-DockerCli ($prefix + $Arguments) -Check
}

function Read-DotEnv {
  $values = @{}
  if (Test-Path $EnvFile) {
    foreach ($line in Get-Content $EnvFile -Encoding UTF8) {
      if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
      $key, $value = $line -split '=', 2
      $values[$key.Trim()] = (($value -split '\s+#', 2)[0]).Trim()
    }
  }
  return $values
}

function Test-PortFree([int]$Port) {
  $client = New-Object System.Net.Sockets.TcpClient
  try { $wait = $client.BeginConnect("127.0.0.1", $Port, $null, $null); return -not ($wait.AsyncWaitHandle.WaitOne(500) -and $client.Connected) }
  catch { return $true } finally { $client.Close() }
}

function Invoke-Doctor {
  $ok = $true
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Say "FAIL" "docker is not on PATH (install Docker Desktop with WSL2)"; return $false }
  $info = Invoke-DockerCli @("info", "--format", "{{.ServerVersion}}")
  if ($info.Code -ne 0) { Say "FAIL" "the Docker daemon does not answer (start Docker Desktop; if it is paused, resume it)"; return $false }
  Say "ok" ("Docker server " + $info.Out)
  $compose = Invoke-DockerCli @("compose", "version", "--short")
  if ($compose.Code -eq 0) { Say "ok" ("docker compose " + $compose.Out) } else { Say "FAIL" "docker compose is missing"; $ok = $false }
  if ($NoGpu) {
    Say "warn" "GPU check skipped (-NoGpu): the gateway cannot load models on this machine"
  } elseif ((Invoke-DockerCli @("image", "inspect", $CudaImage)).Code -ne 0 -and -not $Pull) {
    Say "warn" ("GPU check skipped: the test image {0} (5.6 GB) is not downloaded. Ask the owner, then run: scripts\install.ps1 doctor -Pull" -f $CudaImage)
  } else {
    $gpu = Invoke-DockerCli @("run", "--rm", "--gpus", "all", $CudaImage, "nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader")
    if ($gpu.Code -ne 0) { Say "FAIL" ("GPU is not visible inside Docker: " + $gpu.Out); $ok = $false }
    else { Say "ok" ("GPU in Docker: " + ($gpu.Out -split "`n")[-1]) }
  }
  $drive = New-Object System.IO.DriveInfo ([System.IO.Path]::GetPathRoot($Root))
  $freeGb = [math]::Round($drive.AvailableFreeSpace / 1e9)
  if ($freeGb -gt 60) { $mark = "ok" } else { $mark = "warn" }
  Say $mark ("free disk next to the project: {0} GB (images ~25 GB, models 50-200 GB)" -f $freeGb)
  foreach ($name in $Ports.Keys) {
    $port = $Ports[$name]
    if (Test-PortFree $port) { Say "ok" ("port {0} ({1}) is free" -f $port, $name) }
    else { Say "warn" ("port {0} ({1}) is busy: change it in .env or stop the other program" -f $port, $name) }
  }
  return $ok
}

function Invoke-Init {
  if (-not (Test-Path $EnvFile)) {
    if (-not (Test-Path $EnvExample)) { throw ".env.example is missing" }
    Copy-Item $EnvExample $EnvFile
    Say "ok" "created .env from .env.example - open it in Notepad and set MODEL_DIR (folder with your .gguf models) and AI_CONSOLE_BIND_IP"
  } else { Say "ok" ".env exists" }
  $modelDir = (Read-DotEnv)["MODEL_DIR"]
  if (-not $modelDir -or $modelDir.StartsWith("/path/to") -or $modelDir.StartsWith("C:/path")) {
    Say "warn" "MODEL_DIR in .env is still a placeholder; Docker cannot start model containers until it points to a real folder"
  } elseif (-not (Test-Path $modelDir -PathType Container)) {
    Say "warn" ("MODEL_DIR={0} does not exist yet; create it or fix the path" -f $modelDir)
  }
  foreach ($folder in @("bench_results", "report", "results-db", "media/images", "benchmark/q4kv-20260929", "secrets", "config")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root $folder) | Out-Null
  }
  $stubs = [ordered]@{
    "benchmark/q4kv-20260929/recommended-settings-q4kv-20260929.json" = "{`"model_profiles`":{}}`n"
    "report/report-data.json" = "{`"runs`":[],`"scores`":[],`"responses`":[],`"generated_at`":null}`n"
    "BENCHMARK_RESULTS.csv" = ""; "BENCHMARK_RESULTS.db" = ""; "media/images/qwen-image-2.1-smoke.png" = ""; "secrets/gitea-token" = ""
  }
  $utf8 = New-Object System.Text.UTF8Encoding $false   # no BOM: the containers read these files
  foreach ($relative in $stubs.Keys) {
    $path = Join-Path $Root $relative
    if (-not (Test-Path $path)) { [System.IO.File]::WriteAllText($path, $stubs[$relative], $utf8); Say "ok" ("created placeholder " + $relative) }
  }
  if ((Invoke-DockerCli @("network", "inspect", "ai-net")).Code -ne 0) { Invoke-DockerCli @("network", "create", "ai-net") -Check | Out-Null; Say "ok" "created Docker network ai-net" }
  if ((Invoke-DockerCli @("volume", "inspect", "llm-models-fast")).Code -ne 0) {
    Invoke-DockerCli @("volume", "create", "llm-models-fast") -Check | Out-Null
    Say "ok" "created Docker volume llm-models-fast (copy your .gguf files into it: see docs/INSTALL)"
  }
  $cfg = Invoke-DockerCli @("compose", "--profile", "gateway", "--profile", "build", "--profile", "bench", "config", "-q")
  if ($cfg.Code -eq 0) { Say "ok" "docker compose configuration is valid"; return $true }
  Say "FAIL" ("compose config error: " + $cfg.Out); return $false
}

function Invoke-Build {
  $steps = @()
  if (-not $NoGpu) {
    $steps += , @("llama.cpp (CUDA) base image", @("--profile", "build", "build", "build-upstream"))
    $steps += , @("Bonsai llama.cpp fork image", @("--profile", "build", "build", "build-bonsai"))
    $steps += , @("llama-swap gateway image", @("--profile", "gateway", "build", "llama-swap-gateway"))
  }
  $steps += , @("console, report builder, versioner", @("build", "ai-console", "report-versioner"))
  foreach ($step in $steps) {
    $note = ""; if (-not $NoGpu) { $note = " (the CUDA builds take 15-40 minutes the first time)" }
    Say ".." ("building: " + $step[0] + $note)
    Invoke-Compose $step[1] | Out-Null
    Say "ok" ("built: " + $step[0])
  }
  return $true
}

function Invoke-Up {
  Invoke-Compose @("up", "-d", "ai-console", "report-builder", "stats-report", "gitea", "report-versioner") | Out-Null
  if ($NoGpu) { Say "ok" "services started without the gateway (no GPU): the console, report and Git work, models cannot be loaded"; return $true }
  Invoke-Compose @("--profile", "gateway", "up", "-d", "llama-swap-gateway") | Out-Null
  Say "ok" "services started; the gateway needs ~30 s to become healthy"
  return $true
}

# Local Git server for the report versions: the same as scripts/setup_git.py (Gitea user, token, repository, SSH key,
# versioner). Safe to repeat: existing user, token, repository and key are reused. Secrets stay in secrets/.
function Invoke-GitApi([string]$Method, [string]$Url, $Body, [string]$Auth) {
  $headers = @{}
  if ($Auth) { $headers["Authorization"] = $Auth }
  $json = $null
  if ($null -ne $Body) { $json = [System.Text.Encoding]::UTF8.GetBytes(($Body | ConvertTo-Json -Compress)) }
  try {
    $r = Invoke-WebRequest -Uri $Url -Method $Method -Headers $headers -Body $json -ContentType "application/json" -UseBasicParsing -TimeoutSec 30
    $data = $null; if ($r.Content) { $data = $r.Content | ConvertFrom-Json }
    return @{ Status = [int]$r.StatusCode; Data = $data }
  } catch {
    if ($_.Exception.Response) { return @{ Status = [int]$_.Exception.Response.StatusCode; Data = $_.ErrorDetails.Message } }
    return @{ Status = 0; Data = $_.Exception.Message }
  }
}

function Invoke-GitSetup {
  $dotenv = Read-DotEnv
  $user = $dotenv["GITEA_REPORT_OWNER"]; if (-not $user) { $user = "reports-admin" }
  $repo = $dotenv["GITEA_REPORT_REPO"]; if (-not $repo) { $repo = "model-test-reports" }
  $port = $dotenv["GITEA_WEB_PORT"]; if (-not $port) { $port = "3010" }
  $api = "http://127.0.0.1:$port/api/v1"
  $secrets = Join-Path $Root "secrets"
  New-Item -ItemType Directory -Force -Path $secrets | Out-Null
  $utf8 = New-Object System.Text.UTF8Encoding $false
  $tokenFile = Join-Path $secrets "gitea-token"; $adminFile = Join-Path $secrets "gitea-admin.txt"
  if (-not (Test-Path $tokenFile)) { [System.IO.File]::WriteAllText($tokenFile, "", $utf8) }
  Invoke-Compose @("up", "-d", "gitea") | Out-Null
  $healthy = $false
  for ($i = 0; $i -lt 60; $i++) {
    if ((Invoke-DockerCli @("inspect", "-f", "{{.State.Health.Status}}", "ai-gitea")).Out -eq "healthy") { $healthy = $true; break }
    Start-Sleep -Seconds 3
  }
  if (-not $healthy) { Say "FAIL" "Gitea did not become healthy; see: docker logs ai-gitea"; return $false }

  $password = $null
  if (Test-Path $adminFile) {
    foreach ($line in Get-Content $adminFile -Encoding UTF8) { if ($line -like "password:*") { $password = $line.Substring(9).Trim() } }
  }
  if (-not $password) {
    $bytes = New-Object byte[] 18
    (New-Object System.Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes)
    $password = [Convert]::ToBase64String($bytes).Replace("+", "-").Replace("/", "_")
    $created = Invoke-DockerCli @("exec", "ai-gitea", "gitea", "admin", "user", "create", "--admin", "--username", $user, "--password", $password,
                                  "--email", "$user@local.invalid", "--must-change-password=false")
    if ($created.Code -ne 0) {
      if ($created.Out -notmatch "already exists") { Say "FAIL" ("Gitea user creation failed: " + $created.Out); return $false }
      Invoke-DockerCli @("exec", "ai-gitea", "gitea", "admin", "user", "change-password", "--username", $user, "--password", $password,
                         "--must-change-password=false") -Check | Out-Null
    }
    [System.IO.File]::WriteAllText($adminFile, "user: $user`npassword: $password`nweb: http://127.0.0.1:$port/`n", $utf8)
    Say "ok" "Gitea administrator $user (login data in secrets\gitea-admin.txt)"
  }
  $basic = "Basic " + [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes("${user}:$password"))
  if (-not (Get-Content $tokenFile -Raw -ErrorAction SilentlyContinue)) {
    $name = "versioner-" + (Get-Date -Format "yyyyMMddHHmmss")
    $r = Invoke-GitApi "POST" "$api/users/$user/tokens" @{ name = $name; scopes = @("write:repository", "read:repository", "write:user", "read:user") } $basic
    if ($r.Status -ne 200 -and $r.Status -ne 201) { Say "FAIL" ("token creation failed: " + $r.Status + " " + $r.Data); return $false }
    [System.IO.File]::WriteAllText($tokenFile, $r.Data.sha1, $utf8)
    Say "ok" "access token for the versioner (secrets\gitea-token)"
  }
  $token = "token " + (Get-Content $tokenFile -Raw).Trim()
  if ((Invoke-GitApi "GET" "$api/repos/$user/$repo" $null $token).Status -eq 404) {
    $r = Invoke-GitApi "POST" "$api/user/repos" @{ name = $repo; private = $true; auto_init = $false; default_branch = "main"
      description = "Versions of the local AI model test reports (created by report-versioner)" } $token
    if ($r.Status -ne 200 -and $r.Status -ne 201) { Say "FAIL" ("repository creation failed: " + $r.Status + " " + $r.Data); return $false }
    Say "ok" "private repository $user/$repo"
  }
  $key = Join-Path $secrets "id_ed25519"
  if (-not (Test-Path $key) -and (Get-Command ssh-keygen -ErrorAction SilentlyContinue)) {
    & cmd /c "ssh-keygen -q -t ed25519 -N `"`" -C model-test-reports -f `"$key`"" | Out-Null
  }
  if (Test-Path "$key.pub") {
    $public = (Get-Content "$key.pub" -Raw).Trim()
    $keys = Invoke-GitApi "GET" "$api/user/keys" $null $token
    $known = $false
    foreach ($k in @($keys.Data)) { if ($k.key -and ($k.key.Split(" ")[0..1] -join " ") -eq ($public.Split(" ")[0..1] -join " ")) { $known = $true } }
    if ($keys.Status -eq 200 -and -not $known) { Invoke-GitApi "POST" "$api/user/keys" @{ title = "workstation"; key = $public } $token | Out-Null }
    Say "ok" "SSH key for cloning the versions (secrets\id_ed25519)"
  } else {
    Say "warn" "ssh-keygen not found: no SSH key. The versioner works without it; clone over HTTP with the login in secrets\gitea-admin.txt"
  }
  Invoke-Compose @("up", "-d", "report-versioner") | Out-Null
  Say "ok" ("Git is ready: http://127.0.0.1:$port/$user/$repo  (versions: tags v0001, v0002 ..., stage-<id>-done, final-<date>)")
  return $true
}

function Get-Http([string]$Url) {
  try { return [int](Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 8).StatusCode }
  catch { if ($_.Exception.Response) { return [int]$_.Exception.Response.StatusCode } return $_.Exception.Message }
}

function Invoke-Verify {
  $checks = @(
    @("console health", "http://127.0.0.1:8766/health"), @("console status API", "http://127.0.0.1:8766/api/status"),
    @("model catalog", "http://127.0.0.1:8766/api/models"), @("report page", "http://127.0.0.1:8766/report/"),
    @("test progress page", "http://127.0.0.1:8766/report/progress.html"), @("style package", "http://127.0.0.1:8766/style/dist/homensai-full.css"),
    @("license files", "http://127.0.0.1:8766/legal/README.md"), @("version", "http://127.0.0.1:8766/api/version"))
  if (-not $NoGpu) { $checks += , @("gateway models", "http://127.0.0.1:8080/v1/models") }
  $checks += , @("Gitea", "http://127.0.0.1:3010/api/healthz")
  $good = $true
  foreach ($check in $checks) {
    $status = Get-Http $check[1]
    if ($status -eq 200) { Say "ok" ("{0}: {1} -> 200" -f $check[0], $check[1]) }
    else { $good = $false; Say "FAIL" ("{0}: {1} -> {2}" -f $check[0], $check[1], $status) }
  }
  foreach ($line in ((Invoke-DockerCli @("ps", "--format", "{{.Names}} {{.Status}}")).Out -split "`n")) {
    if ($line -match '^(ai-|hermes|video)') { if ($line -match 'unhealthy') { Say "FAIL" $line } else { Say "ok" $line } }
  }
  return $good
}

$steps = @{ doctor = { Invoke-Doctor }; init = { Invoke-Init }; build = { Invoke-Build }; up = { Invoke-Up }; git = { Invoke-GitSetup }; verify = { Invoke-Verify } }
try {
  if ($Command -eq "all") {
    foreach ($name in @("doctor", "init", "build", "up", "git")) { if (-not (& $steps[$name])) { Say "FAIL" ("stopped at step '" + $name + "'"); exit 1 } }
    Start-Sleep -Seconds 40
    if (Invoke-Verify) { exit 0 } else { exit 1 }
  }
  if (& $steps[$Command]) { exit 0 } else { exit 1 }
} catch {
  Say "FAIL" $_.Exception.Message
  exit 1
}
