# Installationsanleitung (Deutsch)

Andere Sprachen: [English](INSTALL.en.md) · [Русский](INSTALL.ru.md) · Zurück zur [README](../README.de.md)

Diese Anleitung führt Sie von einem leeren Rechner zu einem funktionierenden **Local AI Server**: ein Gateway, das ein lokales Sprachmodell nach dem anderen in den Videospeicher einer einzelnen NVIDIA-Grafikkarte lädt; eine Web-Konsole (Modelle, Chat, Tests, Videogenerierung, Berichte) in drei Sprachen; automatische Testberichte und ein lokaler Git-Server, der jede Version der Berichte aufbewahrt.

> Urheberschaft und Rechte: Ergebnisse und Berichte stehen unter **CC BY 4.0** (nutzen und weitergeben erlaubt, aber **mit Verweis auf den Autor**, <https://homensai.com>); der Code steht unter **MIT**. Modellgewichte sind **nicht** Teil dieses Pakets und behalten ihre eigenen Lizenzen. Siehe Ordner `legal/`.

## Inhalt

1. [Was Sie bekommen](#1-was-sie-bekommen)
2. [Voraussetzungen](#2-voraussetzungen)
3. [Schneller Weg: das Installationsskript](#3-schneller-weg-das-installationsskript)
4. [Installation Schritt für Schritt](#4-installation-schritt-für-schritt)
5. [Optionale Komponenten](#5-optionale-komponenten)
6. [Überprüfung](#6-überprüfung)
7. [Die Konsole benutzen](#7-die-konsole-benutzen)
8. [Testergebnisse, Berichte und Git-Versionen](#8-testergebnisse-berichte-und-git-versionen)
9. [Wartung: Aktualisieren, Sichern, Entfernen](#9-wartung-aktualisieren-sichern-entfernen)
10. [Hinweise zu Linux / macOS](#10-hinweise-zu-linux--macos)
11. [Fehlersuche](#11-fehlersuche)
12. [Sicherheit](#12-sicherheit)
13. [Lizenz und Namensnennung](#13-lizenz-und-namensnennung)

## 1. Was Sie bekommen

| Teil | Container | Port (auf diesem PC) | Aufgabe |
|---|---|---|---|
| Gateway (llama-swap) | `ai-llama-swap-gateway` | 8080 | OpenAI-kompatible API. Startet `llama-server` für das angefragte Modell und entlädt das vorherige. |
| Konsole | `ai-model-console` | 8766 | Weboberfläche: Modellkatalog mit Start/Stopp, Chat, GPU-Telemetrie, Diagnose, Entlade-Timer, Testergebnisse und der **Bericht** unter `/report/`. Sprachen: RU / EN / DE (Umschalter in der Kopfzeile). |
| Berichtsgenerator | `ai-report-builder` | – | Wandelt alle 15 s die Ergebnisdateien der Benchmarks in `report/live-data.json` und das SQLite-Archiv `results-db/llm-results.sqlite` um. |
| Berichts-Weiterleitung | `ai-stats-report` | 8765 | Alte Adresse: leitet auf `http://HOST:8766/report/` weiter. |
| Git-Server | `ai-gitea` | 3010 (Web), 2222 (ssh) | Lokales Gitea mit dem privaten Repository `reports-admin/model-test-reports`. |
| Versionierer | `ai-report-versioner` | – | Speichert jede Minute geänderte Ergebnisse und Berichte in Gitea (Tags `v0001`, `v0002`, …, `stage-<Phase>-done`, `final-<Datum>`). |
| Telemetrie (optional) | `hermes-telemetry` | 9835 | GPU- und llama-Metriken im Prometheus-Format für einen externen Collector. |
| Video Studio (eigenes Projekt, optional) | `video-studio-console`, `video-generation-comfyui-video-1` | 8767, 8188 | Videogenerierung (ComfyUI + Wan 2.1). Eigenes Repository und eigene Anleitung. |
| Open WebUI (optional) | `open-webui` | 3000 | Chat-Oberfläche, die mit dem Gateway verbunden ist. |

In 10 GB Videospeicher passt ein großes Modell, deshalb hält das Gateway **immer nur ein Modell geladen**; die Konsole startet kein LLM, solange Video Studio ein Video generiert (und Video Studio entlädt die Modelle vor dem Start).

## 2. Voraussetzungen

**Hardware**
- NVIDIA-Grafikkarte mit mindestens 8 GB Videospeicher (Autor: RTX 3080, 10 GB). Modelle und Kontextgrößen in `config/llama-swap.yaml` sind auf 10 GB abgestimmt; bei weniger Speicher kleinere Modelle/Kontexte wählen.
- Mindestens 16 GB RAM, empfohlen 32 GB (das Bauen der CUDA-Images und das Laden von 9–27B-Modellen braucht viel RAM).
- Freier Speicherplatz: etwa 25 GB für Docker-Images, 50–200 GB für Modelle.

**Software**
- Windows 10/11 mit **Docker Desktop (WSL2-Backend)** und aktuellem NVIDIA-Treiber (CUDA-12.8-fähig). Das ist die getestete Konfiguration. Für Linux siehe Abschnitt 10.
- Docker Compose v2 (in Docker Desktop enthalten), Python 3.10+ (für die Hilfsskripte, keine zusätzlichen Pakete), Git.
- Internetzugang zum Bauen der Images und zum Herunterladen der Modelle.

**Prüfen Sie zuerst die GPU in Docker** (muss Ihre Grafikkarte ausgeben):

```
docker run --rm --gpus all nvidia/cuda:12.8.1-runtime-ubuntu24.04 nvidia-smi
```

Empfohlene `%USERPROFILE%\.wslconfig` für einen PC mit 32 GB (nach dem Bearbeiten `wsl --shutdown` ausführen):

```
[wsl2]
memory=24GB
processors=8
swap=8GB
```

## 3. Schneller Weg: das Installationsskript

```
git clone https://github.com/HomenSAI/homensai-local-ai-lab.git local-ai-server
cd local-ai-server
python scripts/install.py doctor      # prüft Docker, GPU in Docker, freie Ports und Speicherplatz (lädt selbst nichts herunter; siehe unten)
python scripts/install.py init        # erstellt .env, Ordner, Platzhalter, Docker-Netzwerk und -Volume
# jetzt .env bearbeiten: MODEL_DIR (und AI_CONSOLE_BIND_IP für Netzwerkzugriff), dann die Modelle bereitstellen (Abschnitt 4.5)
python scripts/install.py build       # baut die Images (beim ersten Mal 15–40 Minuten)
python scripts/install.py up          # startet alles
python scripts/install.py verify      # HTTP-Prüfung jedes Teils
```

`python scripts/install.py all` führt doctor, init, build, up und verify in einem Zug aus (nach dem Bearbeiten von `.env` verwenden). Jeder Schritt lässt sich gefahrlos wiederholen. Danach **http://localhost:8766/** öffnen.

- **GPU-Prüfung und das 5,6-GB-Image.** `doctor` prüft die GPU mit dem Image `nvidia/cuda:12.8.1-runtime-ubuntu24.04`. Ist es noch nicht auf dem PC, warnt `doctor` nur und überspringt die Prüfung; fragen Sie den Eigentümer und starten Sie `python scripts/install.py doctor --pull`, um es herunterzuladen (5,6 GB).
- **PC ohne NVIDIA-GPU** (um Konsole, Bericht und Git auszuprobieren): `--no-gpu` an `doctor`, `build`, `up` und `verify` anhängen (oder an `all`). Das Gateway wird nicht gestartet, Modelle lassen sich nicht laden; die Konsole startet ohne GPU-Anforderung (`docker-compose.nogpu.yml`). Beim manuellen Start der Konsole: `docker compose -f docker-compose.yml -f docker-compose.nogpu.yml up -d ai-console`.
- **Selbsttest des Repositorys:** `python -m unittest discover -s tests` (nur Standardbibliothek, ohne GPU und Docker) und `python scripts/make_manifest.py --check`.

## 4. Installation Schritt für Schritt

### 4.1 Docker vorbereiten

1. Docker Desktop installieren, „Use the WSL 2 based engine“ aktivieren, bei Aufforderung neu starten.
2. Sicherstellen, dass die Docker-Engine **läuft und nicht pausiert ist** (im Wal-Menü darf kein „Resume“ stehen).
3. Die GPU-Prüfung aus Abschnitt 2 ausführen.

### 4.2 Code beschaffen

```
git clone https://github.com/HomenSAI/homensai-local-ai-lab.git local-ai-server
cd local-ai-server
```

(oder das ZIP von GitHub herunterladen und entpacken). Alle folgenden Befehle werden in diesem Ordner ausgeführt.

### 4.3 `.env` konfigurieren

```
python scripts/install.py init        # erstellt .env aus .env.example, falls es fehlt
```

`.env` öffnen und mindestens diese Variablen setzen:

| Variable | Bedeutung | Standard / Beispiel |
|---|---|---|
| `MODEL_DIR` | Ordner auf dem Host mit Ihren `.gguf`-Dateien (für Container schreibgeschützt) | `C:/AI/models` oder `/data/models` |
| `MEDIA_DIR` | Arbeitsordner für die optionalen Whisper-/Bild-Profile | `./media` |
| `AI_CONSOLE_BIND_IP` | Adresse, unter der die Konsole zusätzlich zu `127.0.0.1` veröffentlicht wird. LAN-Adresse des PCs eintragen, um sie von anderen Geräten zu öffnen | `127.0.0.1` |
| `AI_CONSOLE_PASSWORD` | Optional. Wenn gesetzt, verlangt die Konsole HTTP-Basic-Anmeldung (beliebiger Benutzername, dieses Passwort) für alles außer `/health`. **Vor dem Öffnen der Konsole im LAN setzen.** `.env` wird von Git ignoriert | leer (kein Passwort) |
| `AI_CONSOLE_ALLOWED_HOSTS` | Optional, durch Komma getrennt. Zusätzliche Hostnamen, die Sie im Browser eingeben (z. B. ein Name aus Ihrem LAN-DNS). `localhost` und IP-Adressen gehen immer; jeder andere `Host` erhält `421` | leer |
| `GITEA_WEB_PORT`, `GITEA_SSH_PORT` | Ports des lokalen Git-Servers | `3010`, `2222` |
| `GITEA_REPORT_OWNER`, `GITEA_REPORT_REPO` | Git-Benutzer und Repository für Berichtsversionen | `reports-admin`, `model-test-reports` |
| `UPSTREAM_LLAMA_COMMIT`, `PRISM_LLAMA_COMMIT`, `WHISPER_CPP_COMMIT`, `STABLE_DIFFUSION_CPP_COMMIT` | Festgelegte Quell-Commits der CUDA-Builds. Nur mit gutem Grund ändern. | festgelegt |
| `GATEWAY_PORT`, `HOST_BIND_IP`, `WHISPER_PORT`, `REPORT_PORT`, `AI_CONSOLE_PORT` | Optionale Port-Anpassungen | 8080, 127.0.0.1, 8082, 8765, 8766 |

Das Projekt braucht keine API-Schlüssel. Das einzige Geheimnis, das in `.env` stehen darf, ist das optionale `AI_CONSOLE_PASSWORD`; `.env` wird von Git ignoriert, committen Sie sie nie und fügen Sie sie nicht in Chats oder Issues ein.

### 4.4 Ordner, Netzwerk und Volume anlegen

`python scripts/install.py init` erledigt all das und ist wiederholbar:
- Ordner `bench_results`, `report`, `results-db`, `media/images`, `benchmark/q4kv-20260929`, `secrets`;
- Platzhalterdateien, die Docker-Bind-Mounts verlangen (`report/report-data.json`, `BENCHMARK_RESULTS.csv`, `BENCHMARK_RESULTS.db`, `media/images/qwen-image-2.1-smoke.png`, `benchmark/q4kv-20260929/recommended-settings-q4kv-20260929.json`);
- Docker-Netzwerk `ai-net` und Volume `llm-models-fast`;
- Prüfung, dass `docker compose config` gültig ist.

Von Hand: `docker network create ai-net` und `docker volume create llm-models-fast`.

### 4.5 Modelle bereitstellen

Das Gateway liest Modelle aus dem Docker-Volume `llm-models-fast` (ein ext4-Volume lädt ein Modell in 11–29 s, ein Windows-Laufwerk über WSL braucht Minuten). `MODEL_DIR` dient den optionalen Whisper-/Bild-Profilen und als Quelle, aus der Sie das Volume füllen.

1. **Benötigte Dateien ermitteln.** Jedes Profil in `config/llama-swap.yaml` nennt seine Datei nach `--model`:
   ```
   grep -o '/models/[^ ]*\.gguf' config/llama-swap.yaml | sort -u
   ```
   Mitgelieferte Profile (Kontextgrößen auf einer RTX 3080 / 10 GB gemessen):

   | Profil | Dateien (relativ zum Bibliothekswurzel) | Kontext |
   |---|---|---|
   | Qwen3.5-9B-MTP-Q4_K_XL | `Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf` | 192K |
   | Qwen3.5-9B-MTP-Q4_K_XL-Vision | dieselbe Datei + `Qwen3/mmproj-F16.gguf` | 128K |
   | Qwen3.5-9B-Q5_K_S | `Qwen3/Qwen3.5-9B-Q5_K_S-4.60bpw.gguf` | 256K |
   | MiniCPM5-2B-Q8_0 | `MiniCPM5/MiniCPM5-2B-Q8_0.gguf` | 128K |
   | Spark-X2.5-4B-Q8_0 | `Spark/Spark-X2.5-4B-Q8_0.gguf` | 256K |
   | Ternary-Bonsai-2-27B-PTQ1_0 | `Ternary-Bonsai-2-27B-PTQ1_0.gguf` | 128K |
   | Qwen3-VL-8B-Instruct-Q4_K_M | `Qwen-Image-2.1/text_encoder/Qwen3VL-8B-Instruct-Q4_K_M.gguf` + `mmproj-Qwen3VL-8B-Instruct-F16.gguf` | 64K |
   | Ornith-1.5-9B-MTP | `top/Ornith-1.5-9B/Ornith-1.5-9B-Q4_K_M.gguf` | 128K |
   | Qwen3-Embedding-0.6B / 4B | `top/Qwen3-Embedding-0.6B/...-Q8_0.gguf`, `top/Qwen3-Embedding-4B/...-Q4_K_M.gguf` | 8K |
   | Qwen2.5-Coder-7B, Llama-3.1-8B, Gemma-3-12B | `cand/<Name>/...Q4_K_M.gguf` | 64K |
   | MiMo-V2.6-Distill-Qwen-9B | `top/MiMo-V2.6-Distill-Qwen-9B/...Q4_K_M.gguf` | 256K |

2. **Nur laden, was Sie wollen.** `MODELS.md` nennt die Hugging-Face-Repositories, Revisionen und SHA-256-Summen der vom Autor festgelegten Modelle. Für ein Profil ohne angegebene Quelle suchen Sie den genauen Dateinamen auf Hugging Face, lesen die Modellkarte und prüfen die Lizenz (manche Lizenzen schränken die kommerzielle Nutzung ein oder verlangen Namensnennung). **Sie brauchen nicht alle Modelle**: Entfernen Sie unerwünschte Profile aus `config/llama-swap.yaml` (ein Profil ohne Datei zeigt die Konsole als „Datei nicht gefunden“).
3. **Integrität prüfen**: `sha256sum <Datei>` mit `MODELS.md` / der Modellseite vergleichen.
4. **Dateien ins Volume kopieren** und dabei die Unterordner der Tabelle beibehalten (Beispiel für eine Datei; pro Datei oder Ordner wiederholen):
   ```
   docker run --rm -v llm-models-fast:/models -v "C:/AI/models:/src:ro" alpine sh -c "mkdir -p /models/Qwen3 && cp /src/Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf /models/Qwen3/"
   ```
   In Git Bash für Windows dem Befehl `MSYS_NO_PATHCONV=1` voranstellen oder PowerShell verwenden.
5. **Beginnen Sie mit einem kleinen Modell**, um die ganze Kette zu testen (zum Beispiel `MiniCPM5-2B-Q8_0`, 2,7 GB), und ergänzen Sie danach die übrigen.

### 4.6 Images bauen

`python scripts/install.py build` führt die folgenden Befehle aus (ein Build nach dem anderen, um RAM zu sparen; die CUDA-Kompilierung dauert beim ersten Mal 15–40 Minuten, danach hilft der Cache):

```
docker compose --profile build build build-upstream      # local/ai-server-upstream:local  (llama.cpp mit CUDA, festgelegter Commit)
docker compose --profile build build build-bonsai        # local/ai-server-bonsai:local    (PrismML-Fork, nur für das Bonsai-Modell)
docker compose --profile gateway build llama-swap-gateway  # local/ai-server-llama-swap:260 (llama-swap v260, SHA-256 geprüft)
docker compose build ai-console report-versioner         # Images von Konsole und Versionierer
```

Wenn Sie das Bonsai-Modell nicht brauchen, bauen Sie nur `build-upstream`, setzen `PRISM_IMAGE=local/ai-server-upstream:local` als Build-Argument von `llama-swap-gateway` (oder `--build-arg`) und entfernen das Bonsai-Profil aus `config/llama-swap.yaml`.

### 4.7 Starten

```
python scripts/install.py up
```

Das entspricht:

```
docker compose up -d ai-console report-builder stats-report gitea report-versioner
docker compose --profile gateway up -d llama-swap-gateway
```

Das Gateway braucht etwa 30 s, bis es `healthy` ist, und startet **ohne geladenes Modell** (die erste Anfrage an ein Modell lädt es, bis zu einer Minute). Öffnen Sie **http://localhost:8766/**.

### 4.8 Git-Server für Berichtsversionen einrichten

```
python scripts/setup_git.py
```

Das Skript startet Gitea, legt den Administrator, ein Zugriffstoken für den Versionierer, einen SSH-Schlüssel und das private Repository an und startet `report-versioner`. Passwörter und Schlüssel landen nur in `secrets/` (von Git ignoriert, nie veröffentlicht). Weboberfläche: `http://localhost:3010/` (Zugangsdaten in `secrets/gitea-admin.txt`). Versionen klonen:

```
git clone -c core.sshCommand="ssh -i secrets/id_ed25519 -o StrictHostKeyChecking=accept-new -p 2222" ssh://git@127.0.0.1:2222/reports-admin/model-test-reports.git
```

### 4.9 Zugriff von anderen Geräten im Netzwerk (optional)

1. In `.env` `AI_CONSOLE_PASSWORD=<langes Passwort>` und `AI_CONSOLE_BIND_IP=<LAN-Adresse dieses PCs>` setzen (bei Zugriff über einen Hostnamen zusätzlich `AI_CONSOLE_ALLOWED_HOSTS`), dann die Konsole neu erstellen: `docker compose up -d --force-recreate --no-deps ai-console`.
2. Den Port in der Firewall nur für das eigene Subnetz öffnen (PowerShell als Administrator):
   ```
   New-NetFirewallRule -DisplayName "AI console 8766 (LAN)" -Direction Inbound -Protocol TCP -LocalPort 8766 -RemoteAddress 192.168.0.0/24 -Profile Any -Action Allow
   ```
   (Subnetz anpassen). Die Konsole nie ins Internet stellen, mit oder ohne Passwort: Basic-Authentifizierung sendet das Passwort unverschlüsselt, daher nur in einem vertrauenswürdigen Netz oder hinter VPN / TLS-Proxy verwenden.

## 5. Optionale Komponenten

### Open WebUI (Chat-Oberfläche)

```
docker run -d --name open-webui --restart unless-stopped -p 3000:8080 -v open-webui:/app/backend/data ghcr.io/open-webui/open-webui:main
docker network connect local-ai-server_default open-webui
powershell -File scripts/configure-openwebui-gateway.ps1
```

Das Skript trägt das Gateway `http://llama-swap-gateway:8080/v1` als OpenAI-Verbindung ein. Open WebUI hat eigene Lizenzbedingungen; siehe `legal/NOTICE-THIRD-PARTY.md`.

### Telemetrie-Exporter

```
cd hermes-telemetry
docker compose -f compose.yaml up -d --build
```

Veröffentlicht `/metrics` und `/health` auf `127.0.0.1:9835` (für das LAN `TELEMETRY_BIND_IP` setzen). Benötigt die Netzwerke `ai-net` und `local-ai-server_default` (von `init` und dem ersten `up` erstellt).

### Videogenerierung: das eigene Projekt „Video Studio“

Die Videogenerierung (Wan 2.1 1.3B + ComfyUI, Storyboard aus einer Idee, Videoberichte) ist **nicht mehr Teil dieses Projekts**: Sie ist ein eigenes Projekt, **Video Studio** (eigenes Repository, eigene Konsole auf Port 8767, eigene Installationsanleitung). Beide Projekte arbeiten nebeneinander:
- die Kopfzeile dieser Konsole hat einen Link „Videogenerierung“, der Video Studio öffnet (`http://HOST:8767/`);
- Video Studio tritt dem Docker-Netzwerk `local-ai-server_default` dieses Projekts bei, um das Gateway zu erreichen (es entlädt vor einem Video die Gateway-Modelle und entwirft Storyboards mit Ihrem lokalen LLM);
- diese Konsole startet kein LLM, solange der ComfyUI-Container von Video Studio die GPU belegt (Containername `video-generation-comfyui-video-1`).
Installieren Sie zuerst dieses Projekt, danach Video Studio.

### Profile für Spracherkennung und Bildgenerierung

`docker compose --profile whisper build whisper` und `--profile qwen-image build qwen-image` bauen die optionalen Profile Whisper (Sprache zu Text) und Qwen-Image; sie brauchen ihre Modelldateien unter `MODEL_DIR` (siehe `.env`, `WHISPER_MODEL`, `QWEN_IMAGE_*`) und werden standardmäßig nicht gestartet.

## 6. Überprüfung

`python scripts/install.py verify` führt diese Prüfungen aus; Sie können sie auch von Hand ausführen:

| Was | Befehl | Erwartet |
|---|---|---|
| GPU in Docker | `docker run --rm --gpus all nvidia/cuda:12.8.1-runtime-ubuntu24.04 nvidia-smi` | Tabelle mit Ihrer GPU |
| Gateway | `curl http://localhost:8080/v1/models` | JSON-Liste der Profile |
| Konsole | `curl http://localhost:8766/health` | `{"ok": true}` |
| Modellkatalog | `curl http://localhost:8766/api/models` | bei kopierten Dateien `"exists": true` |
| Status | `curl http://localhost:8766/api/status` | `docker_available: true` |
| Bericht | `http://localhost:8766/report/` öffnen | Seite lädt, Fußzeile zeigt die Lizenz |
| Alte Adresse | `curl -I http://localhost:8765/` | `301` auf Port 8766 |
| Git | `curl http://localhost:3010/api/healthz` | 200 |
| Container | `docker ps --format "{{.Names}} {{.Status}}"` | `healthy` bei Konsole, Gateway, report-builder, gitea, versioner |
| Erstes Modell | in der Konsole **Start** bei einem Modell drücken, dann Chat | Antwort erscheint; `curl localhost:8080/running` listet das Modell |

Ist `AI_CONSOLE_PASSWORD` gesetzt, hängen Sie `-u any:PASSWORT` an die `curl`-Aufrufe der Konsole an (nicht an `/health`). Auf einem PC ohne GPU `python scripts/install.py verify --no-gpu` verwenden: die Gateway-Prüfungen entfallen.

## 7. Die Konsole benutzen

- **Sprache**: Umschalter RU / EN / DE in der Kopfzeile (wird im Browser gemerkt).
- **1 Status** zeigt, was gerade im Speicher ist; **2 Start** listet Modelle mit Start / Stopp (Start lädt das Modell in den Videospeicher, Stopp entlädt es); die Modellkarten zeigen Quantisierung, Kontext, Datei und ermittelte Parameter.
- **3 Chat** spricht über das Gateway mit dem gewählten Modell (Bildmodelle nehmen Bilder an). Der **Entlade-Timer** entlädt nach N Sekunden alle Modelle.
- **Testergebnisse** zeigen jedes Modell mit allen Tests, sortierbar nach jedem Test, mit Fortschrittsbalken des laufenden Tests, Schätzung der Restzeit bis zum Ende aller Tests und der Phasenliste.
- **Videogenerierung ↗** in der Kopfzeile öffnet das eigene Projekt Video Studio.
- **Bericht und Ergebnisse** (`/report/`): vollständige Tabellen, Diagramme, Empfehlungen, Downloads.

## 8. Testergebnisse, Berichte und Git-Versionen

- Benchmarks schreiben `bench_results/results*.jsonl` (ein JSON-Objekt pro Zeile: `model`, Bewertungen, Geschwindigkeiten, …). Der Berichtsgenerator führt sie, ohne ältere Ergebnisse zu löschen, in SQLite (`results-db/llm-results.sqlite`) zusammen und erzeugt `report/live-data.json`. Die Benchmark-Skripte selbst sind nicht Teil dieses Pakets; jedes Werkzeug, das dieselben Dateien schreibt, funktioniert.
- `report-versioner` speichert bei jeder Änderung `results/`, `tables/`, `report/` und einen JSON-Dump der Datenbank in Gitea: Commits heißen `vNNNN`, abgeschlossene Phasen erhalten `stage-<Phase>-done`, das Ende aller Tests `final-<Datum>`. Die Historie wird nie umgeschrieben. Einen alten Bericht stellen Sie mit `git checkout v0042` wieder her.
- Phasenplan und Gesamtschätzung stammen aus `scripts/build_live_report.py` (`DEFAULT_PLAN`) und lassen sich durch `bench_results/benchmark_plan.json` ersetzen.

## 9. Wartung: Aktualisieren, Sichern, Entfernen

- **Code aktualisieren**: `git pull`, dann `docker compose up -d --build ai-console report-versioner`. Nach dem Bearbeiten von `config/llama-swap.yaml` `docker compose --profile gateway up -d --force-recreate --no-deps llama-swap-gateway` ausführen (ein einzelner Datei-Bind-Mount übernimmt sonst eine ersetzte Datei nicht).
- **Sichern**: `.env`, `config/`, `bench_results/`, `results-db/`, die Docker-Volumes `gitea-data`, `gitea-config`, `ai-console-state` und `secrets/`. Modelle lassen sich neu herunterladen.
- **Alles stoppen**: `docker compose --profile gateway down`.
- **Mit Daten entfernen** (unwiderruflich): `docker compose --profile gateway down -v` (löscht die Volumes außer dem externen `llm-models-fast`); das Modell-Volume entfernen Sie selbst mit `docker volume rm llm-models-fast`.

## 10. Hinweise zu Linux / macOS

- **Linux**: Docker Engine, NVIDIA-Treiber und NVIDIA Container Toolkit installieren, `docker run --rm --gpus all ... nvidia-smi` prüfen. Die Compose-Dateien sind plattformunabhängig; verwenden Sie `python scripts/install.py ...` und Schrägstriche in den Pfaden von `.env`. Die `.ps1`-Skripte sind optionale PowerShell-Helfer. Das Projekt wurde unter Windows 10 + Docker Desktop entwickelt und getestet; unter Linux sollte es funktionieren, wurde vom Autor aber nicht getestet.
- **macOS**: Es gibt kein CUDA, daher laufen die GPU-Images nicht. Nicht unterstützt.
- Wenn die Konsole unter Linux den Docker-Socket nicht sieht, prüfen Sie, ob `/var/run/docker.sock` existiert (die Konsole nutzt ihn, um Container aufzulisten und den Zustand von `llama-server` zu lesen).

## 11. Fehlersuche

| Symptom | Ursache / Lösung |
|---|---|
| `Docker Desktop is manually paused` | Im Wal-Menü fortsetzen; die CLI `docker desktop` kann die Pause nicht aufheben. |
| `port is already allocated` | Ein anderes Programm nutzt den Port; `GITEA_WEB_PORT`, `AI_CONSOLE_PORT` usw. in `.env` ändern (der Doctor listet belegte Ports). |
| `could not select device driver "nvidia"` | GPU für Docker nicht verfügbar: NVIDIA-Treiber aktualisieren, WSL2-Integration aktivieren, Docker Desktop neu starten. |
| `docker compose` meldet fehlende Bind-Quelle | `python scripts/install.py init` ausführen (erstellt Platzhalter und Ordner). |
| Modellkarte zeigt „Datei nicht gefunden“ | Die Datei liegt nicht im Volume `llm-models-fast` unter dem genauen Pfad des Profils (Abschnitt 4.5). |
| Erste Antwort dauert eine Minute | Das Gateway lädt das Modell in den Videospeicher; spätere Antworten sind schnell. |
| Videospeicher reicht nicht | Ein anderes Programm oder der Videocontainer belegt VRAM; die Diagnose der Konsole nennt die Verursacher. Kleineren Kontext oder kleinere Quantisierung wählen. |
| Git Bash verfälscht `/models`-Pfade | `MSYS_NO_PATHCONV=1` voranstellen oder PowerShell verwenden. |
| Konsole zeigt in EN/DE russischen Text | Texte aus Ihren eigenen Daten (Prompts, Modellantworten, Protokolle) werden nie übersetzt. Neue Oberflächentexte gehören in `console/i18n-dict.js` (`node scripts/check_i18n.js de` listet fehlende auf). |
| Berichtsseite leer | Normal, bis die erste `bench_results/results*.jsonl` existiert. |
| `doctor` meldet, das CUDA-Prüfimage sei nicht heruntergeladen | Es lädt 5,6 GB nicht von selbst. Eigentümer fragen, dann `python scripts/install.py doctor --pull`, oder auf einem PC ohne GPU `--no-gpu` verwenden. |
| `docker compose up` bricht mit „could not select device driver“ / „no known GPU vendor“ ab | Docker sieht keine GPU. `python scripts/install.py up --no-gpu` verwenden. |
| Ein Skript oder `curl` erhält von der Konsole `415`, `421`, `403` oder `401` | Die Konsole prüft jede Anfrage: `POST` braucht `Content-Type: application/json`, der `Host` muss `localhost` oder eine IP sein (oder in `AI_CONSOLE_ALLOWED_HOSTS` stehen), ein Passwort kann nötig sein (`curl -u any:PASSWORT`). Siehe [API.md](API.md). |
| Der Browser zeigt `421`, wenn die Konsole über einen Hostnamen geöffnet wird | Namen in `AI_CONSOLE_ALLOWED_HOSTS` in `.env` eintragen und die Konsole neu erstellen. |

## 12. Sicherheit

- Das Gateway hat **keine Authentifizierung**; die Konsole hat ein optionales Passwort (`AI_CONSOLE_PASSWORD`). Halten Sie beide auf `127.0.0.1` oder in einem vertrauenswürdigen Subnetz; veröffentlichen Sie die Ports 8766 / 8080 / 3010 nie im Internet.
- Die Konsole weist fremde `Host`-Namen sowie seitenübergreifende oder Nicht-JSON-`POST`-Anfragen ab und sendet Sicherheits-Header; eine Webseite im selben Browser kann die Modelle daher nicht steuern.
- Der Konsolencontainer bindet `/var/run/docker.sock` ein; das Flag `read_only` schützt ihn nicht. Die Konsole sendet nur eine feste Art von Befehlen darüber und läuft ohne Privilegien, dennoch entspricht Zugriff auf die Konsole Zugriff auf Docker dieses PCs. Details: [SECURITY.md](../SECURITY.md).
- In Gitea ist die Registrierung deaktiviert und eine Anmeldung erforderlich; Passwort und Token liegen nur in `secrets/`.
- Modelldateien stammen von Dritten: SHA-256 prüfen und deren Lizenzen lesen.
- Probleme bitte privat melden, siehe [SECURITY.md](../SECURITY.md).

## 13. Lizenz und Namensnennung

Ergebnisse, Berichte und Texte: **CC BY 4.0**, Nennung „homensai.com (https://homensai.com)“. Code: **MIT**. Software und Modelle Dritter behalten ihre Lizenzen: siehe `legal/NOTICE-THIRD-PARTY.md`. Dies ist keine Rechtsberatung.
