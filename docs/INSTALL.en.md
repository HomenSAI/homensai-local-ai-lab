# Installation guide (English)

Other languages: [Русский](INSTALL.ru.md) · [Deutsch](INSTALL.de.md) · Back to the [README](../README.md)

This guide takes you from an empty machine to a working **Local AI Server**: a gateway that loads one local language model at a time into the video memory of a single NVIDIA GPU, a web console (models, chat, tests, video generation, reports) in three languages, automatic test reports and a local Git server that keeps every version of the reports.

> Author and rights: results and reports are licensed **CC BY-NC 4.0** (use and share for noncommercial purposes only, and you must link to the author, <https://homensai.com>); code is **PolyForm Noncommercial 1.0.0**. Model weights are **not** part of this package and keep their own licenses. See `legal/`.

## Contents

1. [What you get](#1-what-you-get)
2. [Requirements](#2-requirements)
3. [Fast path: the installer script](#3-fast-path-the-installer-script)
4. [Step-by-step installation](#4-step-by-step-installation)
5. [Optional components](#5-optional-components)
6. [Verification](#6-verification)
7. [Using the console](#7-using-the-console)
8. [Test results, reports and Git versions](#8-test-results-reports-and-git-versions)
9. [Maintenance: update, back up, remove](#9-maintenance-update-back-up-remove)
10. [Linux / macOS notes](#10-linux--macos-notes)
11. [Troubleshooting](#11-troubleshooting)
12. [Security](#12-security)

## 1. What you get

| Part | Container | Port (on this PC) | What it does |
|---|---|---|---|
| Gateway (llama-swap) | `ai-llama-swap-gateway` | 8080 | OpenAI-compatible API. Starts `llama-server` for the model you ask for and unloads the previous one. |
| Console | `ai-model-console` | 8766 | Web UI: model catalog with Start/Stop, chat, GPU telemetry, diagnostics, unload timer, test results, and the **report** at `/report/`. Languages: RU / EN / DE (switch in the header). |
| Report builder | `ai-report-builder` | - | Every 15 s turns benchmark result files into `report/live-data.json` and the SQLite archive `results-db/llm-results.sqlite`. |
| Report redirect | `ai-stats-report` | 8765 | Old address: redirects to `http://HOST:8766/report/`. |
| Git server | `ai-gitea` | 3010 (web), 2222 (ssh) | Local Gitea with the private repository `reports-admin/model-test-reports`. |
| Versioner | `ai-report-versioner` | - | Every minute commits changed results and reports to Gitea (tags `v0001`, `v0002`, ..., `stage-<id>-done`, `final-<date>`). |
| Telemetry (optional) | `hermes-telemetry` | 9835 | Prometheus-style GPU / llama metrics for an external collector. |
| Video Studio (separate project, optional) | `video-studio-console`, `video-generation-comfyui-video-1` | 8767, 8188 | Video generation (ComfyUI + Wan 2.1). Own repository and guide. |
| Open WebUI (optional) | `open-webui` | 3000 | Chat UI connected to the gateway. |

Only one large model fits in 10 GB of video memory, so the gateway keeps **one model loaded at a time**; the console refuses to start an LLM while Video Studio generates a video (and Video Studio unloads the models before it starts).

## 2. Requirements

**Hardware**
- NVIDIA GPU with at least 8 GB video memory (author: RTX 3080, 10 GB). Models and context sizes in `config/llama-swap.yaml` are tuned for 10 GB; with less memory use smaller models/contexts.
- 16 GB RAM minimum, 32 GB recommended (building the CUDA images and loading 9-27B models use a lot of RAM).
- Free disk: about 25 GB for Docker images, 50-200 GB for models.

**Software**
- Windows 10/11 with **Docker Desktop (WSL2 backend)** and a current NVIDIA driver (Game Ready or Studio, CUDA 12.8-capable). This is the tested setup. For Linux see section 10.
- Docker Compose v2 (included in Docker Desktop). On Windows nothing else: the installer `scripts\install.ps1` runs in the built-in PowerShell. On Linux: Python 3.10+ (for the helper scripts, no extra packages) and Git.
- Internet access for building images and downloading models.

**Check the GPU in Docker first** (must print your GPU):

```
docker run --rm --gpus all nvidia/cuda:12.8.1-runtime-ubuntu24.04 nvidia-smi
```

Recommended `%USERPROFILE%\.wslconfig` for a 32 GB PC (restart WSL with `wsl --shutdown` after editing):

```
[wsl2]
memory=24GB
processors=8
swap=8GB
```

## 3. Fast path: the installer script

**Windows with only Docker Desktop (no Python, Git or Node on the PC).** Download the ZIP from the GitHub page (Code → Download ZIP), unpack it, open PowerShell in the unpacked folder (Shift + right click → "Open PowerShell window here") and run one command at a time. Each line of the output starts with `[ok]`, `[warn]` or `[FAIL]`:

```
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 doctor
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 init
notepad .env
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 build
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 up
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 verify
```

`scripts\install.ps1` does exactly the same as `scripts/install.py` below (same steps, same checks, `-Pull` and `-NoGpu` instead of `--pull` and `--no-gpu`, `all` for everything) and works in the Windows PowerShell that comes with Windows. The commands below are for Linux or an AI assistant with a shell.


```
git clone https://github.com/HomenSAI/homensai-local-ai-lab.git local-ai-server
cd local-ai-server
python scripts/install.py doctor      # checks Docker, GPU-in-Docker, free ports and disk (it does not download anything; see below)
python scripts/install.py init        # creates .env, folders, placeholders, Docker network and volume
# now edit .env: set MODEL_DIR (and AI_CONSOLE_BIND_IP if you want LAN access), then put your models in place (section 4.5)
python scripts/install.py build       # builds the images (15-40 min the first time)
python scripts/install.py up          # starts everything
python scripts/install.py verify      # HTTP checks of every part
```

`python scripts/install.py all` runs doctor, init, build, up and verify in one go (use it after you edited `.env`). Every step can be repeated safely. Then open **http://localhost:8766/**.

- **GPU check and the 5.6 GB image.** `doctor` checks the GPU with the image `nvidia/cuda:12.8.1-runtime-ubuntu24.04`. If that image is not on the PC yet, `doctor` only warns and skips the check; ask the owner and run `python scripts/install.py doctor --pull` to download it (5.6 GB).
- **A PC without an NVIDIA GPU** (to try the console, the report and Git): add `--no-gpu` to `doctor`, `build`, `up` and `verify` (or to `all`). The gateway is not started and no model can be loaded; the console starts without requesting a GPU (`docker-compose.nogpu.yml`). If you start the console by hand, use `docker compose -f docker-compose.yml -f docker-compose.nogpu.yml up -d ai-console`.
- **Self-check of the repository:** `python -m unittest discover -s tests` (standard library only, no GPU or Docker needed) and `python scripts/make_manifest.py --check`.

## 4. Step-by-step installation

### 4.1 Prepare Docker

1. Install Docker Desktop, enable "Use the WSL 2 based engine", reboot if asked.
2. In Docker Desktop make sure the engine is **running and not paused** (the whale menu must not say "Resume").
3. Run the GPU check from section 2.

### 4.2 Get the code

```
git clone https://github.com/HomenSAI/homensai-local-ai-lab.git local-ai-server
cd local-ai-server
```

(or download the ZIP from GitHub and unpack it). All commands below are run from this folder.

### 4.3 Configure `.env`

```
python scripts/install.py init        # creates .env from .env.example if it does not exist
```

Open `.env` and set at least these variables:

| Variable | Meaning | Default / example |
|---|---|---|
| `MODEL_DIR` | Folder on the host that holds your `.gguf` files (read-only for containers) | `C:/AI/models` or `/data/models` |
| `MEDIA_DIR` | Scratch folder for the optional Whisper / image profiles | `./media` |
| `AI_CONSOLE_BIND_IP` | Address the console is published on, besides `127.0.0.1`. Put the LAN address of the PC to open it from other devices | `127.0.0.1` |
| `AI_CONSOLE_PASSWORD` | Optional. If set, the console asks for HTTP Basic authentication (any user name, this password) on everything except `/health`. **Set it before you open the console to the LAN.** `.env` is ignored by Git | empty (no password) |
| `AI_CONSOLE_ALLOWED_HOSTS` | Optional, comma separated. Extra host names you type in the browser (for example a name from your LAN DNS). `localhost` and IP addresses always work; any other `Host` gets `421` | empty |
| `GITEA_WEB_PORT`, `GITEA_SSH_PORT` | Ports of the local Git server | `3010`, `2222` |
| `GITEA_REPORT_OWNER`, `GITEA_REPORT_REPO` | Git user and repository for report versions | `reports-admin`, `model-test-reports` |
| `UPSTREAM_LLAMA_COMMIT`, `PRISM_LLAMA_COMMIT`, `WHISPER_CPP_COMMIT`, `STABLE_DIFFUSION_CPP_COMMIT` | Pinned source commits of the CUDA builds. Leave them unless you know why you change them. | pinned |
| `GATEWAY_PORT`, `HOST_BIND_IP`, `WHISPER_PORT`, `REPORT_PORT`, `AI_CONSOLE_PORT` | Optional port overrides | 8080, 127.0.0.1, 8082, 8765, 8766 |

The project needs no API keys. The only secret you may put into `.env` is the optional `AI_CONSOLE_PASSWORD`; `.env` is ignored by Git, never commit it or paste it into a chat or an issue.

### 4.4 Create folders, network and volume

`python scripts/install.py init` does all of this and is safe to repeat:
- folders `bench_results`, `report`, `results-db`, `media/images`, `benchmark/q4kv-20260929`, `secrets`;
- placeholder files that Docker bind mounts require (`report/report-data.json`, `BENCHMARK_RESULTS.csv`, `BENCHMARK_RESULTS.db`, `media/images/qwen-image-2.1-smoke.png`, `benchmark/q4kv-20260929/recommended-settings-q4kv-20260929.json`);
- Docker network `ai-net` and volume `llm-models-fast`;
- a check that `docker compose config` is valid.

By hand: `docker network create ai-net` and `docker volume create llm-models-fast`.

### 4.5 Put the models in place

The gateway reads models from the Docker volume `llm-models-fast` (an ext4 volume loads a model in 11-29 s, a Windows drive bind over WSL takes minutes). Your `MODEL_DIR` is used by the optional Whisper / image profiles and as the source from which you fill the volume.

1. **Find out which files are needed.** Every profile in `config/llama-swap.yaml` names its file after `--model`:
   ```
   grep -o '/models/[^ ]*\.gguf' config/llama-swap.yaml | sort -u
   ```
   The shipped profiles (context sizes were measured on an RTX 3080 / 10 GB):

   | Profile | Files (relative to the library root) | Context |
   |---|---|---|
   | Qwen3.5-9B-MTP-Q4_K_XL | `Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf` | 192K |
   | Qwen3.5-9B-MTP-Q4_K_XL-Vision | same file + `Qwen3/mmproj-F16.gguf` | 128K |
   | Qwen3.5-9B-Q5_K_S | `Qwen3/Qwen3.5-9B-Q5_K_S-4.60bpw.gguf` | 256K |
   | MiniCPM5-2B-Q8_0 | `MiniCPM5/MiniCPM5-2B-Q8_0.gguf` | 128K |
   | Spark-X2.5-4B-Q8_0 | `Spark/Spark-X2.5-4B-Q8_0.gguf` | 256K |
   | Ternary-Bonsai-2-27B-PTQ1_0 | `Ternary-Bonsai-2-27B-PTQ1_0.gguf` | 128K |
   | Qwen3-VL-8B-Instruct-Q4_K_M | `Qwen-Image-2.1/text_encoder/Qwen3VL-8B-Instruct-Q4_K_M.gguf` + `mmproj-Qwen3VL-8B-Instruct-F16.gguf` | 64K |
   | Ornith-1.5-9B-MTP | `top/Ornith-1.5-9B/Ornith-1.5-9B-Q4_K_M.gguf` | 128K |
   | Qwen3-Embedding-0.6B / 4B | `top/Qwen3-Embedding-0.6B/...-Q8_0.gguf`, `top/Qwen3-Embedding-4B/...-Q4_K_M.gguf` | 8K |
   | Qwen2.5-Coder-7B, Llama-3.1-8B, Gemma-3-12B | `cand/<name>/...Q4_K_M.gguf` | 64K |
   | MiMo-V2.6-Distill-Qwen-9B | `top/MiMo-V2.6-Distill-Qwen-9B/...Q4_K_M.gguf` | 256K |

2. **Download only what you want.** `MODELS.md` lists the Hugging Face repositories, revisions and SHA-256 sums of the models the author pinned. For a profile whose source is not listed, search the exact file name on Hugging Face, read the model card, and check the license (some licenses restrict commercial use or require attribution). **You do not need all models**: delete the profiles you do not want from `config/llama-swap.yaml` (a profile whose file is missing is shown in the console as "file not found").
3. **Check integrity**: compare `sha256sum <file>` with `MODELS.md` / the model page.
4. **Copy the files into the volume**, keeping the sub-folders of the table above (example for one file; repeat per file or per folder):
   ```
   docker run --rm -v llm-models-fast:/models -v "C:/AI/models:/src:ro" alpine sh -c "mkdir -p /models/Qwen3 && cp /src/Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf /models/Qwen3/"
   ```
   On Git Bash for Windows prefix the command with `MSYS_NO_PATHCONV=1`, or use PowerShell.
5. **Start with one small model** to test the whole chain (for example `MiniCPM5-2B-Q8_0`, 2.7 GB), then add the rest.

### 4.6 Build the images

`python scripts/install.py build` runs the commands below (one build at a time to keep RAM use low; the CUDA compilations take 15-40 minutes each the first time, later builds use the cache):

```
docker compose --profile build build build-upstream      # local/ai-server-upstream:local  (llama.cpp with CUDA, pinned commit)
docker compose --profile build build build-bonsai        # local/ai-server-bonsai:local    (PrismML fork, only for the Bonsai model)
docker compose --profile gateway build llama-swap-gateway  # local/ai-server-llama-swap:260 (llama-swap v260, SHA-256 checked)
docker compose build ai-console report-versioner         # console and versioner images
```

If you do not need the Bonsai model, build only `build-upstream`, set `PRISM_IMAGE=local/ai-server-upstream:local` as a build arg of `llama-swap-gateway` (or `--build-arg`) and remove the Bonsai profile from `config/llama-swap.yaml`.

### 4.7 Start

```
python scripts/install.py up
```

which is the same as:

```
docker compose up -d ai-console report-builder stats-report gitea report-versioner
docker compose --profile gateway up -d llama-swap-gateway
```

The gateway needs about 30 s to become healthy and starts with **no model loaded** (the first request to a model loads it, up to a minute). Open **http://localhost:8766/**.

### 4.8 Set up the Git server for report versions

```
python scripts/setup_git.py
```

It starts Gitea, creates the administrator, an access token for the versioner, an SSH key and the private repository, and starts `report-versioner`. Passwords and keys are written to `secrets/` only (ignored by Git, never published). Web UI: `http://localhost:3010/` (login in `secrets/gitea-admin.txt`). Clone the versions:

```
git clone -c core.sshCommand="ssh -i secrets/id_ed25519 -o StrictHostKeyChecking=accept-new -p 2222" ssh://git@127.0.0.1:2222/reports-admin/model-test-reports.git
```

### 4.9 Access from other devices on your network (optional)

1. In `.env` set `AI_CONSOLE_PASSWORD=<a long password>` and `AI_CONSOLE_BIND_IP=<LAN address of this PC>` (add `AI_CONSOLE_ALLOWED_HOSTS` if you use a host name), then recreate the console: `docker compose up -d --force-recreate --no-deps ai-console`.
2. Open the port in the firewall for your own subnet only (PowerShell as administrator):
   ```
   New-NetFirewallRule -DisplayName "AI console 8766 (LAN)" -Direction Inbound -Protocol TCP -LocalPort 8766 -RemoteAddress 192.168.0.0/24 -Profile Any -Action Allow
   ```
   (replace the subnet by yours). Never expose the console to the internet, with or without a password: Basic authentication sends the password unencrypted, so use it inside a trusted network or behind a VPN / TLS proxy.

## 5. Optional components

### Open WebUI (chat interface)

```
docker run -d --name open-webui --restart unless-stopped -p 3000:8080 -v open-webui:/app/backend/data ghcr.io/open-webui/open-webui:main
docker network connect local-ai-server_default open-webui
powershell -File scripts/configure-openwebui-gateway.ps1
```

The script registers the gateway `http://llama-swap-gateway:8080/v1` as the OpenAI connection. Open WebUI has its own license terms; see `legal/NOTICE-THIRD-PARTY.md`.

### Telemetry exporter

```
cd hermes-telemetry
docker compose -f compose.yaml up -d --build
```

Publishes `/metrics` and `/health` on `127.0.0.1:9835` (set `TELEMETRY_BIND_IP` to publish on the LAN). Needs the networks `ai-net` and `local-ai-server_default` (created by `init` and the first `up`).

### Video generation: the separate project "Video Studio"

Video generation (Wan 2.1 1.3B + ComfyUI, storyboard from an idea, video reports) is **not part of this project any more**: it is a project of its own, **Video Studio** (own repository, own console on port 8767, own installation guide). The two projects work side by side:
- the header of this console has a link "Video generation" that opens Video Studio (`http://HOST:8767/`);
- Video Studio joins the Docker network `local-ai-server_default` of this project to reach the gateway (it unloads the gateway models before a video and drafts storyboards with your local LLM);
- this console refuses to start an LLM while the ComfyUI container of Video Studio holds the GPU (container name `video-generation-comfyui-video-1`).
Install this project first, then Video Studio.

### Speech recognition and image generation profiles

`docker compose --profile whisper build whisper` and `--profile qwen-image build qwen-image` build the optional Whisper (speech to text) and Qwen-Image profiles; they need their model files under `MODEL_DIR` (see `.env`, `WHISPER_MODEL`, `QWEN_IMAGE_*`) and are not started by default.

## 6. Verification

`python scripts/install.py verify` runs these checks; you can also run them by hand:

| What | Command | Expected |
|---|---|---|
| GPU in Docker | `docker run --rm --gpus all nvidia/cuda:12.8.1-runtime-ubuntu24.04 nvidia-smi` | table with your GPU |
| Gateway | `curl http://localhost:8080/v1/models` | JSON list of profiles |
| Console | `curl http://localhost:8766/health` | `{"ok": true}` |
| Model catalog | `curl http://localhost:8766/api/models` | models with `"exists": true` for the files you copied |
| Status | `curl http://localhost:8766/api/status` | `docker_available: true` |
| Report | open `http://localhost:8766/report/` | page loads, footer shows the license |
| Old address | `curl -I http://localhost:8765/` | `301` to port 8766 |
| Git | `curl http://localhost:3010/api/healthz` | 200 |
| Containers | `docker ps --format "{{.Names}} {{.Status}}"` | `healthy` for console, gateway, report-builder, gitea, versioner |
| First model | console, press **Start** on a model, then chat | answer appears; `curl localhost:8080/running` lists the model |

If `AI_CONSOLE_PASSWORD` is set, add `-u any:PASSWORD` to the console `curl` calls (not to `/health`). On a PC without a GPU use `python scripts/install.py verify --no-gpu`: the gateway checks are skipped.

## 7. Using the console

- **Language**: RU / EN / DE switch in the header (remembered in the browser).
- **1 Status** shows what is in memory now; **2 Start** lists models with Start / Stop (Start loads the model into video memory, Stop unloads); the model cards show quantization, context, file, tuned parameters.
- **3 Chat** talks to the selected model through the gateway (images are accepted by vision models). **Unload timer** unloads all models after N seconds.
- **Test results** show every model with all tests, sortable by any test, with a progress bar of the running test, an estimate of the time left until all tests finish, and the stage list.
- **Video generation ↗** in the header opens the separate project Video Studio.
- **Report and results** (`/report/`): full tables, charts, recommendations, downloads.

## 8. Test results, reports and Git versions

- Benchmarks write `bench_results/results*.jsonl` (one JSON object per line: `model`, scores, speeds, ...). The report builder merges them without ever deleting an older result into SQLite (`results-db/llm-results.sqlite`) and builds `report/live-data.json`. The test runners that produced the published results are in `benchmarks/` and run in Docker: `docker compose --profile bench up -d --build bench-runner` (see `benchmarks/README.md`); any other tool that writes the same files works too.
- `report-versioner` commits `results/`, `tables/`, `report/` and a JSON dump of the database to Gitea every time something changes: commits are `vNNNN`, finished stages get `stage-<id>-done`, the end of all tests gets `final-<date>`. History is never rewritten. Restore an old report with `git checkout v0042`.
- The stage plan and the overall estimate come from `scripts/build_live_report.py` (`DEFAULT_PLAN`) and can be overridden with `bench_results/benchmark_plan.json`.

## 9. Maintenance: update, back up, remove

- **Update the code**: `git pull`, then `docker compose up -d --build ai-console report-versioner`. After editing `config/llama-swap.yaml` run `docker compose --profile gateway up -d --force-recreate --no-deps llama-swap-gateway` (a single-file bind mount does not pick up a replaced file otherwise).
- **Back up**: `.env`, `config/`, `bench_results/`, `results-db/`, the Docker volumes `gitea-data`, `gitea-config`, `ai-console-state`, and `secrets/`. Models can be downloaded again.
- **Stop everything**: `docker compose --profile gateway down`.
- **Remove including data** (irreversible): `docker compose --profile gateway down -v` (this deletes the volumes except the external `llm-models-fast`); remove the models volume yourself with `docker volume rm llm-models-fast`.

## 10. Linux / macOS notes

- **Linux**: install Docker Engine, the NVIDIA driver and the NVIDIA Container Toolkit, check `docker run --rm --gpus all ... nvidia-smi`. The compose files are platform neutral; use `python scripts/install.py ...` and forward-slash paths in `.env`. The `.ps1` helper scripts are optional PowerShell conveniences. This project was developed and tested on Windows 10 + Docker Desktop; Linux is expected to work but has not been tested by the author.
- **macOS**: there is no CUDA, so the GPU images do not work. Not supported.
- If the console cannot see the Docker socket on Linux, check that `/var/run/docker.sock` exists (the console uses it to list containers and to read the status of `llama-server`).

## 11. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Docker Desktop is manually paused` | Resume it from the whale menu; `docker desktop` CLI cannot unpause. |
| `port is already allocated` | Another program uses the port; change `GITEA_WEB_PORT`, `AI_CONSOLE_PORT`, ... in `.env` (the doctor lists busy ports). |
| `could not select device driver "nvidia"` | GPU not available to Docker: update the NVIDIA driver, enable WSL2 integration, restart Docker Desktop. |
| `docker compose` complains about a missing bind source | Run `python scripts/install.py init` (creates the placeholder files and folders). |
| Model card says "file not found" | The file is not in the volume `llm-models-fast` under the exact sub-path of the profile (section 4.5). |
| First answer takes a minute | The gateway is loading the model into video memory; later answers are fast. |
| Out of video memory | Another program or the video container holds VRAM; the console diagnostics name the holders. Use a smaller context or a smaller quantization. |
| Git Bash mangles `/models` paths | Prefix the command with `MSYS_NO_PATHCONV=1` or use PowerShell. |
| Console shows Russian text in EN/DE | Texts that come from your own data (prompts, model answers, logs) are never translated. New interface texts must be added to `console/i18n-dict.js` (`node scripts/check_i18n.js de` lists missing ones). |
| Report page empty | Normal until the first `bench_results/results*.jsonl` exists. |
| `doctor` says the CUDA test image is not downloaded | It does not download 5.6 GB on its own. Ask the owner, then `python scripts/install.py doctor --pull`, or use `--no-gpu` on a PC without a GPU. |
| `docker compose up` fails with "could not select device driver" / "no known GPU vendor" | The PC has no GPU visible to Docker. Use `python scripts/install.py up --no-gpu`. |
| A script or `curl` gets `415`, `421`, `403` or `401` from the console | The console checks every request: `POST` needs `Content-Type: application/json`, the `Host` must be `localhost` or an IP (or listed in `AI_CONSOLE_ALLOWED_HOSTS`), a password may be required (`curl -u any:PASSWORD`). See [API.md](API.md). |
| The browser shows `421` after you opened the console by a host name | Add the name to `AI_CONSOLE_ALLOWED_HOSTS` in `.env` and recreate the console. |

## 12. Security

- The gateway has **no authentication**; the console has an optional password (`AI_CONSOLE_PASSWORD`). Keep both on `127.0.0.1` or a trusted subnet; never publish ports 8766 / 8080 / 3010 to the internet.
- The console refuses foreign `Host` names and cross-site or non-JSON `POST` requests, and sends security headers; so a web page you open in the same browser cannot control the models.
- The console container mounts `/var/run/docker.sock`; the `read_only` flag does not protect it. The console sends only one fixed kind of command through it and runs with all capabilities dropped, but treat console access as access to Docker on this PC. Details: [SECURITY.md](../SECURITY.md).
- Gitea has registration disabled and requires sign-in; its password and token live in `secrets/` only.
- Model files come from third parties: verify SHA-256 and read their licenses.
- Report problems privately, see [SECURITY.md](../SECURITY.md).

## 13. License and attribution

Results, reports and texts: **CC BY 4.0**, credit "homensai.com (https://homensai.com)". Code: **MIT**. Third-party software and models keep their own licenses: see `legal/NOTICE-THIRD-PARTY.md`. This is not legal advice.
