"""Always-on model console for the llama-swap gateway."""
from __future__ import annotations

import json
import http.client
import os
import re
import shlex
import socket
import subprocess
import threading
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit

import security
import tests_feed

WEB = Path(__file__).resolve().parent
REPORT_DIR = Path("/app/report")
STYLE_DIR = WEB / "style"   # HomenS.AI Style 1.8.1 (copied from the homensai-style repository; version in the pages' homensai-style meta)
STYLE_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml",
               ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}
DOWNLOADS = {"/BENCHMARK_RESULTS.csv": Path("/app/downloads/BENCHMARK_RESULTS.csv"),
             "/BENCHMARK_RESULTS.db": Path("/app/downloads/BENCHMARK_RESULTS.db"),
             "/media/images/qwen-image-2.1-smoke.png": Path("/app/downloads/qwen-image-2.1-smoke.png")}
MODEL_ROOT = Path(os.environ.get("MODEL_DIR", "/models"))
GATEWAY = os.environ.get("AI_GATEWAY_URL", "http://llama-swap-gateway:8080").rstrip("/")
PORT = int(os.environ.get("AI_CONSOLE_PORT", "8766"))
PASSWORD = os.environ.get("AI_CONSOLE_PASSWORD", "")
ALLOWED_HOSTS = security.parse_hosts(os.environ.get("AI_CONSOLE_ALLOWED_HOSTS"))
MODEL_FAST = Path(os.environ.get("MODEL_FAST_DIR", "/models-fast"))
GATEWAY_CONFIG = Path("/app/llama-swap.yaml")
RECOMMENDATIONS = Path("/app/recommended-settings.json")
TIMER_FILE = Path("/state/unload-timer.json")

# Models run only through the llama-swap gateway; these are the remaining separate service containers.
SERVICE_MODELS = {"whisper": "Whisper large-v3 turbo", "qwen-image": "Qwen-Image 2.1"}
metric_history: dict[str, tuple[float, float]] = {}
metric_lock = threading.Lock()
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()
active_job_id: str | None = None
timer_lock = threading.Lock()
timer_state: dict = {"status": "idle", "deadline": None, "seconds": None, "error": None}
timer_generation = 0


def save_timer() -> None:
    TIMER_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = TIMER_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(timer_state), encoding="utf-8")
    temporary.replace(TIMER_FILE)


def timer_snapshot() -> dict:
    with timer_lock:
        state = dict(timer_state)
    if state["status"] == "counting":
        state["remaining_seconds"] = max(0, int(state["deadline"] - time.time() + 0.999))
    else:
        state["remaining_seconds"] = 0
    return state


def run_unload_timer(generation: int) -> None:
    global timer_state
    while True:
        with timer_lock:
            if generation != timer_generation or timer_state["status"] not in ("counting", "unloading"):
                return
            remaining = (timer_state["deadline"] or 0) - time.time()
            if remaining <= 0 or timer_state["status"] == "unloading":
                timer_state["status"] = "unloading"
                save_timer()
                break
        time.sleep(min(0.5, max(0.05, remaining)))
    try:
        request = urllib.request.Request(GATEWAY + "/api/models/unload", data=b"", method="POST")
        with urllib.request.urlopen(request, timeout=120) as response:
            response.read()
        for _ in range(30):
            _, running, error = gateway_snapshot()
            if error:
                raise RuntimeError(error)
            if not running:
                break
            time.sleep(1)
        else:
            raise RuntimeError("После команды выгрузки модели ещё находятся в памяти.")
        with timer_lock:
            if generation == timer_generation:
                timer_state = {"status": "waiting", "deadline": None, "seconds": timer_state["seconds"], "error": None}
                save_timer()
    except (OSError, RuntimeError, ValueError) as exc:
        with timer_lock:
            if generation == timer_generation:
                timer_state = {"status": "error", "deadline": None, "seconds": timer_state["seconds"], "error": str(exc)}
                save_timer()


class DockerConnection(http.client.HTTPConnection):
    def __init__(self):
        super().__init__("docker", timeout=4)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(4)
        self.sock.connect("/var/run/docker.sock")


def docker_json(path: str):
    connection = DockerConnection()
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        if response.status != 200:
            raise OSError(f"Docker API HTTP {response.status}")
        return json.load(response)
    finally:
        connection.close()


def docker_raw(path: str) -> bytes:
    connection = DockerConnection()
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        if response.status != 200:
            raise OSError(f"Docker API HTTP {response.status}")
        return response.read()
    finally:
        connection.close()


def docker_log_tail(container: str, lines: int = 4) -> list[str]:
    """Last log lines of a container; demultiplexes the non-TTY Docker log stream."""
    raw = docker_raw(f"/containers/{container}/logs?stdout=1&stderr=1&tail={lines}")
    chunks, index = [], 0
    while index + 8 <= len(raw) and raw[index] in (0, 1, 2) and raw[index + 1:index + 4] == b"\0\0\0":
        size = int.from_bytes(raw[index + 4:index + 8], "big")
        chunks.append(raw[index + 8:index + 8 + size])
        index += 8 + size
    text = b"".join(chunks).decode("utf-8", errors="replace") if chunks and index == len(raw) else raw.decode("utf-8", errors="replace")
    return [line.strip() for line in re.split(r"[\r\n]+", text) if re.search(r"\w", line)]


EXEC_CONTAINER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
EXEC_URL = re.compile(r"http://127\.0\.0\.1:\d{1,5}/(?:slots|metrics|health)")


