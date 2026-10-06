import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "http://127.0.0.1:8080/v1/chat/completions"
CONTAINER = "ai-llama-swap-gateway"
OUTDIR = Path(__file__).resolve().parents[1] / "benchmark" / "gateway-acceptance"
OUTDIR.mkdir(parents=True, exist_ok=True)
run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

first_token = threading.Event()
results = {}
errors = {}
stop_monitor = threading.Event()
samples = []


def post(payload, timeout=1800, stream=False):
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return urllib.request.urlopen(req, timeout=timeout)


def long_stream_request():
    start = time.monotonic()
    payload = {
        "model": "Qwen3.5-9B-MTP-Q4_K_XL",
        "messages": [{"role": "user", "content": "Write 50 numbered, distinct, one-sentence observations about a forest walk. Do not stop before item 50."}],
        "max_tokens": 384,
        "temperature": 0.2,
        "stream": True,
    }
    chunks = 0
    chars = 0
    try:
        with post(payload, stream=True) as response:
            for raw in response:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                text = delta.get("content") or delta.get("reasoning_content") or ""
                if text:
                    chars += len(str(text))
                    chunks += 1
                    first_token.set()
        results["request_a"] = {
            "model": payload["model"], "ok": chars > 0,
            "seconds": round(time.monotonic() - start, 2),
            "stream_chunks": chunks, "response_chars": chars,
        }
    except Exception as exc:
        errors["request_a"] = repr(exc)
        results["request_a"] = {"model": payload["model"], "ok": False,
                                "seconds": round(time.monotonic() - start, 2),
                                "stream_chunks": chunks, "response_chars": chars}
        first_token.set()


def second_request():
    start = time.monotonic()
    payload = {
        "model": "Spark-X2.5-4B-Q8_0",
        "messages": [{"role": "user", "content": "Reply in one short sentence: what is 3 + 4?"}],
        "max_tokens": 48,
        "temperature": 0,
        "stream": False,
    }
    try:
        with post(payload) as response:
            data = json.loads(response.read().decode("utf-8"))
        message = data["choices"][0]["message"]
        text = message.get("content") or message.get("reasoning_content") or ""
        results["request_b"] = {
            "model": payload["model"], "ok": bool(text),
            "seconds": round(time.monotonic() - start, 2),
            "response": text,
        }
    except Exception as exc:
        errors["request_b"] = repr(exc)
        results["request_b"] = {"model": payload["model"], "ok": False,
                                 "seconds": round(time.monotonic() - start, 2)}


def llama_processes():
    proc = subprocess.run(
        ["docker", "exec", CONTAINER, "ps", "-eo", "pid,args"],
        text=True, capture_output=True, timeout=10,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Unable to inspect llama-server processes: {proc.stderr.strip()}")
    return [line.strip() for line in proc.stdout.splitlines() if "llama-server" in line]


thread_a = threading.Thread(target=long_stream_request, name="request-a", daemon=True)
thread_a.start()
if not first_token.wait(240):
    errors["first_token"] = "Request A did not yield a content token within the wait window."
else:
    thread_b = threading.Thread(target=second_request, name="request-b", daemon=True)
    thread_b.start()

threads = [thread_a]
if "thread_b" in locals():
    threads.append(thread_b)

while any(thread.is_alive() for thread in threads):
    current = llama_processes()
    samples.append({"utc": datetime.now(timezone.utc).isoformat(),
                    "llama_server_count": len(current), "commands": current})
    time.sleep(0.15)

for thread in threads:
    thread.join(timeout=1)

max_count = max((sample["llama_server_count"] for sample in samples), default=0)
result = {
    "run_id": run_id,
    "request_a_model": "Qwen3.5-9B-MTP-Q4_K_XL",
    "request_b_model": "Spark-X2.5-4B-Q8_0",
    "request_b_started_after_first_content_token_from_a": "request_b" in results,
    "requests": results,
    "errors": errors,
    "max_concurrent_llama_server_processes": max_count,
    "process_samples": samples,
    "pass": (not errors and all(item.get("ok") for item in results.values())
             and max_count <= 1 and "request_b" in results),
}
out = OUTDIR / f"concurrency-race-{run_id}.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "process_samples"}, ensure_ascii=False, indent=2))
print(f"DETAILS={out}")
if not result["pass"]:
    raise SystemExit(1)
