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
- **Можно поручить ИИ-ассистенту:** сервер можно поставить и использовать самому; можно и передать его Claude, ChatGPT/Codex или другому агенту с доступом к командной строке — он прочитает `AGENTS.md` / `CLAUDE.md`, установит, запустит тесты и проверит результаты. См. [docs/AI_OPERATOR.ru.md](docs/AI_OPERATOR.ru.md) и раздел «Сам или с ИИ-ассистентом?» ниже.
- **Опубликованные результаты:** [results-public/RESULTS.md](results-public/RESULTS.md) — 23 модели, 15 допущены к поздним этапам; как они получены (ядро сервера → Claude как супервизор → результаты): [docs/METHODOLOGY.ru.md](docs/METHODOLOGY.ru.md).
- **Связанный проект:** генерация видео (Wan 2.1 + ComfyUI, раскадровку из идеи составляет ваша локальная LLM) — отдельный проект **Video Studio** (свой репозиторий, порт 8767); эта консоль ссылается на него.

## Быстрый старт

**Windows (на компьютере только Docker Desktop — без Python, Git и Node):** скачайте ZIP со страницы GitHub (Code → Download ZIP), распакуйте, откройте PowerShell в папке и выполняйте по одной команде:

```
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 doctor   # Docker, видеокарта в Docker, порты, диск
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 init     # .env, папки, заглушки, сеть, том
#  откройте .env в Блокноте, укажите MODEL_DIR и положите модели .gguf — см. инструкцию, раздел 4.5
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 build    # первая сборка 15–40 минут
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 up
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 git      # локальный Git, который хранит каждую версию отчётов
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 verify   # каждая строка должна быть [ok]
```

**Linux или ИИ-ассистент с доступом к командной строке:** те же шаги на Python 3.10+ (только стандартная библиотека):

```
git clone https://github.com/HomenSAI/homensai-local-ai-lab.git local-ai-server
cd local-ai-server
python scripts/install.py doctor     # Docker, видеокарта в Docker, порты, диск
python scripts/install.py init       # .env, папки, заглушки, сеть, том
#  отредактируйте .env (MODEL_DIR) и разместите модели .gguf — см. руководство, раздел 4.5
python scripts/install.py build      # первая сборка 15–40 минут
python scripts/install.py up
python scripts/install.py git
python scripts/install.py verify
```

Откройте **http://localhost:8766/**.

## Сам или с ИИ-ассистентом?

**ИИ-ассистент не обязателен.** Установка, запуск, тесты и отчёты делаются командами с этой страницы; нужно уметь вставить команду в PowerShell и поправить одну строку `.env` в Блокноте.

| Задача | Сами | Что добавляет ИИ-ассистент |
|---|---|---|
| Установить | шесть команд выше, по одной | выполнит их за вас и исправит то, что покажут `doctor` / `verify` |
| Модели | скачать файлы из [MODELS.md](MODELS.md), положить в том Docker (руководство, раздел 4.5) | подберёт модели под вашу видеокарту, проверит SHA-256 |
| Пользоваться | консоль в браузере (ниже) | — |
| Запустить тесты | одна команда (ниже) | следит за прогоном, проверяет правдоподобность чисел, повторяет сомнительные прогоны |
| Что-то не работает | руководство, раздел 11 «Неполадки» | читает журналы контейнеров и устраняет причину |

Выполнить эти шаги может только ассистент, **который умеет запускать команды на этом компьютере** (например, Claude Code или агент Codex); вставьте ему [PROMPT_FOR_AI.md](PROMPT_FOR_AI.md). На Windows он пользуется тем же установщиком на PowerShell, поэтому серверу по-прежнему нужен только Docker Desktop; у самого ассистента могут быть свои требования — смотрите его документацию. Обычный чат в браузере ничего не установит, но объяснит ошибку, если вставить ему её текст.

## После установки: чем пользоваться

