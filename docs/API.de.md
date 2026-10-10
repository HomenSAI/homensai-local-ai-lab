# HTTP-Schnittstellen (für Bediener und KI-Supervisoren)

Andere Sprachen: [English](API.md) · [Русский](API.ru.md)

Alles Folgende ist einfaches HTTP auf dem lokalen Rechner. Das Gateway hat keine Authentifizierung: Verwenden Sie nur `127.0.0.1` oder ein vertrauenswürdiges LAN. Ersetzen Sie `localhost` durch die LAN-Adresse, wenn Sie die Konsole geöffnet haben (siehe `AI_CONSOLE_BIND_IP`).

## Regeln, die jede Anfrage an die Konsole einhalten muss

Die Konsole prüft jede Anfrage (siehe [SECURITY.de.md](../SECURITY.de.md)); ein Skript oder ein KI-Supervisor muss sich daran halten:

| Regel | Einzelheiten |
|---|---|
| `Host`-Header | `localhost`, eine IP-Adresse oder ein in `AI_CONSOLE_ALLOWED_HOSTS` eingetragener Name; sonst `421`. `/health` ist ausgenommen |
| Passwort | Ist `AI_CONSOLE_PASSWORD` gesetzt, HTTP-Basic-Zugangsdaten senden (beliebiger Benutzername): `curl -u any:PASSWORD ...`; sonst `401`. `/health` ist ausgenommen |
| Inhaltstyp bei `POST` | **Immer** `Content-Type: application/json`, auch bei Aufrufen ohne Body (`/api/timer/cancel`); sonst `415`. Mit `curl` `-H "Content-Type: application/json"` verwenden |
| Herkunft bei `POST` | Skripte senden keinen `Origin`-Header, das ist in Ordnung. Eine Browser-Anfrage von einer anderen Herkunft erhält `403` |
| Body | Ein JSON-Objekt. Leer oder zu groß: `413`; ungültiges JSON oder kein Objekt: `400` |
| Methoden | Nur `GET` und `POST` (`HEAD`, `OPTIONS` antworten mit `501`); die Konsole sendet nie CORS-Header |

Jede Antwort enthält `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` und `Referrer-Policy: no-referrer`. Fehlerantworten haben die Form `{"error": "..."}`.

```
curl -X POST http://localhost:8766/api/start -H "Content-Type: application/json" -d '{"model_key":"MiniCPM5-2B-Q8_0"}'
```

## Gateway – OpenAI-kompatibel, Port 8080

| Methode und Pfad | Zweck |
|---|---|
| `GET /v1/models` | Modellprofile aus `config/llama-swap.yaml` |
| `POST /v1/chat/completions` | Chat; `"model"` ist ein Profilname; die erste Anfrage an ein Modell lädt es (bis zu einer Minute). Die Antwort enthält `usage` und, von llama.cpp, `timings` (`prompt_per_second`, `predicted_per_second`, `prompt_n`, `predicted_n`) |
| `POST /v1/embeddings` | Embeddings mit den Profilen `Qwen3-Embedding-*` |
| `GET /running` | aktuell geladene Modelle: `{"running": [...]}` |
| `POST /api/models/unload` | alle Modelle entladen; `POST /api/models/unload/<model>` entlädt eines |
| `GET /health` | Zustand des Gateways |

Jedes OpenAI-SDK funktioniert mit `base_url="http://localhost:8080/v1"` und einem beliebigen API-Schlüssel. Um das Denken (Thinking) bei Modellen abzuschalten, die es haben, fügen Sie der Anfrage `"chat_template_kwargs": {"enable_thinking": false}` hinzu.

```
curl http://localhost:8080/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"MiniCPM5-2B-Q8_0","messages":[{"role":"user","content":"Say hello in one word"}],"max_tokens":16,"temperature":0}'
```

## Konsole – Port 8766

| Methode und Pfad | Zweck |
|---|---|
| `GET /health` | `{"ok": true}` (braucht weder Passwort noch einen bekannten `Host`) |
| `GET /api/version` | `{"name", "version", "author", "url", "repo"}` |
| `GET /api/status` | Zustand von Docker und GPU, Modelle im Speicher (`active_models`), `host_ai`-Container, `issues` (muss auf einem gesunden System leer sein), laufender Job |
| `GET /api/models` | Katalog mit Vorhandensein der Datei (`exists`), Größe, Kontext, Quantisierung, abgestimmten Parametern |
| `POST /api/start` | Body `{"model_key": "<profile>"}`: lädt ein Modell in den Videospeicher; gibt `{"job_id"}` zurück; `GET /api/jobs/<job_id>` abfragen, bis `status` `complete` oder `error` ist |
| `POST /api/unload` | Body `{"model_key": "<profile>"}`: entlädt ein Modell |
| `POST /api/chat` | Body `{"model_key", "payload": {OpenAI chat request}}`: wie das Gateway, mit dem Videospeicher-Schutz |
| `GET /api/timer`, `POST /api/timer` `{"seconds": 900}`, `POST /api/timer/cancel` | Timer zum Entladen aller Modelle |
| `GET /api/tests` | alle Testergebnisse pro Modell zusammengeführt, der Phasenplan (`plan.stages`, `plan.overall`), die Liste der Testsuiten; das zeigt die Tabelle der Konsole |
| `GET /report/` | die Berichtsseite; `GET /report/live-data.json` ihre Daten |
| `GET /legal/<file>` | Lizenz- und Hinweisdateien |

`/api/start` und `/api/chat` antworten mit `409`, solange der Video-Studio-Container die GPU belegt.

## Berichtsdaten

- `report/live-data.json` – wird alle 15 Sekunden vom Berichtsgenerator geschrieben: `entries` (einer pro Modell mit den Blöcken `general`, `german`, `context`, `stem`, `chem`, `code20`), `plan` (Phasen, Fortschritt, Restzeit), `suites`, `status`.
- `results-db/llm-results.sqlite` – das Archiv (`raw_rows`, `results`, `history`, `model_scores`); nur lesend öffnen.
- Git: Das lokale Gitea (`http://localhost:3010/`) bewahrt jede Berichtsversion als Tags `vNNNN`, `stage-<id>-done`, `final-<date>` auf.

## Dateien, die ein Bediener schreibt

Testwerkzeuge schreiben `bench_results/results_*.jsonl` und `bench_results/<stage>.log`: siehe [RESULTS_FORMAT.de.md](RESULTS_FORMAT.de.md).
