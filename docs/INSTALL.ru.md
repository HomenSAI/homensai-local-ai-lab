# Руководство по установке (Русский)

Другие языки: [English](INSTALL.en.md) · [Deutsch](INSTALL.de.md) · Назад в [README](../README.ru.md)

Это руководство проведёт вас от пустого компьютера до работающего **Local AI Server**: шлюз, который загружает в видеопамять одной видеокарты NVIDIA по одной локальной языковой модели; веб-консоль (модели, чат, тесты, генерация видео, отчёты) на трёх языках; автоматические отчёты по тестам и локальный Git-сервер, хранящий каждую версию отчётов.

> Авторство и права: результаты и отчёты распространяются по лицензии **CC BY-NC 4.0** (можно использовать и распространять только в некоммерческих целях и **со ссылкой на автора**, <https://homensai.com>); код — **PolyForm Noncommercial 1.0.0**. Веса моделей в пакет **не входят** и сохраняют собственные лицензии. См. папку `legal/`.

## Содержание

1. [Что вы получите](#1-что-вы-получите)
2. [Требования](#2-требования)
3. [Быстрый путь: скрипт установки](#3-быстрый-путь-скрипт-установки)
4. [Установка по шагам](#4-установка-по-шагам)
5. [Необязательные компоненты](#5-необязательные-компоненты)
6. [Проверка](#6-проверка)
7. [Работа с консолью](#7-работа-с-консолью)
8. [Результаты тестов, отчёты и версии в Git](#8-результаты-тестов-отчёты-и-версии-в-git)
9. [Обслуживание: обновление, копия, удаление](#9-обслуживание-обновление-копия-удаление)
10. [Заметки по Linux / macOS](#10-заметки-по-linux--macos)
11. [Если что-то не работает](#11-если-что-то-не-работает)
12. [Безопасность](#12-безопасность)
13. [Лицензия и указание авторства](#13-лицензия-и-указание-авторства)

## 1. Что вы получите

| Часть | Контейнер | Порт (на этом ПК) | Что делает |
|---|---|---|---|
| Шлюз (llama-swap) | `ai-llama-swap-gateway` | 8080 | API, совместимый с OpenAI. Запускает `llama-server` для нужной модели и выгружает предыдущую. |
| Консоль | `ai-model-console` | 8766 | Веб-интерфейс: каталог моделей со Стартом/Стопом, чат, телеметрия GPU, диагностика, таймер выгрузки, результаты тестов и **отчёт** по адресу `/report/`. Языки: RU / EN / DE (переключатель в шапке). |
| Сборщик отчёта | `ai-report-builder` | — | Каждые 15 с превращает файлы результатов бенчмарка в `report/live-data.json` и архив SQLite `results-db/llm-results.sqlite`. |
| Перенаправление отчёта | `ai-stats-report` | 8765 | Старый адрес: перенаправляет на `http://ХОСТ:8766/report/`. |
| Git-сервер | `ai-gitea` | 3010 (веб), 2222 (ssh) | Локальный Gitea с закрытым репозиторием `reports-admin/model-test-reports`. |
| Версионер | `ai-report-versioner` | — | Каждую минуту сохраняет изменившиеся результаты и отчёты в Gitea (теги `v0001`, `v0002`, …, `stage-<этап>-done`, `final-<дата>`). |
| Телеметрия (необязательно) | `hermes-telemetry` | 9835 | Метрики GPU и llama в формате Prometheus для внешнего сборщика. |
| Video Studio (отдельный проект, необязательно) | `video-studio-console`, `video-generation-comfyui-video-1` | 8767, 8188 | Генерация видео (ComfyUI + Wan 2.1). Свой репозиторий и руководство. |
| Open WebUI (необязательно) | `open-webui` | 3000 | Чат-интерфейс, подключённый к шлюзу. |

В 10 ГБ видеопамяти помещается одна большая модель, поэтому шлюз держит **одну модель за раз**; консоль не даёт запустить LLM, пока Video Studio генерирует видео (а Video Studio перед стартом выгружает модели).

## 2. Требования

**Железо**
- Видеокарта NVIDIA от 8 ГБ видеопамяти (у автора RTX 3080, 10 ГБ). Модели и размеры контекста в `config/llama-swap.yaml` подобраны под 10 ГБ; при меньшем объёме берите меньшие модели и контексты.
- Оперативной памяти минимум 16 ГБ, лучше 32 ГБ (сборка CUDA-образов и загрузка моделей 9–27B расходуют много памяти).
- Свободное место: около 25 ГБ под образы Docker, 50–200 ГБ под модели.

**Программы**
- Windows 10/11 с **Docker Desktop (движок WSL2)** и свежим драйвером NVIDIA (с поддержкой CUDA 12.8). Это проверенная конфигурация. Linux — раздел 10.
- Docker Compose v2 (входит в Docker Desktop). На Windows больше ничего не нужно: установщик `scripts\install.ps1` работает во встроенном PowerShell. На Linux — Python 3.10+ (для вспомогательных скриптов, дополнительных пакетов не нужно) и Git.
- Интернет для сборки образов и скачивания моделей.

**Сначала проверьте видеокарту в Docker** (должна вывестись ваша карта):

```
docker run --rm --gpus all nvidia/cuda:12.8.1-runtime-ubuntu24.04 nvidia-smi
```

Рекомендуемый `%USERPROFILE%\.wslconfig` для ПК с 32 ГБ (после правки выполните `wsl --shutdown`):

```
[wsl2]
memory=24GB
processors=8
swap=8GB
```

## 3. Быстрый путь: скрипт установки

**Windows, на компьютере только Docker Desktop (без Python, Git и Node).** Скачайте ZIP со страницы GitHub (Code → Download ZIP), распакуйте, откройте PowerShell в распакованной папке (Shift + правый щелчок → «Открыть окно PowerShell здесь») и выполняйте по одной команде. Каждая строка ответа начинается с `[ok]`, `[warn]` или `[FAIL]`:

```
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 doctor
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 init
notepad .env
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 build
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 up
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 git
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 verify
```

`scripts\install.ps1` делает ровно то же, что `scripts/install.py` ниже (те же шаги и проверки, `-Pull` и `-NoGpu` вместо `--pull` и `--no-gpu`, `all` — всё сразу), и работает во встроенном PowerShell Windows. Команды ниже — для Linux или ИИ-ассистента с доступом к командной строке.


```
git clone https://github.com/HomenSAI/homensai-local-ai-lab.git local-ai-server
cd local-ai-server
python scripts/install.py doctor      # проверит Docker, видеокарту в Docker, свободные порты и диск (сам ничего не скачивает; см. ниже)
python scripts/install.py init        # создаст .env, папки, заглушки, сеть и том Docker
# отредактируйте .env: MODEL_DIR (и AI_CONSOLE_BIND_IP для доступа по сети), затем разместите модели (раздел 4.5)
python scripts/install.py build       # соберёт образы (в первый раз 15–40 минут)
python scripts/install.py up          # запустит всё
python scripts/install.py git         # локальный Git, который хранит каждую версию отчётов
python scripts/install.py verify      # HTTP-проверка каждой части
```

`python scripts/install.py all` выполняет doctor, init, build, up, git и verify подряд (запускайте после правки `.env`). Любой шаг можно безопасно повторять. Потом откройте **http://localhost:8766/**.

- **Проверка видеокарты и образ на 5,6 ГБ.** `doctor` проверяет видеокарту образом `nvidia/cuda:12.8.1-runtime-ubuntu24.04`. Если его ещё нет на ПК, `doctor` только предупреждает и пропускает проверку; спросите владельца и запустите `python scripts/install.py doctor --pull`, чтобы скачать образ (5,6 ГБ).
- **ПК без видеокарты NVIDIA** (чтобы попробовать консоль, отчёт и Git): добавьте `--no-gpu` к `doctor`, `build`, `up` и `verify` (или к `all`). Шлюз не запускается, модели загрузить нельзя; консоль стартует без запроса видеокарты (`docker-compose.nogpu.yml`). Если запускаете консоль вручную: `docker compose -f docker-compose.yml -f docker-compose.nogpu.yml up -d ai-console`.
- **Самопроверка репозитория:** `python -m unittest discover -s tests` (только стандартная библиотека, без GPU и Docker) и `python scripts/make_manifest.py --check`.

## 4. Установка по шагам

### 4.1 Подготовьте Docker

1. Установите Docker Desktop, включите «Use the WSL 2 based engine», при необходимости перезагрузитесь.
2. Убедитесь, что движок Docker **запущен и не на паузе** (в меню кита не должно быть пункта «Resume»).
3. Выполните проверку видеокарты из раздела 2.

### 4.2 Получите код

```
git clone https://github.com/HomenSAI/homensai-local-ai-lab.git local-ai-server
cd local-ai-server
```

(или скачайте ZIP с GitHub и распакуйте). Все команды ниже выполняются из этой папки.

### 4.3 Настройте `.env`

```
python scripts/install.py init        # создаёт .env из .env.example, если его нет
```

Откройте `.env` и задайте как минимум:

| Переменная | Что значит | По умолчанию / пример |
|---|---|---|
| `MODEL_DIR` | Папка на хосте с вашими файлами `.gguf` (контейнеры видят её только для чтения) | `C:/AI/models` или `/data/models` |
| `MEDIA_DIR` | Рабочая папка для необязательных профилей Whisper / изображений | `./media` |
| `AI_CONSOLE_BIND_IP` | Адрес, на котором консоль опубликована кроме `127.0.0.1`. Укажите LAN-адрес ПК, чтобы открывать с других устройств | `127.0.0.1` |
| `AI_CONSOLE_PASSWORD` | Необязательно. Если задан, консоль требует HTTP Basic (любое имя пользователя и этот пароль) для всего, кроме `/health`. **Задайте его до того, как откроете консоль для локальной сети.** `.env` не попадает в Git | пусто (без пароля) |
| `AI_CONSOLE_ALLOWED_HOSTS` | Необязательно, через запятую. Дополнительные имена хоста, которые вы вводите в браузере (например, имя из DNS вашей сети). `localhost` и IP-адреса работают всегда; любой другой `Host` получает `421` | пусто |
| `GITEA_WEB_PORT`, `GITEA_SSH_PORT` | Порты локального Git-сервера | `3010`, `2222` |
| `GITEA_REPORT_OWNER`, `GITEA_REPORT_REPO` | Пользователь и репозиторий Git для версий отчётов | `reports-admin`, `model-test-reports` |
| `UPSTREAM_LLAMA_COMMIT`, `PRISM_LLAMA_COMMIT`, `WHISPER_CPP_COMMIT`, `STABLE_DIFFUSION_CPP_COMMIT` | Зафиксированные коммиты исходников для CUDA-сборок. Не меняйте без причины. | зафиксированы |
| `GATEWAY_PORT`, `HOST_BIND_IP`, `WHISPER_PORT`, `REPORT_PORT`, `AI_CONSOLE_PORT` | Необязательная смена портов | 8080, 127.0.0.1, 8082, 8765, 8766 |

Проекту не нужны ключи API. Единственный секрет, который можно положить в `.env`, — необязательный `AI_CONSOLE_PASSWORD`; `.env` не попадает в Git, никогда не коммитьте его и не вставляйте в чат или обращение.

### 4.4 Создайте папки, сеть и том

`python scripts/install.py init` делает всё это и безопасен при повторе:
- папки `bench_results`, `report`, `results-db`, `media/images`, `benchmark/q4kv-20260929`, `secrets`;
- файлы-заглушки, которые требуют bind-монтирования Docker (`report/report-data.json`, `BENCHMARK_RESULTS.csv`, `BENCHMARK_RESULTS.db`, `media/images/qwen-image-2.1-smoke.png`, `benchmark/q4kv-20260929/recommended-settings-q4kv-20260929.json`);
- сеть Docker `ai-net` и том `llm-models-fast`;
- проверку, что `docker compose config` корректен.

Вручную: `docker network create ai-net` и `docker volume create llm-models-fast`.

### 4.5 Разместите модели

Шлюз читает модели из тома Docker `llm-models-fast` (том ext4 загружает модель за 11–29 с, привязка диска Windows через WSL — минуты). `MODEL_DIR` нужен необязательным профилям Whisper / изображений и как источник, из которого вы заполняете том.

1. **Узнайте, какие файлы нужны.** Каждый профиль в `config/llama-swap.yaml` называет файл после `--model`:
   ```
   grep -o '/models/[^ ]*\.gguf' config/llama-swap.yaml | sort -u
   ```
   Поставляемые профили (контексты измерены на RTX 3080 / 10 ГБ):

   | Профиль | Файлы (относительно корня библиотеки) | Контекст |
   |---|---|---|
   | Qwen3.5-9B-MTP-Q4_K_XL | `Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf` | 192K |
   | Qwen3.5-9B-MTP-Q4_K_XL-Vision | тот же файл + `Qwen3/mmproj-F16.gguf` | 128K |
   | Qwen3.5-9B-Q5_K_S | `Qwen3/Qwen3.5-9B-Q5_K_S-4.60bpw.gguf` | 256K |
   | MiniCPM5-2B-Q8_0 | `MiniCPM5/MiniCPM5-2B-Q8_0.gguf` | 128K |
   | Spark-X2.5-4B-Q8_0 | `Spark/Spark-X2.5-4B-Q8_0.gguf` | 256K |
   | Ternary-Bonsai-2-27B-PTQ1_0 | `Ternary-Bonsai-2-27B-PTQ1_0.gguf` | 128K |
   | Qwen3-VL-8B-Instruct-Q4_K_M | `Qwen-Image-2.1/text_encoder/Qwen3VL-8B-Instruct-Q4_K_M.gguf` + `mmproj-Qwen3VL-8B-Instruct-F16.gguf` | 64K |
   | Ornith-1.5-9B-MTP | `top/Ornith-1.5-9B/Ornith-1.5-9B-Q4_K_M.gguf` | 128K |
   | Qwen3-Embedding-0.6B / 4B | `top/Qwen3-Embedding-0.6B/...-Q8_0.gguf`, `top/Qwen3-Embedding-4B/...-Q4_K_M.gguf` | 8K |
   | Qwen2.5-Coder-7B, Llama-3.1-8B, Gemma-3-12B | `cand/<имя>/...Q4_K_M.gguf` | 64K |
   | MiMo-V2.6-Distill-Qwen-9B | `top/MiMo-V2.6-Distill-Qwen-9B/...Q4_K_M.gguf` | 256K |

2. **Скачайте только нужное.** В `MODELS.md` перечислены репозитории Hugging Face, ревизии и суммы SHA-256 моделей, которые зафиксировал автор. Для профиля, источник которого не указан, найдите точное имя файла на Hugging Face, прочтите карточку модели и проверьте лицензию (часть лицензий ограничивает коммерческое использование или требует указания авторства). **Все модели не обязательны**: удалите ненужные профили из `config/llama-swap.yaml` (профиль без файла в консоли отображается как «файл не найден»).
3. **Проверьте целостность**: сравните `sha256sum <файл>` с `MODELS.md` / страницей модели.
4. **Скопируйте файлы в том**, сохраняя подпапки из таблицы (пример для одного файла; повторите для каждого файла или папки):
   ```
   docker run --rm -v llm-models-fast:/models -v "C:/AI/models:/src:ro" alpine sh -c "mkdir -p /models/Qwen3 && cp /src/Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf /models/Qwen3/"
   ```
   В Git Bash для Windows добавьте перед командой `MSYS_NO_PATHCONV=1` или используйте PowerShell.
5. **Начните с одной небольшой модели**, чтобы проверить всю цепочку (например `MiniCPM5-2B-Q8_0`, 2,7 ГБ), потом добавьте остальные.

### 4.6 Соберите образы

`python scripts/install.py build` выполняет команды ниже (по одной сборке за раз, чтобы экономить память; CUDA-компиляция в первый раз занимает 15–40 минут, потом работает кэш):

```
docker compose --profile build build build-upstream      # local/ai-server-upstream:local  (llama.cpp с CUDA, зафиксированный коммит)
docker compose --profile build build build-bonsai        # local/ai-server-bonsai:local    (форк PrismML, только для модели Bonsai)
docker compose --profile gateway build llama-swap-gateway  # local/ai-server-llama-swap:260 (llama-swap v260, проверка SHA-256)
docker compose build ai-console report-versioner         # образы консоли и версионера
```

Если модель Bonsai не нужна, соберите только `build-upstream`, задайте `PRISM_IMAGE=local/ai-server-upstream:local` как аргумент сборки `llama-swap-gateway` (или `--build-arg`) и уберите профиль Bonsai из `config/llama-swap.yaml`.

### 4.7 Запустите

```
python scripts/install.py up
```

это то же самое, что:

```
docker compose up -d ai-console report-builder stats-report gitea report-versioner
docker compose --profile gateway up -d llama-swap-gateway
```

Шлюзу нужно около 30 с, чтобы стать `healthy`; он стартует **без загруженных моделей** (первый запрос к модели загружает её, до минуты). Откройте **http://localhost:8766/**.

### 4.8 Настройте Git-сервер для версий отчётов

```
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 git     # Windows
python scripts/install.py git                                   # Linux
```

Скрипт запускает Gitea, создаёт администратора, токен для версионера, SSH-ключ и закрытый репозиторий, запускает `report-versioner`. Пароли и ключи записываются только в `secrets/` (игнорируется Git, никогда не публикуется). Веб-интерфейс: `http://localhost:3010/` (логин в `secrets/gitea-admin.txt`). Клонировать версии:

```
git clone -c core.sshCommand="ssh -i secrets/id_ed25519 -o StrictHostKeyChecking=accept-new -p 2222" ssh://git@127.0.0.1:2222/reports-admin/model-test-reports.git
```

### 4.9 Доступ с других устройств сети (необязательно)

1. В `.env` задайте `AI_CONSOLE_PASSWORD=<длинный пароль>` и `AI_CONSOLE_BIND_IP=<LAN-адрес этого ПК>` (добавьте `AI_CONSOLE_ALLOWED_HOSTS`, если открываете по имени хоста), затем пересоздайте консоль: `docker compose up -d --force-recreate --no-deps ai-console`.
2. Откройте порт в брандмауэре только для вашей подсети (PowerShell от администратора):
   ```
   New-NetFirewallRule -DisplayName "AI console 8766 (LAN)" -Direction Inbound -Protocol TCP -LocalPort 8766 -RemoteAddress 192.168.0.0/24 -Profile Any -Action Allow
   ```
   (подставьте свою подсеть). Никогда не открывайте консоль в интернет, с паролем или без: Basic-аутентификация передаёт пароль без шифрования, поэтому используйте её только в доверенной сети или за VPN / TLS-прокси.

## 5. Необязательные компоненты

### Open WebUI (чат-интерфейс)

```
docker run -d --name open-webui --restart unless-stopped -p 3000:8080 -v open-webui:/app/backend/data ghcr.io/open-webui/open-webui:main
docker network connect local-ai-server_default open-webui
powershell -File scripts/configure-openwebui-gateway.ps1
```

Скрипт прописывает шлюз `http://llama-swap-gateway:8080/v1` как подключение OpenAI. У Open WebUI собственные условия лицензии; см. `legal/NOTICE-THIRD-PARTY.md`.

### Экспортёр телеметрии

```
cd hermes-telemetry
docker compose -f compose.yaml up -d --build
```

Публикует `/metrics` и `/health` на `127.0.0.1:9835` (чтобы открыть по сети, задайте `TELEMETRY_BIND_IP`). Нужны сети `ai-net` и `local-ai-server_default` (создаются `init` и первым `up`).

### Генерация видео: отдельный проект «Video Studio»

Генерация видео (Wan 2.1 1.3B + ComfyUI, раскадровка из идеи, отчёты по видео) **больше не входит в этот проект**: это самостоятельный проект **Video Studio** (свой репозиторий, своя консоль на порту 8767, своё руководство по установке). Проекты работают рядом:
- в шапке этой консоли есть ссылка «Генерация видео», которая открывает Video Studio (`http://ХОСТ:8767/`);
- Video Studio подключается к сети Docker `local-ai-server_default` этого проекта, чтобы достучаться до шлюза (перед видео он выгружает модели шлюза и составляет раскадровки вашей локальной LLM);
- эта консоль не даёт запустить LLM, пока контейнер ComfyUI из Video Studio держит видеокарту (имя контейнера `video-generation-comfyui-video-1`).
Сначала установите этот проект, потом Video Studio.

### Профили распознавания речи и генерации изображений

`docker compose --profile whisper build whisper` и `--profile qwen-image build qwen-image` собирают необязательные профили Whisper (речь в текст) и Qwen-Image; им нужны файлы моделей в `MODEL_DIR` (см. `.env`, `WHISPER_MODEL`, `QWEN_IMAGE_*`), по умолчанию они не запускаются.

## 6. Проверка

`python scripts/install.py verify` выполняет эти проверки; их можно запустить и вручную:

| Что | Команда | Ожидаемо |
|---|---|---|
| GPU в Docker | `docker run --rm --gpus all nvidia/cuda:12.8.1-runtime-ubuntu24.04 nvidia-smi` | таблица с вашей видеокартой |
| Шлюз | `curl http://localhost:8080/v1/models` | JSON со списком профилей |
| Консоль | `curl http://localhost:8766/health` | `{"ok": true}` |
| Каталог моделей | `curl http://localhost:8766/api/models` | у скопированных файлов `"exists": true` |
| Статус | `curl http://localhost:8766/api/status` | `docker_available: true` |
| Отчёт | откройте `http://localhost:8766/report/` | страница открывается, в подвале лицензия |
| Старый адрес | `curl -I http://localhost:8765/` | `301` на порт 8766 |
| Git | `curl http://localhost:3010/api/healthz` | 200 |
| Контейнеры | `docker ps --format "{{.Names}} {{.Status}}"` | `healthy` у консоли, шлюза, report-builder, gitea, versioner |
| Первая модель | в консоли нажмите **Старт** у модели, потом чат | приходит ответ; `curl localhost:8080/running` показывает модель |

Если задан `AI_CONSOLE_PASSWORD`, добавляйте `-u any:ПАРОЛЬ` к вызовам `curl` консоли (кроме `/health`). На ПК без видеокарты используйте `python scripts/install.py verify --no-gpu`: проверки шлюза пропускаются.

## 7. Работа с консолью

- **Язык**: переключатель RU / EN / DE в шапке (запоминается в браузере).
- **1 Состояние** показывает, что сейчас в памяти; **2 Запуск** — список моделей со Стартом / Стопом (Старт загружает модель в видеопамять, Стоп выгружает); карточки моделей показывают квантование, контекст, файл, подобранные параметры.
- **3 Диалог** общается с выбранной моделью через шлюз (модели с «зрением» принимают изображения). **Таймер выгрузки** выгружает все модели через N секунд.
- **Результаты тестов** показывают каждую модель со всеми тестами, сортировка по любому тесту, полоса прогресса идущего теста, оценка времени до конца всех тестов и список этапов.
- **Генерация видео ↗** в шапке открывает отдельный проект Video Studio.
- **Отчёт и результаты** (`/report/`): полные таблицы, графики, рекомендации, загрузки.

## 8. Результаты тестов, отчёты и версии в Git

- Бенчмарки пишут `bench_results/results*.jsonl` (по одному JSON-объекту в строке: `model`, оценки, скорости, …). Сборщик отчёта объединяет их, не удаляя старые результаты, в SQLite (`results-db/llm-results.sqlite`) и строит `report/live-data.json`. Раннеры тестов, которыми получены опубликованные результаты, лежат в `benchmarks/` и запускаются в Docker: `docker compose --profile bench up -d --build bench-runner` (см. `benchmarks/README.md`); подойдёт и любой другой инструмент, который пишет такие же файлы.
- `report-versioner` при каждом изменении сохраняет в Gitea `results/`, `tables/`, `report/` и JSON-выгрузку базы: коммиты `vNNNN`, завершённые этапы получают `stage-<этап>-done`, конец всех тестов — `final-<дата>`. История не переписывается. Старый отчёт восстанавливается командой `git checkout v0042`.
- План этапов и общая оценка берутся из `scripts/build_live_report.py` (`DEFAULT_PLAN`) и могут быть заменены файлом `bench_results/benchmark_plan.json`.

## 9. Обслуживание: обновление, копия, удаление

- **Обновить код**: `git pull`, затем `docker compose up -d --build ai-console report-versioner`. После правки `config/llama-swap.yaml` выполните `docker compose --profile gateway up -d --force-recreate --no-deps llama-swap-gateway` (одиночный файл в bind-монтировании иначе не обновится после замены).
- **Резервная копия**: `.env`, `config/`, `bench_results/`, `results-db/`, тома Docker `gitea-data`, `gitea-config`, `ai-console-state` и `secrets/`. Модели можно скачать заново.
- **Остановить всё**: `docker compose --profile gateway down`.
- **Удалить вместе с данными** (необратимо): `docker compose --profile gateway down -v` (удаляет тома, кроме внешнего `llm-models-fast`); том с моделями удалите сами: `docker volume rm llm-models-fast`.

## 10. Заметки по Linux / macOS

- **Linux**: установите Docker Engine, драйвер NVIDIA и NVIDIA Container Toolkit, проверьте `docker run --rm --gpus all ... nvidia-smi`. Файлы compose не зависят от платформы; используйте `python scripts/install.py ...` и прямые слэши в путях `.env`. Скрипты `.ps1` — необязательное удобство для PowerShell. Проект разработан и проверен на Windows 10 + Docker Desktop; на Linux должен работать, но автор его не проверял.
- **macOS**: CUDA нет, поэтому GPU-образы не работают. Не поддерживается.
- Если на Linux консоль не видит сокет Docker, проверьте, что `/var/run/docker.sock` существует (консоль использует его, чтобы видеть контейнеры и читать состояние `llama-server`).

## 11. Если что-то не работает

| Симптом | Причина / решение |
|---|---|
| `Docker Desktop is manually paused` | Снимите паузу в меню кита; CLI `docker desktop` её снять не умеет. |
| `port is already allocated` | Порт занят другой программой; поменяйте `GITEA_WEB_PORT`, `AI_CONSOLE_PORT` и т. д. в `.env` (doctor показывает занятые порты). |
| `could not select device driver "nvidia"` | Видеокарта недоступна Docker: обновите драйвер NVIDIA, включите интеграцию WSL2, перезапустите Docker Desktop. |
| `docker compose` ругается на отсутствующий источник bind | Выполните `python scripts/install.py init` (создаёт заглушки и папки). |
| В карточке модели «файл не найден» | Файла нет в томе `llm-models-fast` по точному пути профиля (раздел 4.5). |
| Первый ответ идёт минуту | Шлюз загружает модель в видеопамять; дальше ответы быстрые. |
| Не хватает видеопамяти | VRAM держит другая программа или контейнер видео; диагностика консоли называет держателей. Возьмите меньший контекст или квантование. |
| Git Bash искажает пути `/models` | Добавьте `MSYS_NO_PATHCONV=1` или используйте PowerShell. |
| В консоли на EN/DE есть русский текст | Тексты из ваших данных (промпты, ответы моделей, журналы) никогда не переводятся. Новые надписи интерфейса нужно добавить в `console/i18n-dict.js` (`node scripts/check_i18n.js de` перечисляет недостающие). |
| Страница отчёта пустая | Это нормально, пока нет первого `bench_results/results*.jsonl`. |
| `doctor` пишет, что образ CUDA для проверки не скачан | Сам он 5,6 ГБ не скачивает. Спросите владельца, затем `python scripts/install.py doctor --pull`, либо используйте `--no-gpu` на ПК без видеокарты. |
| `docker compose up` падает с «could not select device driver» / «no known GPU vendor» | Docker не видит видеокарту. Используйте `python scripts/install.py up --no-gpu`. |
| Скрипт или `curl` получает от консоли `415`, `421`, `403` или `401` | Консоль проверяет каждый запрос: для `POST` нужен `Content-Type: application/json`, `Host` должен быть `localhost` или IP (или быть в `AI_CONSOLE_ALLOWED_HOSTS`), может потребоваться пароль (`curl -u any:ПАРОЛЬ`). См. [API.ru.md](API.ru.md). |
| Браузер показывает `421`, когда консоль открыта по имени хоста | Добавьте имя в `AI_CONSOLE_ALLOWED_HOSTS` в `.env` и пересоздайте консоль. |

## 12. Безопасность

- У шлюза **нет аутентификации**; у консоли есть необязательный пароль (`AI_CONSOLE_PASSWORD`). Держите оба на `127.0.0.1` или в доверенной подсети; никогда не публикуйте порты 8766 / 8080 / 3010 в интернет.
- Консоль отклоняет чужие имена `Host`, межсайтовые и не-JSON запросы `POST` и отправляет заголовки безопасности; поэтому страница, открытая в том же браузере, не может управлять моделями.
- Контейнер консоли монтирует `/var/run/docker.sock`; флаг `read_only` его не защищает. Консоль отправляет через сокет только один фиксированный вид команд и работает без привилегий, но доступ к консоли всё равно равен доступу к Docker на этом ПК. Подробности: [SECURITY.ru.md](../SECURITY.ru.md).
- В Gitea регистрация отключена и нужен вход; пароль и токен лежат только в `secrets/`.
- Файлы моделей приходят от третьих лиц: проверяйте SHA-256 и читайте их лицензии.
- О проблемах сообщайте приватно, см. [SECURITY.ru.md](../SECURITY.ru.md).

## 13. Лицензия и указание авторства

Результаты, отчёты и тексты: **CC BY 4.0**, указание «homensai.com (https://homensai.com)». Код: **MIT**. Сторонние программы и модели сохраняют свои лицензии: см. `legal/NOTICE-THIRD-PARTY.md`. Это не юридическая консультация.
