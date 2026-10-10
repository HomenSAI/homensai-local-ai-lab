# Contributing

Thank you for helping. Languages for issues and pull requests: English, Russian or German.

## Rules

1. **Keep the three interface languages complete.** Interface text is written in Russian in `console/*.html|js|py` and translated by `console/i18n-dict.js`. After you add or change a visible text run `node scripts/check_i18n.js de` and `node scripts/check_i18n.js en` and add the missing entries. User data must stay untranslated (`data-no-i18n`).
2. **No secrets, no personal paths or addresses, no model weights** in commits. Use placeholders like `<MODEL_DIR>`.
3. **No new third-party Python packages** in the console, report builder or versioner.
4. **Check your change**: `python -m unittest discover -s tests` (no GPU or Docker needed), `docker compose --profile gateway --profile build config -q`, `docker compose -f docker-compose.yml -f docker-compose.nogpu.yml config -q`, `node --check console/*.js`, `python -m py_compile console/*.py scripts/*.py tests/*.py`, `node scripts/check_i18n.js de` and `en` (must print `missing: 0`), `python scripts/build_site.py` after changing a Markdown file (the `.html` pages of the documentation site are generated from it; CI runs it with `--check`), and `python scripts/make_manifest.py` to refresh `MANIFEST.json` (CI runs it with `--check`).
5. **Security-relevant code**: do not weaken `console/security.py` or the fixed `docker exec` form in `container_server.py`; add a test in `tests/` for every change of them. See [SECURITY.md](SECURITY.md).
6. **Licensing of contributions**: code is contributed under PolyForm Noncommercial 1.0.0; results/reports/texts under CC BY-NC 4.0 with credit to the author (see `legal/`). By opening a pull request you confirm that you have the right to contribute your changes under these licenses.

## Reporting a bug

Include your OS, Docker Desktop version, GPU and driver, the output of `python scripts/install.py doctor`, and the relevant lines of `docker logs <container>`.
