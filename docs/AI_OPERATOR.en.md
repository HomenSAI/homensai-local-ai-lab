# Running the server with an AI supervisor (Claude or ChatGPT)

Other languages: [Русский](AI_OPERATOR.ru.md) · [Deutsch](AI_OPERATOR.de.md)

## The idea

This project is built to be **installed, started and supervised by an AI assistant** - Claude or ChatGPT. You do not have to follow the installation guide by hand: you hand the repository (or just `docs/INSTALL.en.md`) to the assistant, it performs the installation, starts the tests, watches the results, judges whether they are correct and keeps the Git history of the reports in order.

- **The server works on its own.** The gateway, the console, the report builder and the Git versioner run without any AI; the AI is only the operator.
- **The AI is the supervisor.** It decides which tests to run on which models, starts them, checks that the numbers are plausible (timeouts, empty answers, outliers, models that fell back to CPU), repeats suspicious runs and writes the conclusions. The server does not contain a second, built-in judge on purpose (see [DESIGN.en.md](DESIGN.en.md)).
- **Nothing special is needed on the server side** - there is no plug-in to install. The supervisor uses what is already there: the shell on this PC, the REST API of the console ([API.md](API.md)), the OpenAI-compatible gateway on port 8080, the result files ([RESULTS_FORMAT.md](RESULTS_FORMAT.md)) and the Git repository of report versions.

## What the assistant needs

The assistant must be able to **run commands on the machine where the server lives** (or reach it through a secure channel). Typical ways:

| Assistant | How it gets access | Notes |
|---|---|---|
| **Claude Code** (CLI / desktop / IDE) | works in the cloned repository folder and runs shell commands; reads `CLAUDE.md` automatically | the simplest option |
| **Claude Desktop / Claude with local tools** | local file and command tools (for example an MCP server for the file system and shell that you enable yourself) | you decide which folders and commands are allowed |
| **ChatGPT agents with local access** (Codex CLI / desktop agent) | works in the cloned folder; reads `AGENTS.md` automatically | same idea |
| **A ChatGPT / Claude browser chat without local access** | cannot reach `localhost`; it can only *advise* while you paste outputs | to give it access you would need a tunnel - **not recommended**, the console has no password |

If you do open the server to a remote assistant, put it behind an authenticating tunnel or VPN and give it read-only access first. Never publish ports 8766, 8080, 3010 or 8767 to the internet as they are.

## Hand-over: the prompt to give the assistant

Open the assistant in the repository folder (or attach `docs/INSTALL.en.md`) and say:

```
You are the installer and supervisor of this "Local AI Server" project (read AGENTS.md / CLAUDE.md, docs/INSTALL.en.md, docs/AI_OPERATOR.en.md).
1. Install it on this machine following docs/INSTALL.en.md: run `python scripts/install.py doctor`, fix what it reports, then init, build, up, verify. `doctor` never downloads the 5.6 GB CUDA test image by itself: ask me before `doctor --pull`. On a PC without an NVIDIA GPU use `--no-gpu`.
   Ask me before anything destructive, before downloading files larger than 1 GB, and for every choice that I must make (model folder, network address).
2. Put the models I name into the Docker volume as described in section 4.5. Do not invent download sources; verify SHA-256.
3. Run the tests I ask for on the models I ask for (see docs/RESULTS_FORMAT.md for the result files). Run one model at a time; the gateway swaps models by itself.
4. Supervise: after each test check that the results are plausible, repeat suspicious runs, and report to me in a short table: model, test, score, speed, anything odd.
5. Never expose the console or the gateway to the internet, never write secrets into files that go to Git, never delete my data.
```

## How the console treats scripts and assistants

The console checks every request ([API.md](API.md), [SECURITY.md](../SECURITY.md)). Your commands must comply, and a refusal is information, not an obstacle to get around:

- `POST` calls need `-H "Content-Type: application/json"` (also without a body), for example `curl -X POST http://localhost:8766/api/start -H "Content-Type: application/json" -d '{"model_key":"..."}'`. `415` means the header is missing.
- If the human set `AI_CONSOLE_PASSWORD`, ask them for it and use `curl -u any:PASSWORD`; never write it into a file that goes to Git, into a result file or into a report. `401` means a password is required.
- `421` means a host name that is not allowed: use `localhost` or the IP address; ask the human before adding names to `AI_CONSOLE_ALLOWED_HOSTS`.
- Do not disable these checks, do not edit `console/security.py` or the password to get a call through; report the refusal to the human.

## The supervision loop (what the assistant does)

1. **Check health**: `python scripts/install.py verify`, `curl localhost:8766/api/status` (`issues` must be empty; "gateway stopped" is expected only while tests hold the GPU).
2. **Pick models and tests** with the human; make sure the model files exist (`curl localhost:8766/api/models` -> `exists: true`).
3. **Run a test**: send prompts to `http://localhost:8080/v1/chat/completions` with the model alias (the gateway loads it, the first answer takes up to a minute), measure, and append one JSON line per model and test to `bench_results/results_<suite>.jsonl` in the documented format. Write a progress line and a finish marker to `bench_results/<suite>.log` (`PROGRESS i/n`, `<NAME>-FINISHED`) so the console shows the stage, a progress bar and the time left.
4. **Judge the result**: compare with the other models and with earlier results (`/api/tests`), look for: empty or truncated answers, `finish_reason` other than `stop`, speed that collapsed (CPU fallback; check `vram` and `host_free_min_gb`), scores that contradict a repeat, tasks that every model fails (probably a wrong checker, not a weak model).
5. **Record**: the report builder and the versioner do it automatically (SQLite archive, `vNNNN` tags in the local Gitea). Add the conclusions to `bench_results/report.md` (the first lines appear on the report page).
6. **Report to the human**: a table plus the list of suspicious findings and what was repeated.

## Rules for the assistant

- One model in video memory at a time; do not start a second GPU job while a test or a video renders.
- Never edit or delete results of earlier runs; add new rows (the archive keeps old values, but the history is the evidence).
- Do not put prompts or answers that contain personal data into Git; the repository is meant to be shareable (results are CC BY 4.0 with credit to <https://homensai.com>).
- Ask the human before: deleting files or volumes, changing `.env` network addresses, opening ports, downloading large files, publishing anything.
- Do not weaken the console's protection (Host / Origin / password checks, the fixed `docker exec` form) and never publish the password; if a call is refused, say so.
- A model that did not load is recorded as `{"model": ..., "load_ok": false, "error": "short reason"}` (no paths in `error`); it is shown as failed, not hidden. If a result row gets `invalid_items`, the checker produced impossible scores: fix the checker and append a new row ([RESULTS_FORMAT.md](RESULTS_FORMAT.md)).
- If a command fails, read the log (`docker logs <container>`), fix the cause, do not retry blindly.
