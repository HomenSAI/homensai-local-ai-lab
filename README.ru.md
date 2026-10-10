# Local AI Server

**Запускайте локальные языковые модели на одной видеокарте NVIDIA: веб-консоль, автоматические отчёты по тестам, генерация видео и версии результатов.**
Языки: [English](README.md) · Русский · [Deutsch](README.de.md)

Автор: **Serhii Khomenko** · [homensai.com](https://homensai.com) · info@homensai.com · Результаты и отчёты: CC BY-NC 4.0 · Код: PolyForm Noncommercial 1.0.0 · только некоммерческое использование, указание автора обязательно

## Что это

Самостоятельно разворачиваемый набор для рабочей станции с одной видеокартой (разработан на RTX 3080 с 10 ГБ, Windows 10 + Docker Desktop):

- **Шлюз** ([llama-swap](https://github.com/mostlygeek/llama-swap) + [llama.cpp](https://github.com/ggml-org/llama.cpp)): API, совместимый с OpenAI, на порту 8080; загружает одну модель за раз и переключает по запросу.
- **Консоль** (порт 8766, **русский / English / Deutsch**): каталог моделей со Стартом/Стопом, чат, телеметрия GPU, диагностика, таймер выгрузки, результаты тестов с прогрессом и оценкой оставшегося времени и страница **отчёта**.
- **Отчёты**: результаты бенчмарков превращаются в живой отчёт и архив SQLite, который не теряет старые результаты.
- **История версий**: локальный Gitea хранит каждую версию отчётов (теги `v0001`…, `stage-<этап>-done`, `final-<дата>`).
- **Управляется ИИ-ассистентом:** сервер рассчитан на то, что его устанавливает, запускает и контролирует Claude или ChatGPT (агент с доступом к оболочке): передайте ему репозиторий, он прочитает `AGENTS.md` / `CLAUDE.md`, установит, запустит тесты и проверит результаты. Без ассистента сервер тоже работает. См. [docs/AI_OPERATOR.ru.md](docs/AI_OPERATOR.ru.md).
- **Опубликованные результаты:** [results-public/RESULTS.md](results-public/RESULTS.md) — 23 модели, 15 допущены к поздним этапам; как они получены (ядро сервера → Claude как супервизор → результаты): [docs/METHODOLOGY.ru.md](docs/METHODOLOGY.ru.md).
- **Связанный проект:** генерация видео (Wan 2.1 + ComfyUI, раскадровку из идеи составляет ваша локальная LLM) — отдельный проект **Video Studio** (свой репозиторий, порт 8767); эта консоль ссылается на него.

## Быстрый старт

```
git clone https://github.com/HomenSAI/homensai-local-ai-lab.git local-ai-server
cd local-ai-server
python scripts/install.py doctor     # Docker, видеокарта в Docker, порты, диск
python scripts/install.py init       # .env, папки, заглушки, сеть, том
#  отредактируйте .env (MODEL_DIR) и разместите модели .gguf — см. руководство, раздел 4.5
python scripts/install.py build      # первая сборка 15–40 минут
python scripts/install.py up
python scripts/install.py verify
```

Откройте **http://localhost:8766/**.

## Документация

| | English | Русский | Deutsch |
|---|---|---|---|
| Полное руководство по установке | [INSTALL.en.md](docs/INSTALL.en.md) | [INSTALL.ru.md](docs/INSTALL.ru.md) | [INSTALL.de.md](docs/INSTALL.de.md) |
| Обзор | [README.md](README.md) | этот файл | [README.de.md](README.de.md) |

Ещё: [почему сделано так](docs/DESIGN.ru.md) · [HTTP-интерфейсы](docs/API.md) · [формат файлов результатов](docs/RESULTS_FORMAT.md) · [происхождение кода](PROVENANCE.md) · [тексты страницы репозитория](docs/GITHUB_REPO.md) · [архитектура](docs/ARCHITECTURE.md) · [политика безопасности](SECURITY.md) · [участие](CONTRIBUTING.md) · [журнал изменений](CHANGELOG.md) · [список моделей](MODELS.md) · [файлы лицензий](legal/)

## Требования одной строкой

Видеокарта NVIDIA от 8 ГБ, 16–32 ГБ ОЗУ, около 25 ГБ диска под образы и 50–200 ГБ под модели, Docker Desktop (WSL2) с поддержкой GPU, Python 3.10+, Git. Linux с NVIDIA Container Toolkit должен работать (автор не проверял); macOS не поддерживается (нет CUDA).

## Что не входит

Веса моделей (скачайте сами и соблюдайте их лицензии), ваши собственные результаты тестов (`bench_results/`, появляются при прогоне), видео, секреты. Раннеры тестов лежат в [benchmarks/](benchmarks/README.md); опубликованные результаты — в [rtx3080-local-ai-benchmarks](https://github.com/HomenSAI/rtx3080-local-ai-benchmarks). У шлюза **нет пароля**, пароль консоли (`AI_CONSOLE_PASSWORD`) необязателен: используйте оба только на `127.0.0.1` или в доверенной сети, никогда в интернете. Консоль также отклоняет межсайтовые запросы и чужие имена `Host` ([SECURITY.md](SECURITY.md)).

## Лицензия и указание авторства

- Результаты, отчёты и тексты: **[CC BY-NC 4.0](legal/LICENSE-RESULTS-CC-BY-NC-4.0.md)** — можно использовать и распространять **только в некоммерческих целях**, **ссылка на автора обязательна**: `Данные: homensai.com (https://homensai.com), CC BY-NC 4.0`.
- Код: **[PolyForm Noncommercial 1.0.0](LICENSE)** — только некоммерческое использование; уведомление (Required Notice) и строка автора сохраняются в каждой копии. Коммерческое использование кода или результатов — только по письменному соглашению с автором.
- Сторонние программы и модели сохраняют свои лицензии: [NOTICE-THIRD-PARTY.md](legal/NOTICE-THIRD-PARTY.md). Названия продуктов — товарные знаки их владельцев; проект с ними не связан и не одобрен ими.
