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
- **Optional von einem KI-Assistenten betrieben:** Sie können den Server selbst installieren und nutzen; Sie können ihn auch Claude, ChatGPT/Codex oder einem anderen Agenten mit Shell-Zugriff übergeben, der `AGENTS.md` / `CLAUDE.md` liest, installiert, die Tests ausführt und die Ergebnisse prüft. Siehe [docs/AI_OPERATOR.de.md](docs/AI_OPERATOR.de.md) und „Selbst oder mit einem KI-Assistenten?“ unten.
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
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 git      # lokales Git, das jede Version der Berichte aufbewahrt
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
python scripts/install.py git
python scripts/install.py verify
```

Öffnen Sie **http://localhost:8766/**.

## Selbst oder mit einem KI-Assistenten?

**Ein KI-Assistent ist nicht nötig.** Installation, Start, Tests und Berichte erledigen Sie mit den Befehlen dieser Seite; Sie müssen einen Befehl in PowerShell einfügen und eine Zeile der `.env` im Editor ändern können.

| Aufgabe | Selbst | Was ein KI-Assistent hinzufügt |
|---|---|---|
| Installieren | die sechs Befehle oben, einer nach dem anderen | führt sie für Sie aus und behebt, was `doctor` / `verify` melden |
| Modelle | die Dateien aus [MODELS.de.md](MODELS.de.md) laden und ins Docker-Volume legen (Anleitung, Abschnitt 4.5) | wählt Modelle für Ihre Karte, prüft SHA-256 |
| Benutzen | die Konsole im Browser (unten) | — |
| Tests starten | ein Befehl (unten) | überwacht den Lauf, prüft die Zahlen auf Plausibilität, wiederholt verdächtige Läufe |
| Etwas geht nicht | Anleitung, Abschnitt 11 „Fehlerbehebung“ | liest die Container-Logs und behebt die Ursache |

Diese Schritte kann nur ein Assistent ausführen, **der Befehle auf diesem Computer starten kann** (zum Beispiel Claude Code oder ein Codex-Agent); geben Sie ihm [PROMPT_FOR_AI.md](PROMPT_FOR_AI.md). Unter Windows nutzt er denselben PowerShell-Installer, der Server braucht also weiterhin nur Docker Desktop; der Assistent selbst kann eigene Voraussetzungen haben, siehe seine Dokumentation. Ein gewöhnlicher Browser-Chat installiert nichts, erklärt aber eine Fehlermeldung, die Sie einfügen.

## Nach der Installation: was Sie benutzen

| Was | Wo |
|---|---|
| Konsole: Modelle starten und stoppen, Chat, GPU-Last, Diagnose | http://localhost:8766/ |
| Bericht mit allen Testergebnissen, Download als CSV und SQLite | http://localhost:8766/report/ |
| Testfortschritt (Phasen, aktuelles Modell, Restzeit) | http://localhost:8766/report/progress.html |
| OpenAI-kompatible API für andere Programme (Open WebUI, Skripte, IDEs) | http://localhost:8080/v1 |
| Jede Version der Berichte (lokales Git) | http://localhost:3010/ (Zugangsdaten in `secrets/gitea-admin.txt`) |
| Tests starten | `docker compose --profile bench up -d --build bench-runner` ([benchmarks/README.md](benchmarks/README.de.md)) |

**Ohne GPU ausprobieren:** [tests/virtual-3080/](tests/virtual-3080/README.de.md) installiert das ganze System auf einem Linux-Rechner mit Docker und einer virtuellen RTX 3080 (simulierte Zahlen) – zum Kennenlernen oder um Änderungen zu testen.

## Dokumentation

Dieselbe Dokumentation als Website auf dem Kern HomenS.AI Style (Menü, Schaltflächen EN | DE | RU, helles und dunkles Design, jede Seite in drei Sprachen): <https://homensai.github.io/homensai-local-ai-lab/site/index.de.html>. Die Seiten werden mit `python scripts/build_site.py` aus diesen Markdown-Dateien gebaut (dafür wird eine Kopie des Stilkerns gebraucht, siehe CONTRIBUTING).

| | English | Русский | Deutsch |
|---|---|---|---|
| Vollständige Installationsanleitung | [INSTALL.en.md](docs/INSTALL.en.md) | [INSTALL.ru.md](docs/INSTALL.ru.md) | [INSTALL.de.md](docs/INSTALL.de.md) |
| Überblick | [README.de.md](README.de.md) | [README.ru.md](README.ru.md) | diese Datei |

Weiteres: [warum es so gebaut wurde](docs/DESIGN.de.md) · [HTTP-Schnittstellen](docs/API.de.md) · [Ergebnisdateiformat](docs/RESULTS_FORMAT.de.md) · [Herkunft des Codes](PROVENANCE.md) · [Texte der Repository-Seite](docs/GITHUB_REPO.md) · [Architektur](docs/ARCHITECTURE.de.md) · [Sicherheitsrichtlinie](SECURITY.de.md) · [Mitwirken](CONTRIBUTING.md) · [Änderungsprotokoll](CHANGELOG.md) · [Modellübersicht](MODELS.de.md) · [Lizenzdateien](legal/)

## Voraussetzungen in einer Zeile

NVIDIA-GPU mit mindestens 8 GB, 16–32 GB RAM, etwa 25 GB Speicher für Images plus 50–200 GB für Modelle, Docker Desktop (WSL2) mit GPU-Unterstützung; unter Windows sonst nichts (PowerShell-Installer), unter Linux Python 3.10+ und Git. Linux mit NVIDIA Container Toolkit sollte funktionieren (vom Autor nicht getestet); macOS wird nicht unterstützt (kein CUDA).

## Nicht enthalten

Modellgewichte (selbst herunterladen und deren Lizenzen beachten), eigene Testergebnisse (`bench_results/`, entstehen beim Testlauf), Videos, Geheimnisse. Die Test-Runner liegen in [benchmarks/](benchmarks/README.de.md); die veröffentlichten Ergebnisse in [rtx3080-local-ai-benchmarks](https://github.com/HomenSAI/rtx3080-local-ai-benchmarks). Das Gateway hat **kein Passwort**, das Passwort der Konsole (`AI_CONSOLE_PASSWORD`) ist optional: beide nur auf `127.0.0.1` oder in einem vertrauenswürdigen Netzwerk verwenden, nie im Internet. Die Konsole weist außerdem seitenübergreifende Anfragen und fremde `Host`-Namen ab ([SECURITY.de.md](SECURITY.de.md)).

## Lizenz und Namensnennung

- Ergebnisse, Berichte und Texte: **[CC BY-NC 4.0](legal/LICENSE-RESULTS-CC-BY-NC-4.0.md)** – Nutzung und Weitergabe **nur für nichtkommerzielle Zwecke**, **Verweis auf den Autor ist Pflicht**: `Daten: homensai.com (https://homensai.com), CC BY-NC 4.0`.
- Code: **[PolyForm Noncommercial 1.0.0](LICENSE)** – nur nichtkommerzielle Nutzung; der Required Notice und die Autorenzeile bleiben in jeder Kopie. Kommerzielle Nutzung von Code oder Ergebnissen nur nach schriftlicher Vereinbarung mit dem Autor.
- Software und Modelle Dritter behalten ihre Lizenzen: [NOTICE-THIRD-PARTY.md](legal/NOTICE-THIRD-PARTY.md). Produktnamen sind Marken ihrer Inhaber; das Projekt steht in keiner Verbindung zu ihnen und wird von ihnen nicht unterstützt.
