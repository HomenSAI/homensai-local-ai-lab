# Architecture

```
 browser ──► console :8766 (Python, stdlib only) ──► gateway :8080 (llama-swap) ──► llama-server (one model in VRAM)
                │  │                                      ▲
                │  └─ docker.sock (container list; status of llama-server via a fixed `docker exec curl`; refuses an LLM start while Video Studio holds the GPU)
                │
                ├─ /report/  ◄── report/live-data.json ◄── report-builder ◄── bench_results/results*.jsonl
                │                                              └──► results-db/llm-results.sqlite (never loses old results)
                └─ /legal/   license and third-party notices

 report-versioner ──(every minute, only on change)──► gitea :3010  tags v0001..., stage-<id>-done, final-<date>
```

## Components

| Path | Role |
|---|---|
| `docker-compose.nogpu.yml` | Override for a machine without an NVIDIA GPU: the console starts without requesting one (`install.py up --no-gpu`). |
| `docker-compose.yml` | All services. Profiles: `gateway` (llama-swap), `build` (base image builders), `whisper`, `qwen-image`, `media-tools` (optional). |
| `Dockerfile.upstream` / `.bonsai` | llama.cpp (CUDA 12.8, architecture 86) and the PrismML fork, built from pinned commits. |
| `Dockerfile.llama-swap` | llama-swap v260 (SHA-256 checked) on top of the upstream image, with the Bonsai runtime copied to `/opt/prism`. |
| `config/llama-swap.yaml` | One profile per model: file, context size, KV-cache type, speculative decoding, TTL. Edit it to add or remove models. |
| `console/` | `container_server.py` (HTTP server, Docker/gateway access), `security.py` (Host / Origin / password checks and security headers), `tests_feed.py` (test table feed); static `index.html`, `app.js`, `app.css`, `shell.js` (theme button, author footer); `i18n.js` + `i18n-dict.js` (RU/EN/DE); `style/`: HomenS.AI Style 1.6.0 (stylesheet, fonts, logo, scripts), served at `/style/`. |
| `report/` | Static report page; `live-data.json` and `live-status.json` are written by the builder. `progress.html` + `progress.js`: test progress (stage plan from `live-data.json`) in the process view A/B/C of HomenS.AI Style; `contact.html` + `contact.js`: the contact block of the style (required in every HomenS.AI project). |
| `scripts/build_live_report.py` | Collects result files, merges them into SQLite (`raw_rows`, `results`, `history`, `model_scores`), builds the stage plan, the progress and the time-left estimate. |
| `scripts/versioner.py`, `scripts/setup_git.py` | Report versioning into Gitea and its one-time setup. |
| `scripts/install.py` | doctor / init / build / up / verify (`--no-gpu`, `doctor --pull`). |
| `scripts/build_site.py` | Builds the documentation site (GitHub Pages) in HomenS.AI Style: every Markdown file becomes the `.html` page next to it (root `README.md` → `index.html`), `site/` holds its CSS, script and the contact pages; `--check` for CI. |
| `scripts/make_manifest.py` | Writes / checks `MANIFEST.json` (size and SHA-256 of every tracked file). |
| `tests/` | Standard-library unit tests: console security, report builder, public results, installer, manifest (`python -m unittest discover -s tests`). |
| `hermes-telemetry/` | Small metrics exporter (GPU, llama). |
| `benchmarks/`, `docker/bench-runner/` | Test runners of the published results and their container (profile `bench`); they write `bench_results/`. See `benchmarks/README.md`. |
| `legal/` | CC BY-NC 4.0 (results), PolyForm Noncommercial 1.0.0 (code), third-party notices. |

## Design decisions

- **One model at a time.** 10 GB of video memory fits one large model; llama-swap unloads the old model before loading the next. The console blocks LLM start while video generation holds the GPU.
- **Model volume.** Models are served from a Docker (ext4) volume because a Windows-drive bind over WSL is ~10x slower to load.
- **No third-party Python packages** in the console, builder and versioner: they run on `python:3.12-slim` / `alpine` with the standard library only.
- **Results are never overwritten.** Different tests (general, German, context, STEM, ...) are kept apart; the SQLite archive keeps history; Git keeps every report version.
- **Interface text is Russian in the source** and translated on the fly by `i18n.js`; user data (prompts, answers, logs) is marked `data-no-i18n` and never translated. `scripts/check_i18n.js` lists untranslated fragments.
- **Single-file bind mounts** (config files) do not follow a replaced file: recreate the service after editing them.

## Related project

**Video Studio** (separate repository): its own console (port 8767) plus the ComfyUI + Wan 2.1 container. It joins this project's Docker network `local-ai-server_default` to call the gateway (unload models before a video, storyboard with the local LLM). This console only checks whether the ComfyUI container runs, to avoid starting an LLM while the GPU is busy.
