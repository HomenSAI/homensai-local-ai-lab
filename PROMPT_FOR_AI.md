# Start here: the prompt for your AI assistant

**English** · [Русский](#русский) · [Deutsch](#deutsch)

## English

**Do you need this?** No: the server installs with six commands that you can run yourself (README, "Quick start"). An assistant is a convenience: it runs the same commands, chooses and downloads models, reads the logs when something fails and later runs and checks your tests.

**How it works.** You open an AI assistant **that can run commands on your PC** (Claude Code with Sonnet or Opus, a ChatGPT/Codex agent, or another coding agent), point it at this repository (clone it, or give it the folder), and paste the prompt below. The assistant builds everything exactly as the author did - Docker, the containers, the AI server, the console, the reports - checks it, and finishes with the message **"All ready - start testing"** plus a status table. From then on it also runs and supervises your tests ([docs/AI_OPERATOR.en.md](docs/AI_OPERATOR.en.md)).

A plain browser chat (without access to your computer) cannot do this: it can only explain the steps.

**Prompt - copy everything in the box:**

```
You are the installer and supervisor of the project in this folder ("Local AI Server": a llama.cpp/llama-swap model server for one NVIDIA GPU, a web console, test reports with Git history). Build it on THIS computer exactly as the author did and then tell me it is ready for testing.

Read first: AGENTS.md (or CLAUDE.md), docs/INSTALL.en.md, docs/AI_OPERATOR.en.md, docs/API.md.

Work in this order and report briefly after each step:
0. Prerequisites. Check: Windows 10/11 (or Linux with NVIDIA Container Toolkit), an NVIDIA GPU and driver (`nvidia-smi`), WSL2, Docker Desktop running and NOT paused, Docker Compose v2. On Windows nothing else is needed: use the PowerShell installer `powershell -ExecutionPolicy Bypass -File scripts\install.ps1 <step>` (do not install Python, Git or Node on Windows). On Linux use `python scripts/install.py <step>` (Python 3.10+). Below, `install <step>` means the installer of this system. If something is missing, tell me what and how you would install it (for example `wsl --install`, `winget install Docker.Desktop`) and WAIT for my yes: installing system software and reboots are my decision.
1. `install doctor` - fix everything it reports (ports busy, GPU not visible in Docker, little disk space), ask me if the fix is not obvious. It does not download the 5.6 GB CUDA test image by itself: ask me before `doctor --pull` (`-Pull` in PowerShell). If this PC has no NVIDIA GPU, tell me and use `--no-gpu` (`-NoGpu`) for doctor / build / up / verify.
2. `install init` - then ask me for: the folder for model files (MODEL_DIR), and whether the console should be reachable from other devices on my network (AI_CONSOLE_BIND_IP; default: this PC only). Write the answers into .env. If the console must be reachable from other devices, ask me for a password and put it into `AI_CONSOLE_PASSWORD` in .env (never anywhere that goes to Git).
3. Models: ask me which models I want (default for a first run: the small smoke-test model MiniCPM5-2B-Q8_0, about 2.7 GB). Download only from the sources and revisions listed in MODELS.md, verify SHA-256, place the files in the Docker volume as in section 4.5 of docs/INSTALL.en.md. Ask me before any download larger than 1 GB. Do not invent sources.
4. `install build` (15-40 minutes the first time), `install up`, then `install git` (the local Git server that keeps every version of the reports).
5. `install verify` - every line must be [ok]. Then prove the chain works: load the smoke-test model through the console API and get one real answer from it through the gateway; show me the answer, the speed (tokens/s) and the GPU memory used.
6. Optional, only if I ask: Open WebUI, Video Studio (separate repository).

Rules: one model in video memory at a time; never open ports 8766/8080/3010 to the internet; never write secrets or personal data into files that go to Git; ask before deleting anything; if a command fails read the log (`docker logs <container>`), fix the cause and do not retry blindly.

FINISH with exactly this message (fill it in from real checks, do not guess):
"All ready - start testing.
 Console: http://localhost:8766/   Report: http://localhost:8766/report/   Gateway API: http://localhost:8080/v1
 Version: <from /api/version>   GPU: <name, memory>   Models installed: <list>   verify: <n of n ok>
 Smoke test: <model> answered '<answer>' at <tokens/s> tok/s.
 Warnings: <anything that is not perfect, or 'none'>.
 Next: tell me which tests to run on which models (see docs/AI_OPERATOR.en.md) and I will run and check them."
```

## Русский

**Нужно ли это?** Нет: сервер ставится шестью командами, которые можно выполнить самому (README, «Быстрый старт»). Ассистент — удобство: он выполнит те же команды, подберёт и скачает модели, разберёт журналы, если что-то не так, а потом запустит и проверит ваши тесты.

**Как это работает.** Вы открываете ИИ-ассистента, **который умеет выполнять команды на вашем ПК** (Claude Code с Sonnet или Opus, агент ChatGPT/Codex или другой кодовый агент), указываете ему этот репозиторий (клонируете или даёте папку) и вставляете промпт ниже. Ассистент собирает всё так же, как у автора, — Docker, контейнеры, ИИ-сервер, консоль, отчёты, — проверяет и заканчивает сообщением **«Всё готово — тестируй»** с таблицей состояния. Дальше он же запускает и контролирует ваши тесты ([docs/AI_OPERATOR.ru.md](docs/AI_OPERATOR.ru.md)).

Обычный чат в браузере (без доступа к вашему компьютеру) этого сделать не может: он только объяснит шаги.

**Промпт — скопируйте всё из рамки:**

```
Ты — установщик и супервизор проекта в этой папке («Local AI Server»: сервер моделей llama.cpp/llama-swap для одной видеокарты NVIDIA, веб-консоль, отчёты по тестам с историей в Git). Собери его на ЭТОМ компьютере в точности так, как у автора, и затем сообщи мне, что всё готово к тестированию.

Сначала прочитай: AGENTS.md (или CLAUDE.md), docs/INSTALL.ru.md, docs/AI_OPERATOR.ru.md, docs/API.md.

Работай по порядку и коротко отчитывайся после каждого шага:
0. Предпосылки. Проверь: Windows 10/11 (или Linux с NVIDIA Container Toolkit), видеокарту и драйвер NVIDIA (`nvidia-smi`), WSL2, запущенный и НЕ приостановленный Docker Desktop, Docker Compose v2. На Windows больше ничего не нужно: используй установщик на PowerShell `powershell -ExecutionPolicy Bypass -File scripts\install.ps1 <шаг>` (не ставь на Windows Python, Git и Node). На Linux — `python scripts/install.py <шаг>` (Python 3.10+). Ниже `install <шаг>` — установщик этой системы. Если чего-то нет, скажи, чего и как ты это поставишь (например `wsl --install`, `winget install Docker.Desktop`) и ЖДИ моего «да»: установка системных программ и перезагрузки — моё решение.
1. `install doctor` — исправь всё, что он покажет (занятые порты, видеокарта не видна в Docker, мало места), если исправление неочевидно — спроси меня. Образ CUDA на 5,6 ГБ он сам не скачивает: спроси меня перед `doctor --pull` (`-Pull` в PowerShell). Если на ПК нет видеокарты NVIDIA, скажи мне и используй `--no-gpu` (`-NoGpu`) для doctor / build / up / verify.
2. `install init` — затем спроси меня: папку для файлов моделей (MODEL_DIR) и нужен ли доступ к консоли с других устройств сети (AI_CONSOLE_BIND_IP; по умолчанию — только этот ПК). Запиши ответы в .env. Если консоль нужна с других устройств, спроси у меня пароль и запиши его в `AI_CONSOLE_PASSWORD` в .env (никуда, что попадает в Git).
3. Модели: спроси, какие модели я хочу (для первого запуска по умолчанию — маленькая проверочная модель MiniCPM5-2B-Q8_0, около 2,7 ГБ). Скачивай только из источников и ревизий, указанных в MODELS.md, проверь SHA-256, положи файлы в том Docker по разделу 4.5 docs/INSTALL.ru.md. Перед любой загрузкой больше 1 ГБ спрашивай меня. Не выдумывай источники.
4. `install build` (в первый раз 15–40 минут), `install up`, затем `install git` (локальный Git, который хранит каждую версию отчётов).
5. `install verify` — каждая строка должна быть [ok]. Затем докажи, что цепочка работает: загрузи проверочную модель через API консоли и получи от неё один настоящий ответ через шлюз; покажи ответ, скорость (токенов/с) и занятую видеопамять.
6. По желанию и только если я попрошу: Open WebUI, Video Studio (отдельный репозиторий).

Правила: одна модель в видеопамяти за раз; никогда не открывай порты 8766/8080/3010 в интернет; не записывай секреты и персональные данные в файлы, попадающие в Git; перед удалением чего-либо спрашивай; если команда падает, читай лог (`docker logs <контейнер>`), устраняй причину и не повторяй вслепую.

ЗАВЕРШИ ровно таким сообщением (заполни по реальным проверкам, не угадывай):
«Всё готово — тестируй.
 Консоль: http://localhost:8766/   Отчёт: http://localhost:8766/report/   API шлюза: http://localhost:8080/v1
 Версия: <из /api/version>   GPU: <название, память>   Модели: <список>   verify: <n из n ok>
 Проверка: модель <имя> ответила «<ответ>» со скоростью <ток/с> ток/с.
 Предупреждения: <всё, что не идеально, или «нет»>.
 Дальше: скажи, какие тесты на каких моделях запускать (см. docs/AI_OPERATOR.ru.md), я запущу и проверю».
```

## Deutsch

**Brauchen Sie das?** Nein: Der Server lässt sich mit sechs Befehlen selbst installieren (README, „Schnellstart“). Ein Assistent ist eine Erleichterung: Er führt dieselben Befehle aus, wählt und lädt Modelle, liest bei Fehlern die Logs und führt später Ihre Tests aus und prüft sie.

**So funktioniert es.** Sie öffnen einen KI-Assistenten, **der Befehle auf Ihrem PC ausführen kann** (Claude Code mit Sonnet oder Opus, ein ChatGPT-/Codex-Agent oder ein anderer Coding-Agent), zeigen ihm dieses Repository (klonen oder den Ordner geben) und fügen den folgenden Prompt ein. Der Assistent baut alles genau wie der Autor – Docker, die Container, den KI-Server, die Konsole, die Berichte –, prüft es und endet mit der Meldung **„Alles bereit – jetzt testen“** samt Statustabelle. Danach führt und überwacht er auch Ihre Tests ([docs/AI_OPERATOR.de.md](docs/AI_OPERATOR.de.md)).

Ein gewöhnlicher Browser-Chat (ohne Zugriff auf Ihren Rechner) kann das nicht: Er kann die Schritte nur erklären.

**Prompt – alles aus dem Kasten kopieren:**

```
Du bist Installateur und Supervisor des Projekts in diesem Ordner („Local AI Server“: ein llama.cpp/llama-swap-Modellserver für eine NVIDIA-GPU, eine Web-Konsole, Testberichte mit Git-Historie). Baue ihn auf DIESEM Computer genau so, wie der Autor es getan hat, und melde mir danach, dass er testbereit ist.

Lies zuerst: AGENTS.md (oder CLAUDE.md), docs/INSTALL.de.md, docs/AI_OPERATOR.de.md, docs/API.md.

Arbeite in dieser Reihenfolge und berichte nach jedem Schritt kurz:
0. Voraussetzungen. Prüfe: Windows 10/11 (oder Linux mit NVIDIA Container Toolkit), NVIDIA-GPU und -Treiber (`nvidia-smi`), WSL2, laufendes und NICHT pausiertes Docker Desktop, Docker Compose v2. Unter Windows wird sonst nichts gebraucht: verwende den PowerShell-Installer `powershell -ExecutionPolicy Bypass -File scripts\install.ps1 <Schritt>` (installiere unter Windows kein Python, Git oder Node). Unter Linux `python scripts/install.py <Schritt>` (Python 3.10+). Unten bedeutet `install <Schritt>` den Installer dieses Systems. Fehlt etwas, sage mir was und wie du es installieren würdest (z. B. `wsl --install`, `winget install Docker.Desktop`) und WARTE auf mein „Ja“: Systemsoftware und Neustarts entscheide ich.
1. `install doctor` – behebe alles, was gemeldet wird (belegte Ports, GPU in Docker nicht sichtbar, wenig Speicher); frage mich, wenn die Lösung nicht offensichtlich ist. Das 5,6-GB-CUDA-Image lädt er nicht von selbst: frage mich vor `doctor --pull` (`-Pull` in PowerShell). Hat der PC keine NVIDIA-GPU, sage es mir und verwende `--no-gpu` (`-NoGpu`) für doctor / build / up / verify.
2. `install init` – frage mich dann nach: dem Ordner für Modelldateien (MODEL_DIR) und ob die Konsole von anderen Geräten im Netzwerk erreichbar sein soll (AI_CONSOLE_BIND_IP; Standard: nur dieser PC). Schreibe die Antworten in .env. Soll die Konsole von anderen Geräten erreichbar sein, frage mich nach einem Passwort und trage es in `AI_CONSOLE_PASSWORD` in .env ein (nie dorthin, was in Git landet).
3. Modelle: Frage, welche Modelle ich möchte (Standard für den ersten Lauf: das kleine Testmodell MiniCPM5-2B-Q8_0, etwa 2,7 GB). Lade nur aus den in MODELS.md genannten Quellen und Revisionen, prüfe SHA-256, lege die Dateien wie in Abschnitt 4.5 von docs/INSTALL.de.md ins Docker-Volume. Frage mich vor jedem Download über 1 GB. Erfinde keine Quellen.
4. `install build` (beim ersten Mal 15–40 Minuten), `install up`, dann `install git` (der lokale Git-Server, der jede Version der Berichte aufbewahrt).
5. `install verify` – jede Zeile muss [ok] sein. Beweise dann, dass die Kette funktioniert: Lade das Testmodell über die Konsolen-API und hole über das Gateway eine echte Antwort; zeige mir Antwort, Geschwindigkeit (Tokens/s) und belegten Videospeicher.
6. Optional und nur auf meine Bitte: Open WebUI, Video Studio (eigenes Repository).

Regeln: ein Modell gleichzeitig im Videospeicher; öffne die Ports 8766/8080/3010 nie ins Internet; schreibe keine Geheimnisse oder personenbezogenen Daten in Dateien, die in Git landen; frage vor jedem Löschen; scheitert ein Befehl, lies das Log (`docker logs <Container>`), behebe die Ursache und wiederhole nicht blind.

BEENDE mit genau dieser Meldung (aus echten Prüfungen ausfüllen, nicht raten):
„Alles bereit – jetzt testen.
 Konsole: http://localhost:8766/   Bericht: http://localhost:8766/report/   Gateway-API: http://localhost:8080/v1
 Version: <aus /api/version>   GPU: <Name, Speicher>   Modelle: <Liste>   verify: <n von n ok>
 Test: Modell <Name> antwortete „<Antwort>“ mit <Tokens/s> Tok/s.
 Warnungen: <alles, was nicht perfekt ist, oder „keine“>.
 Als Nächstes: sagen Sie mir, welche Tests auf welchen Modellen laufen sollen (siehe docs/AI_OPERATOR.de.md), ich führe sie aus und prüfe sie.“
```
