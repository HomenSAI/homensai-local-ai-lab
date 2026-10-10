# Changelog

## 1.5.0 - documentation site in HomenS.AI Style (2026-10-10)

English
- The documentation on GitHub Pages (https://homensai.github.io/homensai-local-ai-lab/) is now built in HomenS.AI Style 1.6.0 instead of the plain GitHub theme: header with the HomenS.AI logo, menu (Home, Installation, Documentation, Results, GitHub, Contact), language switch RU / EN / DE between the translations of a page, light and dark theme, table of contents, bottom navigation with a "Documents" sheet on phones, licence line and author footer from the brand data, and the "Contact" page with the robot (`site/contact.<lang>.html`).
- `scripts/build_site.py` (standard library only) turns every Markdown file into the `.html` page next to it (the root `README.md` becomes `index.html`), keeps the GitHub anchors of the headings, points links between documents to the pages and links to other files to GitHub; `--check` is a CI step and a unit test. The pages use the style copy in `console/style/`, no external addresses, no inline styles or scripts (Content-Security-Policy in every page) and open from the disk as well; `.nojekyll` makes GitHub Pages serve them as they are. The old page addresses (for example `docs/DESIGN.ru.html`) stay the same.
- README (EN/RU/DE) links the site; AGENTS, CLAUDE, CONTRIBUTING and ARCHITECTURE say to rebuild the pages after changing Markdown.

Русский
- Документация на GitHub Pages (https://homensai.github.io/homensai-local-ai-lab/) теперь собирается на HomenS.AI Style 1.6.0 вместо простой темы GitHub: шапка со знаком HomenS.AI, меню (Главная, Установка, Документация, Результаты, GitHub, Контакт), переключатель языков RU / EN / DE между переводами страницы, светлая и тёмная тема, оглавление, нижняя панель с листом «Документы» на телефоне, строка лицензии и подвал автора из данных бренда, страница «Контакт» с роботом (`site/contact.<язык>.html`).
- `scripts/build_site.py` (только стандартная библиотека) делает из каждого файла Markdown страницу `.html` рядом с ним (корневой `README.md` — `index.html`), сохраняет якоря заголовков как на GitHub, ведёт ссылки между документами на страницы, а ссылки на прочие файлы — на GitHub; `--check` — шаг CI и модульный тест. Страницы берут копию стиля из `console/style/`, без внешних адресов, inline-стилей и inline-скриптов (Content-Security-Policy в каждой странице), открываются и с диска; `.nojekyll` заставляет GitHub Pages отдавать их как есть. Прежние адреса страниц (например, `docs/DESIGN.ru.html`) не изменились.
- README (EN/RU/DE) ссылается на сайт; AGENTS, CLAUDE, CONTRIBUTING и ARCHITECTURE требуют пересобирать страницы после правки Markdown.

## 1.4.0 - virtual RTX 3080, Git setup in the installer, documentation for installing without an AI assistant (2026-10-10)

English
- Virtual RTX 3080 (`tests/virtual-3080/`): installs and runs the whole system on a Linux machine with Docker and no GPU - a virtual NVIDIA driver for Docker (`--gpus all` works, `nvidia-smi` is injected into GPU containers), a stand-in for llama.cpp / llama-swap / llama-bench with the same paths and APIs and a 10 GB memory model (a model that does not fit fails with "out of memory"), and sparse model files. Used for a full test from a fresh download: install, console, chat, the test phases that use the GPU (general test, German, maximum context with f16/q8/q4 cache and video memory overflow, final check through the gateway), report, SQLite archive, progress page, Git versions; the virtual server takes 1-4 s per request so the 0.5 s samplers of the tests see the GPU load, and reads multi-line `cmd` values of `config/llama-swap.yaml`. Test report: `tests/virtual-3080/REPORT.ru.md`.
- Installers: new step `git` (`install.ps1 git` on Windows, `install.py git` on Linux) sets up the local Git server for the report versions and is part of `all`; on Windows it needs no Python. `setup_git.py` no longer stops when `ssh-keygen` is missing (the SSH key is only for cloning the versions yourself) and starts the versioner without rebuilding it.
- Fixes found by the virtual test: the test runner container had no GPU access (`gpus: all`), so on the real card the peak video memory of the tests would have been recorded as 0; the versioner masked every character of its error messages when the token was still empty.
- Documentation: README (EN/RU/DE) says plainly that an AI assistant is not required, what it adds, which assistants can do it and what to use after the installation (console, report, test progress, API, versions, tests); `PROMPT_FOR_AI.md` uses the PowerShell installer on Windows (no Python or Git) and includes the Git step; the guides list the `git` step.

Русский
- Виртуальная RTX 3080 (`tests/virtual-3080/`): ставит и запускает всю систему на Linux-машине с Docker без видеокарты — виртуальный драйвер NVIDIA для Docker (`--gpus all` работает, `nvidia-smi` появляется в контейнерах с GPU), замена llama.cpp / llama-swap / llama-bench с теми же путями и API и моделью памяти 10 ГБ (модель, которая не помещается, падает с «out of memory»), разреженные файлы моделей. С ним выполнена полная проверка с чистого скачивания: установка, консоль, диалог, этапы тестов, которые работают с видеокартой (общий тест, немецкий, максимальный контекст с кэшем f16/q8/q4 и нехваткой видеопамяти, итоговая проверка через шлюз), отчёт, архив SQLite, ход тестов, версии в Git; виртуальный сервер тратит на запрос 1–4 с, чтобы замеры тестов (раз в 0,5 с) видели загрузку GPU, и читает многострочные `cmd` из `config/llama-swap.yaml`. Отчёт о проверке: `tests/virtual-3080/REPORT.ru.md`.
- Установщики: новый шаг `git` (`install.ps1 git` на Windows, `install.py git` на Linux) настраивает локальный Git для версий отчётов и входит в `all`; на Windows Python не нужен. `setup_git.py` больше не останавливается без `ssh-keygen` (SSH-ключ нужен только для собственного клонирования версий) и запускает версионер без пересборки.
- Исправления по итогам виртуальной проверки: у контейнера раннера тестов не было доступа к видеокарте (`gpus: all`), поэтому на настоящей карте пик видеопамяти в тестах записался бы как 0; версионер маскировал каждую букву сообщений об ошибке, пока токен был пустым.
- Документация: в README (EN/RU/DE) прямо сказано, что ИИ-ассистент не обязателен, что он добавляет, какой ассистент подходит и чем пользоваться после установки (консоль, отчёт, ход тестов, API, версии, тесты); `PROMPT_FOR_AI.md` на Windows использует установщик на PowerShell (без Python и Git) и включает шаг Git; в руководствах есть шаг `git`.

## 1.3.0 - console and report on HomenS.AI Style (2026-10-10)

- The console (port 8766) and the report page (`/report/`) use HomenS.AI Style 1.6.0, the shared design of all HomenS.AI projects: header with the HomenS.AI logo, navigation, language switch and theme button, light and dark theme (the console was dark only), IBM Plex fonts, footer with the author links from the brand data, bottom navigation on phones.
- The style package is copied into `console/style/` (pinned by `<meta name="homensai-style" content="1.6.0">` in both pages) and served at `/style/` with path checks; `shell.js` sets up the theme button and the footer.
- `app.css` and `report.css` keep the layout, but every colour and font is now a style token (about 200 fixed colours replaced).
- Content-Security-Policy allows the console's own fonts (`font-src 'self'`); without it the fonts would have been blocked.
- New page "Test progress" (`/report/progress.html`, linked from the console and the report): the stage plan of the report builder in the process view A/B/C of HomenS.AI Style 1.6.0 (command centre, pipeline, terminal) with labels for model tests; display only, refreshed every 15 seconds.
- Windows installer without Python: `scripts\install.ps1` (doctor, init, build, up, verify, all; `-NoGpu`, `-Pull`) does the same as `scripts/install.py` in the PowerShell that comes with Windows, so the PC needs only Docker Desktop. README and INSTALL (EN/RU/DE) start with the ZIP download and this script; `install.py` stays for Linux and AI assistants. CI checks that the script parses.
- New page "Contact" (`/report/contact.html`, in the navigation of every page): the contact block of HomenS.AI Style with the robot, texts and links from the brand data in RU/EN/DE, as the style requires for every project.
- Footer: noncommercial licence of results and code with links to both licence texts; translations for the new texts (RU/EN/DE).

## 1.2.0 - test runners, noncommercial licence, security and reliability fixes (2026-10-10)

Licence
- Noncommercial use only, credit to the author mandatory, as in `rtx3080-local-ai-benchmarks`: code under PolyForm Noncommercial 1.0.0 (full text in `LICENSE` and `legal/LICENSE-CODE-POLYFORM-NC.txt`, with the Required Notice and the author line), results, reports and texts under CC BY-NC 4.0 (`legal/LICENSE-RESULTS-CC-BY-NC-4.0.md`). Commercial use needs a written agreement with the author. README, INSTALL, DESIGN, AI_OPERATOR, CONTRIBUTING, the console and report footers and the public results snapshot are updated.

Test runners
- The runners and task files of the published results moved here from `rtx3080-local-ai-benchmarks` (that repository now holds only the results): `benchmarks/`, one flat folder as in the original run (the scripts import each other; the copy split into per-test folders could not run). `benchmarks/README.md` maps every test to its runner, tasks and result file.
- New `bench-runner` service (profile `bench`): `docker compose --profile bench up -d --build bench-runner` runs the phases of `BENCH_PHASES` inside Docker, with the log names and finish markers of the console stage plan, and resumes after a restart. `scripts/bench/` moved into `benchmarks/`; the old `/ai-server/bench_results/run_container.sh` path is fixed.
- Code test: the sandbox uses `python:3.12-slim` and copies the files in (the removed `local/cad-sandbox:cq` image and host-path mounts made it unusable). Context test: the filler text is found on Linux too (the pattern worked only on Windows). Vision tasks: `make_images.py` draws the three pictures, which were never published; a missing picture skips the task instead of stopping the run. `gen_profiles_from_ctx.py` no longer needs a hand-edited project path.



Security
- The console now guards every request (`console/security.py`): only `localhost`, IP addresses and `AI_CONSOLE_ALLOWED_HOSTS` are accepted as `Host` (DNS rebinding, `421`); `POST` must be `application/json` from the same origin (cross-site request forgery, `415` / `403`). Before, any web page open in the operator's browser could start, stop and unload models and set the unload timer.
- Optional HTTP Basic password for the console: `AI_CONSOLE_PASSWORD` (everything except `/health`). Set it before using `AI_CONSOLE_BIND_IP` other than `127.0.0.1`.
- Security headers on every answer: `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options`, `Referrer-Policy`, `Cross-Origin-Resource-Policy`.
- The Docker socket is used for one fixed kind of command only (curl against `127.0.0.1` status endpoints of a plain-named container); everything else is refused. The console container runs with `cap_drop: ALL` and `no-new-privileges`.
- `SECURITY.md`, `docs/DESIGN.*`, `docs/INSTALL.*` and `docs/API.md` no longer call the socket "read calls only" or the console "without authentication"; they describe the real protection and its limits.

Fixes
- Report builder: a model that did not load (`load_ok: false`) without a `quality` list was silently dropped; it is now listed as failed. Impossible scores (`max` of 0 or less, a non-number, a negative score) are ignored and counted in `invalid_items`, a score above `max` is clamped (a broken checker showed 500 %).
- Public results: failed models are marked "failed to load" instead of "admitted"; `make_public_results.py` has real argument parsing (`--help` created a folder named `--help`) and a clear error when the report data is missing.
- Report page: no longer fails on the empty placeholder data file of a fresh installation; the misleading hint about a missing `serve-report.ps1` is gone.
- Console: removed the stale built-in model table that disagreed with `config/llama-swap.yaml`; the console answers bad request bodies (not an object, invalid JSON) with `400` instead of dropping the connection; `/favicon.ico` no longer logs a 404.
- Installer: `doctor` no longer downloads the 5.6 GB CUDA image silently (`doctor --pull` does, after you agreed); `--no-gpu` for a PC without an NVIDIA GPU (`docker-compose.nogpu.yml`); `verify` no longer checks the `/video` page that does not exist.
- `scripts/check_i18n.js` no longer reports a false gap for texts that start with a quotation mark and no longer uses `eval`.
- Removed `console/video.html`: a leftover page of the separate Video Studio project (no route, no `video.js`, not copied into the image). The header link "Video generation" still points to Video Studio on port 8767.
- `.env.example`: removed the duplicated `PUBLIC_REPO_URL` and the unused `VIDEO_HOST_DIR`.

Quality
- Unit tests without third-party packages (`tests/`, run `python -m unittest discover -s tests`): console security, report builder, public results, installer, manifest.
- CI runs the tests, fails on missing translations (it used to ignore them) and checks `MANIFEST.json`.
- `MANIFEST.json` is generated by `scripts/make_manifest.py` (hashes of the content with Unix line endings, so the result is the same on Windows and Linux) and was out of date; it is refreshed.

## 1.1.0 - server scripts moved here from the benchmark repository

- Moved from `rtx3080-local-ai-benchmarks`: PowerShell and Python scripts for model runs, media and context probes (`scripts/`), benchmark profile generators (`scripts/bench/`), Dockerfiles for the bench runner and GGUF conversion (`docker/`).
- Added the release workflow `.github/workflows/release.yml`: it creates a GitHub release from the matching section of this changelog.

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
