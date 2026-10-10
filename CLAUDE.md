# Claude Code: working instructions

The same instructions as `AGENTS.md` (this file is read automatically by Claude Code). In short:

- **You install, start and supervise this server for the human.** The server works without you; you are the operator and the reviewer of the tests.
- Read `docs/AI_OPERATOR.en.md`, `docs/INSTALL.en.md`, `docs/API.md`, `docs/RESULTS_FORMAT.md`, `docs/METHODOLOGY.en.md`.
- Install with `python scripts/install.py doctor | init | build | up | git | verify` (`--no-gpu` on a PC without an NVIDIA GPU; `doctor --pull` downloads 5.6 GB, ask first); on the owner's Windows PC, which has only Docker Desktop, use `scripts\install.ps1` with the same steps (`-NoGpu`, `-Pull`); ask the human for `MODEL_DIR`, the network address and, for LAN use, the console password (`AI_CONSOLE_PASSWORD`); start with one small model.
- One model in video memory at a time; test results are appended to `bench_results/results_*.jsonl` with progress in `bench_results/<stage>.log`; check every result for plausibility and repeat suspicious runs before you report.
- Ask before deleting, opening ports, downloading more than 1 GB or publishing. Never expose the console or gateway to the internet, never write secrets into Git, never rewrite earlier results.
- Console `POST` calls need `Content-Type: application/json`; never weaken `console/security.py` or the fixed `docker exec` form.
- Changing code: standard library only in the console, keep RU/EN/DE complete (`node scripts/check_i18n.js de`), run `python -m unittest discover -s tests`, `python scripts/build_site.py` after changing Markdown (the `.html` pages are generated) and `python scripts/make_manifest.py --check`, bump `VERSION` and `CHANGELOG.md` for a release.

Full text: [AGENTS.md](AGENTS.md).
