# Local AI Server

**Lokale Sprachmodelle auf einer einzelnen NVIDIA-Grafikkarte betreiben: Web-Konsole, automatische Testberichte, Videogenerierung und versionierte Ergebnisse.**
Sprachen: [English](README.md) · [Русский](README.ru.md) · Deutsch

Autor: **Serhii Khomenko** · [homensai.com](https://homensai.com) · info@homensai.com · Ergebnisse und Berichte: CC BY-NC 4.0 · Code: PolyForm Noncommercial 1.0.0 · nur nichtkommerzielle Nutzung, Namensnennung erforderlich

## Was es ist

Ein selbst gehosteter Stack für einen Arbeitsplatzrechner mit einer GPU (entwickelt auf einer RTX 3080 mit 10 GB, Windows 10 + Docker Desktop):

- **Gateway** ([llama-swap](https://github.com/mostlygeek/llama-swap) + [llama.cpp](https://github.com/ggml-org/llama.cpp)): OpenAI-kompatible API auf Port 8080; lädt jeweils ein Modell und wechselt bei Bedarf.
- **Konsole** (Port 8766, **Deutsch / English / Русский**): Modellkatalog mit Start/Stopp, Chat, GPU-Live-Telemetrie, Diagnose, Entlade-Timer, Testergebnisse mit Fortschritt und Restzeitschätzung und die **Berichtsseite**.
- **Berichte**: Benchmark-Ergebnisse werden zu einem Live-Bericht und einem SQLite-Archiv, das ältere Ergebnisse nie verliert.
- **Versionsverlauf**: Ein lokales Gitea bewahrt jede Version der Berichte auf (Tags `v0001` …, `stage-<Phase>-done`, `final-<Datum>`).
- **Von einem KI-Assistenten betrieben:** Der Server ist darauf ausgelegt, von Claude oder ChatGPT (Agent mit Shell-Zugriff) installiert, gestartet und überwacht zu werden: Geben Sie ihm das Repository, er liest `AGENTS.md` / `CLAUDE.md`, installiert, führt die Tests aus und prüft die Ergebnisse. Der Server läuft auch ohne Assistenten. Siehe [docs/AI_OPERATOR.de.md](docs/AI_OPERATOR.de.md).
- **Veröffentlichte Ergebnisse:** [results-public/RESULTS.md](results-public/RESULTS.md) – 23 Modelle, 15 für die späteren Phasen zugelassen; wie sie entstanden (Serverkern → Claude als Supervisor → Ergebnisse): [docs/METHODOLOGY.de.md](docs/METHODOLOGY.de.md).
- **Verwandtes Projekt:** Die Videogenerierung (Wan 2.1 + ComfyUI, Storyboard aus einer Idee von Ihrem lokalen LLM) ist ein eigenes Projekt, **Video Studio** (eigenes Repository, Port 8767); diese Konsole verlinkt darauf.

## Schnellstart

**Windows (auf dem PC nur Docker Desktop – ohne Python, Git und Node):** ZIP von der GitHub-Seite laden (Code → Download ZIP), entpacken, PowerShell im Ordner öffnen und einen Befehl nach dem anderen ausführen:

```
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 doctor   # Docker, GPU in Docker, Ports, Speicherplatz
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 init     # .env, Ordner, Platzhalter, Netzwerk, Volume
#  .env im Editor öffnen, MODEL_DIR setzen und die .gguf-Modelle ablegen – siehe Anleitung, Abschnitt 4.5
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 build    # erster Build 15–40 Minuten
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 up
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 verify   # jede Zeile muss [ok] sein
```

**Linux oder ein KI-Assistent mit Shell:** dieselben Schritte mit Python 3.10+ (nur Standardbibliothek):

```
git clone https://github.com/HomenSAI/homensai-local-ai-lab.git local-ai-server
cd local-ai-server
python scripts/install.py doctor     # Docker, GPU in Docker, Ports, Speicherplatz
python scripts/install.py init       # .env, Ordner, Platzhalter, Netzwerk, Volume
#  .env bearbeiten (MODEL_DIR) und .gguf-Modelle bereitstellen – siehe Anleitung, Abschnitt 4.5
python scripts/install.py build      # erster Build 15–40 Minuten
python scripts/install.py up
python scripts/install.py verify
```

Öffnen Sie **http://localhost:8766/**.

## Dokumentation

| | English | Русский | Deutsch |
|---|---|---|---|
| Vollständige Installationsanleitung | [INSTALL.en.md](docs/INSTALL.en.md) | [INSTALL.ru.md](docs/INSTALL.ru.md) | [INSTALL.de.md](docs/INSTALL.de.md) |
| Überblick | [README.md](README.md) | [README.ru.md](README.ru.md) | diese Datei |

Weiteres: [warum es so gebaut wurde](docs/DESIGN.de.md) · [HTTP-Schnittstellen](docs/API.md) · [Ergebnisdateiformat](docs/RESULTS_FORMAT.md) · [Herkunft des Codes](PROVENANCE.md) · [Texte der Repository-Seite](docs/GITHUB_REPO.md) · [Architektur](docs/ARCHITECTURE.md) · [Sicherheitsrichtlinie](SECURITY.md) · [Mitwirken](CONTRIBUTING.md) · [Änderungsprotokoll](CHANGELOG.md) · [Modellübersicht](MODELS.md) · [Lizenzdateien](legal/)

## Voraussetzungen in einer Zeile

NVIDIA-GPU mit mindestens 8 GB, 16–32 GB RAM, etwa 25 GB Speicher für Images plus 50–200 GB für Modelle, Docker Desktop (WSL2) mit GPU-Unterstützung; unter Windows sonst nichts (PowerShell-Installer), unter Linux Python 3.10+ und Git. Linux mit NVIDIA Container Toolkit sollte funktionieren (vom Autor nicht getestet); macOS wird nicht unterstützt (kein CUDA).

## Nicht enthalten

Modellgewichte (selbst herunterladen und deren Lizenzen beachten), eigene Testergebnisse (`bench_results/`, entstehen beim Testlauf), Videos, Geheimnisse. Die Test-Runner liegen in [benchmarks/](benchmarks/README.md); die veröffentlichten Ergebnisse in [rtx3080-local-ai-benchmarks](https://github.com/HomenSAI/rtx3080-local-ai-benchmarks). Das Gateway hat **kein Passwort**, das Passwort der Konsole (`AI_CONSOLE_PASSWORD`) ist optional: beide nur auf `127.0.0.1` oder in einem vertrauenswürdigen Netzwerk verwenden, nie im Internet. Die Konsole weist außerdem seitenübergreifende Anfragen und fremde `Host`-Namen ab ([SECURITY.md](SECURITY.md)).

## Lizenz und Namensnennung

- Ergebnisse, Berichte und Texte: **[CC BY-NC 4.0](legal/LICENSE-RESULTS-CC-BY-NC-4.0.md)** – Nutzung und Weitergabe **nur für nichtkommerzielle Zwecke**, **Verweis auf den Autor ist Pflicht**: `Daten: homensai.com (https://homensai.com), CC BY-NC 4.0`.
- Code: **[PolyForm Noncommercial 1.0.0](LICENSE)** – nur nichtkommerzielle Nutzung; der Required Notice und die Autorenzeile bleiben in jeder Kopie. Kommerzielle Nutzung von Code oder Ergebnissen nur nach schriftlicher Vereinbarung mit dem Autor.
- Software und Modelle Dritter behalten ihre Lizenzen: [NOTICE-THIRD-PARTY.md](legal/NOTICE-THIRD-PARTY.md). Produktnamen sind Marken ihrer Inhaber; das Projekt steht in keiner Verbindung zu ihnen und wird von ihnen nicht unterstützt.
