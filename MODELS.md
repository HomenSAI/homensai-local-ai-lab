# Model inventory and profiles

Model assets stay in `<MODEL_DIR>`; containers receive that host directory as a read-only bind mount at `/models`. No model weights are copied into Docker images. Checksums are recorded in `MODELS.sha256`.

| Logical name | Host file | Source / revision | Quant / metadata | Bytes | SHA256 | Runtime / profile | Initial context / KV | Accelerator | Role |
|---|---|---|---|---:|---|---|---|---|---|
| Bonsai 2 27B | `<MODEL_DIR>/Ternary-Bonsai-2-27B-PTQ1_0.gguf` | `prism-ml/Ternary-Bonsai-2-27B-gguf` | PTQ1_0, qwen35, 851 tensors, 64 layers | 5,946,648,928 | `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3` | PrismML only / `bonsai` | 32768 stable; F16 KV; 8488 MiB sampled peak | None | Experimental, higher-quality compressed 27B-class option; compare output quality manually |
| Qwen3.5 9B MTP | `<MODEL_DIR>/Qwen3\Qwen3.5-9B-UD-Q4_K_XL.gguf` | `unsloth/Qwen3.5-9B-MTP-GGUF@9716a636ee4bddc3fed678220b7a33dd2a4160ae` | UD-Q4_K_XL, qwen35, nextn_predict_layers=1 | 6,135,034,208 | `362f85a2d7dbc0259e926d5ac33ca0d0f17fd3753496d65bfd2106384c929d3f` | Upstream llama.cpp / `qwen` | 65536; F16 KV; 8050 MiB base, 8678 MiB MTP n=2 peak | `draft-mtp` n-max=2; 86.7 vs 71.4 tok/s in fixed-seed content check, 69% acceptance | HEAVY / REASONING / COMPLEX CODING / LONG CONTEXT |
| Qwen3.5 9B existing comparison | `<MODEL_DIR>/Qwen3\Qwen3.5-9B-Q5_K_S-4.60bpw.gguf` | `byteshape/Qwen3.5-9B-GGUF` (source inferred from metadata) | Q5_K_S, 4.60 bpw, qwen35, non-MTP | 5,155,948,384 | `cbb7c4bd88d9a6313a82c5a8441c4cce7d431876f8250404d16a340d74260a04` | Upstream llama.cpp / `qwen-q5` | 65536 smoke verified | No MTP | Existing non-MTP comparison against MTP Q4 profile |
| Qwen3.5 Vision projector | `<MODEL_DIR>/Qwen3\mmproj-F16.gguf` | Same pinned Unsloth Qwen MTP repo/revision | F16, clip, Qwen3VL merger | 918,165,984 | `5a40d1f771686432172a4981018a0d30d03a5aaf5793a5badd5416573362a232` | Upstream llama.cpp / `qwen-vision` | 32768 context smoke verified separately | MTP off | Image input through the OpenAI-compatible API |
| MiniCPM5 2B | `<MODEL_DIR>/MiniCPM5\MiniCPM5-2B-Q8_0.gguf` | `openbmb/MiniCPM5-2B-GGUF@2079a22f3beaa4e306449978533478fe0522f4b3` | Q8_0, llama, 381 tensors, 42 blocks | 2,679,710,688 | `c5415f8989bf88a8288f1b55a3cc371af53c07b0faa220a63bd7a990cfaba078` | Upstream llama.cpp / `minicpm`, `dual-minicpm` | Single 65536; dual 8192; single 5831 MiB peak | DSpark OFF selected; n=4 was faster in repeated throughput run but failed the same-prompt concise-answer sanity check; n=7 slower | FAST / ROUTER / SIMPLE TOOLS |
| MiniCPM5 DSpark head | `<MODEL_DIR>/MiniCPM5\MiniCPM5-2.6B-DSpark.gguf` | `openbmb/MiniCPM5-2B-DSpark-GGUF@a261d2b4abc9c9ebfbad2af8a817a09802fc4ca3` | BF16 DFlash head, 5 draft blocks, block size 7 | 652,730,240 | `57df08640f0534a1aac075d1c8bdacdb2b7e5815da6f4e5cfd39ecac3a3f0c26` | Upstream llama.cpp, MiniCPM only | Single A/B only; off initially | GPU draft offload only if supported and measured faster | Optional accelerator, not a required dependency |
| Spark-X2.5 4B | `<MODEL_DIR>/Spark\Spark-X2.5-4B-Q8_0.gguf` | `XHToken/Spark-X2.5-4B-GGUF@9826e0be84e6e6e8b9668abc91421109a1df1e2d` | Q8_0, architecture `spark2_5` | 4,375,021,152 | `5c2c3c190e4337e1016b8593ca8e26e8b18c972200b107385d4ec61a25d9dea2` | Upstream llama.cpp / `spark`, `dual-spark` | Single 65536 F16 KV; dual 16384 Q8_0 KV | Thinking OFF for browser/default; thinking ON produced no user-facing `content` in the quality check | MID / AGENT / CODING / TOOLS |
| Whisper large-v3 turbo | `<MODEL_DIR>/audio\ggml-large-v3-turbo-q8_0.bin` | `ggerganov/whisper.cpp@5359861c739e955e79d9a303bcbc70fb988958b1` | Q8_0 GGML binary | 874,188,075 | `317eb69c11673c9de1e1f0d459b253999804ec71ac4c23c17ecf5fbe24e259a1` | whisper.cpp CUDA / on-demand `whisper` at 8082 | Load on demand; stop after processing | None | STT in Russian, Ukrainian, German and English |
| Qwen-Image-2.1 diffusion model | `<MODEL_DIR>/Qwen-Image-2.1\qwen-image-2.1-Q5_K_M.gguf` | `unsloth/Qwen-Image-2.1-GGUF@2c31ccd392b367a6637841a143813320a02dff55` | Q5_K_M GGUF v3, 265 tensors; header has 0 metadata KVs and diffusion tensor names | 5,390,223,072 | `4b53321654dd3bf0aa8dd6bb821fdcb1c9053ca735070e359a23cbb9f97268ce` | stable-diffusion.cpp CUDA / on-demand `qwen-image` | 1024×1024, 20 steps, seed 42; passed in 231.7 s, 7081 MiB VRAM / 5714 MiB container RAM peak | Diffusion Flash Attention, disk-backed diffusion weights, VAE tiling, Qwen3-VL text encoder | Text-to-image tested; image editing remains available with vision projector |
| Qwen-Image-2.1 text encoder | `<MODEL_DIR>/Qwen-Image-2.1\text_encoder\Qwen3VL-8B-Instruct-Q4_K_M.gguf` | `Qwen/Qwen3-VL-8B-Instruct-GGUF@f982a07559d4a2f6c8744d840bf6fccab30eea96` | Q4_K_M GGUF v3, qwen3vl, 399 tensors, 36 blocks, metadata context 262144 | 5,027,784,800 | `67d1659bfe71b89d50b45a4ad1a9e5b997e5bb16ce5da66a6a6167abd569e9e2` | stable-diffusion.cpp / Qwen Image only | CPU-offload; not a resident chat LLM | Prompt conditioning | Required for Qwen-Image text-to-image |
| Qwen3-VL image-edit projector | `<MODEL_DIR>/Qwen-Image-2.1\text_encoder\mmproj-Qwen3VL-8B-Instruct-F16.gguf` | Same pinned Qwen3-VL repo/revision | F16 GGUF v3, clip/mmproj, 352 tensors | 1,159,029,824 | `ca524100ebf825c9a870db1c580d03879e0da0ab2541697e2458e64891cf9d38` | stable-diffusion.cpp / Qwen Image edit only | Loaded only for image-edit requests | Vision encoding | Required to condition Qwen-Image edits on reference images |
| Qwen-Image-2.1 VAE | `<MODEL_DIR>/Qwen-Image-2.1\vae\qwen_image_2.1_vae_bf16.safetensors` | `Comfy-Org/Qwen-Image-2.1@9a44dbdb47cefd046be9c0a13476192f34c8db8e` | BF16 safetensors, 238 tensors; metadata `qwen_image_2.1_vae` | 675,509,688 | `bb21f7473051e1ac368515dd3f2e15cd44d7a11748ee8823e1ddca3e4876b7c9` | stable-diffusion.cpp / Qwen Image only | Offload as runtime requires | None | Decode generated image latents |

