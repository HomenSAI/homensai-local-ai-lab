#!/usr/bin/env python3
"""Run the canonical benchmark protocol serially against a local llama.cpp API."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "test-data" / "protocol-cases.jsonl"
OUT = ROOT / "benchmark-output" / "protocol"
SUITE_ORDER = ["technical_smoke", "german_practical", "goethe_c1_15min", "goethe_c2_15min",
               "scientific_c2", "math_10min", "goethe_c1_official"]
METRIC_NAMES = ["prompt_tokens_total", "prompt_seconds_total", "tokens_predicted_total",
                "tokens_predicted_seconds_total", "spec_decode_num_draft_tokens_total",
                "spec_decode_num_accepted_tokens_total", "spec_decode_num_drafts_total"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_metrics(base_url: str) -> dict[str, float]:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/metrics", timeout=15) as res:
            text = res.read().decode("utf-8", errors="replace")
    except Exception:
        return {}
    result: dict[str, float] = {}
    for name in METRIC_NAMES:
        match = re.search(r"(?m)^llamacpp:" + re.escape(name) + r"(?:\{[^}]*\})?\s+([-+\d.eE]+)\s*$", text)
        if match:
            try:
                result[name] = float(match.group(1))
            except ValueError:
                pass
    return result


def gpu_sample() -> dict[str, Any]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"error": "nvidia-smi not found on host"}
    try:
        p = subprocess.run([exe, "--query-gpu=utilization.gpu,memory.used,power.draw,temperature.gpu",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=8, check=True)
        fields = [x.strip() for x in p.stdout.strip().split(",")]
        if len(fields) < 4:
            raise ValueError("unexpected nvidia-smi response")
        return {"gpu_util_percent": float(fields[0]), "vram_used_mib": int(float(fields[1])),
                "power_w": float(fields[2]), "temperature_c": int(float(fields[3]))}
    except Exception as exc:
        return {"error": f"nvidia-smi: {exc}"}


def docker_sample(container_id: str) -> dict[str, Any]:
    if not container_id:
        return {"error": "project service container id was not provided"}
    exe = shutil.which("docker.exe") or shutil.which("docker")
    if not exe:
        return {"error": "Docker CLI not found"}
    try:
        p = subprocess.run([exe, "stats", "--no-stream", "--format", "{{json .}}", container_id],
                           capture_output=True, text=True, timeout=10, check=True)
        doc = json.loads(p.stdout.strip().splitlines()[-1])
        cpu = re.search(r"([\d.]+)%", doc.get("CPUPerc", ""))
        mem = re.search(r"([\d.]+)\s*(B|KiB|MiB|GiB|kB|MB|GB)", doc.get("MemUsage", ""), re.I)
        factor = {"b": 1, "kib": 1024, "mib": 1024**2, "gib": 1024**3,
                  "kb": 1000, "mb": 1000**2, "gb": 1000**3}
        return {"docker_cpu_percent": float(cpu.group(1)) if cpu else None,
                "docker_memory_bytes": int(float(mem.group(1)) * factor[mem.group(2).lower()]) if mem else None,
                "docker_raw": doc}
    except Exception as exc:
        return {"error": f"docker stats: {exc}"}


def container_metadata(container_id: str) -> dict[str, Any]:
    exe = shutil.which("docker.exe") or shutil.which("docker")
    if not exe:
        return {"error": "Docker CLI not found", "image_tag": "local/ai-server-upstream:local"}
    try:
        p = subprocess.run([exe, "inspect", container_id], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=20, check=True)
        doc = json.loads(p.stdout)[0]
        model_rel = {"minicpm":"MiniCPM5/MiniCPM5-2B-Q8_0.gguf",
                     "spark":"Spark/Spark-X2.5-4B-Q8_0.gguf"}[ARGS_MODEL_KEY]
        model_path = ROOT.parent / Path(model_rel)
        image_tag = doc.get("Config", {}).get("Image")
        return {"container_id":container_id,"container_name":doc.get("Name","").lstrip("/"),
                "image_tag":image_tag,"image_id":doc.get("Image"),"command":doc.get("Config",{}).get("Cmd"),
                "model_path":str(model_path),"model_size_bytes":model_path.stat().st_size if model_path.is_file() else None,
                "model_sha256":hashlib.file_digest(model_path.open("rb"),"sha256").hexdigest() if model_path.is_file() else None}
    except Exception as exc:
        return {"container_id":container_id,"image_tag":"local/ai-server-upstream:local","error":f"docker inspect: {exc}"}


class Telemetry:
    def __init__(self, run_id: str, path: Path, container_id: str, interval: float = 1.0) -> None:
        self.run_id, self.path, self.container_id, self.interval = run_id, path, container_id, interval
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, name="gpu-telemetry", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=10)

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            row = {"event": "telemetry", "run_id": self.run_id, "sampled_utc": utc_now(),
                   "source": "host-nvidia-smi+docker-stats", **gpu_sample(), **docker_sample(self.container_id)}
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                f.flush()
            self.stop_event.wait(self.interval)


def write_line(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        f.flush()


def api_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(url, data=(json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None),
                                     headers={"Content-Type": "application/json"} if payload else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


ARGS_MODEL_KEY = "minicpm"


def main() -> int:
    global ARGS_MODEL_KEY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-key", choices=("minicpm", "spark"), required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--container-id", required=True)
    parser.add_argument("--context", type=int, default=8192)
    parser.add_argument("--load-seconds", type=float, default=None)
    parser.add_argument("--output-root", type=Path, default=OUT)
    parser.add_argument("--suite", action="append", choices=SUITE_ORDER,
                        help="Run selected suite(s); repeat this flag to select more than one.")
    args = parser.parse_args()
    ARGS_MODEL_KEY = args.model_key

    if not CASES.is_file():
        parser.error(f"canonical test cases missing: {CASES}")
    model_info = {"minicpm": ("MiniCPM5-2B-Q8_0", "MiniCPM5/MiniCPM5-2B-Q8_0.gguf", "minicpm5-2b"),
                  "spark": ("Spark-X2.5-4B-Q8_0", "Spark/Spark-X2.5-4B-Q8_0.gguf", "spark-x2.5-4b")}[args.model_key]
    assets = [json.loads(line) for line in CASES.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    suites = {name: sorted((x for x in assets if x["suite"] == name), key=lambda x: x["sequence"]) for name in SUITE_ORDER}
    if sum(map(len, suites.values())) != len(assets):
        parser.error("protocol case manifest contains an unregistered suite")
    selected_suites = args.suite or SUITE_ORDER
    selected_case_count = sum(len(suites[name]) for name in selected_suites)

    base = args.base_url.rstrip("/")
    models = api_json(base + "/v1/models")
    model_ids = [str(x.get("id", "")) for x in models.get("data", [])]
    if len(model_ids) != 1 or model_info[2] not in model_ids[0].lower():
        parser.error(f"API identity guard failed: expected one {model_info[2]} model, got {model_ids}")
    health = api_json(base + "/health")
    if str(health.get("status", "ok")).lower() not in ("ok", "healthy"):
        parser.error(f"API health check failed: {health}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"protocol-{args.model_key}-{stamp}-{uuid.uuid4().hex[:8]}"
    model_dir = args.output_root / args.model_key
    model_dir.mkdir(parents=True, exist_ok=True)
    output = model_dir / f"{run_id}.jsonl"
    telemetry_file = model_dir / f"{run_id}-telemetry.jsonl"
    start = utc_now()
    threads = int(os.environ.get("LLAMA_THREADS", "4"))
    batch_threads = int(os.environ.get("LLAMA_THREADS_BATCH", "8"))
    container_info = container_metadata(args.container_id)
    versions_text = (ROOT/"VERSIONS.md").read_text(encoding="utf-8-sig") if (ROOT/"VERSIONS.md").exists() else ""
    upstream_match = re.search(r"UPSTREAM_LLAMA_COMMIT\s*=\s*([0-9a-f]{40})", versions_text, re.I)
    environment = {"gpu": "NVIDIA GeForce RTX 3080 10 GB", "device": "cuda", "context": args.context,
                   "threads": threads, "batch_threads": batch_threads, "parallel": 1,
                   "protocol_device_deviation": "GPU CUDA instead of notebook CPU-only; MiniCPM server Q8_0 instead of baseline Q4_K_M" if args.model_key == "minicpm" else "GPU CUDA instead of notebook CPU-only",
                   "api_model_id": model_ids[0], "container_id": args.container_id,
                   "model_path":container_info.get("model_path"),"model_size_bytes":container_info.get("model_size_bytes"),
                   "model_sha256":container_info.get("model_sha256"),"docker_image_tag":container_info.get("image_tag"),
                   "docker_image_id":container_info.get("image_id"),"llama_cpp_commit":upstream_match.group(1) if upstream_match else None,
                   "load_seconds":args.load_seconds,"ram_rss_bytes":"n/a; llama-server process RSS is not exposed by this Windows/WDDM runner"}
    config = {"context": args.context, "threads": threads, "batch_threads": batch_threads, "parallel": 1,
              "temperature": 1.0, "top_p": 0.95, "min_p": 0.0,
              "reasoning_effort": "none", "seed": None, "tools": False, "retrieval": False,
              "stream": False, "model_quant": "Q8_0"}
    write_line(output, {"event": "run", "run_id": run_id, "model_key": args.model_key,
                        "model_name": model_info[0], "gguf": model_info[1], "suite": "protocol_all",
                        "started_utc": start, "status": "running", "config": config, "environment": environment})
    write_line(output, {"event":"preflight","run_id":run_id,"sampled_utc":utc_now(),
                        "health_raw":health,"models_raw":models,"container_inspect":container_info})
    telemetry = Telemetry(run_id, telemetry_file, args.container_id)
    telemetry.start()
    all_errors = 0
    all_started = time.monotonic()
    suite_summary: dict[str, Any] = {}
    try:
        for suite_name in selected_suites:
            cases = suites[suite_name]
            if not cases:
                continue
            deadline = cases[0].get("suite_seconds")
            suite_start = time.monotonic()
            attempted = completed = after_deadline = errors = 0
            seen: set[str] = set()
            not_started: list[str] = []
            for case in cases:
                if deadline and time.monotonic() - suite_start >= deadline:
                    not_started.extend(c["case_id"] for c in cases if c["case_id"] not in seen)
                    break
                case_started = utc_now()
                case_mono = time.monotonic()
                metrics_before = parse_metrics(base)
                request_body = {"model": model_ids[0], "messages": case["messages"],
                                "max_tokens": case["max_tokens"], "temperature": 1.0,
                                "top_p": 0.95, "min_p": 0.0, "reasoning_effort": "none",
                                "stream": False}
                raw: dict[str, Any] = {}
                answer = ""
                error = None
                try:
                    raw = api_json(base + "/v1/chat/completions", request_body, timeout=1800)
                    choices = raw.get("choices") or []
                    if choices:
                        message = choices[0].get("message") or {}
                        answer = str(message.get("content") or message.get("reasoning_content") or "")
                    else:
                        error = "API returned no choices"
                except Exception as exc:
                    error = str(exc)
                duration = time.monotonic() - case_mono
                metrics_after = parse_metrics(base)
                delta = {key: max(0.0, metrics_after.get(key, 0.0) - metrics_before.get(key, 0.0))
                         for key in METRIC_NAMES if key in metrics_before and key in metrics_after}
                usage = raw.get("usage") or {}
                finished = utc_now()
                out_of_time = bool(deadline and time.monotonic() - suite_start > deadline)
                attempted += 1
                completed += int(not error)
                errors += int(bool(error))
                all_errors += int(bool(error))
                after_deadline += int(out_of_time)
                seen.add(case["case_id"])
                response_id = f"{run_id}-{case['case_id']}"
                row = {"event": "response", "response_id": response_id, "run_id": run_id,
                       "suite": suite_name, "case_id": case["case_id"], "sequence": case["sequence"],
                       "cycle": 1, "started_utc": case_started, "finished_utc": finished,
                       "duration_seconds": round(duration, 4), "prompt": case["prompt"],
                       "request": request_body, "answer": answer,
                       "finish_reason": ((raw.get("choices") or [{}])[0].get("finish_reason")),
                       "prompt_tokens": usage.get("prompt_tokens", delta.get("prompt_tokens_total")),
                       "completion_tokens": usage.get("completion_tokens", delta.get("tokens_predicted_total")),
                       "timings": {"api_usage": usage, "metrics_delta": delta,
                                   "ttft_seconds": None, "note": "Protocol is non-streaming; TTFT is measured by the separate performance benchmark."},
                       "error": error, "after_deadline": out_of_time,
                       "raw": raw if raw else {"error": error}}
                write_line(output, row)
                print(f"{suite_name} {attempted}/{len(cases)} {case['case_id']} {duration:.1f}s" +
                      (f" ERROR {error}" if error else "") + (" AFTER_DEADLINE" if out_of_time else ""), flush=True)
            suite_row = {"suite": suite_name, "deadline_seconds": deadline,
                         "active_seconds": round(time.monotonic() - suite_start, 3),
                         "attempted": attempted, "completed": completed, "api_errors": errors,
                         "after_deadline": after_deadline, "not_started_case_ids": not_started,
                         "unique_cases_attempted": len(seen)}
            suite_summary[suite_name] = suite_row
            write_line(output, {"event": "suite_finished", "run_id": run_id, **suite_row})
        total = round(time.monotonic() - all_started, 3)
        finished = utc_now()
        status = "complete" if all_errors == 0 else "complete_with_errors"
        summary = {"total_wall_seconds": total, "api_errors": all_errors, "suites": suite_summary,
                   "protocol_case_count": selected_case_count, "protocol_total_case_count": len(assets),
                   "selected_suites": selected_suites,
                   "note": "GPU protocol adaptation; notebook reference is CPU-only. Selected suites were isolated to bound WSL RAM."}
        write_line(output, {"event": "run_finished", "run_id": run_id, "finished_utc": finished,
                            "status": status, "summary": summary})
        print(json.dumps({"run_id": run_id, "output": str(output), "telemetry": str(telemetry_file),
                          "status": status, "summary": summary}, ensure_ascii=False, indent=2))
        return 0 if all_errors == 0 else 2
    finally:
        telemetry.stop()


if __name__ == "__main__":
    raise SystemExit(main())
