# Архитектура

Другие языки: [English](ARCHITECTURE.md) · [Deutsch](ARCHITECTURE.de.md)

```
 browser ──► console :8766 (Python, stdlib only) ──► gateway :8080 (llama-swap) ──► llama-server (one model in VRAM)
                │  │                                      ▲
                │  └─ docker.sock (container list; status of llama-server via a fixed `docker exec curl`; refuses an LLM start while Video Studio holds the GPU)
                │
                ├─ /report/  ◄── report/live-data.json ◄── report-builder ◄── bench_results/results*.jsonl
                │                                              └──► results-db/llm-results.sqlite (never loses old results)
                └─ /legal/   license and third-party notices

 report-versioner ──(every minute, only on change)──► gitea :3010  tags v0001..., stage-<id>-done, final-<date>
```

## Компоненты

| Путь | Роль |
|---|---|
| `docker-compose.nogpu.yml` | Переопределение для машины без видеокарты NVIDIA: консоль запускается, не запрашивая её (`install.py up --no-gpu`). |
| `docker-compose.yml` | Все сервисы. Профили: `gateway` (llama-swap), `build` (сборщики базовых образов), `whisper`, `qwen-image`, `media-tools` (необязательные). |
| `Dockerfile.upstream` / `.bonsai` | llama.cpp (CUDA 12.8, архитектура 86) и форк PrismML, собранные из закреплённых коммитов. |
| `Dockerfile.llama-swap` | llama-swap v260 (с проверкой SHA-256) поверх образа upstream, со средой выполнения Bonsai, скопированной в `/opt/prism`. |
| `config/llama-swap.yaml` | По одному профилю на модель: файл, размер контекста, тип KV-кэша, спекулятивное декодирование, TTL. Правьте его, чтобы добавить или убрать модели. |
| `console/` | `container_server.py` (HTTP-сервер, доступ к Docker и шлюзу), `security.py` (проверки Host / Origin / пароля и заголовки безопасности), `tests_feed.py` (данные для таблицы тестов); статические `index.html`, `app.js`, `app.css`, `shell.js` (кнопка темы, подвал с автором); `i18n.js` + `i18n-dict.js` (RU/EN/DE); `style/`: HomenS.AI Style 1.6.0 (таблица стилей, шрифты, логотип, скрипты), раздаётся по адресу `/style/`. |
| `report/` | Статическая страница отчёта; `live-data.json` и `live-status.json` записывает сборщик. `progress.html` + `progress.js`: прогресс тестов (план этапов из `live-data.json`) в виде процесса A/B/C из HomenS.AI Style; `contact.html` + `contact.js`: блок «Контакт» из стиля (обязателен в каждом проекте HomenS.AI). |
| `scripts/build_live_report.py` | Собирает файлы результатов, объединяет их в SQLite (`raw_rows`, `results`, `history`, `model_scores`), строит план этапов, прогресс и оценку оставшегося времени. |
| `scripts/versioner.py`, `scripts/setup_git.py` | Версионирование отчётов в Gitea и его однократная настройка. |
| `scripts/install.py` | doctor / init / build / up / verify (`--no-gpu`, `doctor --pull`). |
| `scripts/build_site.py` | Собирает сайт документации (GitHub Pages): превращает файлы Markdown в `site/site.json` и `site/content/` и запускает сборщик сайтов HomenS.AI Style, который пишет `site/<страница>.<язык>.html` и копирует ядро в `site/style/`; прежние адреса страниц становятся переадресациями; `--check` для CI. |
| `scripts/make_manifest.py` | Записывает / проверяет `MANIFEST.json` (размер и SHA-256 каждого отслеживаемого файла). |
| `tests/` | Модульные тесты на стандартной библиотеке: безопасность консоли, сборщик отчёта, опубликованные результаты, установщик, манифест (`python -m unittest discover -s tests`). |
| `hermes-telemetry/` | Небольшой экспортёр метрик (GPU, llama). |
| `benchmarks/`, `docker/bench-runner/` | Раннеры тестов, которыми получены опубликованные результаты, и их контейнер (профиль `bench`); они пишут в `bench_results/`. См. `benchmarks/README.md`. |
| `legal/` | CC BY-NC 4.0 (результаты), PolyForm Noncommercial 1.0.0 (код), уведомления о стороннем ПО. |

## Проектные решения

- **Одна модель за раз.** В 10 ГБ видеопамяти помещается одна большая модель; llama-swap выгружает старую модель, прежде чем загрузить следующую. Консоль не даёт запустить LLM, пока генерация видео держит видеокарту.
- **Том для моделей.** Модели раздаются из тома Docker (ext4), потому что через привязку диска Windows по WSL они загружаются примерно в 10 раз медленнее.
- **Никаких сторонних пакетов Python** в консоли, сборщике и версионере: они работают на `python:3.12-slim` / `alpine` только со стандартной библиотекой.
- **Результаты никогда не перезаписываются.** Разные тесты (общий, немецкий, контекст, STEM, ...) хранятся раздельно; архив SQLite хранит историю; Git хранит каждую версию отчёта.
- **Текст интерфейса в исходниках — на русском**, его на лету переводит `i18n.js`; данные пользователя (промпты, ответы, логи) помечены `data-no-i18n` и никогда не переводятся. `scripts/check_i18n.js` выводит список непереведённых фрагментов.
- **Bind-монтирование одиночных файлов** (файлы конфигурации) не подхватывает заменённый файл: после их правки пересоздайте сервис.

## Связанный проект

**Video Studio** (отдельный репозиторий): своя консоль (порт 8767) и контейнер ComfyUI + Wan 2.1. Он подключается к сети Docker этого проекта `local-ai-server_default`, чтобы обращаться к шлюзу (выгрузить модели перед видео, составить раскадровку с помощью локальной LLM). Эта консоль только проверяет, работает ли контейнер ComfyUI, чтобы не запустить LLM, пока видеокарта занята.