| Что | Где |
|---|---|
| Консоль: старт и стоп моделей, диалог, загрузка видеокарты, диагностика | http://localhost:8766/ |
| Отчёт со всеми результатами тестов, выгрузка CSV и SQLite | http://localhost:8766/report/ |
| Ход тестов (этапы, текущая модель, оставшееся время) | http://localhost:8766/report/progress.html |
| API, совместимый с OpenAI, для других программ (Open WebUI, скрипты, редакторы кода) | http://localhost:8080/v1 |
| Все версии отчётов (локальный Git) | http://localhost:3010/ (вход — в `secrets/gitea-admin.txt`) |
| Запустить тесты | `docker compose --profile bench up -d --build bench-runner` ([benchmarks/README.md](benchmarks/README.md)) |

**Попробовать без видеокарты:** [tests/virtual-3080/](tests/virtual-3080/README.md) ставит всю систему на Linux-машину с Docker и виртуальной RTX 3080 (условные числа) — чтобы освоить систему или проверить изменения.

## Документация

Та же документация в виде сайта на HomenS.AI Style (меню, переключатель языков, светлая и тёмная тема): <https://homensai.github.io/homensai-local-ai-lab/README.ru.html>. Страницы собираются из этих файлов Markdown командой `python scripts/build_site.py`.

| | English | Русский | Deutsch |
|---|---|---|---|
| Полное руководство по установке | [INSTALL.en.md](docs/INSTALL.en.md) | [INSTALL.ru.md](docs/INSTALL.ru.md) | [INSTALL.de.md](docs/INSTALL.de.md) |
| Обзор | [README.md](README.md) | этот файл | [README.de.md](README.de.md) |

Ещё: [почему сделано так](docs/DESIGN.ru.md) · [HTTP-интерфейсы](docs/API.md) · [формат файлов результатов](docs/RESULTS_FORMAT.md) · [происхождение кода](PROVENANCE.md) · [тексты страницы репозитория](docs/GITHUB_REPO.md) · [архитектура](docs/ARCHITECTURE.md) · [политика безопасности](SECURITY.md) · [участие](CONTRIBUTING.md) · [журнал изменений](CHANGELOG.md) · [список моделей](MODELS.md) · [файлы лицензий](legal/)

## Требования одной строкой

Видеокарта NVIDIA от 8 ГБ, 16–32 ГБ ОЗУ, около 25 ГБ диска под образы и 50–200 ГБ под модели, Docker Desktop (WSL2) с поддержкой GPU; на Windows больше ничего (установщик на PowerShell), на Linux — Python 3.10+ и Git. Linux с NVIDIA Container Toolkit должен работать (автор не проверял); macOS не поддерживается (нет CUDA).

## Что не входит

Веса моделей (скачайте сами и соблюдайте их лицензии), ваши собственные результаты тестов (`bench_results/`, появляются при прогоне), видео, секреты. Раннеры тестов лежат в [benchmarks/](benchmarks/README.md); опубликованные результаты — в [rtx3080-local-ai-benchmarks](https://github.com/HomenSAI/rtx3080-local-ai-benchmarks). У шлюза **нет пароля**, пароль консоли (`AI_CONSOLE_PASSWORD`) необязателен: используйте оба только на `127.0.0.1` или в доверенной сети, никогда в интернете. Консоль также отклоняет межсайтовые запросы и чужие имена `Host` ([SECURITY.md](SECURITY.md)).

## Лицензия и указание авторства

- Результаты, отчёты и тексты: **[CC BY-NC 4.0](legal/LICENSE-RESULTS-CC-BY-NC-4.0.md)** — можно использовать и распространять **только в некоммерческих целях**, **ссылка на автора обязательна**: `Данные: homensai.com (https://homensai.com), CC BY-NC 4.0`.
- Код: **[PolyForm Noncommercial 1.0.0](LICENSE)** — только некоммерческое использование; уведомление (Required Notice) и строка автора сохраняются в каждой копии. Коммерческое использование кода или результатов — только по письменному соглашению с автором.
- Сторонние программы и модели сохраняют свои лицензии: [NOTICE-THIRD-PARTY.md](legal/NOTICE-THIRD-PARTY.md). Названия продуктов — товарные знаки их владельцев; проект с ними не связан и не одобрен ими.
