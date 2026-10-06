import base64
import binascii
import hashlib
import json
import struct
import subprocess
import threading
import time
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmark" / "gateway-acceptance"
OUT.mkdir(parents=True, exist_ok=True)
IMAGE = OUT / "vision-fixture-red-circle-blue-square.png"
API = "http://127.0.0.1:8080/v1/chat/completions"
CONTAINER = "ai-llama-swap-gateway"
PROFILES = [
    ("Qwen3.5-9B-MTP-Q4_K_XL-Vision", "/models/Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf"),
    ("Qwen3-VL-8B-Instruct-Q4_K_M", "/models/Qwen-Image-2.1/text_encoder/Qwen3VL-8B-Instruct-Q4_K_M.gguf"),
]


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)


def make_fixture() -> None:
    width, height = 256, 128
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # PNG filter: None
        for x in range(width):
            color = (255, 255, 255)
            if (x - 78) ** 2 + (y - 64) ** 2 <= 30**2:
                color = (230, 25, 45)  # red circle
            if 151 <= x <= 211 and 34 <= y <= 94:
                color = (25, 75, 225)  # blue square
            raw.extend(color)
    data = bytearray(b"\x89PNG\r\n\x1a\n")
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(bytes(raw), level=6))
    data += chunk(b"IEND", b"")
    IMAGE.write_bytes(data)


def gpu_sample() -> dict:
    proc = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu,power.draw", "--format=csv,noheader,nounits"],
        text=True, capture_output=True, timeout=10, check=True,
    )
    fields = [part.strip() for part in proc.stdout.splitlines()[0].split(",")]
    return {"memory_used_mib": int(float(fields[0])), "memory_total_mib": int(float(fields[1])),
            "gpu_util_pct": int(float(fields[2])), "power_w": float(fields[3])}


def server_processes() -> list[str]:
    proc = subprocess.run(["docker", "exec", CONTAINER, "ps", "-eo", "pid,args"],
                          text=True, capture_output=True, timeout=10)
    if proc.returncode:
        raise RuntimeError(f"Cannot inspect gateway process list: {proc.stderr.strip()}")
    return [line.strip() for line in proc.stdout.splitlines() if "llama-server" in line]


def main() -> int:
    if not IMAGE.exists():
        make_fixture()
    digest = hashlib.sha256(IMAGE.read_bytes()).hexdigest()
    data_url = "data:image/png;base64," + base64.b64encode(IMAGE.read_bytes()).decode("ascii")
    results = []
    for model, expected_path in PROFILES:
        samples = []
        stop = threading.Event()

        def monitor() -> None:
            while not stop.is_set():
                try:
                    samples.append(gpu_sample())
                except Exception:
                    pass
                stop.wait(0.5)

        watcher = threading.Thread(target=monitor, daemon=True)
        watcher.start()
        started = time.monotonic()
        row = {"model": model, "expected_model_path": expected_path, "status": "FAIL"}
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": "Count the colored shapes. Name each color and shape in one short sentence."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]}],
                "max_tokens": 64,
                "temperature": 0,
                "stream": False,
            }
            req = urllib.request.Request(API, data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=1800) as response:
                body = json.loads(response.read().decode("utf-8"))
            message = body["choices"][0]["message"]
            text = message.get("content") or message.get("reasoning_content") or ""
            processes = server_processes()
            path_seen = any(expected_path in line for line in processes)
            low = str(text).lower()
            visual_sanity = all(term in low for term in ("red", "blue")) and any(term in low for term in ("circle", "round")) and any(term in low for term in ("square", "rectangle"))
            row.update({
                "status": "PASS" if text and path_seen and len(processes) == 1 and visual_sanity else "FAIL",
                "http_status": 200, "seconds": round(time.monotonic() - started, 2),
                "prompt_tokens": body.get("usage", {}).get("prompt_tokens"),
                "output_tokens": body.get("usage", {}).get("completion_tokens"),
                "response": text, "visual_sanity_check": visual_sanity,
                "process_count": len(processes), "processes": processes,
            })
        except Exception as exc:
            row.update({"seconds": round(time.monotonic() - started, 2), "error": repr(exc)})
        finally:
            stop.set()
            watcher.join(timeout=2)
        row["gpu_peak"] = {
            "memory_used_mib": max((s["memory_used_mib"] for s in samples), default=None),
            "gpu_util_pct": max((s["gpu_util_pct"] for s in samples), default=None),
            "power_w": max((s["power_w"] for s in samples), default=None),
        }
        row["gpu_samples"] = samples
        row["image_sha256"] = digest
        results.append(row)
        print(f"MODEL={model} STATUS={row['status']} SECONDS={row['seconds']} VISUAL={row.get('visual_sanity_check')}")

    report = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "fixture": str(IMAGE), "fixture_sha256": digest,
        "prompt": "Count the colored shapes. Name each color and shape in one short sentence.",
        "results": results,
        "pass": all(row["status"] == "PASS" for row in results),
    }
    target = OUT / f"vision-image-test-{report['run_id']}.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"RESULT={target}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
