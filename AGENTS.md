# Instructions for AI agents (Codex / ChatGPT agents, Claude Code and other coding assistants)

This repository is **Local AI Server**: a model gateway (llama-swap + llama.cpp) for one NVIDIA GPU, a console with test results and reports, and a Git versioner. It is meant to be **installed, started and supervised by an AI assistant**; you are that assistant. Humans own the decisions listed under "Ask first".

Read first: `docs/AI_OPERATOR.en.md` (your role and the supervision loop), `docs/INSTALL.en.md` (installation), `docs/API.md` (interfaces), `docs/RESULTS_FORMAT.md` (result files), `docs/METHODOLOGY.en.md` (how the published results were made). Other languages of the same files: `.ru.md`, `.de.md`.

## Install (summary)

```
python scripts/install.py doctor      # fix what it reports before going on (it never downloads the 5.6 GB CUDA image: ask first, then `doctor --pull`)
python scripts/install.py init        # creates .env - ask the human for MODEL_DIR and the network address
python scripts/install.py build       # 15-40 minutes the first time
python scripts/install.py up
python scripts/install.py verify      # every line must be [ok]
```

No NVIDIA GPU on this PC: add `--no-gpu` to doctor / build / up / verify (console, report and Git only). Models: section 4.5 of `docs/INSTALL.en.md`. Do not invent download sources; verify SHA-256; start with one small model.

## Operate and supervise

- Console `http://localhost:8766/` (report at `/report/`), gateway `http://localhost:8080/v1` (OpenAI-compatible), local Git `http://localhost:3010/`.
- One model in video memory at a time. Never start two GPU jobs together. The separate project Video Studio (port 8767) also needs the whole GPU.
- Write test results as appended JSON lines to `bench_results/results_*.jsonl` and progress to `bench_results/<stage>.log` exactly as in `docs/RESULTS_FORMAT.md`; the report, the versions in Git and the time estimates follow automatically.
- After every test check the numbers: empty or truncated answers, `finish_reason` other than `stop`, collapsed speed (CPU fallback), results that a repeat contradicts, tasks that every model fails (suspect the checker first). Repeat suspicious runs, then report to the human as a short table.
- `python scripts/make_public_results.py` writes the publishable summary (`results-public/`); it contains no prompts or answers.

## Ask first (never decide alone)

Deleting files or Docker volumes, downloading the 5.6 GB CUDA test image (`doctor --pull`), choosing the console password (`AI_CONSOLE_PASSWORD`), changing network addresses or opening ports, downloads larger than 1 GB, publishing anything (Git push, release), editing `.env` values that the human set.

## Never

Expose ports 8766, 8080, 3010, 8767 to the internet; put secrets, tokens or personal data into files that go to Git (`secrets/` and `.env` are ignored); edit or delete earlier result rows (append new ones); skip checks with `--no-verify`-style shortcuts.

## Code rules (if you change this repository)

Run `python -m unittest discover -s tests` and `python scripts/make_manifest.py --check` (rewrite with `python scripts/make_manifest.py` after you changed files). Never weaken the checks in `console/security.py` (Host / Origin / Content-Type / password) and the fixed `docker exec` form in `container_server.py`; new `POST` endpoints must go through `Handler.guarded`, and every change of them needs a test. Standard library only in `console/`, `scripts/build_live_report.py`, `scripts/versioner.py`; keep the three interface languages complete (`node scripts/check_i18n.js de` and `en`); bump `VERSION` and `CHANGELOG.md` for a release; license: code MIT, results and texts CC BY 4.0 with credit to <https://homensai.com>.
