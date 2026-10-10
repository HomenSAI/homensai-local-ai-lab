# Virtual RTX 3080: test the whole system without a GPU

Other languages: [Русский](README.ru.md) · [Deutsch](README.de.md)

This kit installs Local AI Lab on a Linux machine that has Docker but no NVIDIA card, and lets every part run as if an RTX 3080 (10 GB) were present: the gateway loads and swaps models, the console shows video memory and GPU load, the test runner measures speed, context and quality, the report builder, the progress page and the Git versioner work on the results. **No model is real**: answers are fixed texts and all numbers are simulated. Use it to learn the system, to rehearse an installation, or to test changes before running them on the real card. Never install it on a computer with a real NVIDIA GPU.

## What is simulated

| Part | Stand-in | File |
|---|---|---|
| NVIDIA driver in Docker (`--gpus all`, `gpus: all`) | a hook with the name Docker looks for; it copies the virtual `nvidia-smi` into every GPU container | `nvidia-container-runtime-hook` |
| `nvidia-smi` | "NVIDIA GeForce RTX 3080, 10240 MiB"; used memory and load come from the running virtual model servers | `nvidia-smi` |
| llama.cpp `llama-server`, `llama-bench` and `llama-swap` | one Python program with the same paths and APIs (`/health`, `/v1/chat/completions` with `timings`, `/tokenize`, `/slots`, `/metrics`, `/v1/embeddings`, `/v1/models`, `/running`, unload); video memory = file size + KV cache for the context and cache type; a model that does not fit stops with "out of memory" like the real one | `fake_llama.py`, `Dockerfile`, `curl` |
| model files | sparse `.gguf` files with plausible sizes (they take almost no disk) | `make_models.py` |

## Steps (Linux, Docker Engine, as root or with sudo)

```
# 1. the virtual driver: Docker must find it when it starts
sudo cp tests/virtual-3080/nvidia-container-runtime-hook tests/virtual-3080/nvidia-smi /usr/local/bin/
sudo systemctl restart docker
docker run --rm --gpus all python:3.12-slim nvidia-smi      # must print the RTX 3080 line

# 2. the system, as in the guide (Linux path)
python3 scripts/install.py doctor
python3 scripts/install.py init                              # then set MODEL_DIR in .env to any empty folder
docker build -t local/ai-server-llama-swap:260 tests/virtual-3080    # the virtual gateway instead of the CUDA builds
docker run --rm -v llm-models-fast:/models -v "$PWD":/lab:ro python:3.12-slim \
    python /lab/tests/virtual-3080/make_models.py /lab /models          # the virtual model files
python3 scripts/install.py build --no-gpu                    # console and versioner (the CUDA images are not needed)
python3 scripts/install.py up
python3 scripts/install.py git
python3 scripts/install.py verify                            # every line [ok]

# 3. the tests
docker compose --profile bench up -d --build bench-runner
```

Then open http://localhost:8766/ (console), http://localhost:8766/report/progress.html (test progress) and http://localhost:3010/ (versions).

Test report of 10.10.2026 (in Russian): [REPORT.ru.md](REPORT.ru.md).

**To remove it:** `docker compose --profile bench --profile gateway down`, `docker volume rm llm-models-fast`, delete `/usr/local/bin/nvidia-container-runtime-hook` and `/usr/local/bin/nvidia-smi`, restart Docker.
