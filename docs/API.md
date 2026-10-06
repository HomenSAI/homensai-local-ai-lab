# HTTP interfaces (for operators and AI supervisors)

Everything below is plain HTTP on the local machine. The gateway has no authentication: use `127.0.0.1` or a trusted LAN only. Replace `localhost` with the LAN address if you opened the console (see `AI_CONSOLE_BIND_IP`).

## Rules every console request must follow

The console checks each request (see [SECURITY.md](../SECURITY.md)); a script or an AI supervisor has to comply:

| Rule | Detail |
|---|---|
| `Host` header | `localhost`, an IP address, or a name listed in `AI_CONSOLE_ALLOWED_HOSTS`; otherwise `421`. `/health` is exempt |
| Password | If `AI_CONSOLE_PASSWORD` is set, send HTTP Basic credentials (any user name): `curl -u any:PASSWORD ...`; otherwise `401`. `/health` is exempt |
| `POST` content type | **Always** `Content-Type: application/json`, also for calls without a body (`/api/timer/cancel`); otherwise `415`. With `curl` use `-H "Content-Type: application/json"` |
| `POST` origin | Scripts send no `Origin` header, which is fine. A browser request from another origin gets `403` |
| Body | A JSON object. Empty or too large: `413`; invalid JSON or not an object: `400` |
| Methods | `GET` and `POST` only (`HEAD`, `OPTIONS` answer `501`); the console never sends CORS headers |

Every answer carries `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer`. Error answers are `{"error": "..."}`.

```
curl -X POST http://localhost:8766/api/start -H "Content-Type: application/json" -d '{"model_key":"MiniCPM5-2B-Q8_0"}'
```

## Gateway - OpenAI-compatible, port 8080

| Method and path | Purpose |
|---|---|
| `GET /v1/models` | model profiles from `config/llama-swap.yaml` |
| `POST /v1/chat/completions` | chat; `"model"` is a profile name; the first request to a model loads it (up to a minute). The response contains `usage` and, from llama.cpp, `timings` (`prompt_per_second`, `predicted_per_second`, `prompt_n`, `predicted_n`) |
| `POST /v1/embeddings` | embeddings with the `Qwen3-Embedding-*` profiles |
| `GET /running` | models currently loaded: `{"running": [...]}` |
| `POST /api/models/unload` | unload every model; `POST /api/models/unload/<model>` unloads one |
| `GET /health` | gateway health |

Any OpenAI SDK works with `base_url="http://localhost:8080/v1"` and an arbitrary API key. To switch off thinking in models that have it, add `"chat_template_kwargs": {"enable_thinking": false}` to the request.

```
curl http://localhost:8080/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"MiniCPM5-2B-Q8_0","messages":[{"role":"user","content":"Say hello in one word"}],"max_tokens":16,"temperature":0}'
```

## Console - port 8766

| Method and path | Purpose |
|---|---|
| `GET /health` | `{"ok": true}` (needs no password and no known `Host`) |
| `GET /api/version` | `{"name", "version", "author", "url", "repo"}` |
| `GET /api/status` | Docker and GPU state, models in memory (`active_models`), `host_ai` containers, `issues` (must be empty on a healthy system), running job |
| `GET /api/models` | catalog with file existence (`exists`), size, context, quantization, tuned parameters |
| `POST /api/start` | body `{"model_key": "<profile>"}`: loads a model into video memory; returns `{"job_id"}`; poll `GET /api/jobs/<job_id>` until `status` is `complete` or `error` |
| `POST /api/unload` | body `{"model_key": "<profile>"}`: unloads one model |
| `POST /api/chat` | body `{"model_key", "payload": {OpenAI chat request}}`: same as the gateway, with the video-memory guard |
| `GET /api/timer`, `POST /api/timer` `{"seconds": 900}`, `POST /api/timer/cancel` | unload-all timer |
| `GET /api/tests` | all test results joined per model, the stage plan (`plan.stages`, `plan.overall`), the suites list; this is what the console table shows |
| `GET /report/` | the report page; `GET /report/live-data.json` its data |
| `GET /legal/<file>` | license and notice files |

`/api/start` and `/api/chat` answer `409` while the Video Studio container holds the GPU.

## Report data

- `report/live-data.json` - written every 15 seconds by the report builder: `entries` (one per model with `general`, `german`, `context`, `stem`, `chem`, `code20` blocks), `plan` (stages, progress, time left), `suites`, `status`.
- `results-db/llm-results.sqlite` - the archive (`raw_rows`, `results`, `history`, `model_scores`); open it read-only.
- Git: the local Gitea (`http://localhost:3010/`) holds every report version as tags `vNNNN`, `stage-<id>-done`, `final-<date>`.

## Files an operator writes

Test tools write `bench_results/results_*.jsonl` and `bench_results/<stage>.log`: see [RESULTS_FORMAT.md](RESULTS_FORMAT.md).
