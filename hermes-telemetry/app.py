#!/usr/bin/env python3
"""Read NVIDIA/llama.cpp state and expose it to LAN clients and a push receiver."""
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Models are served on demand by the llama-swap gateway; LLAMA_URLS is an optional
# fallback for llama-server instances running outside the gateway.
LLAMA_SWAP_URL = os.getenv("LLAMA_SWAP_URL", "http://llama-swap-gateway:8080").strip().rstrip("/")
configured_llama_urls = os.getenv("LLAMA_URLS", os.getenv("LLAMA_URL", ""))
LLAMA_URLS = [url.strip().rstrip("/") for url in configured_llama_urls.split(",") if url.strip()]
GPU_RECEIVER_URL = os.getenv("GPU_RECEIVER_URL", "")
LLAMA_RECEIVER_URL = os.getenv("LLAMA_RECEIVER_URL", "")
TOKEN_FILE = os.getenv("TOKEN_FILE", "/run/secrets/receiver-token")
TOKEN_HEADER = os.getenv("TOKEN_HEADER", "X-Telemetry-Token")
INTERVAL = max(2, int(os.getenv("SAMPLE_INTERVAL_SECONDS", "5")))
state = {"sampled_at": None, "gpu": None, "llama": None, "delivery": {}}
lock = threading.Lock()


def get_json(url):
    with urllib.request.urlopen(url, timeout=3) as response:
        return json.load(response)


def get_text(url):
    with urllib.request.urlopen(url, timeout=3) as response:
        return response.read().decode("utf-8", errors="replace")


def to_float(value):
    value = value.strip()
    if value.upper() in ("N/A", "[NOT SUPPORTED]"):
        return None
    return float(value)


def gpu_sample():
    fields = ("name,utilization.gpu,utilization.memory,memory.used,memory.free,"
              "memory.total,temperature.gpu,power.draw,power.limit,fan.speed,"
              "clocks.current.graphics,clocks.current.memory,utilization.encoder,"
              "utilization.decoder,clocks_throttle_reasons.active")
    cmd = ["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"]
    output = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=3).stdout
    rows = list(csv.reader(io.StringIO(output), skipinitialspace=True))
    if not rows or len(rows[0]) < 15:
        raise RuntimeError("NVIDIA GPU not found")
    values = [item.strip() for item in rows[0]]
    throttle_mask = int(values[14], 0)
    sample = {
        "name": values[0],
        "gpu_utilization_percent": to_float(values[1]),
        "gpu_memory_utilization_percent": to_float(values[2]),
        "vram_used_mib": to_float(values[3]),
        "vram_free_mib": to_float(values[4]),
        "vram_total_mib": to_float(values[5]),
        "temperature_c": to_float(values[6]),
        "power_w": to_float(values[7]),
        "power_limit_w": to_float(values[8]),
        "fan_speed_percent": to_float(values[9]),
        "graphics_clock_mhz": to_float(values[10]),
        "memory_clock_mhz": to_float(values[11]),
        "encoder_utilization_percent": to_float(values[12]),
        "decoder_utilization_percent": to_float(values[13]),
        "gpu_throttle_reason_mask": throttle_mask,
        "gpu_idle_active": int(bool(throttle_mask & 0x1)),
        "gpu_application_clock_setting_active": int(bool(throttle_mask & 0x2)),
        "gpu_sw_power_cap_active": int(bool(throttle_mask & 0x4)),
        "gpu_hw_slowdown_active": int(bool(throttle_mask & 0x8)),
        "gpu_sync_boost_active": int(bool(throttle_mask & 0x10)),
        "gpu_sw_thermal_slowdown_active": int(bool(throttle_mask & 0x20)),
        "gpu_hw_thermal_slowdown_active": int(bool(throttle_mask & 0x40)),
        "gpu_hw_power_brake_active": int(bool(throttle_mask & 0x80)),
        "gpu_display_clock_setting_active": int(bool(throttle_mask & 0x100)),
        "gpu_throttle_active": int(bool(throttle_mask & ~0x1)),
    }
    if sample["vram_total_mib"]:
        sample["vram_used_percent"] = 100.0 * sample["vram_used_mib"] / sample["vram_total_mib"]
    else:
        sample["vram_used_percent"] = None
    return sample


