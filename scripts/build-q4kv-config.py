"""Build an isolated llama-swap config for the Q4 weight / Q4 KV experiment."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config" / "llama-swap.yaml"
TARGET = ROOT / "config" / "llama-swap-q4kv.yaml"

CONTEXTS = {
    "Qwen3.5-9B-MTP-Q4_K_XL": 131072,
    "Qwen3.5-9B-MTP-Q4_K_XL-Vision": 98304,
    "Qwen3.5-9B-Q5_K_S": 131072,
    "MiniCPM5-2B-Q8_0": 131072,
    "Spark-X2.5-4B-Q8_0": 262144,
    "Ternary-Bonsai-2-27B-PTQ1_0": 65536,
    "Qwen3-VL-8B-Instruct-Q4_K_M": 32768,
}

text = SOURCE.read_text(encoding="utf-8")
text = text.replace("/models/MiniCPM5/MiniCPM5-2B-Q8_0.gguf", "/models/MiniCPM5/MiniCPM5-2B-Q4_K_M-requant.gguf")
text = text.replace("/models/Spark/Spark-X2.5-4B-Q8_0.gguf", "/models/Spark/Spark-X2.5-4B-Q4_K_M-requant.gguf")
text = text.replace("--cache-type-k f16 --cache-type-v f16", "--cache-type-k q4_0 --cache-type-v q4_0")
for model, context in CONTEXTS.items():
    pattern = rf"(?ms)^  {re.escape(model)}:\n(.*?)(?=^  [A-Za-z0-9][^\n]*:\n|^routing:)"
    match = re.search(pattern, text)
    if not match:
        raise RuntimeError(model)
    section = match.group(0)
    section = re.sub(r"--ctx-size \d+", f"--ctx-size {context}", section, count=1)
    section = re.sub(r"(?m)^      context: \d+$", f"      context: {context}", section, count=1)
    if "--cache-type-k q4_0" not in section:
        section = section.replace("--parallel 1 --batch-size 512 --ubatch-size 128", "--parallel 1 --batch-size 512 --ubatch-size 128\n      --cache-type-k q4_0 --cache-type-v q4_0")
    if model == "Qwen3.5-9B-MTP-Q4_K_XL":
        section = section.replace(" --spec-type draft-mtp --spec-draft-n-max 2", "")
    text = text[:match.start()] + section + text[match.end():]

text = text.replace("MiniCPM5-2B-Q8_0", "MiniCPM5-2B-Q4_K_M-requant")
text = text.replace("Spark-X2.5-4B-Q8_0", "Spark-X2.5-4B-Q4_K_M-requant")
text = text.replace("MiniCPM5 2B Q8_0", "MiniCPM5 2B Q4_K_M from Q8")
text = text.replace("Spark X2.5 4B Q8_0", "Spark X2.5 4B Q4_K_M from Q8")

TARGET.write_text("# Experimental variant: Q4/Q5 weights where available, Q4_0 KV cache.\n# MiniCPM and Spark weights were requantized from Q8; Bonsai remains PTQ1_0.\n" + text, encoding="utf-8")
print(TARGET)