## Verification notes

- Bonsai is GGUF v3, architecture `qwen35`, file_type 143. Its bytes match the Hub LFS checksum. PTQ1_0 must use the PrismML runtime and must not be routed through stock llama.cpp.
- The selected Qwen MTP file is GGUF v3, architecture `qwen35`, 442 tensors and 33 blocks. Metadata contains `nextn_predict_layers=1` and four `.nextn.*` tensors. The existing Q5_K_S file is non-MTP and remains untouched; its new `qwen-q5` profile is an explicit comparison service.
- The Qwen3.5 projector is GGUF v3 `clip` with Qwen3VL vision/projector metadata.
- MiniCPM GGUF is Q8_0, 381 tensors and 42 blocks. Metadata context is 131072; profile contexts remain benchmark-controlled.
- DSpark is a separate DFlash GGUF head with 5 blocks and block size 7. It loads with the pinned runtime; n=4 acceptance was measured, but the exact short-answer sanity response lost required explanatory content, so standalone MiniCPM remains the default. n=7 was slower.
- Spark GGUF is v3, architecture `spark2_5`, file_type 7. The pinned upstream runtime is newer than the native-support merge at b10828.
- Whisper bytes and size match the official Hub LFS object at the recorded revision.
- Qwen Image diffusion, Qwen3-VL encoder, edit mmproj and Qwen Image 2.1 VAE have exact sizes and locally computed SHA256 values matching each pinned Hugging Face local `etag`; repository revisions are also checked. The diffusion GGUF header is v3, has 265 tensor descriptors and zero metadata entries; its descriptors use `model.diffusion_model.*` names, so no `general.architecture` value is claimed. The three other assets expose the recorded metadata.
- Qwen-Image-2.1 is a diffusion transformer, not a chat/text model. `llama.cpp` does not execute its `qwen_image` architecture. Main language models stay on llama.cpp; the Qwen Image profile uses pinned `stable-diffusion.cpp` inside this same Docker project. The 1024×1024/20-step test passed with `--params-backend diffusion=disk`, CPU offload and tiled VAE; output and peak telemetry are under `media/images/`.