def parse_metrics(text):
    metrics = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.rsplit(None, 1)
        if len(parts) != 2:
            continue
        try:
            metrics[parts[0]] = float(parts[1])
        except ValueError:
            continue
    return metrics


def summarize(endpoint, health, loaded_models, slots, metrics, source):
    active = [slot for slot in slots if slot.get("is_processing")]
    decoded_tokens = 0
    prompt_tokens = 0
    remaining_tokens = 0
    contexts = []
    capacities = []
    for slot in active:
        prompt_tokens += int(slot.get("n_prompt_tokens_processed", 0) or 0)
        next_tokens = slot.get("next_token") or []
        if isinstance(next_tokens, dict):
            next_tokens = [next_tokens]
        slot_decoded = sum(int(token.get("n_decoded", 0) or 0) for token in next_tokens)
        decoded_tokens += slot_decoded
        remaining_tokens += sum(int(token.get("n_remain", 0) or 0) for token in next_tokens)
        contexts.append(int(slot.get("n_prompt_tokens_processed", 0) or 0) + slot_decoded)
        capacities.append(int(slot.get("n_ctx", 0) or 0))
    context_used = max(contexts, default=0)
    context_capacity = max(capacities, default=0)
    return {"reachable": True, "health": health, "source": source,
            "endpoint": endpoint, "model_loaded": bool(loaded_models),
            "loaded_models": loaded_models,
            "active_slots": len(active),
            "context_used_tokens": context_used,
            "context_capacity_tokens": context_capacity,
            "context_used_percent": 100.0 * context_used / context_capacity if context_capacity else 0.0,
            "prompt_tokens_current": prompt_tokens,
            "decoded_tokens_current": decoded_tokens,
            "generation_remaining_tokens": remaining_tokens,
            "metrics": metrics}


def as_slot_list(slots):
    if isinstance(slots, dict):
        return [slots]
    return slots if isinstance(slots, list) else []


def gateway_sample():
    """Sample llama-swap without loading anything: only models already in memory are queried."""
    get_text(LLAMA_SWAP_URL + "/health")
    running = get_json(LLAMA_SWAP_URL + "/running").get("running") or []
    loaded_models, slots, metrics, busiest = [], [], {}, -1
    for item in running:
        name = item.get("model") or item.get("name")
        if not name or item.get("state") != "ready":
            continue
        loaded_models.append(name)
        base = LLAMA_SWAP_URL + "/upstream/" + urllib.parse.quote(name, safe="")
        try:
            model_slots = as_slot_list(get_json(base + "/slots"))
        except (OSError, ValueError):
            model_slots = []
        slots.extend(model_slots)
        busy = sum(1 for slot in model_slots if slot.get("is_processing"))
        # Report llama.cpp counters of the busiest model (first one on a tie).
        if busy > busiest:
            try:
                metrics = parse_metrics(get_text(base + "/metrics"))
                busiest = busy
            except (OSError, ValueError):
                pass
    return summarize(LLAMA_SWAP_URL, "ok", loaded_models, slots, metrics, "llama-swap")


def direct_sample(base_url):
    health = get_json(base_url + "/health")
    response = get_json(base_url + "/v1/models")
    models = response.get("data") or response.get("models", [])
    loaded_models = [model.get("id") or model.get("name") or model.get("model")
                     for model in models]
    slots = as_slot_list(get_json(base_url + "/slots"))
    metrics = parse_metrics(get_text(base_url + "/metrics"))
    return summarize(base_url, health.get("status", "ok"), loaded_models, slots, metrics, "llama-server")


def llama_sample():
    failures = []
    if LLAMA_SWAP_URL:
        try:
            gateway = gateway_sample()
            if gateway["model_loaded"] or not LLAMA_URLS:
                return gateway
        except Exception as exc:
            gateway = None
            failures.append("llama-swap:" + type(exc).__name__)
    else:
        gateway = None
    if LLAMA_URLS:
        with ThreadPoolExecutor(max_workers=len(LLAMA_URLS)) as pool:
            futures = [pool.submit(direct_sample, base_url) for base_url in LLAMA_URLS]
            for future in as_completed(futures):
                try:
                    return future.result()
                except Exception as exc:
                    failures.append(type(exc).__name__)
    if gateway:
        return gateway
    raise RuntimeError("llama_endpoints_unavailable:" + ",".join(failures))


