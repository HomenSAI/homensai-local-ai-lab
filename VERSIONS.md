# Pinned runtime and tool versions

The original llama.cpp/PrismML/Whisper pins were inspected on 2026-09-26; the Qwen Image diffusion runtime and asset pins were checked on 2026-09-27. Dockerfiles fetch exact Git commits and check out detached HEADs; no runtime source uses a floating latest reference.

| Component | Pin | Reason / status |
|---|---|---|
| Upstream `ggml-org/llama.cpp` | `81bc6b83f827df746eb129235488d325c49cae52` | Current upstream commit observed while preparing this project. Spark2.5 support merge is `3ad1ba7336986d98592d3e28cafd1a406715351f`, tag b10828; GitHub compare showed the selected commit 372 commits newer than b10828. Used for Qwen, MiniCPM, Spark and Qwen Vision. |
| Bonsai `PrismML-Eng/llama.cpp` | Release `prism-b10743-adfffbe`; commit `adfffbe41b2cabcd51fff326ab045662265062bb` | Used only for PTQ1_0 Bonsai. Gateway command sets `LD_LIBRARY_PATH=/opt/prism:/usr/local/cuda/lib64` so its matching PrismML ggml libraries load; actual 32K GPU smoke passed. |
| `ggml-org/whisper.cpp` | `d09f61a708f3487afa956ff578e60eae5e7a233c` | Official upstream commit observed during setup; version metadata 1.9.4-dev. Used for whisper-server and whisper-cli. |
| `leejet/stable-diffusion.cpp` | `3f8527a46c54ecf4cb4ed6003da8e8982283c73c` | CUDA C++ diffusion runtime for Qwen-Image-2.1 GGUF. Its official model guide documents the Qwen3-VL encoder, Qwen Image 2.1 VAE, GGUF diffusion input, CPU offload and image-edit mmproj. Separate from llama.cpp because Qwen Image is a diffusion architecture. |
| CUDA build/runtime base | `nvidia/cuda:12.8.1-devel-ubuntu24.04` and `nvidia/cuda:12.8.1-runtime-ubuntu24.04` | Fixed CUDA toolkit image tags used by the upstream, PrismML, Whisper and image runtime Dockerfiles. |
| GPU target | `CMAKE_CUDA_ARCHITECTURES=86` / NVIDIA `sm_86` | Exact target for RTX 3080. On 2026-09-28 Windows `nvidia-smi` reports driver 617.14 and CUDA compatibility 13.4; a temporary container from the pre-existing CUDA image enumerated the RTX 3080 successfully. This supersedes the earlier WSL NVML failure note. |
| Docker CLI / Compose | Docker CLI 29.7.2; Compose v5.5.1; Docker Engine 29.8.0; Docker Desktop 4.92.0 | Verified available after the user's continuation command. Docker Desktop was not launched by the agent. |
| Hugging Face CLI | `hf` 1.8.0 | Used with immutable revisions; each downloaded size and SHA256 matches Hub LFS metadata. |

## Pinned model asset revisions

| Repository | Revision | Asset(s) |
|---|---|---|
| `unsloth/Qwen-Image-2.1-GGUF` | `2c31ccd392b367a6637841a143813320a02dff55` | `qwen-image-2.1-Q5_K_M.gguf` |
| `Qwen/Qwen3-VL-8B-Instruct-GGUF` | `f982a07559d4a2f6c8744d840bf6fccab30eea96` | Q4_K_M text encoder and F16 mmproj for image-edit |
| `Comfy-Org/Qwen-Image-2.1` | `9a44dbdb47cefd046be9c0a13476192f34c8db8e` | `vae/qwen_image_2.1_vae_bf16.safetensors` |

## Download integrity and host memory

- The four Qwen Image 2.1 assets are present under `<MODEL_DIR>/Qwen-Image-2.1`; exact file size, pinned local-dir revision, and locally computed SHA256 matched Hugging Face Hub metadata.
- The download helper skips any existing target asset and downloads serially. To limit memory on the 16 GiB host, it sets HF Xet range concurrency to 4 and reconstruction/download buffers to 512 MiB total (256 MiB per-file). These are the documented `HF_XET_NUM_CONCURRENT_RANGE_GETS` and `HF_XET_RECONSTRUCTION_*` controls; do not set HF_XET high-performance mode on this host.

