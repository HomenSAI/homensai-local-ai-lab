#!/usr/bin/env python3
# Local AI Lab - (c) 2026 Serhii Khomenko - https://homensai.com/
"""Virtual RTX 3080 for testing Local AI Lab without a GPU: a stand-in for llama.cpp and llama-swap.

The same file acts as every program of the gateway image, chosen by the name it is started under:
  llama-server  one model server (the API of llama.cpp: /health, /v1/chat/completions, /tokenize, /slots, ...)
  llama-bench   the speed benchmark (prints the llama-bench JSON)
  llama-swap    the gateway: reads config/llama-swap.yaml, starts one llama-server per model on 127.0.0.1:5800+,
                swaps models, proxies /v1/*, lists /v1/models and /running, unloads on request

Nothing is computed: answers are fixed texts and the numbers come from a simple model of a 10 GB card
(weights = file size, KV cache = context x model size x cache type). A model that does not fit fails to load,
like the real one. Only the Python standard library is used.
"""
import hashlib, json, math, os, re, shlex, signal, subprocess, sys, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VRAM_MIB = 10240                 # RTX 3080 10 GB
BASE_MIB = 380                   # CUDA context, compute buffers
KV_FACTOR = {"f16": 1.0, "q8_0": 0.53, "q4_0": 0.28}


# ---------------------------------------------------------------- the virtual card
def billions(path):
    # the file name first, then the folder: "cand/Mistral-Nemo-12B-Instruct/Mistral-Nemo-Instruct-2407-Q4_K_M.gguf"
    for part in (os.path.basename(path), path):
        m = re.search(r"(\d+(?:\.\d+)?)B", part, re.I)
        if m:
            return float(m.group(1))
    return 4.0


def native_context(name):
    low = name.lower()
    return 262144 if any(k in low for k in ("qwen3.5", "ornith", "mimo", "spark")) else 131072


def profile(args):
    """VRAM need (MiB), native context and speeds of a server started with these llama.cpp arguments."""
    model = args.get("model", "")
    size = sum(os.path.getsize(p) for p in (model, args.get("mmproj")) if p and os.path.isfile(p))
    weights = size / 2**20
    ctx = int(args.get("ctx", 4096))
    b = billions(model)
    kv = ctx * b * 0.0035 * KV_FACTOR.get(args.get("ctk", "f16"), 1.0)
    gb = max(weights / 1024, 0.3)
    tg = round(min(190.0, 460.0 / gb), 1)
    return {"vram": int(BASE_MIB + weights + kv), "native": native_context(model), "tg": tg, "pp": round(tg * 24, 1),
            "weights": int(weights)}


def parse_args(argv):
    out, i = {}, 0
    names = {"-m": "model", "--model": "model", "-c": "ctx", "--ctx-size": "ctx", "--port": "port", "--host": "host",
             "--alias": "alias", "--mmproj": "mmproj", "-ctk": "ctk", "--cache-type-k": "ctk", "-ngl": "ngl",
             "--n-gpu-layers": "ngl", "-p": "n_prompt", "-n": "n_gen", "-o": "output"}
    while i < len(argv):
        key = names.get(argv[i])
        if key and i + 1 < len(argv):
            out[key] = argv[i + 1]; i += 2
        else:
            i += 1
    return out


# ---------------------------------------------------------------- llama-server
def reply_text(alias, prompt):
    notes = re.findall(r"NOTE-[A-Z]: [^\n]+", prompt)
    if notes:
        return "\n".join(f"{i + 1}. {n.split(': ', 1)[1]}" for i, n in enumerate(notes))
    if "python" in prompt.lower() and ("code" in prompt.lower() or "```" in prompt):
        return "```python\n# answer of a virtual model: no real code\ndef solve(*args, **kwargs):\n    return None\n```"
    if "ОТВЕТ" in prompt:
        return "Решение виртуальной модели (условные данные).\nОТВЕТ: 42"
    if "одним словом" in prompt:
        return "готово"
    return f"Ответ виртуальной модели {alias} на виртуальной RTX 3080 (условные данные, не настоящий ИИ)."