def post(url, payload):
    if not os.path.isfile(TOKEN_FILE):
        raise RuntimeError("receiver_token_missing")
    headers = {"Content-Type": "application/json"}
    with open(TOKEN_FILE, "r", encoding="utf-8") as source:
        token = source.read().strip()
    if not token:
        raise RuntimeError("receiver_token_missing")
    headers[TOKEN_HEADER] = token
    request = urllib.request.Request(url, json.dumps(payload).encode(), headers, method="POST")
    with urllib.request.urlopen(request, timeout=3) as response:
        return response.status


def update():
    while True:
        sample = {"sampled_at": datetime.now(timezone.utc).isoformat(), "gpu": None,
                  "llama": None, "delivery": {}}
        try:
            sample["gpu"] = gpu_sample()
        except Exception as exc:
            sample["gpu_error"] = type(exc).__name__
        try:
            sample["llama"] = llama_sample()
        except Exception as exc:
            sample["llama"] = {"reachable": False, "model_loaded": False, "loaded_models": []}
            sample["llama_error"] = type(exc).__name__
        for key, url, data in (("gpu", GPU_RECEIVER_URL, sample["gpu"]),
                               ("llama", LLAMA_RECEIVER_URL, sample["llama"])):
            if url and data:
                try:
                    sample["delivery"][key] = {"http_status": post(url, data), "ok": True}
                except Exception as exc:
                    sample["delivery"][key] = {"ok": False, "error": type(exc).__name__}
        with lock:
            state.clear()
            state.update(sample)
        time.sleep(INTERVAL)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/health", "/status", "/metrics"):
            self.send_error(404)
            return
        with lock:
            current = dict(state)
        fresh = bool(current["sampled_at"] and
                     datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(current["sampled_at"]).timestamp() < INTERVAL * 3)
        # /health answers for the exporter itself: it samples and the GPU is readable. A stopped gateway
        # (benchmarks, video generation) or an idle one with no model loaded is not a fault of this container;
        # it is reported separately as llama_reachable / llama_model_loaded and as "degraded" in /status.
        llama_up = bool(current["llama"] and current["llama"].get("reachable"))
        healthy = fresh and current["gpu"] is not None
        if self.path == "/metrics":
            gpu = current["gpu"] or {}
            llama = current["llama"] or {}
            age = 0.0
            if current["sampled_at"]:
                age = max(0.0, datetime.now(timezone.utc).timestamp() -
                          datetime.fromisoformat(current["sampled_at"]).timestamp())
            lines = [f"{key} {value}" for key, value in gpu.items()
                     if key != "name" and isinstance(value, (int, float))]
            lines.extend(f"{key} {value}" for key, value in llama.get("metrics", {}).items())
            lines += [f"llama_reachable {int(bool(llama.get('reachable')))}",
                      f"llama_model_loaded {int(bool(llama.get('model_loaded')))}",
                      f"llama_active_slots {int(llama.get('active_slots', 0))}",
                      f"llama_context_used_tokens {int(llama.get('context_used_tokens', 0))}",
                      f"llama_context_capacity_tokens {int(llama.get('context_capacity_tokens', 0))}",
                      f"llama_context_used_percent {float(llama.get('context_used_percent', 0.0)):.3f}",
                      f"llama_prompt_tokens_current {int(llama.get('prompt_tokens_current', 0))}",
                      f"llama_decoded_tokens_current {int(llama.get('decoded_tokens_current', 0))}",
                      f"llama_generation_remaining_tokens {int(llama.get('generation_remaining_tokens', 0))}",
                      f"telemetry_gpu_sample_success {int(current['gpu'] is not None)}",
                      f"telemetry_llama_sample_success {int(bool(llama.get('reachable')))}",
                      f"telemetry_sample_age_seconds {age:.3f}"]
            body = ("\n".join(lines) + "\n").encode()
            content_type = "text/plain; charset=utf-8"
        else:
            payload = {"healthy": healthy, "degraded": healthy and not llama_up, **current} if self.path == "/status" else {"healthy": healthy}
            body = json.dumps(payload, ensure_ascii=False).encode()
            content_type = "application/json; charset=utf-8"
        self.send_response(200 if self.path != "/health" or healthy else 503)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # client closed early (e.g. urllib raising on a 503 before reading the body)

    def log_message(self, *args):
        pass


threading.Thread(target=update, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", 9835), Handler).serve_forever()
