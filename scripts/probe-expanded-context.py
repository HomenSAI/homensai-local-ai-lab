"""Try larger llama-swap contexts, preserving the original config on failure."""
import json
import re
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "llama-swap.yaml"
BACKUP = ROOT / "config" / "llama-swap.before-context-probe.yaml"
RESULTS = ROOT / "benchmark" / "expanded-context-20260929.jsonl"
TARGETS = [
    ("Qwen3-VL-8B-Instruct-Q4_K_M", 16384),
    ("MiniCPM5-2B-Q8_0", 131072),
    ("Spark-X2.5-4B-Q8_0", 98304),
    ("Qwen3.5-9B-Q5_K_S", 98304),
    ("Qwen3.5-9B-MTP-Q4_K_XL-Vision", 49152),
    ("Ternary-Bonsai-2-27B-PTQ1_0", 49152),
    ("Qwen3.5-9B-MTP-Q4_K_XL", 81920),
]


def set_context(source, model, context):
    pattern = rf"(?ms)^  {re.escape(model)}:\n(.*?)(?=^  [A-Za-z0-9][^\n]*:\n|^routing:)"
    match = re.search(pattern, source)
    if not match:
        raise RuntimeError(f"Missing config section: {model}")
    section = match.group(0)
    section = re.sub(r"--ctx-size \d+", f"--ctx-size {context}", section, count=1)
    section = re.sub(r"(?m)^      context: \d+$", f"      context: {context}", section, count=1)
    return source[:match.start()] + section + source[match.end():]


def restart():
    cmd = subprocess.run(["docker", "restart", "--timeout", "100", "ai-llama-swap-gateway"], capture_output=True, text=True, timeout=150)
    if cmd.returncode:
        raise RuntimeError(cmd.stderr[-800:])
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=5):
                return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Gateway health timeout")


def post(model, words, timeout):
    content = "Remember code K7M42. " + " blue" * words + "\nWhat code was at the start? Reply with the code only."
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": content}], "max_tokens": 96, "temperature": 0, "stream": False, "chat_template_kwargs": {"enable_thinking": False}}).encode()
    request = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def main():
    original = CONFIG.read_text(encoding="utf-8")
    BACKUP.write_text(original, encoding="utf-8")
    accepted = original
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    try:
        for model, context in TARGETS:
            row = {"utc": datetime.now(timezone.utc).isoformat(), "model": model, "target_context": context}
            start = time.monotonic()
            trial = set_context(accepted, model, context)
            CONFIG.write_text(trial, encoding="utf-8")
            try:
                restart()
                response = post(model, int(context * 0.88), 600)
                answer = response["choices"][0]["message"]
                out = (answer.get("content") or answer.get("reasoning_content") or "").strip()
                tokens = response.get("usage", {}).get("prompt_tokens", 0)
                if tokens < context * 0.8:
                    raise RuntimeError(f"Only {tokens} input tokens were counted")
                row.update(status="stable", prompt_tokens=tokens, completion_tokens=response.get("usage", {}).get("completion_tokens"), answer=out[:300], recall=("K7M42" in out))
                accepted = trial
            except Exception as exc:
                row.update(status="failed", error=str(exc)[:800])
                CONFIG.write_text(accepted, encoding="utf-8")
                restart()
            row["seconds"] = round(time.monotonic() - start, 2)
            gpu = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True)
            row["gpu_mib"] = gpu.stdout.strip()
            with RESULTS.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(json.dumps(row, ensure_ascii=False), flush=True)
    finally:
        CONFIG.write_text(accepted, encoding="utf-8")
        restart()


if __name__ == "__main__":
    main()
