# Changelog

## 1.0.0 - first public package

- llama-swap gateway with one-model-at-a-time loading; 15 model profiles measured on an RTX 3080 / 10 GB.
- Console on port 8766 in Russian, English and German: model catalog with Start/Stop, chat, GPU telemetry, diagnostics, unload timer, test results (sortable, with progress bar, stage plan and time-left estimate), report page at `/report/`. Video generation is a separate project, Video Studio.
- Report builder with a SQLite archive that never loses old results; separate results per test type.
- Local Gitea with automatic report versioning (`vNNNN`, `stage-<id>-done`, `final-<date>` tags).
- Installer (`scripts/install.py`: doctor, init, build, up, verify) and installation guides in English, Russian and German.
- AI-supervisor operation: `AGENTS.md`, `CLAUDE.md` and `docs/AI_OPERATOR.*` (hand-over prompt, supervision loop, rules), `docs/API.md`, `docs/RESULTS_FORMAT.md`.
- Published results snapshot (`results-public/`) and `docs/METHODOLOGY.*` (server core -> Claude as supervisor -> results), `docs/DESIGN.*` (why it was built this way), `PROVENANCE.md`, `docs/GITHUB_REPO.md`.
- Optional `PUBLIC_REPO_URL` shows a GitHub link in the footers.
- Licenses: results and reports CC BY 4.0 (credit to https://homensai.com required), code MIT, third-party notices.
