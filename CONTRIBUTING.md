# Contributing

Thank you for helping. Languages for issues and pull requests: English, Russian or German.

## Rules

1. **Keep the three interface languages complete.** Interface text is written in Russian in `console/*.html|js|py` and translated by `console/i18n-dict.js`. After you add or change a visible text run `node scripts/check_i18n.js de` and `node scripts/check_i18n.js en` and add the missing entries. User data must stay untranslated (`data-no-i18n`).
2. **No secrets, no personal paths or addresses, no model weights** in commits. Use placeholders like `<MODEL_DIR>`.
3. **No new third-party Python packages** in the console, report builder or versioner.
4. **Check your change**: `docker compose --profile gateway --profile build config -q`, `node --check console/*.js`, `python -m py_compile console/*.py scripts/*.py`.
5. **Licensing of contributions**: code is contributed under the MIT license; results/reports/texts under CC BY 4.0 with credit to the author (see `legal/`). By opening a pull request you confirm that you have the right to contribute your changes under these licenses.

## Reporting a bug

Include your OS, Docker Desktop version, GPU and driver, the output of `python scripts/install.py doctor`, and the relevant lines of `docker logs <container>`.
