# Why it was built this way

Other languages: [Русский](DESIGN.ru.md) · [Deutsch](DESIGN.de.md) · Structure: [ARCHITECTURE.md](ARCHITECTURE.md)

Each decision below lists the reason and where the value lives. Values marked *measured* come from our own runs on an RTX 3080 (10 GB) and are meant to be re-measured on other hardware.

| Decision | Why | Where |
|---|---|---|
| **One model in video memory at a time** | 10 GB hold one 7-27B model with a long context; two models would force tiny contexts or CPU fallback. llama-swap unloads the old model before it loads the next | `config/llama-swap.yaml` (`ttl`, `unloadTimeout`) |
| **llama-swap in front of llama.cpp** | gives an OpenAI-compatible API on one port, loads models on demand and unloads them after an idle time, so any chat client or AI assistant can use the server without knowing about processes | `Dockerfile.llama-swap`, port 8080 |
| **Pinned versions and checksums** | llama.cpp commits, the llama-swap release (SHA-256) and the base image digest are fixed so that a result can be reproduced months later | `.env`, `Dockerfile.*` |
| **Models in a Docker (ext4) volume** | a Windows-drive bind over WSL read at ~22-45 MB/s and a cold load took 6-14 minutes; from the volume it takes 11-29 seconds (*measured*) | `docker-compose.yml`, `llm-models-fast` |
| **Context sizes taken from tests, not from the model card** | the profile context is the largest window at which the model started, found 3 of 3 hidden facts at 80% fill and kept its speed on the GPU (*measured*, KV cache f16 / q8 / q4) | `config/llama-swap.yaml`, stage "Maximum stable context" |
| **GPU only, 64K minimum for the later stages** | spilling into RAM gives 1-3 tokens/s, which is not a working server; the author's rule keeps the comparison honest | [METHODOLOGY.en.md](METHODOLOGY.en.md) |
| **No built-in LLM judge** | a model grading models adds an unmeasured error. Checkers are deterministic (computed answers, exact match, running tests); a supervising AI reviews the results instead and its review is written down | [AI_OPERATOR.en.md](AI_OPERATOR.en.md) |
| **An AI assistant as the operator, no plug-in** | the server exposes only normal interfaces (shell, REST, OpenAI API, files). Any assistant that can run commands can operate it, and the server works without one | [AI_OPERATOR.en.md](AI_OPERATOR.en.md) |
| **Console, builder and versioner use only the Python standard library** | no dependency to patch or audit, small attack surface, the images build in seconds | `console/`, `scripts/` |
| **Results are never overwritten** | different tests are kept apart; the SQLite archive keeps history; Git keeps every version of the reports (`vNNNN`, `stage-<id>-done`, `final-<date>`) so that any past report can be restored | `scripts/build_live_report.py`, `scripts/versioner.py` |
| **File-based result protocol** | a test tool only has to append JSON lines and a marker to a log; the plan, progress bar and time-left estimate come from the files, so the tools stay replaceable | [RESULTS_FORMAT.md](RESULTS_FORMAT.md) |
| **Video generation is a separate project** | video needs the whole GPU, has its own release cycle, its own 10 GB of model files and its own audience | Video Studio repository |
| **Interface text in one language, translated at run time** | no build step; user data is excluded from translation so prompts and answers stay exact; `scripts/check_i18n.js` finds gaps | `console/i18n*.js` |
| **No password, local binding by default** | the tool is for a trusted PC or LAN; adding weak authentication would only give a false sense of safety, so the docs say plainly: never expose it | [SECURITY.md](../SECURITY.md) |
| **Docker socket mounted read-only into the console** | the console must see which containers hold the GPU and whether the video container runs; its code only reads container state (no start/stop calls). The read-only flag is a hint, not a security boundary: anyone who reaches the console reaches Docker | `docker-compose.yml` |
| **Results CC BY 4.0, code MIT** | results should travel with credit to the author; code should be reusable | `legal/` |