class ModelServer:
    def __init__(self, args):
        self.args, self.alias = args, args.get("alias") or os.path.basename(args.get("model", "model"))
        self.ctx = int(args.get("ctx", 4096))
        self.p = profile(args)
        self.counters = {"prompt": 0, "prompt_s": 0.0, "gen": 0, "gen_s": 0.0}
        self.busy = False

    def chat(self, body):
        msgs = body.get("messages") or [{"content": body.get("prompt", "")}]
        prompt = "\n".join(m["content"] if isinstance(m.get("content"), str) else
                           " ".join(p.get("text", "") for p in m.get("content") or [] if isinstance(p, dict)) for m in msgs)
        n_prompt = max(1, len(prompt) // 4)          # about 4 characters per token, as llama.cpp tokenizers give here
        if n_prompt > self.ctx:
            return 400, {"error": {"code": 400, "message": f"the request exceeds the available context size ({n_prompt} > {self.ctx})",
                                   "type": "exceed_context_size_error"}}
        text = reply_text(self.alias, prompt if n_prompt <= self.p["native"] else "")
        n_gen = min(int(body.get("max_tokens") or 256), max(1, len(text) // 3))
        fill = n_prompt / max(1, self.ctx)
        tg = round(self.p["tg"] * (1 - 0.35 * fill), 1)
        pp = round(self.p["pp"] * (1 - 0.25 * fill), 1)
        self.counters["prompt"] += n_prompt; self.counters["prompt_s"] += n_prompt / pp
        self.counters["gen"] += n_gen; self.counters["gen_s"] += n_gen / tg
        return 200, {"id": "chatcmpl-virtual", "object": "chat.completion", "created": int(time.time()), "model": self.alias,
                     "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
                     "usage": {"prompt_tokens": n_prompt, "completion_tokens": n_gen, "total_tokens": n_prompt + n_gen},
                     "timings": {"prompt_n": n_prompt, "prompt_ms": round(1000 * n_prompt / pp, 1), "prompt_per_second": pp,
                                 "predicted_n": n_gen, "predicted_ms": round(1000 * n_gen / tg, 1), "predicted_per_second": tg}}

    def handle(self, method, path, body):
        if path == "/health":
            return 200, {"status": "ok"}
        if path == "/vgpu":
            return 200, {"used_mib": self.p["vram"], "util": 97 if self.busy else 3}
        if path in ("/v1/models", "/models"):
            return 200, {"object": "list", "data": [{"id": self.alias, "object": "model", "owned_by": "llamacpp",
                                                     "meta": {"n_ctx_train": self.p["native"]}}]}
        if path == "/props":
            return 200, {"default_generation_settings": {"n_ctx": self.ctx}, "total_slots": 1,
                         "model_path": self.args.get("model"), "build_info": "virtual-3080"}
        if path == "/slots":
            return 200, [{"id": 0, "n_ctx": self.ctx, "is_processing": self.busy, "params": {"temperature": 0.8, "top_k": 40}}]
        if path == "/metrics":
            c = self.counters
            return 200, ("llamacpp:prompt_tokens_total %d\nllamacpp:prompt_seconds_total %.3f\n"
                         "llamacpp:tokens_predicted_total %d\nllamacpp:tokens_predicted_seconds_total %.3f\n"
                         % (c["prompt"], c["prompt_s"], c["gen"], c["gen_s"]))
        if path == "/tokenize":
            content = (body or {}).get("content", "")
            return 200, {"tokens": list(range(max(1, len(content) // 4)))}
        if path == "/detokenize":
            return 200, {"content": ""}
        if path in ("/v1/embeddings", "/embeddings"):
            items = (body or {}).get("input") or [""]
            items = [items] if isinstance(items, str) else items
            data = []
            for i, text in enumerate(items):
                seed = hashlib.sha256(str(text).encode()).digest()
                vec = [((seed[j % 32] + j) % 97) / 97 - 0.5 for j in range(1024)]
                norm = math.sqrt(sum(v * v for v in vec)) or 1
                data.append({"object": "embedding", "index": i, "embedding": [v / norm for v in vec]})
            return 200, {"object": "list", "data": data, "model": self.alias, "usage": {"prompt_tokens": 8, "total_tokens": 8}}
        if path in ("/v1/chat/completions", "/chat/completions", "/v1/completions", "/completion"):
            self.busy = True
            try:
                time.sleep(0.05)
                return self.chat(body or {})
            finally:
                self.busy = False
        return 404, {"error": {"code": 404, "message": "File Not Found"}}


def make_handler(route):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def answer(self, status, payload, ctype=None):
            data = payload.encode() if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype or ("text/plain; charset=utf-8" if isinstance(payload, str) else "application/json"))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def body(self):
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
            try:
                return json.loads(raw) if raw else {}
            except ValueError:
                return {}

        def do_GET(self):
            self.answer(*route("GET", self.path.split("?")[0], None, self))

        def do_POST(self):
            self.answer(*route("POST", self.path.split("?")[0], self.body(), self))
    return Handler


def llama_server(argv):
    args = parse_args(argv)
    model = args.get("model", "")
    print("build: virtual-3080 (simulated llama.cpp, no real inference)", flush=True)
    print("ggml_cuda_init: found 1 CUDA devices:\n  Device 0: NVIDIA GeForce RTX 3080 (virtual), compute capability 8.6, VMM: yes", flush=True)
    if not os.path.isfile(model):
        print(f"gguf_init_from_file: failed to open GGUF file '{model}'", flush=True)
        print("error: failed to load model", flush=True)
        sys.exit(1)
    server = ModelServer(args)
    p = server.p
    print(f"llama_model_loader: loaded meta data from {model}", flush=True)
    print(f"print_info: n_ctx_train      = {p['native']}", flush=True)
    time.sleep(min(3.0, 0.4 + p["weights"] / 4000))
    if p["vram"] > VRAM_MIB - 120:
        print(f"ggml_backend_cuda_buffer_type_alloc_buffer: allocating {p['vram'] - p['weights']} MiB on device 0: "
              f"cudaMalloc failed: out of memory", flush=True)
        print("llama_init_from_model: failed to initialize the context: failed to allocate buffer for kv cache", flush=True)
        sys.exit(1)
    print(f"llama_context: n_ctx = {server.ctx}; virtual VRAM {p['vram']} MiB of {VRAM_MIB}", flush=True)
    host, port = args.get("host", "127.0.0.1"), int(args.get("port", 8080))
    print(f"main: server is listening on http://{host}:{port} - starting the main loop", flush=True)
    ThreadingHTTPServer((host, port), make_handler(lambda m, path, body, h: server.handle(m, path, body))).serve_forever()


def llama_bench(argv):
    args = parse_args(argv)
    if not os.path.isfile(args.get("model", "")):
        print(f"error: failed to load model '{args.get('model')}'", file=sys.stderr)
        sys.exit(1)
    p = profile({**args, "ctx": "4096"})
    time.sleep(1.0)
    print(json.dumps([{"model_filename": args["model"], "n_prompt": 512, "n_gen": 0, "avg_ts": p["pp"], "stddev_ts": 1.2},
                      {"model_filename": args["model"], "n_prompt": 0, "n_gen": 128, "avg_ts": p["tg"], "stddev_ts": 0.4}], indent=1))


# ---------------------------------------------------------------- llama-swap
def read_config(path):
    models, alias, in_models = {}, None, False
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if re.match(r"^models:\s*$", line):
            in_models = True
        elif in_models and re.match(r"^\S", line):
            in_models = False
        elif in_models and (m := re.match(r"^  ([^\s#][^:]*):\s*$", line)):
            alias = m.group(1).strip("'\"")
            models[alias] = {"cmd": "", "description": "", "ttl": 900, "vision": False, "context": 0}
        elif in_models and alias and (m := re.match(r"^    (cmd|description|ttl):\s*(.*)$", line)):
            value = m.group(2).strip()
            if m.group(1) == "description" and value[:1] in "'\"":
                value = value[1:-1]
            models[alias][m.group(1)] = value
        elif in_models and alias and line.strip() == "- image":
            models[alias]["vision"] = True
    for alias, item in models.items():
        ctx = re.search(r"--ctx-size\s+(\d+)", item["cmd"])
        item["context"] = int(ctx.group(1)) if ctx else 0
        item["embedding"] = "--embedding" in item["cmd"] or "embedding" in alias.lower()
    return models


class Swap:
    def __init__(self, config):
        self.config, self.lock = config, threading.Lock()
        self.models, self.running, self.next_port = read_config(config), {}, 5800

    def stop_all(self):
        for alias, item in list(self.running.items()):
            item["proc"].terminate()
            try:
                item["proc"].wait(10)
            except subprocess.TimeoutExpired:
                item["proc"].kill()
            print(f"swap: unloaded {alias}", flush=True)
        self.running.clear()

    def ensure(self, alias):
        with self.lock:
            if alias in self.running and self.running[alias]["proc"].poll() is None:
                return self.running[alias]["port"]
            self.stop_all()                                   # one model in video memory at a time
            port = self.next_port
            self.next_port = 5800 + (self.next_port - 5800 + 1) % 200
            cmd = self.models[alias]["cmd"].replace("${PORT}", str(port))
            argv = shlex.split(cmd)
            print(f"swap: loading {alias} on port {port}", flush=True)
            proc = subprocess.Popen(argv, stdout=sys.stdout, stderr=sys.stdout)
            self.running[alias] = {"proc": proc, "port": port, "cmd": cmd, "since": time.time()}
            for _ in range(600):
                if proc.poll() is not None:
                    del self.running[alias]
                    raise RuntimeError(f"upstream command exited prematurely ({alias})")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                        if r.status == 200:
                            return port
                except OSError:
                    time.sleep(0.3)
            raise RuntimeError("health check timed out")

    def forward(self, port, method, path, body):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=1800) as r:
                raw = r.read().decode()
                return r.status, (json.loads(raw) if raw[:1] in "[{" else raw)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def route(self, method, path, body, handler):
        if path in ("/health", "/"):
            return 200, "OK"
        if path == "/vgpu":
            used, util = BASE_MIB if self.running else 0, 0
            for item in list(self.running.values()):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{item['port']}/vgpu", timeout=1) as r:
                        d = json.load(r); used, util = d["used_mib"], d["util"]
                except OSError:
                    pass
            return 200, {"used_mib": used, "util": util}
        if path == "/v1/models":
            data = []
            for alias, item in self.models.items():
                loaded = alias in self.running
                data.append({"id": alias, "object": "model", "created": int(time.time()), "owned_by": "llama-swap",
                             "name": alias, "description": item["description"], "context_length": item["context"],
                             "status": {"value": "loaded" if loaded else "unloaded"},
                             "architecture": {"input_modalities": ["text", "image"] if item["vision"] else ["text"]}})
            return 200, {"object": "list", "data": data}
        if path == "/running":
            return 200, {"running": [{"model": a, "state": "ready", "proxy": f"http://127.0.0.1:{i['port']}", "cmd": i["cmd"],
                                      "ttl": int(self.models[a].get("ttl") or 900)} for a, i in self.running.items()]}
        if path in ("/unload", "/api/models/unload") or path.startswith("/api/models/unload/"):
            with self.lock:
                target = path.rsplit("/", 1)[-1] if path.startswith("/api/models/unload/") else None
                if target and target in self.running:
                    item = self.running.pop(target); item["proc"].terminate(); item["proc"].wait(10)
                elif not target:
                    self.stop_all()
            return 200, "OK"
        if path.startswith("/upstream/"):
            alias, _, rest = path[len("/upstream/"):].partition("/")
            if alias not in self.models:
                return 404, {"error": f"model {alias} not found"}
            try:
                return self.forward(self.ensure(alias), method, "/" + rest, body)
            except RuntimeError as exc:
                return 502, {"error": str(exc)}
        if path.startswith("/v1/") and method == "POST":
            alias = str((body or {}).get("model") or "")
            if alias not in self.models:
                return 400, {"error": f"could not find suitable handler for {alias}"}
            try:
                return self.forward(self.ensure(alias), method, path, body)
            except RuntimeError as exc:
                return 502, {"error": str(exc)}
        return 404, {"error": "not found"}


def llama_swap(argv):
    config, listen = "/etc/llama-swap/config.yaml", "0.0.0.0:8080"
    for i, a in enumerate(argv):
        if a in ("-config", "--config"):
            config = argv[i + 1]
        if a in ("-listen", "--listen"):
            listen = argv[i + 1]
    swap = Swap(config)
    host, _, port = listen.rpartition(":")
    print(f"llama-swap (virtual-3080): {len(swap.models)} models from {config}, listening on {listen}", flush=True)
    signal.signal(signal.SIGTERM, lambda *a: (swap.stop_all(), sys.exit(0)))
    ThreadingHTTPServer((host or "0.0.0.0", int(port)), make_handler(swap.route)).serve_forever()


if __name__ == "__main__":
    role = os.path.basename(sys.argv[0])
    {"llama-bench": llama_bench, "llama-swap": llama_swap}.get(role, llama_server)(sys.argv[1:])
