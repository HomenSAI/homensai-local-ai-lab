# How the results were obtained

Other languages: [Русский](METHODOLOGY.ru.md) · [Deutsch](METHODOLOGY.de.md) · The numbers: [results-public/RESULTS.md](../results-public/RESULTS.md)

## The chain: core -> supervisor -> results -> this repository

```
 server core                      supervisor                         results                           published
 gateway (llama-swap + llama.cpp) Claude (Anthropic, Claude Code     bench_results/results*.jsonl      this repository:
 console, report builder,         sessions on the same PC, working   -> report builder -> SQLite       code, docs, results-public/
 Git versioner                    under the author's direction)      archive + live report             (Git tags v0001 ... final-<date>)
 [this repository, code]          prepares, runs and checks tests    -> local Gitea versions
```

1. **Server core** - the code in this repository: the llama-swap gateway on top of pinned llama.cpp builds, the console, the report builder that merges result files without deleting older results, the versioner that commits every report version to Git. It does not judge anything by itself.
2. **Supervisor** - Claude, used as a coding and operations assistant on the author's PC (see [AI_OPERATOR.en.md](AI_OPERATOR.en.md)). Under the author's direction it wrote and adapted the test scripts, ran them against the gateway one model at a time, watched the runs, repeated suspicious ones, parsed the result files and wrote the reports and conclusions.
3. **Results** - one JSON line per model and test in `bench_results/results*.jsonl` (format: [RESULTS_FORMAT.md](RESULTS_FORMAT.md)); the report builder turns them into the live report and an SQLite archive; the versioner commits every change to the local Gitea.
4. **Publication** - [results-public/](../results-public/) is generated from the live data by `scripts/make_public_results.py` (no raw prompts or answers) and published together with the code.

## Rules set by the author (they shape every number)

- **GPU only.** A model that only works by spilling into RAM/CPU (1-3 tokens/s) is not counted as working.
- **Stable GPU context of at least 64K** is required to take part in the later stages. 23 models went through the first stages; 8 did not reach 64K on the GPU and were removed from the later tests (they are listed in the table with the reason); 15 were admitted.
- **One model in video memory at a time**; the gateway swaps models, the supervisor never runs two GPU jobs together.
- **Nothing is overwritten**: a repeated test adds a new row; the archive and Git keep the earlier values.

## What was measured (stages in the order they ran)

| Stage | What it measures |
|---|---|
| General test (8K context) | Russian language, logic, code, instruction following, vision; prompt and generation speed, video memory peak |
| German: passive | 30 forms of the German passive, exact-answer check |
| Maximum stable context | the largest window at which the server starts, finds 3 of 3 hidden facts at 80% fill and keeps its speed; KV cache tried on the GPU as f16, q8 and q4 |
| Accelerators and embeddings | speed with and without MTP, DFlash or a draft model (14 profiles); two embedding models |
| Math and physics, grade 11 | 40 generated tasks (20 + 20) with a computed answer; some models also with thinking enabled |
| Reliability (soak) | every gateway profile goes through a series of steps: start, answers at different context sizes, video memory peak, free host memory |
| Code, 20 tasks | 20 programming tasks in three difficulty levels, checked by running tests |
| Chemistry, grade 11 | 10 tasks with a computed answer |
| Final profiles and report | measured contexts are moved into the gateway profiles and verified |

Environment: NVIDIA GeForce RTX 3080 (10 GB), Windows 10 + Docker Desktop (WSL2), llama.cpp commit `81bc6b83f827df746eb129235488d325c49cae52`, PrismML fork `adfffbe41b2cabcd51fff326ab045662265062bb` (Bonsai model only), llama-swap v260. The runs took place between 2026-09-30 and 2026-10-06.

## Limits you should know

- **One machine, small task sets.** 10-40 tasks per test: differences of a few percent are noise. The tables are a guide, not a ranking of model quality.
- **Tests were written and checked by an AI supervisor.** A checker can contain a mistake; the supervisor looked for tasks that every model fails (a sign of a wrong checker) and repeated suspicious runs, but no human re-graded every answer.
- **Tasks are generated or written by us**, not copied from public benchmarks; they are therefore not comparable with published leaderboards.
- **Settings matter**: quantization, context size, KV-cache type and thinking mode are part of every result; they are stored in the rows and in `config/llama-swap.yaml`.
- **The benchmark scripts themselves are not part of this release** (they still contain machine-specific paths); the result files, their format and the stage plan are, so any tool can produce comparable rows.

## Linking a copy of the repository to the results

If you publish a fork, put its address into `.env` as `PUBLIC_REPO_URL=https://github.com/HomenSAI/homensai-local-ai-lab`: the console and report footers then show a "GitHub" link and the console reports it in `/api/version`.