## Measured production settings (RTX 3080 10 GiB)

- Qwen3.5 MTP n-max=2: three-repeat average 93.4 tok/s vs 79.8 tok/s MTP-off (+17%); the same fixed-seed content check also passed, with 69% draft acceptance and 8678 MiB peak. n=4 averaged 88.3 tok/s, n=6 62.2 tok/s. Keep n=2 at 65536 context.
- MiniCPM: DSpark OFF. The three-repeat n=4 run averaged about 155 tok/s vs 143 tok/s standalone, but its same-prompt content check dropped the requested explanation and produced an invalid `faulthandler.dump_traceback_limit` example. n=7 averaged about 131 tok/s. Preserve the valid single-model profile; dual context is 8192.
- Spark: single profile F16 KV / 65536 context; dual profile Q8_0 KV / 16384. Three-repeat means were about 81.1 tok/s (F16) and 75.2 tok/s (Q8_0); Q8_0 is retained only for the resident pair's memory headroom. Set `enable_thinking=false` for normal API/UI requests because thinking-on returned no user-facing content within the test cap.
- Bonsai: PrismML only, context 32768 passed with 8488 MiB sampled peak (~1.7 GiB available). It remains experimental pending manual answer-quality comparison.
- Qwen Vision: context 32768 passed separately; peak 8143 MiB. Whisper is on-demand only.

## Dual-resident gate

Only MiniCPM5 + Spark may be resident together. The tested 8192 + 16384 setup with Spark Q8_0 KV passed: idle combined VRAM 8289 MiB (1951 MiB free); controlled simultaneous peak 8300 MiB (1940 MiB free), no OOM/CUDA errors; sequential throughput change was within 1% for each. Dual mode is enabled, but requests should run sequentially by default. Single-model profiles keep their own measured KV settings.

## Unified API catalog (2026-09-28)

The active gateway exposes these llama.cpp chat profiles through one API. Exact public model IDs retain family, variant and quantization; model weights stay at the existing host paths.

| Public model ID | Host model file | Runtime | Context | GPU offload / KV | Mode |
|---|---|---|---:|---|---|
| `Qwen3.5-9B-MTP-Q4_K_XL` | `Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf` | Upstream llama.cpp | 65536 | all layers / F16 | MTP `draft-mtp`, n-max 2 |
| `Qwen3.5-9B-MTP-Q4_K_XL-Vision` | same Qwen GGUF + `Qwen3/mmproj-F16.gguf` | Upstream llama.cpp | 49152 | all layers / F16 | Vision, MTP off |
| `Qwen3.5-9B-Q5_K_S` | `Qwen3/Qwen3.5-9B-Q5_K_S-4.60bpw.gguf` | Upstream llama.cpp | 65536 | all layers / F16 | Text |
| `MiniCPM5-2B-Q8_0` | `MiniCPM5/MiniCPM5-2B-Q8_0.gguf` | Upstream llama.cpp | 131072 | all layers / F16 | DSpark off; long-input recall caveat |
| `Spark-X2.5-4B-Q8_0` | `Spark/Spark-X2.5-4B-Q8_0.gguf` | Upstream llama.cpp | 98304 | all layers / F16 | Thinking defaults off in UI; long-input recall caveat |
| `Ternary-Bonsai-2-27B-PTQ1_0` | `Ternary-Bonsai-2-27B-PTQ1_0.gguf` | PrismML llama.cpp only | 32768 | all layers / F16 | Experimental |
| `Qwen3-VL-8B-Instruct-Q4_K_M` | `Qwen-Image-2.1/text_encoder/Qwen3VL-8B-Instruct-Q4_K_M.gguf` + matching F16 mmproj | Upstream llama.cpp | 16384 | all layers / F16 | Vision; 16K long input and image smoke tested |

All seven profiles belong to llama-swap's single `swap: true`, `exclusive: true` group. `globalTTL=900` unloads an idle backend after 15 minutes. The gateway has no preload list, so its initial/restarted state is `ACTIVE MODEL=NONE`. Qwen Image diffusion and Whisper STT do not implement chat completions and are not included in `/v1/models`.
