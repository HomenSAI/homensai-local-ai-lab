"""Test the second configuration through the isolated llama-swap gateway."""
import argparse
import json
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmark" / "q4kv-20260929.jsonl"
MODELS = [
    ("Qwen3.5-9B-MTP-Q4_K_XL", 262144),
    ("Qwen3.5-9B-MTP-Q4_K_XL-Vision", 163840),
    ("Qwen3.5-9B-Q5_K_S", 262144),
    ("MiniCPM5-2B-Q4_K_M", 131072),
    ("Spark-X2.5-4B-Q4_K_M", 524288),
    ("Ternary-Bonsai-2-27B-PTQ1_0", 163840),
    ("Qwen3-VL-8B-Instruct-Q4_K_M", 65536),
]
TASK = ("1. Подтверди, что ты успешно загрузилась и считываешь контекст при данных параметрах квантования; "
        "назови контрольный код из начала запроса. "
        "2. В 2–3 предложениях объясни, как модель Q4/Q5 и KV-кеш Q4/Q5 влияют на VRAM и доступное окно. "
        "3. Напиши короткий тестовый ответ, подтверждающий стабильность генерации.")


def run(model, context, long_input, timeout, words_override=None):
    if long_input:
        # A repeated neutral paragraph gives roughly one token per filler word.
        filler = " blue" * (words_override if words_override is not None else int(context * 0.82))
        content = "Контрольный код: R7K29.\nКонтекст для проверки:" + filler + "\n" + TASK
    else:
        content = "Контрольный код: R7K29.\n" + TASK
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": content}], "max_tokens": 256,
                       "temperature": 0, "stream": False, "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request("http://127.0.0.1:8085/v1/chat/completions", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--long", action="store_true")
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--models", nargs="*")
    ap.add_argument("--words", type=int)
    args = ap.parse_args()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    for model, ctx in MODELS:
        if args.models and model not in args.models:
            continue
        row = {"utc": datetime.now(timezone.utc).isoformat(), "model": model, "context": ctx, "long_input": args.long, "words_override": args.words}
        start = time.monotonic()
        try:
            result = run(model, ctx, args.long, args.timeout, args.words)
            msg = result["choices"][0]["message"]
            answer = (msg.get("content") or msg.get("reasoning_content") or "").strip()
            row.update(status="ok" if answer else "empty", prompt_tokens=result.get("usage", {}).get("prompt_tokens"),
                       completion_tokens=result.get("usage", {}).get("completion_tokens"),
                       finish_reason=result["choices"][0].get("finish_reason"), recall="R7K29" in answer,
                       answer=answer[:1200])
        except Exception as exc:
            row.update(status="error", error=str(exc)[:800])
        row["seconds"] = round(time.monotonic() - start, 2)
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], text=True, capture_output=True)
        row["gpu_mib"] = gpu.stdout.strip()
        with OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"{model}: {row['status']} prompt={row.get('prompt_tokens')} recall={row.get('recall')} seconds={row['seconds']}", flush=True)


if __name__ == "__main__":
    main()
