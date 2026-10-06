# Result files and stage plan

A test tool (a script, or an AI supervisor working by hand) talks to the report builder through files in `bench_results/` only. The builder reads `results*.jsonl` every 15 seconds; nothing else has to be called. One JSON object per line, UTF-8, **append only**.

## 1. Result rows (file name decides the kind)

| File | Kind | Required fields | Optional fields |
|---|---|---|---|
| `results_all.jsonl` | general test | `model`, `load_ok` (bool), `quality`: list of `{task, cat, score, max}` (`cat` is one of `Русский`, `Логика`, `Код`, `Инструкции`, `Зрение`) | `file`, `quant`, `size_gb`, `mode`, `ngl`, `placement`, `pp`, `tg`, `vram_peak_8k`, `vram_bench`, `load_s`, `max_ctx`, `ctx`, `host_free_min_gb`, `guard_killed`, `error` |
| `results_german.jsonl` | German | `model`, `score`, `n`, `items`: list of `{cat, ok}` | `tokens`, `minutes`, `mode` |
| `results_ctx.jsonl` | maximum context | `model`, `best_ctx`, `cfgs`: `{config: {best_ctx, tg, vram}}` | `native_ctx`, `cap`, `ref_tg_8k`, `best_cfg`, `recommended_cfg`, `minutes` |
| `results_ctx_trials.jsonl` | single context trials | `model`, `ctx`, `stable` (bool) | `cfg`, `hits`, `pp`, `tg`, `vram_peak` |
| `results_stem.jsonl` | math + physics | `model`, `math`, `phys`, `total`, `n` | `think`, `tokens`, `truncated`, `minutes`, `items` |
| `results_chem.jsonl` | chemistry | `model`, `score` (of 10) | `think`, `truncated`, `minutes`, `items` |
| `results_code20.jsonl` | code, 20 tasks | `model`, `passed`, `n` | `by_level` (`{"1": [passed, total], ...}`), `failed` (task names), `tokens`, `minutes`, `request_errors` |
| `results_accel.jsonl` | accelerators / embeddings | `kind` (`spec` or `embed`), `profile` | `baseline`, `spec_flags`, `dim`, `top1`, `verdict` |
| `results_soak.jsonl` | reliability | `model`, `ctx`, `steps` | `problems`, `vram_peak`, `gpu_util_peak`, `host_free_min_gb`, `load_s` |

A newer row for the same `(suite, model)` replaces the value shown in the report, **the older value stays in the SQLite archive and in Git**. Never edit a line that was already written; append a new one.

Model names must be stable between files: the same `model` string joins the rows of different tests into one line of the table. Names that appear in the model list file `bench_top.py` (`TOP`) define which models belong to the current plan; other names are kept but not counted.

## 2. Stage log and markers

Every stage may have a log `bench_results/<name>.log` (written by the tool):

```
=== <model name> (anything)     # starts a model: the console shows "now testing <model>"
PROGRESS 7/20                   # tasks done of all, before every task: gives an exact progress bar
DONE ... / STEM ... / CTX ...   # one result line per model (free text, shown as "last result")
<NAME>-FINISHED                 # last line: marks the whole stage as done
```

Without `PROGRESS` lines the console estimates progress from the average time per model.

## 3. The stage plan

`scripts/build_live_report.py` defines `DEFAULT_PLAN`; to change it without editing code create `bench_results/benchmark_plan.json`:

```json
{"stages": [
  {"id": "stem", "title": "Math and physics", "per_model": false, "scope": "eligible",
   "results": ["results_stem.jsonl"], "log": "bench_stem.log", "finish_marker": "STEM-FINISHED",
   "after": "accel", "est_minutes_per_model": 6, "what": "short description shown in the console"}
]}
```

| Field | Meaning |
|---|---|
| `id`, `title`, `what`, `note` | identifier, name, description and hint shown in the stage list |
| `results` | result files that count for this stage (rows of other files are ignored here) |
| `log`, `finish_marker` | log file and the line that marks completion |
| `per_model` | true: progress is "models done of all models of the plan" |
| `scope: "eligible"` | the stage counts only models that were not removed by the 64K rule |
| `fixed_total` | stage with a fixed number of items (for example 16 gateway profiles) |
| `est_minutes_per_model`, `est_total_minutes` | estimates used for the "until all tests finish" bar before real timings exist |
| `after` | stage that has to finish first (only shown to the reader) |

Removed models: a model counts as removed when `results_ctx.jsonl` has `best_ctx` below 65536 and the model is not listed in `bench_results/ctx_recheck.txt` (one name per line, for models kept for a re-check).

## 4. The public snapshot

`python scripts/make_public_results.py` writes `results-public/RESULTS.md`, `results-summary.csv` and `results-summary.json` from `report/live-data.json`: aggregated numbers only, no prompts or answers.
