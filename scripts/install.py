#!/usr/bin/env python3
"""Installer / doctor for the Local AI Server (Windows, Linux, macOS with Docker + NVIDIA GPU).

  python scripts/install.py doctor      # check the machine: Docker, GPU in Docker, ports, free disk
  python scripts/install.py init        # create .env, folders, placeholder files, Docker network and model volume
  python scripts/install.py build       # build the base images and the gateway (one at a time, low RAM use)
  python scripts/install.py up          # start console, report builder, report redirect, Git; start the gateway
  python scripts/install.py verify      # HTTP checks of every part (run after `up`)
  python scripts/install.py all         # doctor + init + build + up + verify

Nothing here needs third-party Python packages. Every step is idempotent: run it again after fixing a problem.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE, ENV_EXAMPLE = ROOT / ".env", ROOT / ".env.example"
PORTS = {"console/report": 8766, "gateway API": 8080, "report redirect": 8765, "Gitea web": 3010, "Gitea ssh": 2222}


def run(cmd, check=True, capture=False, timeout=None, **kw):
    done = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace",
                          capture_output=capture, timeout=timeout, **kw)
    if check and done.returncode:
        raise SystemExit(f"command failed ({done.returncode}): {' '.join(map(str, cmd))}\n{(done.stderr or '')[-800:]}")
    return done


def say(mark, text):
    print(f"[{mark}] {text}", flush=True)


def read_env():
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                values[key.strip()] = re.split(r"\s+#", value.strip(), maxsplit=1)[0].strip()
    return values


def port_free(port):
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def doctor():
    ok = True
    if not shutil.which("docker"):
        say("FAIL", "docker is not on PATH (install Docker Desktop with WSL2, or Docker Engine + NVIDIA Container Toolkit)")
        return False
    info = run(["docker", "info", "--format", "{{.ServerVersion}}"], check=False, capture=True)
    if info.returncode:
        say("FAIL", "the Docker daemon does not answer (start Docker Desktop; if it is paused, resume it)")
        return False
    say("ok", f"Docker server {info.stdout.strip()}")
    compose = run(["docker", "compose", "version", "--short"], check=False, capture=True)
    say("ok" if compose.returncode == 0 else "FAIL", f"docker compose {compose.stdout.strip()}")
    ok &= compose.returncode == 0
    gpu = run(["docker", "run", "--rm", "--gpus", "all", "nvidia/cuda:12.8.1-runtime-ubuntu24.04", "nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
              check=False, capture=True, timeout=600)
    if gpu.returncode:
        say("FAIL", "GPU is not visible inside Docker: " + (gpu.stderr or "").strip()[-200:])
        ok = False
    else:
        say("ok", "GPU in Docker: " + gpu.stdout.strip().splitlines()[-1])
    free_gb = shutil.disk_usage(ROOT).free / 1e9
    say("ok" if free_gb > 60 else "warn", f"free disk next to the project: {free_gb:.0f} GB (images ~25 GB, models 50-200 GB)")
    for name, port in PORTS.items():
        say("ok" if port_free(port) else "warn", f"port {port} ({name}) {'is free' if port_free(port) else 'is busy: change it in .env or stop the other program'}")
    return ok


def init():
    if not ENV_FILE.exists():
        if not ENV_EXAMPLE.exists():
            raise SystemExit(".env.example is missing")
        shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
        say("ok", "created .env from .env.example - open it and set MODEL_DIR (folder with your .gguf models) and AI_CONSOLE_BIND_IP")
    else:
        say("ok", ".env exists")
    env = read_env()
    model_dir = env.get("MODEL_DIR", "")
    if not model_dir or model_dir.startswith("/path/to") or model_dir.startswith("C:/path"):
        say("warn", "MODEL_DIR in .env is still a placeholder; Docker cannot start model containers until it points to a real folder")
    elif not Path(model_dir).is_dir():
        say("warn", f"MODEL_DIR={model_dir} does not exist yet; create it or fix the path")
    for folder in ["bench_results", "report", "results-db", "media/images", "benchmark/q4kv-20260929", "secrets", "config"]:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    stubs = {
        "benchmark/q4kv-20260929/recommended-settings-q4kv-20260929.json": '{"model_profiles":{}}\n',
        "report/report-data.json": '{"runs":[],"scores":[],"responses":[],"generated_at":null}\n',
        "BENCHMARK_RESULTS.csv": "",
        "BENCHMARK_RESULTS.db": "",
        "media/images/qwen-image-2.1-smoke.png": "",
        "secrets/gitea-token": "",
    }
    for relative, content in stubs.items():
        path = ROOT / relative
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            say("ok", f"created placeholder {relative}")
    if run(["docker", "network", "inspect", "ai-net"], check=False, capture=True).returncode:
        run(["docker", "network", "create", "ai-net"], capture=True)
        say("ok", "created Docker network ai-net")
    if run(["docker", "volume", "inspect", "llm-models-fast"], check=False, capture=True).returncode:
        run(["docker", "volume", "create", "llm-models-fast"], capture=True)
        say("ok", "created Docker volume llm-models-fast (copy your .gguf files into it: see docs/INSTALL)")
    cfg = run(["docker", "compose", "--profile", "gateway", "--profile", "build", "config", "-q"], check=False, capture=True)
    say("ok" if cfg.returncode == 0 else "FAIL", "docker compose configuration is valid" if cfg.returncode == 0 else "compose config error: " + (cfg.stderr or "")[-400:])
    return cfg.returncode == 0


def build():
    steps = [("llama.cpp (CUDA) base image", ["--profile", "build", "build", "build-upstream"]),
             ("Bonsai llama.cpp fork image", ["--profile", "build", "build", "build-bonsai"]),
             ("llama-swap gateway image", ["--profile", "gateway", "build", "llama-swap-gateway"]),
             ("console, report builder, versioner", ["build", "ai-console", "report-versioner"])]
    for title, args in steps:
        say("..", f"building: {title} (the CUDA builds take 15-40 minutes the first time)")
        run(["docker", "compose", *args])
        say("ok", f"built: {title}")
    return True


def up():
    run(["docker", "compose", "up", "-d", "ai-console", "report-builder", "stats-report", "gitea", "report-versioner"])
    run(["docker", "compose", "--profile", "gateway", "up", "-d", "llama-swap-gateway"])
    say("ok", "services started; the gateway needs ~30 s to become healthy")
    return True


def http(url, timeout=8):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, response.read(4096).decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - report any failure as text
        return None, str(exc)


def verify():
    checks = [("console health", "http://127.0.0.1:8766/health", 200), ("console status API", "http://127.0.0.1:8766/api/status", 200),
              ("model catalog", "http://127.0.0.1:8766/api/models", 200), ("report page", "http://127.0.0.1:8766/report/", 200),
              ("video page", "http://127.0.0.1:8766/video", 200), ("license files", "http://127.0.0.1:8766/legal/README.md", 200), ("version", "http://127.0.0.1:8766/api/version", 200),
              ("gateway models", "http://127.0.0.1:8080/v1/models", 200), ("Gitea", "http://127.0.0.1:3010/api/healthz", 200)]
    good = True
    for title, url, code in checks:
        status, body = http(url)
        passed = status == code
        good &= passed
        say("ok" if passed else "FAIL", f"{title}: {url} -> {status if status else body[:80]}")
    ps = run(["docker", "ps", "--format", "{{.Names}} {{.Status}}"], check=False, capture=True).stdout
    for line in ps.splitlines():
        if re.match(r"(ai-|hermes|video)", line):
            say("ok" if "unhealthy" not in line else "FAIL", line)
    return good


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    steps = {"doctor": doctor, "init": init, "build": build, "up": up, "verify": verify}
    if command == "all":
        for name in ("doctor", "init", "build", "up"):
            if not steps[name]():
                raise SystemExit(f"stopped at step '{name}'")
        time.sleep(40)
        raise SystemExit(0 if verify() else 1)
    if command not in steps:
        raise SystemExit(__doc__)
    raise SystemExit(0 if steps[command]() else 1)


if __name__ == "__main__":
    main()
