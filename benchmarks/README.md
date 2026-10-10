# Benchmarks: the test runners

These scripts produced the published results of [rtx3080-local-ai-benchmarks](https://github.com/HomenSAI/rtx3080-local-ai-benchmarks) (23 models on an RTX 3080 / 10 GB, 2026-09-29 – 2026-10-06). That repository holds only the results; the code to repeat the tests is here.

## Tests, scripts and result files

| Test (folder in the results repository) | Phase | Runner | Tasks | Result file in `bench_results/` |
|---|---|---|---|---|
| 01-general-quality | `general` | `bench_top.py` (model list `TOP`) + `bench_all.py` | `qtasks.py`, 3 code tasks from `coding_tasks.py`, pictures from `make_images.py` | `results_all.jsonl` |
| 02-german-passive | `german`, `german_fix` | `german_all.py`, `german_fix.py` (re-run of empty answers), `qa_bench.py` | `qa_tasks.py` | `results_german.jsonl`, `results_german_fix.jsonl` |
| 03-max-context | `context` | `bench_ctx.py` + `mneedle.py` (3 hidden facts at 80 % fill) | filler text from the Python standard library | `results_ctx.jsonl`, `results_ctx_trials.jsonl` |
| 04-soak-reliability | `soak` | `soak.py` (through the gateway on port 8080) | profiles of `config/llama-swap.yaml` | `results_soak.jsonl` |
| 05-math-physics-grade11 | `stem` | `bench_stem.py` | `stem_tasks.py` | `results_stem.jsonl` |
| 06-chemistry-grade11 | `chem` | `bench_chem.py` | `chem_tasks.py` | `results_chem.jsonl` |
| 07-coding-20 | `code20` | `bench_code20.py`, tests in a sandbox without network (`code_eval_harness.py`) | `coding_tasks.py` | `results_code20.jsonl` |
| 08-accelerators-embeddings | `accel` | `bench_accel.py` | speculative-decoding profiles of `config/llama-swap.yaml`, embedding models | `results_accel.jsonl` |

`bench_top.py` and `bench_all.py` hold the shared parts: the model list, starting a model in its own container (`bench-srv`, port 8090, image `local/ai-server-llama-swap:260`, models from the Docker volume `llm-models-fast`), the RAM guard and the checkers.
After the context test, `gen_profiles_from_ctx.py` and `finalize_profiles.py` turn the measured windows into gateway profiles (`config/llama-swap-ctx.yaml` → `config/llama-swap-final.yaml`, candidates that are not live until you copy them); `exclude_not_gpu.md` lists the models removed by the 64K rule.

## Run (everything in Docker)

Build the gateway images first (`docs/INSTALL.*`, sections on the build), put the models into the volume `llm-models-fast` and fill the paths in `TOP` of `bench_top.py`. Then:

```
docker compose --profile bench up -d --build bench-runner
```

The runner copies these scripts into `bench_results/`, draws the vision pictures and runs the phases in the order of `BENCH_PHASES` (default `general german context german_fix accel stem chem code20`; add `soak` to test the gateway profiles). Each phase writes its log (`bench_full.log`, `bench_ctx.log`, ...) with the finish marker the console expects, so the console shows the stage, the progress bar and the time left. Every phase skips finished models, so a restart continues where it stopped. To run other phases: `BENCH_PHASES="stem chem"` in `.env`, delete `bench_results/run_all.log` and start the runner again. Stop it with `docker compose --profile bench stop bench-runner`.

The runner controls Docker on this PC through the Docker socket (it starts and stops the model containers and the gateway): start it only for a test run.

## Differences from the published run

- The vision pictures of the published run were not kept; `make_images.py` redraws the same content (shapes, order code, 7 dots), so vision scores are comparable but not identical.
- The code sandbox now uses the plain `python:3.12-slim` image (`SANDBOX_IMAGE`) and copies the files into it, so it works inside the runner container.
- The filler text of the context test is rebuilt from the Python standard library of the runner image; results can differ slightly between Python versions.
- Tested in the cloud without a GPU: the runner container, the phases, the logs and markers, the code sandbox (reference solutions pass, a broken one fails) and the pictures. A full run needs the NVIDIA GPU and the models.
