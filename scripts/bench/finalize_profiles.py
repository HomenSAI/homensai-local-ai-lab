"""config/llama-swap-ctx.yaml (from gen_profiles_from_ctx.py) -> config/llama-swap-final.yaml
Rules (user, 2026-10-02): only models with a stable GPU context >= 64K; accelerators only where benchmarked faster (>=1.10x); no CPU/RAM auto-fit."""
import re, yaml, os
HERE = os.path.dirname(os.path.abspath(__file__)); CFG = os.path.join(HERE, "..", "config")
c = yaml.safe_load(open(os.path.join(CFG, "llama-swap-ctx.yaml"), encoding="utf-8"))
M = c["models"]
DROP = ["Gemma-4-12B-it", "Gemma-4-12B-it-QAT", "Gemma-4-E4B-it", "LFM2.5-8B-A1B", "LFM2.5-2.6B", "Qwen3-8B-Draft", "R1-Distill-Llama-8B-Draft", "Mistral-Nemo-12B",
        "Qwen3.5-9B-Q5_K_S-Draft", "MiMo-V2.6-Distill-Qwen-9B-Draft"]       # excluded by 64K rule / duplicate of a plain profile
for n in DROP: M.pop(n, None)


def plain(old, new):
    m = M.pop(old); cmd = " ".join(m["cmd"].split())
    cmd = cmd.replace("--fit on -fitt 1024", "--n-gpu-layers all --fit off")
    cmd = re.sub(r" --spec-type \S+", "", cmd); cmd = re.sub(r" --spec-draft-model \S+", "", cmd)
    cmd = re.sub(r" -ngld \S+", "", cmd); cmd = re.sub(r" --spec-draft-n-max \d+", "", cmd)
    cmd = cmd.replace("--alias " + old, "--alias " + new)
    m["cmd"] = cmd; m["name"] = new; M[new] = m


for old, new in [("Qwen2.5-Coder-7B-Draft", "Qwen2.5-Coder-7B"), ("Llama-3.1-8B-Draft", "Llama-3.1-8B"), ("Gemma-3-12B-Draft", "Gemma-3-12B")]: plain(old, new)
# MiMo: MTP was slower (x0.71) -> plain weights
m = M.pop("MiMo-V2.6-Distill-Qwen-9B-MTP")
cmd = " ".join(m["cmd"].split()).replace("MiMo-V2.6-Distill-Qwen-9B-MTP/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M-MTP.gguf", "MiMo-V2.6-Distill-Qwen-9B/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf")
cmd = re.sub(r" --spec-type \S+", "", cmd); cmd = re.sub(r" --spec-draft-n-max \d+", "", cmd).replace("--alias MiMo-V2.6-Distill-Qwen-9B-MTP", "--alias MiMo-V2.6-Distill-Qwen-9B")
m["cmd"] = cmd; m["name"] = "MiMo-V2.6-Distill-Qwen-9B"; M["MiMo-V2.6-Distill-Qwen-9B"] = m
# vision models: >= 64K (text probes passed at 64K with q4 / q8; the projector needs ~1 GB -> validate in the soak)
for n, kv in [("Qwen3-VL-8B-Instruct-Q4_K_M", "q4_0"), ("Qwen2.5-VL-7B", "q8_0")]:
    cmd = " ".join(M[n]["cmd"].split()); cmd = re.sub(r"--ctx-size \d+", "--ctx-size 65536", cmd)
    cmd = re.sub(r"-ctk \S+ -ctv \S+", f"-ctk {kv} -ctv {kv}", cmd).replace("--fit on -fitt 512", "--n-gpu-layers all --fit off")
    M[n]["cmd"] = cmd
# 262K at 95% fill spilled out of VRAM in the soak (MTP/DFlash heads need extra VRAM) -> 192K
for n in ("Qwen3.5-9B-MTP-Q4_K_XL",):
    M[n]["cmd"] = re.sub(r"--ctx-size \d+", "--ctx-size 196608", " ".join(M[n]["cmd"].split()))
# soak 2026-10-06: Ornith MTP/DFlash spill at 196K -> 128K; Gemma-3-12B hung at 98K -> 64K; Qwen2.5-VL-7B loses facts at 64K -> dropped (duplicate of Qwen3-VL / Qwen3.5-Vision)
for n in ("Ornith-1.5-9B-MTP", "Ornith-1.5-9B-DFlash"): M[n]["cmd"] = re.sub(r"--ctx-size \d+", "--ctx-size 131072", " ".join(M[n]["cmd"].split()))
M["Gemma-3-12B"]["cmd"] = re.sub(r"--ctx-size \d+", "--ctx-size 65536", " ".join(M["Gemma-3-12B"]["cmd"].split()))
M.pop("Qwen2.5-VL-7B", None)
M.pop("Ornith-1.5-9B-DFlash", None)      # soak: spills at 131K (draft model costs VRAM), speed gain equals MTP -> duplicate
# best results: thinking mode lowered or did not raise scores for every hybrid model (truncated answers, loops) -> default OFF (a request can still turn it on)
for n in ("Qwen3.5-9B-MTP-Q4_K_XL", "Qwen3.5-9B-MTP-Q4_K_XL-Vision", "Qwen3.5-9B-Q5_K_S", "MiniCPM5-2B-Q8_0", "Spark-X2.5-4B-Q8_0", "Ternary-Bonsai-2-27B-PTQ1_0", "Ornith-1.5-9B-MTP", "MiMo-V2.6-Distill-Qwen-9B"):
    if "--chat-template-kwargs" not in M[n]["cmd"]: M[n]["cmd"] = " ".join(M[n]["cmd"].split()) + " --chat-template-kwargs '{\"enable_thinking\":false}'"
# descriptions / capabilities from the real command line
SPEED = {"MTP": "accelerator MTP (x1.3-1.6 measured)", "DFlash": "accelerator DFlash (x1.34 measured)"}
for n, m in M.items():
    cmd = m["cmd"]; mc = re.search(r"--ctx-size (\d+)", cmd); kv = re.search(r"-ctk (\S+)", cmd)
    if mc and "Embedding" not in n:
        ctx = int(mc.group(1)); m.setdefault("capabilities", {})["context"] = ctx
        acc = "; accelerator: " + (SPEED["DFlash"] if "DFlash" in n else SPEED["MTP"]) if "MTP" in n or "DFlash" in n else ""
        m["description"] = f"GPU only; context {ctx // 1024}K (tested 3/3 facts), KV {kv.group(1) if kv else 'f16'}{acc}. Final profile 2026-10-03."
g = c["routing"]["router"]["settings"]["groups"]       # group members must match the final profile names
g["all-local-llm"]["members"] = [n for n in M if n != "Qwen3-Embedding-0.6B"]
g["embeddings"]["members"] = ["Qwen3-Embedding-0.6B"]
out = os.path.join(CFG, "llama-swap-final.yaml"); yaml.safe_dump(c, open(out, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False, width=10000)
print(len(M), "profiles ->", out)
for n, m in M.items(): print(f"  {n:38} ctx={re.search(r'--ctx-size (\d+)', m['cmd']) and re.search(r'--ctx-size (\d+)', m['cmd']).group(1)}")
