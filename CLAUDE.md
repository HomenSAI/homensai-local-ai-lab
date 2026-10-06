# Claude Code: working instructions

The same instructions as `AGENTS.md` (this file is read automatically by Claude Code). In short:

- **You install, start and supervise this server for the human.** The server works without you; you are the operator and the reviewer of the tests.
- Read `docs/AI_OPERATOR.en.md`, `docs/INSTALL.en.md`, `docs/API.md`, `docs/RESULTS_FORMAT.md`, `docs/METHODOLOGY.en.md`.
- Install with `python scripts/install.py doctor | init | build | up | verify`; ask the human for `MODEL_DIR` and the network address; start with one small model.
- One model in video memory at a time; test results are appended to `bench_results/results_*.jsonl` with progress in `bench_results/<stage>.log`; check every result for plausibility and repeat suspicious runs before you report.
- Ask before deleting, opening ports, downloading more than 1 GB or publishing. Never expose the console or gateway to the internet, never write secrets into Git, never rewrite earlier results.
- Changing code: standard library only in the console, keep RU/EN/DE complete (`node scripts/check_i18n.js de`), bump `VERSION` and `CHANGELOG.md` for a release.

Full text: [AGENTS.md](AGENTS.md).
