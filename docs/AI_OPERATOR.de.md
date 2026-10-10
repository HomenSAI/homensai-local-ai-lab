# Betrieb des Servers mit einem KI-Supervisor (Claude oder ChatGPT)

Andere Sprachen: [English](AI_OPERATOR.en.md) · [Русский](AI_OPERATOR.ru.md)

## Die Idee

Dieses Projekt ist dafür gebaut, von einem **KI-Assistenten installiert, gestartet und überwacht** zu werden – Claude oder ChatGPT. Sie müssen die Installationsanleitung nicht von Hand abarbeiten: Sie geben dem Assistenten das Repository (oder nur `docs/INSTALL.de.md`), er installiert, startet die Tests, beobachtet die Ergebnisse, beurteilt ihre Richtigkeit und hält die Git-Historie der Berichte in Ordnung.

- **Der Server läuft von selbst.** Gateway, Konsole, Berichtsgenerator und Git-Versionierer laufen ohne KI; die KI ist nur der Bediener.
- **Die KI ist der Supervisor.** Sie entscheidet, welche Tests auf welchen Modellen laufen, startet sie, prüft die Plausibilität der Zahlen (Zeitüberschreitungen, leere Antworten, Ausreißer, Modelle, die auf die CPU ausgewichen sind), wiederholt verdächtige Läufe und schreibt Schlussfolgerungen. Einen zweiten, eingebauten „Richter“ enthält der Server absichtlich nicht (siehe [DESIGN.de.md](DESIGN.de.md)).
- **Auf der Serverseite ist nichts Besonderes nötig** – es gibt kein Plug-in zu installieren. Der Supervisor nutzt, was schon da ist: die Shell auf diesem PC, die REST-API der Konsole ([API.md](API.md)), das OpenAI-kompatible Gateway auf Port 8080, die Ergebnisdateien ([RESULTS_FORMAT.md](RESULTS_FORMAT.md)) und das Git-Repository der Berichtsversionen.

## Was der Assistent braucht

Der Assistent muss **Befehle auf dem Rechner ausführen können, auf dem der Server läuft** (oder ihn über einen sicheren Kanal erreichen). Typische Wege:

| Assistent | Zugriff | Hinweise |
|---|---|---|
| **Claude Code** (CLI / Desktop / IDE) | arbeitet im geklonten Repository-Ordner und führt Shell-Befehle aus; liest `CLAUDE.md` automatisch | einfachste Variante |
| **Claude Desktop / Claude mit lokalen Werkzeugen** | lokale Datei- und Befehlswerkzeuge (zum Beispiel ein MCP-Server für Dateisystem und Shell, den Sie selbst aktivieren) | Sie bestimmen erlaubte Ordner und Befehle |
| **ChatGPT-Agenten mit lokalem Zugriff** (Codex CLI / Desktop-Agent) | arbeitet im geklonten Ordner; liest `AGENTS.md` automatisch | gleiche Idee |
| **ChatGPT-/Claude-Browser-Chat ohne lokalen Zugriff** | kann `localhost` nicht erreichen; kann nur *beraten*, während Sie Ausgaben einfügen | für Zugriff bräuchte man einen Tunnel – **nicht empfohlen**, die Konsole hat kein Passwort |

Wenn Sie den Server dennoch einem entfernten Assistenten öffnen, stellen Sie ihn hinter einen Tunnel mit Authentifizierung oder VPN und geben Sie zunächst nur Lesezugriff. Veröffentlichen Sie die Ports 8766, 8080, 3010 und 8767 nie unverändert im Internet.

## Übergabe: was Sie dem Assistenten sagen

Öffnen Sie den Assistenten im Repository-Ordner (oder hängen Sie `docs/INSTALL.de.md` an) und schreiben Sie:

```
Du bist Installateur und Supervisor dieses Projekts „Local AI Server“ (lies AGENTS.md / CLAUDE.md, docs/INSTALL.de.md, docs/AI_OPERATOR.de.md).
1. Installiere es auf diesem Rechner nach docs/INSTALL.de.md: führe `python scripts/install.py doctor` aus, behebe die Meldungen, dann init, build, up, verify. `doctor` lädt das 5,6-GB-CUDA-Prüfimage nie von selbst: frage mich vor `doctor --pull`. Auf einem PC ohne NVIDIA-GPU `--no-gpu` verwenden.
   Frage mich vor jeder unumkehrbaren Aktion, vor Downloads über 1 GB und bei jeder Entscheidung, die ich treffen muss (Modellordner, Netzwerkadresse).
2. Lege die von mir genannten Modelle wie in Abschnitt 4.5 ins Docker-Volume. Erfinde keine Download-Quellen; prüfe SHA-256.
3. Führe die gewünschten Tests auf den gewünschten Modellen aus (Ergebnisdateien: docs/RESULTS_FORMAT.md). Ein Modell nach dem anderen; das Gateway wechselt Modelle selbst.
4. Überwache: prüfe nach jedem Test die Plausibilität, wiederhole verdächtige Läufe und berichte mir in einer kurzen Tabelle: Modell, Test, Punktzahl, Geschwindigkeit, Auffälligkeiten.
5. Öffne Konsole und Gateway nie ins Internet, schreibe keine Geheimnisse in Dateien, die in Git landen, lösche keine meiner Daten.
```