## Official references checked

- Upstream build and CLI/server configuration: [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).
- CUDA shared-backend linker workaround used by all CUDA Dockerfiles: [llama.cpp issue #23357](https://github.com/ggml-org/llama.cpp/issues/23357) documents adding `/usr/local/cuda/lib64/stubs` and `-lcuda` to executable/shared linker flags when CUDA driver VMM symbols do not propagate from `libggml-cuda.so`.
- Native Spark2.5 support and merge point: [llama.cpp PR #27868](https://github.com/ggml-org/llama.cpp/pull/27868).
- Speculative mode names, draft parameters and documented caveats: [llama.cpp speculative decoding guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md).
- Prometheus metric names, including draft and accepted token counters: [llama.cpp server metrics docs](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).
- Bonsai PTQ1_0 runtime guidance: [PrismML Bonsai demo](https://github.com/PrismML-Eng/Bonsai-demo).
- PrismML's [KV cache guide](https://github.com/PrismML-Eng/Bonsai-demo/blob/main/KV-CACHE.md) notes its scripts enable Flash Attention; the Bonsai profile starts with FA on.
- MiniCPM DSpark official artifact and example: [MiniCPM5 DSpark GGUF card](https://huggingface.co/openbmb/MiniCPM5-2B-DSpark-GGUF).
- Spark thinking mode uses `chat_template_kwargs.enable_thinking`: [XHToken Spark-X2.5 usage guide](https://github.com/XHToken/Spark-X2.5).
- Whisper server arguments and multipart endpoint: [whisper.cpp server README](https://github.com/ggml-org/whisper.cpp/blob/master/examples/server/README.md).
- Qwen Image 2.1 backend, GGUF denoiser, Qwen3-VL text encoder/VAE, edit projector and CPU-offload example: [stable-diffusion.cpp guide at the pinned commit](https://github.com/leejet/stable-diffusion.cpp/blob/3f8527a46c54ecf4cb4ed6003da8e8982283c73c/docs/qwen_image_2.1.md). The Unsloth Q5_K_M GGUF card explicitly lists `stable-diffusion.cpp` support and its denoiser/text-encoder/VAE dependencies: [Qwen-Image-2.1 GGUF README](https://huggingface.co/unsloth/Qwen-Image-2.1-GGUF).
- `stable-diffusion.cpp` [CUDA build instructions](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/build.md) and [Qwen-Image-2.1 GGUF repository](https://huggingface.co/unsloth/Qwen-Image-2.1-GGUF).
- Driver/toolkit compatibility: [NVIDIA CUDA compatibility documentation](https://docs.nvidia.com/deploy/cuda-compatibility/forward-compatibility.html).

## Unified gateway pin (2026-09-28)

| Component | Pin | Integrity / purpose |
|---|---|---|
| `mostlygeek/llama-swap` | Release `v260`, commit `fcefa7b` | Official Linux amd64 release archive SHA256 `d856a908507560cbdc253300bcf49092c7ead3c85098687428b0c9d4832ff46d`; config is checked against the v260 schema. |
| Gateway upstream runtime | Existing `local/ai-server-upstream:local`, image ID recorded in `PROJECT_STATE.md` | Uses upstream llama.cpp commit above; standard Qwen, MiniCPM, Spark and Qwen3-VL models. |
| Gateway Bonsai runtime | Existing `local/ai-server-bonsai:local`, image ID recorded in `PROJECT_STATE.md` | PrismML commit above, copied with its matching shared libraries to `/opt/prism`; used only for PTQ1_0 Bonsai. |

The gateway API uses `http://localhost:8080/v1`; Compose publishes only `127.0.0.1:8080`. The existing Windows portproxy maps `<LAN_IP>:8080` to that loopback address. Seven chat profiles use one exclusive swap group, idle TTL 900 seconds, and no preload. Qwen Image diffusion and Whisper STT are intentionally outside the chat model catalog.

Previous upstream, PrismML, Whisper, diffusion CUDA images and model runtimes were built/tested as recorded in `PROJECT_STATE.md`. The unified gateway acceptance results, including all seven text profiles, the exclusive-switch race, two real image-input profiles, Open WebUI, and host/LAN health, are recorded in `benchmark/gateway-acceptance/GATEWAY_FINAL_ACCEPTANCE_20260928.md`.
