#!/usr/bin/env python3
# Local AI Lab - (c) 2026 Serhii Khomenko - https://homensai.com/
"""Creates the model files of the virtual RTX 3080 test machine: every .gguf named in config/llama-swap.yaml and in
benchmarks/bench_top.py (TOP), as sparse files with a GGUF header and a plausible size, so they take almost no disk.
The virtual llama.cpp derives video memory and speed from the size.

  docker run --rm -v llm-models-fast:/models -v "$PWD":/lab:ro python:3.12-slim \
      python /lab/tests/virtual-3080/make_models.py /lab /models
"""
import os, re, sys

lab, target = sys.argv[1], sys.argv[2]
names = set(re.findall(r"/models/(\S+?\.gguf)", open(os.path.join(lab, "config/llama-swap.yaml"), encoding="utf-8").read()))
top = open(os.path.join(lab, "benchmarks/bench_top.py"), encoding="utf-8").read().split("TOP = [", 1)[1].split("\n]", 1)[0]
names |= set(re.findall(r'"([^"]+?\.gguf)"', top))
BITS = [("PTQ1", 1.7), ("Q8", 8.5), ("Q6", 6.6), ("Q5", 5.6), ("Q4", 4.8), ("F16", 16), ("BF16", 16), ("Q3", 3.9), ("Q2", 3.0)]


def size_of(name):
    base = os.path.basename(name)
    if "mmproj" in base.lower():
        return int(0.85e9)
    if "mtp" in base.lower() and "head" in base.lower():
        return int(0.45e9)                     # MTP head of a model, not a whole model
    b = re.search(r"(\d+(?:\.\d+)?)B", base, re.I) or re.search(r"(\d+(?:\.\d+)?)B", name, re.I)   # file name, then folder
    params = float(b.group(1)) if b else 4.0
    bits = next((v for k, v in BITS if k.lower() in base.lower()), 5.0)
    return int(params * 1e9 * bits / 8)


for name in sorted(names):
    path = os.path.join(target, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(b"GGUF\x03\x00\x00\x00virtual-3080")
            f.truncate(size_of(name))
    print(f"{os.path.getsize(path) / 1e9:6.2f} GB  {name}")
print(f"{len(names)} virtual model files in {target}")