## Wie die Konsole Skripte und Assistenten behandelt

Die Konsole prüft jede Anfrage ([API.md](API.md), [SECURITY.md](../SECURITY.md)). Ihre Befehle müssen das einhalten; eine Ablehnung ist eine Information, kein Hindernis, das man umgeht:

- `POST`-Aufrufe brauchen `-H "Content-Type: application/json"` (auch ohne Body), z. B. `curl -X POST http://localhost:8766/api/start -H "Content-Type: application/json" -d '{"model_key":"..."}'`. `415` heißt: Der Header fehlt.
- Hat der Mensch `AI_CONSOLE_PASSWORD` gesetzt, fragen Sie ihn danach und verwenden `curl -u any:PASSWORT`; schreiben Sie es nie in Dateien, die in Git landen, in Ergebnisdateien oder in einen Bericht. `401` heißt: Passwort nötig.
- `421` heißt: nicht erlaubter Hostname; verwenden Sie `localhost` oder die IP-Adresse; fragen Sie den Menschen, bevor Sie Namen in `AI_CONSOLE_ALLOWED_HOSTS` eintragen.
- Schalten Sie diese Prüfungen nicht ab, ändern Sie weder `console/security.py` noch das Passwort, um einen Aufruf durchzubringen; melden Sie die Ablehnung dem Menschen.

## Die Überwachungsschleife (was der Assistent tut)

1. **Zustand prüfen**: `python scripts/install.py verify`, `curl localhost:8766/api/status` (`issues` muss leer sein; „Gateway gestoppt“ ist nur erwartet, solange Tests die GPU belegen).
2. **Modelle und Tests wählen** zusammen mit dem Menschen; sicherstellen, dass die Modelldateien existieren (`curl localhost:8766/api/models` → `exists: true`).
3. **Test ausführen**: Anfragen an `http://localhost:8080/v1/chat/completions` mit dem Profilnamen des Modells senden (das Gateway lädt es, die erste Antwort dauert bis zu einer Minute), messen und pro Modell und Test eine JSON-Zeile in `bench_results/results_<Test>.jsonl` im dokumentierten Format anhängen. Fortschrittszeilen und eine Abschlussmarke in `bench_results/<Test>.log` schreiben (`PROGRESS i/n`, `<NAME>-FINISHED`), damit die Konsole Phase, Fortschrittsbalken und Restzeit zeigt.
4. **Ergebnis beurteilen**: mit anderen Modellen und früheren Ergebnissen vergleichen (`/api/tests`); achten auf leere oder abgeschnittene Antworten, `finish_reason` ungleich `stop`, eingebrochene Geschwindigkeit (CPU-Ausweichen; `vram` und `host_free_min_gb` ansehen), Punktzahlen, die einer Wiederholung widersprechen, Aufgaben, an denen alle Modelle scheitern (eher ein falscher Prüfer als ein schwaches Modell).
5. **Festhalten**: Berichtsgenerator und Versionierer erledigen das automatisch (SQLite-Archiv, `vNNNN`-Tags im lokalen Gitea). Schlussfolgerungen in `bench_results/report.md` ergänzen (die ersten Zeilen erscheinen auf der Berichtsseite).
6. **Dem Menschen berichten**: Tabelle plus Liste verdächtiger Funde und was wiederholt wurde.

## Regeln für den Assistenten

- Ein Modell gleichzeitig im Videospeicher; keinen zweiten GPU-Job starten, solange ein Test oder ein Video-Rendering läuft.
- Ergebnisse früherer Läufe nie ändern oder löschen; neue Zeilen anhängen (das Archiv behält alte Werte, aber die Historie ist der Beleg).
- Keine Prompts oder Antworten mit personenbezogenen Daten in Git; das Repository soll teilbar sein (Ergebnisse unter CC BY-NC 4.0 mit Nennung von <https://homensai.com>).
- Vor Folgendem den Menschen fragen: Dateien oder Volumes löschen, Netzwerkadressen in `.env` ändern, Ports öffnen, große Dateien laden, etwas veröffentlichen.
- Den Schutz der Konsole nicht abschwächen (Host-/Origin-/Passwort-Prüfung, die feste Form von `docker exec`) und das Passwort nie veröffentlichen; wird ein Aufruf abgelehnt, das melden.
- Ein Modell, das nicht geladen wurde, wird als `{"model": ..., "load_ok": false, "error": "kurzer Grund"}` erfasst (keine Pfade in `error`); es wird als fehlgeschlagen angezeigt, nicht versteckt. Erhält eine Ergebniszeile `invalid_items`, lieferte der Prüfer unmögliche Punktzahlen: Prüfer korrigieren und eine neue Zeile anhängen ([RESULTS_FORMAT.md](RESULTS_FORMAT.md)).
- Schlägt ein Befehl fehl, das Log lesen (`docker logs <Container>`), die Ursache beheben, nicht blind wiederholen.
