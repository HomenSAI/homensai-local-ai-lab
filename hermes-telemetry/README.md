# Hermes / Codex AI telemetry on the server

The `hermes-telemetry` Docker container reads NVIDIA GPU counters and the active
`llama.cpp` server. It does not run a model server or load a model itself.

Local network endpoints on the server (`${LAN_IP:-127.0.0.1}:9835`):

- `GET /status`: JSON with GPU counters, Llama server health, loaded model IDs,
  active slots, and delivery results. This is the shared status source for Hermes
  and Codex.
- `GET /health`: HTTP 200 when the exporter itself works: the sample is fresh and the GPU is
  readable; otherwise 503. A stopped or idle llama-swap gateway does not make it unhealthy:
  `/status` then reports `"degraded": true`, and `llama_reachable` / `llama_model_loaded`
  in `/metrics` show the gateway state.
- `GET /metrics`: numeric text metrics for monitoring.

A remote collector (Prometheus, Grafana Agent, ...) should pull `/metrics` every 5 seconds.
use `/status` for a JSON snapshot. Windows Firewall permits these connections
from that notebook IP only. The exporter reads the llama-swap gateway
(`LLAMA_SWAP_URL`, default `http://llama-swap-gateway:8080`): `/running` for the
models in memory, then `/upstream/<model>/slots` and `/metrics` for each ready
model, so it never triggers a model load. `LLAMA_URLS` optionally adds
llama-server instances running outside the gateway. It does not push data to the notebook.

The GPU metrics include utilization, VRAM use, temperature, fan speed, power,
clocks, encoder/decoder utilization, and clock-throttle reasons. The Llama
metrics include model and health state, active/deferred requests, token counts,
throughput, live context fill, and counters from llama.cpp's `/metrics` endpoint.
TCP `8080` is the separate OpenAI-compatible model API, also limited to the
notebook IP; telemetry collection itself only needs TCP `9835`.

Start or update with `docker compose -f compose.yaml up -d --build` from this
directory. Docker Desktop starts at Windows sign-in; this container has
`restart: unless-stopped` and joins the existing `ai-net` network.

Optional notebook push delivery: set `GPU_RECEIVER_URL` to the notebook's production
`/gpu-sample` URL and `LLAMA_RECEIVER_URL` to its production AI status route. Mount
a permanent receiver token at `/run/secrets/receiver-token`; it is sent in the
header named by `TOKEN_HEADER` (default `X-Telemetry-Token`) and is never included
in `/status`. The receiver
contract and permanent credential are pending from notebook Codex. Do not use
the earlier temporary test token for this service.

The GPU POST JSON fields are `name`, `gpu_utilization_percent`,
`vram_used_mib`, `vram_free_mib`, `temperature_c`, and `power_w`. The AI POST
contains the `llama` object from `/status`. The receiver must agree to these
schemas before delivery is enabled.
