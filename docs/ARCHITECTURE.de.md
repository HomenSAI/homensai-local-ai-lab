# Architektur

Andere Sprachen: [English](ARCHITECTURE.md) · [Русский](ARCHITECTURE.ru.md)

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

## Komponenten

| Pfad | Rolle |
|---|---|
| `docker-compose.nogpu.yml` | Override für einen Rechner ohne NVIDIA-GPU: Die Konsole startet, ohne eine anzufordern (`install.py up --no-gpu`). |
| `docker-compose.yml` | Alle Dienste. Profile: `gateway` (llama-swap), `build` (Builder der Basis-Images), `whisper`, `qwen-image`, `media-tools` (optional). |
| `Dockerfile.upstream` / `.bonsai` | llama.cpp (CUDA 12.8, Architektur 86) und der PrismML-Fork, gebaut aus festgelegten Commits. |
| `Dockerfile.llama-swap` | llama-swap v260 (SHA-256 geprüft) auf Basis des Upstream-Images, mit der nach `/opt/prism` kopierten Bonsai-Laufzeitumgebung. |
| `config/llama-swap.yaml` | Ein Profil pro Modell: Datei, Kontextgröße, KV-Cache-Typ, spekulatives Dekodieren, TTL. Bearbeiten Sie die Datei, um Modelle hinzuzufügen oder zu entfernen. |
| `console/` | `container_server.py` (HTTP-Server, Zugriff auf Docker/Gateway), `security.py` (Host-/Origin-/Passwort-Prüfungen und Sicherheits-Header), `tests_feed.py` (Daten für die Testtabelle); statische `index.html`, `app.js`, `app.css`, `shell.js` (Design-Schalter, Fußzeile mit Autor); `i18n.js` + `i18n-dict.js` (RU/EN/DE); `style/`: HomenS.AI Style 1.6.0 (Stylesheet, Schriften, Logo, Skripte), ausgeliefert unter `/style/`. |
| `report/` | Statische Berichtsseite; `live-data.json` und `live-status.json` schreibt der Generator. `progress.html` + `progress.js`: Testfortschritt (Phasenplan aus `live-data.json`) in der Prozessansicht A/B/C von HomenS.AI Style; `contact.html` + `contact.js`: der Kontaktblock des Stils (in jedem HomenS.AI-Projekt vorgeschrieben). |
| `scripts/build_live_report.py` | Sammelt Ergebnisdateien, führt sie in SQLite zusammen (`raw_rows`, `results`, `history`, `model_scores`), erstellt den Phasenplan, den Fortschritt und die Restzeitschätzung. |
| `scripts/versioner.py`, `scripts/setup_git.py` | Versionierung der Berichte in Gitea und deren einmalige Einrichtung. |
| `scripts/install.py` | doctor / init / build / up / verify (`--no-gpu`, `doctor --pull`). |
| `scripts/build_site.py` | Baut die Dokumentations-Website (GitHub Pages): macht aus den Markdown-Dateien `site/site.json` und `site/content/` und startet den Website-Builder von HomenS.AI Style, der `site/<seite>.<sprache>.html` schreibt und den Kern nach `site/style/` kopiert; alte Seitenadressen werden zu Weiterleitungen; `--check` für CI. |
| `scripts/make_manifest.py` | Schreibt / prüft `MANIFEST.json` (Größe und SHA-256 jeder versionierten Datei). |
| `tests/` | Unit-Tests mit der Standardbibliothek: Konsolensicherheit, Berichtsgenerator, veröffentlichte Ergebnisse, Installer, Manifest (`python -m unittest discover -s tests`). |
| `hermes-telemetry/` | Kleiner Metrik-Exporter (GPU, llama). |
| `benchmarks/`, `docker/bench-runner/` | Test-Runner der veröffentlichten Ergebnisse und ihr Container (Profil `bench`); sie schreiben nach `bench_results/`. Siehe `benchmarks/README.md`. |
| `legal/` | CC BY-NC 4.0 (Ergebnisse), PolyForm Noncommercial 1.0.0 (Code), Hinweise zu Drittanbietern. |

## Entwurfsentscheidungen

- **Ein Modell nach dem anderen.** In 10 GB Videospeicher passt ein großes Modell; llama-swap entlädt das alte Modell, bevor es das nächste lädt. Die Konsole blockiert den Start eines LLM, solange die Videogenerierung die GPU belegt.
- **Modell-Volume.** Modelle werden aus einem Docker-Volume (ext4) bereitgestellt, weil ein Bind eines Windows-Laufwerks über WSL beim Laden etwa 10-mal langsamer ist.
- **Keine Python-Pakete von Drittanbietern** in Konsole, Generator und Versionierer: Sie laufen auf `python:3.12-slim` / `alpine` nur mit der Standardbibliothek.
- **Ergebnisse werden nie überschrieben.** Verschiedene Tests (allgemein, Deutsch, Kontext, MINT, ...) werden getrennt gehalten; das SQLite-Archiv bewahrt die Historie; Git bewahrt jede Berichtsversion.
- **Oberflächentexte sind im Quelltext Russisch** und werden von `i18n.js` zur Laufzeit übersetzt; Benutzerdaten (Prompts, Antworten, Logs) sind mit `data-no-i18n` markiert und werden nie übersetzt. `scripts/check_i18n.js` listet nicht übersetzte Fragmente auf.
- **Bind-Mounts einzelner Dateien** (Konfigurationsdateien) übernehmen eine ersetzte Datei nicht: Erstellen Sie den Dienst nach dem Bearbeiten neu.

## Verwandtes Projekt

**Video Studio** (eigenes Repository): eine eigene Konsole (Port 8767) plus der Container mit ComfyUI + Wan 2.1. Es tritt dem Docker-Netzwerk `local-ai-server_default` dieses Projekts bei, um das Gateway aufzurufen (Modelle vor einem Video entladen, Storyboard mit dem lokalen LLM). Diese Konsole prüft nur, ob der ComfyUI-Container läuft, damit kein LLM gestartet wird, während die GPU belegt ist.
