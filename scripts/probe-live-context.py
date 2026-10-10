"""Exercise real input prompts near each gateway profile's configured context."""
import argparse
import json
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MODELS = {
    "Qwen3.5-9B-MTP-Q4_K_XL": 65536,
    "Qwen3.5-9B-MTP-Q4_K_XL-Vision": 32768,
    "Qwen3.5-9B-Q5_K_S": 65536,
    "MiniCPM5-2B-Q8_0": 65536,
    "Spark-X2.5-4B-Q8_0": 65536,
    "Ternary-Bonsai-2-27B-PTQ1_0": 32768,
    "Qwen3-VL-8B-Instruct-Q4_K_M": 8192,
}
OUT = Path(__file__).resolve().parents[1] / "benchmark" / "context-20260929.jsonl"


def post(model, words, timeout):
    marker = "K7M42"
    content = f"Remember code {marker}. " + (" blue" * words) + "\nWhat code was at the start? Reply with the code only."
    payload = json.dumps({"model": model, "messages": [{"role": "user", "content": content}], "max_tokens": 96, "temperature": 0, "stream": False, "chat_template_kwargs": {"enable_thinking": False}}).encode()
    request = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", payload, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="*", default=list(MODELS))
    parser.add_argument("--fraction", type=float, default=0.88)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    for model in args.models:
        ctx = MODELS[model]
        words = int(ctx * args.fraction)
        start = time.monotonic()
        row = {"utc": datetime.now(timezone.utc).isoformat(), "model": model, "configured_context": ctx, "repeated_words": words}
        try:
            response = post(model, words, args.timeout)
            answer = response["choices"][0]["message"]
            text = (answer.get("content") or answer.get("reasoning_content") or "").strip()
            row.update(status="pass" if "K7M42" in text else "wrong_answer", prompt_tokens=response.get("usage", {}).get("prompt_tokens"), completion_tokens=response.get("usage", {}).get("completion_tokens"), finish_reason=response["choices"][0].get("finish_reason"), answer=text[:400])
        except Exception as exc:
            row.update(status="error", error=str(exc)[:800])
        row["seconds"] = round(time.monotonic() - start, 2)
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True)
        row["gpu_mib"] = gpu.stdout.strip()
        with OUT.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps(row, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
