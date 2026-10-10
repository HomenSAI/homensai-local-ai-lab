# Local AI Server

**Run local language models on one NVIDIA GPU, with a web console, automatic test reports, video generation and versioned results.**
Languages: English · [Русский](README.ru.md) · [Deutsch](README.de.md)

Author: **Serhii Khomenko** · [homensai.com](https://homensai.com) · info@homensai.com · Results & reports: CC BY 4.0 (credit required) · Code: MIT

## Purpose

This project is a **lab for testing many local AI models on one computer**: every model is started through one gateway on a single GPU, run through the same automated tests, and the results are collected in one report. The measured results are in the companion repository [rtx3080-local-ai-benchmarks](https://github.com/HomenSAI/rtx3080-local-ai-benchmarks).

## What it is

A self-hosted stack for a single-GPU workstation (developed on an RTX 3080 with 10 GB, Windows 10 + Docker Desktop):

- **Gateway** ([llama-swap](https://github.com/mostlygeek/llama-swap) + [llama.cpp](https://github.com/ggml-org/llama.cpp)): an OpenAI-compatible API on port 8080 that loads one model at a time and swaps on demand.
- **Console** (port 8766, **English / Deutsch / Русский**): model catalog with Start/Stop, chat, live GPU telemetry, diagnostics, unload timer, test results with progress and time-left estimate, and the **report** page.
- **Reports**: benchmark results become a live report and a SQLite archive that never loses older results.
- **Version history**: a local Gitea keeps every version of the reports (tags `v0001`..., `stage-<id>-done`, `final-<date>`).
- **Run by an AI assistant:** the server is built to be installed, started and supervised by Claude or ChatGPT (an agent with shell access): hand it the repository, it reads `AGENTS.md` / `CLAUDE.md`, installs, runs the tests, checks the results. The server works without one. See [docs/AI_OPERATOR.en.md](docs/AI_OPERATOR.en.md).
- **Published results:** [results-public/RESULTS.md](results-public/RESULTS.md) - 23 models, 15 admitted to the later stages; how they were produced (server core -> Claude as supervisor -> results): [docs/METHODOLOGY.en.md](docs/METHODOLOGY.en.md).
- **Related project:** video generation (Wan 2.1 + ComfyUI, storyboard drafted by your local LLM) is its own project, **Video Studio** (separate repository, port 8767); this console links to it.

## Quick start

```
git clone https://github.com/HomenSAI/homensai-local-ai-lab.git local-ai-server
cd local-ai-server
python scripts/install.py doctor     # Docker, GPU in Docker, ports, disk
python scripts/install.py init       # .env, folders, placeholders, network, volume
#  edit .env (MODEL_DIR) and put your .gguf models in place - see the guide, section 4.5
python scripts/install.py build      # first build 15-40 min
python scripts/install.py up
python scripts/install.py verify
```

Open **http://localhost:8766/**.

## Documentation

| | English | Русский | Deutsch |
|---|---|---|---|
| Full installation guide | [INSTALL.en.md](docs/INSTALL.en.md) | [INSTALL.ru.md](docs/INSTALL.ru.md) | [INSTALL.de.md](docs/INSTALL.de.md) |
| Overview | this file | [README.ru.md](README.ru.md) | [README.de.md](README.de.md) |

More: [why it was built this way](docs/DESIGN.en.md) · [HTTP interfaces](docs/API.md) · [result file format](docs/RESULTS_FORMAT.md) · [code provenance](PROVENANCE.md) · [repository page texts](docs/GITHUB_REPO.md) · [architecture](docs/ARCHITECTURE.md) · [security policy](SECURITY.md) · [contributing](CONTRIBUTING.md) · [changelog](CHANGELOG.md) · [model inventory](MODELS.md) · [license files](legal/)

## Requirements in one line

NVIDIA GPU with 8 GB+ video memory, 16-32 GB RAM, ~25 GB disk for images plus 50-200 GB for models, Docker Desktop (WSL2) with GPU support, Python 3.10+, Git. Linux with the NVIDIA Container Toolkit should work (untested by the author); macOS is not supported (no CUDA).

## Not included

Model weights (download them yourself and respect their licenses), your own test results (`bench_results/`, written when you run the tests), videos, secrets. The test runners are in [benchmarks/](benchmarks/README.md); the published results are in [rtx3080-local-ai-benchmarks](https://github.com/HomenSAI/rtx3080-local-ai-benchmarks). The gateway has **no password** and the console's password (`AI_CONSOLE_PASSWORD`) is optional: use both on `127.0.0.1` or a trusted network only, never on the internet. The console also refuses cross-site requests and foreign `Host` names ([SECURITY.md](SECURITY.md)).

## License and attribution

- Results, reports and texts: **[CC BY 4.0](legal/LICENSE-RESULTS-CC-BY-4.0.md)** - you may use and share them, **a link to the author is mandatory**: `Data: homensai.com (https://homensai.com), CC BY 4.0`.
- Code: **[MIT](LICENSE)** with the copyright notice kept.
- Third-party software and models keep their own licenses: [NOTICE-THIRD-PARTY.md](legal/NOTICE-THIRD-PARTY.md). Product names are trademarks of their owners; this project is not affiliated with or endorsed by them.
