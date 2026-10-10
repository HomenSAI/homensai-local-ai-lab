"""Protocol A smoke attempt for Bonsai on the pinned upstream llama.cpp binary."""
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = Path(r"<ROOT>\Ternary-Bonsai-2-27B-PTQ1_0.gguf")
OUT = ROOT / "benchmark" / "q4kv-20260929" / "bonsai-upstream-protocol-A.json"
model_sha = hashlib.sha256(MODEL.read_bytes()).hexdigest()
payload = {
    "model": "Ternary-Bonsai-2-27B-PTQ1_0",
    "messages": [{"role": "user", "content": (
        "Контрольный код: R7K29. Подтверди загрузку и назови код. "
        "В 2–3 предложениях объясни влияние Q4/Q5 весов и KV на VRAM и контекст. "
        "Заверши коротким тестовым ответом о стабильности генерации."
    )}],
    "max_tokens": 192, "temperature": 0, "stream": False,
}
row = {
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "suite": "A: technical smoke; user-requested Q4 KV / context 8192",
    "runtime": "pinned upstream llama.cpp /app/llama-server in llama-swap",
    "configured_context": 8192, "cache_type_k": "q4_0", "cache_type_v": "q4_0",
    "model_path": str(MODEL), "model_size_bytes": MODEL.stat().st_size, "model_sha256": model_sha,
    "exact_request": payload, "status": "pending",
}
started = time.monotonic()
try:
    request = urllib.request.Request("http://127.0.0.1:8085/v1/chat/completions", json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        row["http_status"] = response.status
        row["response"] = json.load(response)
    answer = row["response"]["choices"][0]["message"].get("content", "")
    row["status"] = "pass" if "R7K29" in answer else "wrong_answer"
except Exception as exc:
    row["status"] = "failed_to_load_or_respond"
    row["error"] = repr(exc)
finally:
    row["seconds"] = round(time.monotonic() - started, 3)
    logs = subprocess.run(["docker", "logs", "ai-q4kv-test"], text=True, capture_output=True, timeout=30)
    row["gateway_logs_tail"] = (logs.stdout + logs.stderr)[-20000:]
    row["finished_utc"] = datetime.now(timezone.utc).isoformat()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Bonsai upstream protocol A: {row['status']} after {row['seconds']} s; evidence: {OUT}")