def docker_exec_read(container: str, url: str, fail: bool = True) -> bytes:
    """Read an internal model endpoint without publishing its port on the network.

    The Docker socket is root-equivalent, so only one fixed kind of command is ever sent through it: curl against a
    llama-server status endpoint on 127.0.0.1 inside a container whose name has the plain Docker name form."""
    if not EXEC_CONTAINER.fullmatch(container) or not EXEC_URL.fullmatch(url):
        raise OSError("docker exec refused: container or URL is not an allowed form")
    command = ["curl", "--max-time", "2", "-fsS" if fail else "-sS", url]
    payload = json.dumps({"AttachStdout": True, "AttachStderr": True, "Tty": True,
                          "Cmd": command}).encode("utf-8")
    connection = DockerConnection()
    try:
        connection.request("POST", f"/containers/{container}/exec", payload,
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 201:
            raise OSError(f"Docker exec create HTTP {response.status}")
        exec_id = json.load(response)["Id"]
    finally:
        connection.close()
    connection = DockerConnection()
    try:
        connection.request("POST", f"/exec/{exec_id}/start", b'{"Detach":false,"Tty":true}',
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise OSError(f"Docker exec start HTTP {response.status}")
        return response.read()
    finally:
        connection.close()


def gateway_port(item: dict) -> int | None:
    proxy = urlsplit(str(item.get("proxy") or ""))
    if proxy.hostname not in ("localhost", "127.0.0.1") or not proxy.port or not 5800 <= proxy.port <= 6000:
        return None
    return proxy.port


def llama_slots(container: str, port: int | None) -> list[dict]:
    if not port:
        return []
    try:
        raw = docker_exec_read(container, f"http://127.0.0.1:{port}/slots")
        slots = json.loads(raw)
        return slots if isinstance(slots, list) else []
    except (OSError, ValueError, KeyError):
        return []


def llama_metrics(container: str, port: int | None, alias: str) -> dict:
    if not port:
        return {}
    try:
        raw = docker_exec_read(container, f"http://127.0.0.1:{port}/metrics")
        counters = {}
        for line in raw.decode("utf-8", errors="replace").splitlines():
            if line.startswith("llamacpp:"):
                parts = line.split()
                if len(parts) == 2:
                    try:
                        counters[parts[0]] = float(parts[1])
                    except ValueError:
                        pass
        if not counters:
            return {}
        generated = counters.get("llamacpp:tokens_predicted_total", 0.0)
        seconds = counters.get("llamacpp:tokens_predicted_seconds_total", 0.0)
        speed = generated / seconds if seconds > 0 else None
        with metric_lock:
            previous = metric_history.get(alias)
            if previous and generated >= previous[0] and seconds > previous[1]:
                speed = (generated - previous[0]) / (seconds - previous[1])
            metric_history[alias] = (generated, seconds)
            read_tokens = counters.get("llamacpp:prompt_tokens_total", 0.0)
            read_seconds = counters.get("llamacpp:prompt_seconds_total", 0.0)
            read_speed = read_tokens / read_seconds if read_seconds > 0 else None
            previous_read = metric_history.get(alias + ":read")
            if previous_read and read_tokens >= previous_read[0] and read_seconds > previous_read[1]:
                read_speed = (read_tokens - previous_read[0]) / (read_seconds - previous_read[1])
            metric_history[alias + ":read"] = (read_tokens, read_seconds)
        return {"prompt_tokens_total": int(counters.get("llamacpp:prompt_tokens_total", 0)),
                "generated_tokens_total": int(generated),
                "speed_tps": round(speed, 1) if speed is not None else None,
                "prompt_speed_tps": round(read_speed, 1) if read_speed is not None else None}
    except (OSError, ValueError, KeyError):
        return {}


def docker_services() -> tuple[list[dict], str | None]:
    try:
        containers = docker_json("/containers/json?all=0")
        result = []
        for item in containers:
            labels = item.get("Labels") or {}
            if labels.get("com.docker.compose.project") != "local-ai-server":
                continue
            result.append({"id": item["Id"], "name": (item.get("Names") or [""])[0].lstrip("/"),
                           "service": labels.get("com.docker.compose.service") or "",
                           "state": item.get("State") or "", "status": item.get("Status") or ""})
        return result, None
    except (OSError, ValueError) as exc:
        return [], str(exc)


VIDEO_CONTAINER = os.environ.get("VIDEO_CONTAINER", "video-generation-comfyui-video-1")


def video_busy() -> str | None:
    """Message when the separate Video Studio project holds the GPU (its ComfyUI container is running), else None."""
    try:
        if docker_json(f"/containers/{VIDEO_CONTAINER}/json")["State"]["Running"]:
            return "Работает генерация видео (ComfyUI держит видеопамять). Остановите её в проекте Video Studio."
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def gateway_json(path: str, timeout: int = 5) -> dict:
    with urllib.request.urlopen(GATEWAY + path, timeout=timeout) as response:
        return json.load(response)


def gateway_snapshot() -> tuple[list[dict], list[dict], str | None]:
    try:
        models = gateway_json("/v1/models").get("data", [])
        running = gateway_json("/running").get("running", [])
        return models, running, None
    except (OSError, ValueError) as exc:
        return [], [], str(exc)


def gpu_sample() -> dict:
    sampled = utc_now()
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,power.draw,temperature.gpu",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=True)
        fields = [part.strip() for part in result.stdout.splitlines()[0].split(",")]
        return {"available": True, "name": fields[0], "memory_total_mib": int(float(fields[1])),
                "memory_used_mib": int(float(fields[2])), "memory_free_mib": int(float(fields[3])),
                "utilization_percent": int(float(fields[4])), "power_w": float(fields[5]),
                "temperature_c": int(float(fields[6])), "sampled_utc": sampled}
    except (OSError, ValueError, IndexError, subprocess.SubprocessError) as exc:
        return {"available": False, "error": str(exc), "sampled_utc": sampled}


_config_cache: dict = {"mtime": None, "assets": {}}


def config_assets() -> dict[str, tuple[str, ...]]:
    """alias -> model files (relative to the gateway's /models), read from the live llama-swap config."""
    try:
        mtime = GATEWAY_CONFIG.stat().st_mtime
        if _config_cache["mtime"] == mtime:
            return _config_cache["assets"]
        assets: dict[str, tuple[str, ...]] = {}
        in_models, alias, block = False, None, []

        def flush() -> None:
            if alias:
                text = " ".join(block)
                files = re.findall(r"--(?:model|mmproj)\s+/models/(\S+?\.gguf)", text)
                if files:
                    assets[alias] = tuple(files)
        for line in GATEWAY_CONFIG.read_text(encoding="utf-8").splitlines():
            if re.match(r"^models:\s*$", line):
                in_models = True
            elif in_models and re.match(r"^\S", line):
                break
            elif in_models and (match := re.match(r"^  ([^\s#][^:]*):\s*$", line)):
                flush()
                alias, block = match.group(1).strip("'\""), []
            elif in_models:
                block.append(line)
        flush()
        _config_cache.update(mtime=mtime, assets=assets)
        return assets
    except OSError:
        return {}


def model_files(alias: str) -> list[Path]:
    """Model files as this container sees them: the fast volume first, then the legacy MODEL_DIR mount."""
    relative = config_assets().get(alias, ())
    return [MODEL_FAST / file if (MODEL_FAST / file).is_file() or not (MODEL_ROOT / file).is_file() else MODEL_ROOT / file
            for file in relative]


def catalog_entry(model: dict) -> dict:
    alias = str(model.get("id", ""))
    paths = model_files(alias)
    files = tuple(str(path.relative_to(MODEL_FAST if MODEL_FAST in path.parents else MODEL_ROOT)) for path in paths)
    primary = paths[0] if paths else None
    modalities = (model.get("architecture") or {}).get("input_modalities") or []
    vision = "image" in modalities
    return {"key": alias, "name": alias, "asset": files[0] if files else "", "path": str(primary) if primary else "",
            "exists": bool(paths) and all(path.is_file() for path in paths),
            "size_bytes": primary.stat().st_size if primary and primary.is_file() else 0,
            "sha256": None, "extra": [{"path": str(path), "exists": path.is_file()} for path in paths[1:]],
            "profile": "gateway", "service": "llama-swap-gateway", "port": 8080,
            "kind": "embedding" if "embedding" in alias.lower() else "vision" if vision else "chat", "context": model.get("context_length") or model.get("context_window") or 0,
            "group": "Embedding" if "embedding" in alias.lower() else "Vision" if vision else "LLM", "role": "ШЛЮЗ ОСТАНОВЛЕН" if model.get("gateway_offline") else "ЗАГРУЖЕНА" if (model.get("status") or {}).get("value") == "loaded" else "ДОСТУПНА ПО ЗАПРОСУ",
            "note": model.get("description") or "", "quant": quantization(files[0] if files else alias) or "—"}


_catalog_cache: dict = {"mtime": None, "items": []}


def config_catalog() -> list[dict]:
    """Models of the live llama-swap config: alias, context, vision flag, description (used while the gateway is down)."""
    try:
        mtime = GATEWAY_CONFIG.stat().st_mtime
        if _catalog_cache["mtime"] == mtime:
            return _catalog_cache["items"]
        items, in_models, alias, block = [], False, None, []

        def flush() -> None:
            if alias:
                text = " ".join(block)
                ctx = re.search(r"--ctx-size\s+(\d+)", text)
                desc = re.search(r"description:\s*(['\"]?)(.*?)\1\s+cmd:", text)
                items.append({"alias": alias, "context": int(ctx.group(1)) if ctx else 0, "vision": "--mmproj" in text,
                              "description": desc.group(2) if desc else ""})

        for line in GATEWAY_CONFIG.read_text(encoding="utf-8").splitlines():
            if re.match(r"^models:\s*$", line):
                in_models = True
            elif in_models and re.match(r"^\S", line):
                break
            elif in_models and (match := re.match(r"^  ([^\s#][^:]*):\s*$", line)):
                flush()
                alias, block = match.group(1).strip("'\""), []
            elif in_models:
                block.append(line.strip())
        flush()
        _catalog_cache.update(mtime=mtime, items=items)
        return items
    except OSError:
        return []


def catalog_models(models: list[dict]) -> list[dict]:
    if models:
        return models
    entries = config_catalog()
    return [{"id": item["alias"], "description": item["description"] or "Модель из конфигурации llama-swap; шлюз сейчас остановлен.",
             "context_length": item["context"], "status": {"value": "unloaded"}, "gateway_offline": True,
             "architecture": {"input_modalities": ["text", "image"] if item["vision"] else ["text"]}}
            for item in entries]


def command_options(command: str) -> dict[str, str]:
    args = shlex.split(command)
    options: dict[str, str] = {}
    for index, arg in enumerate(args):
        if arg.startswith("--"):
            options[arg] = args[index + 1] if index + 1 < len(args) and not args[index + 1].startswith("--") else "on"
    return options


def quantization(filename: str) -> str | None:
    match = re.search(r"(PTQ\d+_\d+|Q\d+(?:_K_[A-Z]+|_\d+))", filename, re.IGNORECASE)
    return match.group(1).upper() if match else None


def tuning_for(alias: str) -> dict:
    try:
        profiles = json.loads(RECOMMENDATIONS.read_text(encoding="utf-8")).get("model_profiles", {})
    except (OSError, ValueError):
        return {}
    if alias in profiles:
        profile = profiles[alias]
        return {key: profile[key] for key in (
            "use", "recommended_context_tokens", "recommended_max_input_tokens",
            "largest_tested_context_tokens", "largest_tested_input_tokens",
            "largest_tested_input_recall_pass", "peak_vram_mib", "cache_type_k",
            "cache_type_v", "runtime", "notes") if key in profile}
    baseline = next((value for value in profiles.values() if value.get("baseline_profile") == alias), None)
    if baseline:
        return {"recommended_context_tokens": baseline.get("baseline_recommended_context_tokens"),
                "runtime": baseline.get("baseline_runtime_settings"),
                "notes": "Базовый профиль из сравнения с квантованной версией модели."}
    return {}


def active_entry(item: dict, model_by_id: dict[str, dict]) -> dict:
    alias = str(item.get("model") or item.get("name") or "")
    state = str(item.get("state") or "").lower()
    options = command_options(str(item.get("cmd") or ""))
    parameters = []
    quant = quantization(options.get("--model", alias))
    if quant:
        parameters.append({"label": "Квантование весов", "value": quant})
    for flag, label in (("--model", "Файл"), ("--mmproj", "Vision projector"), ("--ctx-size", "Контекст"),
                        ("--n-gpu-layers", "Слои GPU"), ("--flash-attn", "Flash Attention"),
                        ("--parallel", "Параллельные слоты"), ("--batch-size", "Batch"),
                        ("--ubatch-size", "Micro-batch"), ("--cache-type-k", "KV cache K"),
                        ("--cache-type-v", "KV cache V"), ("--spec-type", "Speculative decoding"),
                        ("--spec-draft-n-max", "MTP n-max")):
        if flag in options:
            value = options[flag].rsplit("/", 1)[-1] if flag in ("--model", "--mmproj") else options[flag]
            parameters.append({"label": label, "value": value})
    if item.get("ttl") is not None:
        parameters.append({"label": "Idle unload", "value": f"{item['ttl']} с"})
    ready = state == "ready" and (model_by_id.get(alias, {}).get("status") or {}).get("value") == "loaded"
    port = gateway_port(item)
    slots = llama_slots("ai-llama-swap-gateway", port) if ready else []
    token_stats = llama_metrics("ai-llama-swap-gateway", port, alias) if ready else {}
    return {"key": alias, "name": alias, "service": "llama-swap-gateway", "container": "ai-llama-swap-gateway",
            "port": 8080, "api_model_id": alias, "api_ready": ready, "status": state,
            "quantization": quant, "tuning": tuning_for(alias),
            "kind": "vision" if "image" in ((model_by_id.get(alias, {}).get("architecture") or {}).get("input_modalities") or []) else "chat",
            "parameters": parameters, "recent_errors": [],
            "activity": slot_activity(slots, options.get("--ctx-size"), ready, token_stats)}


def request_parameters(slot: dict | None) -> list[dict]:
    """Sampling parameters of the request being processed, as reported by llama.cpp /slots."""
    params = (slot or {}).get("params") or {}
    out = []
    for key, label in (("n_predict", "Макс. длина ответа"), ("temperature", "Температура"), ("top_k", "top_k"),
                       ("top_p", "top_p"), ("min_p", "min_p"), ("repeat_penalty", "Штраф повторов")):
        value = params.get(key)
        if value is None:
            continue
        if key == "n_predict" and isinstance(value, int) and value < 0:
            text = "без ограничения"
        else:
            text = f"{value:g}" if isinstance(value, float) else str(value)
        out.append({"label": label, "value": text})
    return out


def slot_activity(slots: list[dict], ctx_fallback, ready: bool, token_stats: dict) -> dict:
    current = next((slot for slot in slots if slot.get("is_processing")), None)
    slot = current or (slots[0] if slots else None)
    context = None
    try:
        total = int((slot or {}).get("n_ctx") or ctx_fallback or 0)
        if slot and total > 0:
            prompt = int(slot.get("n_prompt_tokens") or 0)
            processed = int(slot.get("n_prompt_tokens_processed") or 0)
            decoded = int(((slot.get("next_token") or [{}])[0]).get("n_decoded") or 0)
            used = min(total, max(prompt, processed + decoded))
            context = {"used_tokens": used, "total_tokens": total, "free_tokens": total - used,
                       "percent": round(100 * used / total, 1)}
    except (TypeError, ValueError, IndexError):
        pass
    next_token = (current or {}).get("next_token") or [{}]
    generated = next_token[0].get("n_decoded") if current and next_token else None
    return {"busy": bool(current), "state": "Генерирует ответ" if current else "Модель загружена" if ready else "Модель загружается",
            "context": context, "prompt_tokens": current.get("n_prompt_tokens") if current else None,
            "prompt_processed": current.get("n_prompt_tokens_processed") if current else None,
            "generated_tokens": generated, "token_stats": token_stats,
            "max_tokens": ((current or {}).get("params") or {}).get("n_predict") if current else None,
            "request_parameters": request_parameters(current)}


def container_model_entry(service: dict) -> dict:
    kind = service["service"]
    alias = SERVICE_MODELS[kind]
    busy = kind == "qwen-image"
    detail = docker_json(f"/containers/{service['id']}/json")
    config = detail.get("Config") or {}
    env = dict(entry.split("=", 1) for entry in config.get("Env") or [] if "=" in entry)
    command = config.get("Cmd") or []
    parameters = []
    quant = quantization(env.get("LLAMA_MODEL", "") if kind != "qwen-image" else str(command))
    if quant:
        parameters.append({"label": "Квантование весов", "value": quant})
    if kind == "qwen-image":
        for flag, label in (("--diffusion-model", "Файл"), ("--llm", "Text encoder"),
                            ("--width", "Ширина"), ("--height", "Высота"), ("--steps", "Шаги")):
            if flag in command and command.index(flag) + 1 < len(command):
                value = command[command.index(flag) + 1]
                parameters.append({"label": label, "value": value.rsplit("/", 1)[-1] if flag in ("--diffusion-model", "--llm") else value})
    else:
        for key, label in (("LLAMA_MODEL", "Файл"), ("LLAMA_CTX_SIZE", "Контекст"),
                           ("LLAMA_GPU_LAYERS", "Слои GPU"), ("LLAMA_FLASH_ATTN", "Flash Attention")):
            if env.get(key):
                value = env[key].rsplit("/", 1)[-1] if key == "LLAMA_MODEL" else env[key]
                parameters.append({"label": label, "value": value})
    health = (detail.get("State") or {}).get("Health") or {}
    ready = health.get("Status") == "healthy"
    return {"key": alias, "name": alias, "service": kind, "container": service["name"],
            "port": None, "api_model_id": alias, "api_ready": ready, "status": service["status"],
            "quantization": quant, "tuning": tuning_for(alias),
            "kind": "image" if kind == "qwen-image" else "audio" if kind == "whisper" else "chat",
            "parameters": parameters, "recent_errors": [],
            "activity": {"busy": busy, "state": "Генерирует изображение" if busy else "Модель загружена" if ready else "Сервис запускается",
                         "context": None, "prompt_tokens": None, "prompt_processed": None,
                         "generated_tokens": None, "request_parameters": []}}


AI_KEYWORDS = (("llama-swap", "gateway"), ("llama-server", "llm"), ("ollama", "llm"), ("vllm", "llm"),
               ("text-generation", "llm"), ("sglang", "llm"), ("koboldcpp", "llm"),
               ("comfyui", "image"), ("stable-diffusion", "image"), ("sd-server", "image"),
               ("whisper", "audio"), ("open-webui", "ui"), ("unsloth", "train"))
ROLE_LABELS = {"gateway": "Шлюз llama-swap", "llm": "LLM-сервер", "image": "Генерация изображений и видео",
               "audio": "Распознавание речи", "ui": "Веб-интерфейс", "train": "Обучение",
               "job": "Фоновая задача", "gpu": "GPU-сервис"}
LLAMA_FLAGS = ((("-m", "--model"), "Файл"), (("--mmproj",), "Vision projector"), (("-c", "--ctx-size"), "Контекст"),
               (("-ngl", "--n-gpu-layers", "--gpu-layers"), "Слои GPU"), (("-fa", "--flash-attn"), "Flash Attention"),
               (("-np", "--parallel"), "Параллельные слоты"), (("-ctk", "--cache-type-k"), "KV cache K"),
               (("-ctv", "--cache-type-v"), "KV cache V"))
# Exit codes of a normal `docker stop` / kill; not worth an alert.
QUIET_EXIT_CODES = {0, 128, 130, 137, 143}


def arg_value(args: list[str], names: tuple[str, ...]) -> str | None:
    for index, arg in enumerate(args):
        if arg in names:
            return args[index + 1] if index + 1 < len(args) and not args[index + 1].startswith("-") else "on"
        if "=" in arg and arg.split("=", 1)[0] in names:
            return arg.split("=", 1)[1]
    return None


def classify_container(image: str, command: str, labels: dict, env: dict, gpu: bool) -> str | None:
    service = labels.get("com.docker.compose.service", "")
    if labels.get("com.docker.compose.project") == "local-ai-server" and service in SERVICE_MODELS:
        return "image" if service == "qwen-image" else "audio" if service == "whisper" else "llm"
    for keyword, role in AI_KEYWORDS:
        if keyword in command.lower():
            return role
    for keyword, role in AI_KEYWORDS:
        if keyword in image.lower():
            # The llama.cpp images are reused for helper scripts (downloads, benchmarks).
            return "job" if role in ("gateway", "llm") else role
    if env.get("LLAMA_MODEL"):
        return "llm"
    if "ai-server" in image or "llm" in image.lower():
        return "job"
    return "gpu" if gpu else None


def parse_docker_time(value: str | None) -> float | None:
    if not value or value.startswith("0001-"):
        return None
    try:
        return datetime.fromisoformat(re.sub(r"\.(\d{6})\d*", r".\1", value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def llama_health(container: str, port: int) -> str:
    """ok / loading / down for a llama-server running inside `container`."""
    try:
        raw = docker_exec_read(container, f"http://127.0.0.1:{port}/health", fail=False)
        text = raw.decode("utf-8", errors="replace")
        if '"ok"' in text:
            return "ok"
        return "loading" if "Loading" in text or "503" in text else "down"
    except OSError:
        return "down"


def comfy_queue(port: int) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://host.docker.internal:{port}/queue", timeout=1) as response:
            data = json.load(response)
        return {"running": len(data.get("queue_running") or []), "pending": len(data.get("queue_pending") or [])}
    except (OSError, ValueError):
        return None


def host_ai_inventory(running_gateway: list[dict], gpu: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Every AI-related container on this Docker host, direct llama-servers as model cards, and issues."""
    entries, direct_models, issues = [], [], []
    self_id = socket.gethostname()
    now = time.time()
    for item in docker_json("/containers/json?all=1"):
        labels = item.get("Labels") or {}
        if item["Id"].startswith(self_id) or labels.get("com.docker.compose.service") == "ai-console":
            continue
        try:
            detail = docker_json(f"/containers/{item['Id']}/json")
        except (OSError, ValueError):
            continue
        config = detail.get("Config") or {}
        state = detail.get("State") or {}
        env = dict(entry.split("=", 1) for entry in config.get("Env") or [] if "=" in entry)
        args = list(config.get("Entrypoint") or []) + list(config.get("Cmd") or [])
        image = config.get("Image") or item.get("Image") or ""
        gpu_request = any("gpu" in sum(request.get("Capabilities") or [], [])
                          for request in (detail.get("HostConfig") or {}).get("DeviceRequests") or [])
        role = classify_container(image, " ".join(args), labels, env, gpu_request)
        if not role:
            continue
        name = (item.get("Names") or [""])[0].lstrip("/")
        running = state.get("Status") == "running"
        health = (state.get("Health") or {}).get("Status") if running else None
        ports = []
        for target, bindings in ((detail.get("NetworkSettings") or {}).get("Ports") or {}).items():
            for binding in bindings or []:
                if binding.get("HostIp") in ("::", "[::]"):
                    continue
                host = "127.0.0.1" if binding.get("HostIp") in ("", "0.0.0.0", "127.0.0.1") else binding["HostIp"]
                ports.append({"host": host, "port": int(binding["HostPort"]), "target": target,
                              "public": binding.get("HostIp") in ("", "0.0.0.0")})
        entry = {"id": item["Id"][:12], "container": name, "image": image, "role": role,
                 "role_label": ROLE_LABELS[role], "project": labels.get("com.docker.compose.project"),
                 "state": state.get("Status") or item.get("State") or "", "health": health,
                 "exit_code": None if running else state.get("ExitCode"), "gpu": gpu_request,
                 "started_utc": state.get("StartedAt") if running else None,
                 "finished_utc": None if running else state.get("FinishedAt"),
                 "ports": ports, "model": None, "details": [],
                 "activity": {"state": "Остановлен", "busy": False, "ready": False}, "last_log": None}
        if not running:
            finished = parse_docker_time(state.get("FinishedAt"))
            code = state.get("ExitCode")
            if state.get("Status") == "restarting":
                entry["activity"]["state"] = "Перезапускается"
                issues.append({"severity": "error", "title": f"{name}: контейнер перезапускается по кругу",
                               "detail": f"Код выхода {code}. {state.get('Error') or ''}".strip(),
                               "source": name, "checked_utc": utc_now()})
            elif code not in QUIET_EXIT_CODES and finished and now - finished < 1800:
                issues.append({"severity": "warning", "title": f"{name}: аварийно завершился (код {code})",
                               "detail": state.get("Error") or "Проверьте журнал контейнера.",
                               "source": name, "checked_utc": utc_now()})
            entries.append(entry)
            continue
        if health == "unhealthy":
            log = [part.get("Output", "") for part in (state.get("Health") or {}).get("Log") or []]
            last = next((line.strip() for text in reversed(log) for line in reversed(text.splitlines()) if line.strip()), "")
            issues.append({"severity": "warning", "title": f"{name}: health-check не проходит",
                           "detail": last[:300] or "Контейнер отмечен как unhealthy.",
                           "source": name, "checked_utc": utc_now()})
        activity = entry["activity"]
        activity.update({"state": {"starting": "Запускается", "unhealthy": "Health-check не проходит"}.get(health, "Работает"),
                         "ready": health in (None, "healthy")})
        if role == "gateway":
            loaded = [str(model.get("model") or model.get("name") or "") for model in running_gateway]
            entry["model"] = " · ".join(loaded) or "Модели выгружены"
            entry["details"].append({"label": "Загружено моделей", "value": str(len(loaded))})
            activity["state"] = "Модели в памяти" if loaded else "Ожидает запрос"
        elif role == "llm" and any("llama-server" in arg for arg in args):
            port = int(arg_value(args, ("--port",)) or 8080)
            model_file = arg_value(args, ("-m", "--model")) or ""
            alias = arg_value(args, ("-a", "--alias")) or model_file.rsplit("/", 1)[-1].removesuffix(".gguf") or name
            entry["model"] = alias
            parameters = []
            quant = quantization(model_file)
            if quant:
                parameters.append({"label": "Квантование весов", "value": quant})
            for names, label in LLAMA_FLAGS:
                value = arg_value(args, names)
                if value:
                    parameters.append({"label": label, "value": value.rsplit("/", 1)[-1] if label in ("Файл", "Vision projector") else value})
            entry["details"] = [p for p in parameters if p["label"] in ("Квантование весов", "Контекст", "KV cache K", "Слои GPU")]
            live = llama_health(name, port)
            ready = live == "ok"
            slots = llama_slots(name, port) if ready else []
            stats = llama_metrics(name, port, f"container:{name}") if ready else {}
            model_activity = slot_activity(slots, arg_value(args, ("-c", "--ctx-size")), ready, stats)
            if live == "down":
                model_activity["state"] = "API не отвечает"
            activity.update({"state": model_activity["state"], "busy": model_activity["busy"], "ready": ready,
                             "generated_tokens": model_activity["generated_tokens"],
                             "speed_tps": stats.get("speed_tps")})
            host_port = next((p["port"] for p in ports if p["target"].startswith(f"{port}/")), None)
            direct_models.append({"key": f"container:{name}", "name": alias, "service": "llama-server вне шлюза",
                                  "container": name, "port": host_port, "api_model_id": f"контейнер {name}",
                                  "api_ready": ready, "status": live, "external": True, "quantization": quant,
                                  "tuning": tuning_for(alias), "kind": "chat", "parameters": parameters,
                                  "recent_errors": [], "activity": model_activity})
        elif role == "llm" and env.get("LLAMA_MODEL"):
            entry["model"] = env["LLAMA_MODEL"].rsplit("/", 1)[-1]
        elif role == "image":
            port = next((p["port"] for p in ports), None)
            queue = comfy_queue(port) if port and "comfy" in image.lower() else None
            if queue:
                activity["busy"] = queue["running"] > 0
                activity["state"] = f"Генерирует · в очереди {queue['pending']}" if queue["running"] else "Ожидает задание"
                entry["details"].append({"label": "Очередь", "value": f"{queue['running']} + {queue['pending']}"})
        if role in ("job", "train", "gpu") or health == "unhealthy":
            try:
                lines = docker_log_tail(name)
                entry["last_log"] = lines[-1][:240] if lines else None
            except OSError:
                pass
            if role == "job":
                command = " ".join(args)
                entry["model"] = command if len(command) <= 80 else command[:77] + "…"
                activity["state"] = "Выполняется"
        entries.append(entry)
    holders = [e["container"] for e in entries if e["state"] == "running" and e["role"] != "gateway"
               and (e["gpu"] or e["role"] == "llm")]
    if gpu.get("available") and holders and gpu.get("memory_free_mib", 1 << 20) < 1536:
        issues.append({"severity": "warning", "title": "Мало свободной VRAM для шлюза",
                       "detail": f"Свободно {gpu['memory_free_mib']} MiB. Видеопамять вне llama-swap могут держать: "
                                 f"{', '.join(holders)}. Загрузка модели через шлюз может не поместиться.",
                       "source": "NVIDIA", "checked_utc": utc_now()})
    order = {"gateway": 0, "llm": 1, "image": 2, "audio": 3, "ui": 4, "train": 5, "job": 6, "gpu": 7}
    entries.sort(key=lambda e: (e["state"] != "running", order.get(e["role"], 9), e["container"]))
    return entries, direct_models, issues


def bench_running() -> bool:
    try:
        return bool(docker_json("/containers/bench-runner/json")["State"]["Running"])
    except (OSError, ValueError, KeyError, TypeError):
        return False


def status_payload() -> dict:
    models, running, gateway_error = gateway_snapshot()
    services, docker_error = docker_services()
    by_id = {str(item.get("id")): item for item in models}
    active = [active_entry(item, by_id) for item in running]
    for service in services:
        if service["service"] in SERVICE_MODELS:
            try:
                active.append(container_model_entry(service))
            except (OSError, ValueError):
                continue
    gpu = gpu_sample()
    issues = []
    host_ai: list[dict] = []
    if docker_error is None:
        try:
            host_ai, direct_models, host_issues = host_ai_inventory(running, gpu)
            active.extend(direct_models)
            issues.extend(host_issues)
        except (OSError, ValueError) as exc:
            issues.append({"severity": "warning", "title": "Не удалось опросить контейнеры хоста",
                           "detail": str(exc), "source": "Docker", "checked_utc": utc_now()})
    if docker_error:
        issues.append({"severity": "error", "title": "Docker недоступен", "detail": docker_error,
                       "source": "Docker", "checked_utc": utc_now()})
    if gateway_error and not any(item["service"] in SERVICE_MODELS for item in services):
        if bench_running():
            issues.append({"severity": "info", "title": "Шлюз остановлен на время тестов",
                           "detail": "Работает контейнер bench-runner: шлюз выключен намеренно, после тестов его можно запустить.",
                           "source": "llama-swap", "checked_utc": utc_now()})
        else:
            issues.append({"severity": "warning", "title": "Шлюз моделей остановлен", "detail": gateway_error,
                           "source": "llama-swap", "checked_utc": utc_now()})
    if not gpu.get("available"):
        issues.append({"severity": "warning", "title": "Телеметрия GPU недоступна",
                       "detail": gpu.get("error", ""), "source": "NVIDIA", "checked_utc": utc_now()})
    with jobs_lock:
        job = dict(jobs[active_job_id]) if active_job_id and active_job_id in jobs else None
    return {"mode": "gateway", "utc": utc_now(), "docker_available": docker_error is None,
            "docker_error": docker_error, "gateway_available": gateway_error is None,
            "docker_checked_utc": utc_now(), "docker_project_services": services,
            "active_models": active, "host_ai": host_ai, "gpu": gpu, "issues": issues,
            "models": [{"key": str(item.get("id")), "service_state": "running" if gateway_error is None else None,
                        "api_ready": (item.get("status") or {}).get("value") == "loaded",
                        "api_model_ids": [str(item.get("id"))] if (item.get("status") or {}).get("value") == "loaded" else []}
                       for item in models], "job": job}


def load_model(job_id: str, alias: str) -> None:
    with jobs_lock:
        jobs[job_id].update({"status": "running", "log": "Запрашиваю загрузку модели через llama-swap…"})
    try:
        models, _, gateway_error = gateway_snapshot()
        if gateway_error:
            raise RuntimeError("Шлюз llama-swap остановлен. Дождитесь завершения другой GPU-задачи.")
        if alias not in {str(item.get("id")) for item in models}:
            raise RuntimeError("Модель отсутствует в каталоге шлюза.")
        payload = {"model": alias, "messages": [{"role": "user", "content": "Ответь одним словом: готово."}],
                   "max_tokens": 1, "stream": False}
        request = urllib.request.Request(
            GATEWAY + "/v1/chat/completions", data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=1200) as response:
            response.read()
        with jobs_lock:
            jobs[job_id].update({"status": "complete", "log": "Модель загружена в память.",
                                 "result": {"model": alias, "message": "Модель загружена в память."},
                                 "finished_utc": utc_now()})
    except (OSError, RuntimeError, ValueError) as exc:
        with jobs_lock:
            jobs[job_id].update({"status": "error", "error": str(exc), "log": str(exc),
                                 "finished_utc": utc_now()})


class Handler(BaseHTTPRequestHandler):
    def send_security_headers(self) -> None:
        for name, value in security.SECURITY_HEADERS.items():
            self.send_header(name, value)

    def send_bytes(self, content: bytes, mime: str, status: int = 200, headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_security_headers()
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content)

    def guarded(self) -> bool:
        """False (after answering) when the request fails the Host / Origin / password checks of security.py."""
        verdict = security.check(self.command, self.path, self.headers, PASSWORD, ALLOWED_HOSTS)
        if verdict is None:
            return True
        status, message, headers = verdict
        self.send_bytes(json.dumps({"error": message}, ensure_ascii=False).encode("utf-8"),
                        "application/json; charset=utf-8", status, headers)
        return False

    def read_json(self, limit: int) -> dict | None:
        """JSON object of the request body, or None after an error answer (bad size, bad JSON, not an object)."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > limit:
            self.send_json({"error": "Некорректный размер запроса."}, 413)
            return None
        try:
            data = json.loads(self.rfile.read(length))
        except ValueError as exc:
            self.send_json({"error": f"Некорректный JSON: {exc}"}, 400)
            return None
        if not isinstance(data, dict):
            self.send_json({"error": "Тело запроса должно быть JSON-объектом."}, 400)
            return None
        return data

    def send_json(self, data: dict, status: int = 200) -> None:
        self.send_bytes(json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

    def do_GET(self) -> None:
        if not self.guarded():
            return
        if self.path == "/health":
            self.send_json({"ok": True})
        elif self.path == "/favicon.ico":
            self.send_response(204)
            self.send_security_headers()
            self.end_headers()
        elif self.path == "/api/tests":
            self.send_json(tests_feed.payload())
        elif self.path == "/api/models":
            models, _, error = gateway_snapshot()
            self.send_json({"models": [catalog_entry(item) for item in catalog_models(models)], "error": error})
        elif self.path == "/api/status":
            self.send_json(status_payload())
        elif self.path == "/api/timer":
            self.send_json(timer_snapshot())
        elif re.fullmatch(r"/api/jobs/[a-f0-9]{12}", self.path):
            job_id = self.path.rsplit("/", 1)[-1]
            with jobs_lock:
                job = dict(jobs[job_id]) if job_id in jobs else None
            self.send_json(job or {"error": "Задача не найдена."}, 200 if job else 404)
        elif self.path.split("?", 1)[0] == "/api/version":
            try:
                version = Path("/app/VERSION").read_text(encoding="utf-8").strip()
            except OSError:
                version = "dev"
            self.send_json({"name": "Local AI Server", "version": version, "author": "Serhii Khomenko", "url": "https://homensai.com", "contact": "info@homensai.com",
                            "repo": os.environ.get("PUBLIC_REPO_URL", "")})
        else:
            file = {"/": "index.html", "/index.html": "index.html", "/app.css": "app.css",
                    "/app.js": "app.js", "/shell.js": "shell.js",
                    "/i18n.js": "i18n.js", "/i18n-dict.js": "i18n-dict.js"}.get(self.path.split("?", 1)[0])
            clean = self.path.split("?", 1)[0]
            if clean == "/report":
                self.send_response(301)
                self.send_header("Location", "/report/")
                self.send_security_headers()
                self.end_headers()
                return
            if not file and (clean.startswith("/report/") or clean in DOWNLOADS):
                relative = "index.html" if clean == "/report/" else clean[len("/report/"):]
                target = DOWNLOADS[clean] if clean in DOWNLOADS else (REPORT_DIR / relative).resolve()
                if ".." in relative or (clean not in DOWNLOADS and REPORT_DIR.resolve() not in target.parents) or not target.is_file():
                    self.send_error(404)
                    return
                mime = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                        ".json": "application/json; charset=utf-8", ".md": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8",
                        ".csv": "text/csv; charset=utf-8", ".png": "image/png", ".db": "application/octet-stream"}.get(target.suffix, "application/octet-stream")
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Cache-Control", "no-store")
                self.send_security_headers()
                body = target.read_bytes()
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if not file and clean.startswith("/style/"):
                # HomenS.AI Style package (console/style/): stylesheets, scripts, logo and fonts of the shared design.
                relative = clean[len("/style/"):]
                target = (STYLE_DIR / relative).resolve()
                mime = STYLE_TYPES.get(target.suffix)
                if ".." in relative or STYLE_DIR.resolve() not in target.parents or not mime or not target.is_file():
                    self.send_error(404)
                    return
                self.send_bytes(target.read_bytes(), mime)
                return
            if not file and self.path.startswith("/legal/"):
                name = self.path[len("/legal/"):].split("?", 1)[0]
                target = WEB.parent / "legal" / name
                if "/" in name or ".." in name or not target.is_file():
                    self.send_error(404)
                    return
                self.send_bytes(target.read_bytes(), "text/plain; charset=utf-8")
                return
            if not file:
                self.send_error(404)
                return
            path = WEB / file
            mime = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                    ".js": "text/javascript; charset=utf-8"}[path.suffix]
            self.send_bytes(path.read_bytes(), mime)

    def do_POST(self) -> None:
        if not self.guarded():
            return
        if self.path in ("/api/start", "/api/chat") and (busy := video_busy()):
            self.send_json({"error": busy}, 409)
            return
        if self.path in ("/api/timer", "/api/timer/cancel"):
            global timer_generation, timer_state
            if self.path.endswith("/cancel"):
                with timer_lock:
                    if timer_state["status"] != "counting":
                        self.send_json({"error": "Отсчёт сейчас не идёт."}, 409)
                        return
                    timer_generation += 1
                    timer_state = {"status": "idle", "deadline": None, "seconds": None, "error": None}
                    save_timer()
                self.send_json(timer_snapshot())
                return
            try:
                data = self.read_json(4096)
                if data is None:
                    return
                seconds = data.get("seconds")
                if isinstance(seconds, bool) or not isinstance(seconds, int) or not 1 <= seconds <= 604800:
                    self.send_json({"error": "Укажите целое число секунд от 1 до 604800."}, 400)
                    return
                with timer_lock:
                    if timer_state["status"] == "unloading":
                        self.send_json({"error": "Выгрузка уже выполняется."}, 409)
                        return
                    timer_generation += 1
                    generation = timer_generation
                    timer_state = {"status": "counting", "deadline": time.time() + seconds,
                                   "seconds": seconds, "error": None}
                    save_timer()
                threading.Thread(target=run_unload_timer, args=(generation,), daemon=True).start()
                self.send_json(timer_snapshot())
            except (OSError, ValueError, TypeError) as exc:
                self.send_json({"error": str(exc)}, 400)
            return
        if self.path == "/api/unload":
            try:
                data = self.read_json(4096)
                if data is None:
                    return
                alias = str(data.get("model_key") or "")
                if alias not in config_assets():
                    self.send_json({"error": "Неизвестная модель."}, 404)
                    return
                _, running, error = gateway_snapshot()
                if error:
                    self.send_json({"error": "Шлюз llama-swap недоступен: " + error}, 502)
                    return
                if alias not in {str(item.get("model") or item.get("name") or "") for item in running}:
                    self.send_json({"error": "Эта модель сейчас не загружена."}, 409)
                    return
                request = urllib.request.Request(
                    GATEWAY + "/api/models/unload/" + quote(alias, safe=""), data=b"", method="POST")
                with urllib.request.urlopen(request, timeout=120) as response:
                    response.read()
                self.send_json({"model": alias, "message": "Модель выгружена из памяти."})
            except urllib.error.HTTPError as exc:
                self.send_json({"error": exc.read(2048).decode("utf-8", errors="replace")}, 502)
            except (OSError, ValueError, TypeError) as exc:
                self.send_json({"error": str(exc)}, 502)
            return
        if self.path == "/api/start":
            try:
                data = self.read_json(4096)
                if data is None:
                    return
                alias = str(data.get("model_key") or "")
                if alias not in config_assets():
                    self.send_json({"error": "Неизвестная модель."}, 404)
                    return
                global active_job_id
                with jobs_lock:
                    if active_job_id and jobs.get(active_job_id, {}).get("status") in ("queued", "running"):
                        self.send_json({"error": "Загрузка другой модели уже выполняется."}, 409)
                        return
                    job_id = uuid.uuid4().hex[:12]
                    jobs[job_id] = {"job_id": job_id, "kind": "start", "model_key": alias,
                                    "status": "queued", "log": "Ожидает запуска…", "started_utc": utc_now()}
                    active_job_id = job_id
                threading.Thread(target=load_model, args=(job_id, alias), daemon=True).start()
                self.send_json({"job_id": job_id, "status": "queued"})
            except (ValueError, TypeError) as exc:
                self.send_json({"error": str(exc)}, 400)
            return
        if self.path != "/api/chat":
            self.send_json({"error": "Управление моделями доступно через llama-swap и Open WebUI."}, 501)
            return
        try:
            data = self.read_json(32 * 1024 * 1024)
            if data is None:
                return
            alias = str(data.get("model_key") or "")
            available = {str(item.get("id")) for item in gateway_json("/v1/models").get("data", [])}
            if alias not in available:
                self.send_json({"error": "Модель отсутствует в каталоге шлюза."}, 404)
                return
            payload = data.get("payload") or {}
            if not isinstance(payload, dict):
                self.send_json({"error": "payload должен быть JSON-объектом."}, 400)
                return
            payload["model"] = alias
            request = urllib.request.Request(
                GATEWAY + "/v1/chat/completions", data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(request, timeout=1800) as response:
                self.send_bytes(response.read(), "application/json; charset=utf-8")
        except urllib.error.HTTPError as exc:
            self.send_json({"error": exc.read(2048).decode("utf-8", errors="replace")}, 502)
        except (OSError, ValueError, TypeError) as exc:
            self.send_json({"error": str(exc)}, 502)


def gpu_holders() -> list[str]:
    try:
        entries, _, _ = host_ai_inventory([], gpu_sample())
    except (OSError, ValueError):
        return []
    return [e["container"] for e in entries if e["state"] == "running" and (e["gpu"] or e["role"] == "llm")
            and e["role"] != "gateway" and e["container"] != VIDEO_CONTAINER]


def main() -> None:
    global timer_generation, timer_state
    try:
        stored = json.loads(TIMER_FILE.read_text(encoding="utf-8"))
        if stored.get("status") in ("counting", "unloading") and isinstance(stored.get("deadline"), (int, float)):
            timer_state = stored
            timer_generation += 1
            threading.Thread(target=run_unload_timer, args=(timer_generation,), daemon=True).start()
        elif stored.get("status") in ("waiting", "error"):
            timer_state = stored
    except (OSError, ValueError, TypeError):
        pass
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"AI model console listening on 0.0.0.0:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
