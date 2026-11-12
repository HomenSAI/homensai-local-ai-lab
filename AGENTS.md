# Instructions for AI agents (Codex / ChatGPT agents, Claude Code and other coding assistants)

This repository is **Local AI Server**: a model gateway (llama-swap + llama.cpp) for one NVIDIA GPU, a console with test results and reports, and a Git versioner. It is meant to be **installed, started and supervised by an AI assistant**; you are that assistant. Humans own the decisions listed under "Ask first".

Read first: `docs/AI_OPERATOR.en.md` (your role and the supervision loop), `docs/INSTALL.en.md` (installation), `docs/API.md` (interfaces), `docs/RESULTS_FORMAT.md` (result files), `docs/METHODOLOGY.en.md` (how the published results were made). Other languages of the same files: `.ru.md`, `.de.md`.

## Install (summary)

On the owner's Windows PC only Docker Desktop is installed (no Python, Git or Node): use `powershell -ExecutionPolicy Bypass -File scripts\install.ps1 doctor | init | build | up | git | verify` (`-NoGpu`, `-Pull`) there. On Linux or in your own shell use the Python installer:

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

Run `python -m unittest discover -s tests` and `python scripts/make_manifest.py --check` (rewrite with `python scripts/make_manifest.py` after you changed files). After changing a Markdown file, rebuild the documentation site with `python scripts/build_site.py --style <folder of homensai-style 1.8.0 or newer>` (it writes `site/content/` and `site/site.json` and runs the site builder of the style core; CI checks it with `--check`; never edit `site/*.html` or the redirect pages by hand). Every site page exists in English, Russian and German: a new or changed document needs all three Markdown files. Never weaken the checks in `console/security.py` (Host / Origin / Content-Type / password) and the fixed `docker exec` form in `container_server.py`; new `POST` endpoints must go through `Handler.guarded`, and every change of them needs a test. Standard library only in `console/`, `scripts/build_live_report.py`, `scripts/versioner.py`; keep the three interface languages complete (`node scripts/check_i18n.js de` and `en`); bump `VERSION` and `CHANGELOG.md` for a release; license: code PolyForm Noncommercial 1.0.0, results and texts CC BY-NC 4.0 (noncommercial use only) with credit to <https://homensai.com>.

<!-- HSAI-AI-CONTEXT-CACHING-POLICY:BEGIN -->
## Mandatory AI preflight and token-cost optimization (owner instruction, 2026-11-12)

Before substantive work, map the **complete tracked project structure** and active state; read README, root/nested AGENTS and CLAUDE rules, architecture/status/handoff/decisions, manifests, dependencies, CI, tests, configuration and relevant sources **end-to-end**. Distinguish current files from archives/generated/vendor/sensitive content. Reuse a concise, version-aware project context map; refresh changing facts. Never blindly paste an entire repository into a model prompt.

**Audit before coding:** classify stable vs dynamic context (tools, instructions, common documents/examples, conversations, results). Reuse compact summaries, targeted reads and diffs; plan model choice, token budget, prompt caching and measurements. For direct Claude Messages API, enable top-level `cache_control: {"type":"ephemeral"}` for reusable conversation prefixes or explicit breakpoints at the **end of stable prefixes**; keep changing content after them, order `tools → system → messages`, respect 4 slots, 20-block lookback, model minimum lengths and invalidations. Default TTL 5m; use 1h only when justified by measured reuse economics. Measure `cache_creation_input_tokens`, `cache_read_input_tokens`, baseline costs/latency, and correctness; disable ineffective caching. Never cache/expose secrets unnecessarily.

**Claude Code is not the same as an API client:** use only its supported built-in context/cache behavior; these repository rules do not raise subscription limits. If a repo has no qualifying Claude API calls, mark API caching **not applicable**, and optimize context retrieval instead. Before finishing, report inspected sources, caching opportunities/implementation, real metrics vs estimates, tests and limitations. Follow existing repo safety/branch/release rules.

Canonical policy: https://github.com/HomenSAI/homensai-core/blob/main/docs/AI_CONTEXT_EFFICIENCY_POLICY.md
<!-- HSAI-AI-CONTEXT-CACHING-POLICY:END -->
