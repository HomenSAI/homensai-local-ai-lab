# Benchmarks: die Test-Runner

Andere Sprachen: [English](README.md) · [Русский](README.ru.md)

Diese Skripte haben die veröffentlichten Ergebnisse von [rtx3080-local-ai-benchmarks](https://github.com/HomenSAI/rtx3080-local-ai-benchmarks) erzeugt (23 Modelle auf einer RTX 3080 / 10 GB, 2026-09-29 – 2026-10-06). Jenes Repository enthält nur die Ergebnisse; der Code zum Wiederholen der Tests liegt hier.

## Tests, Skripte und Ergebnisdateien

| Test (Ordner im Ergebnis-Repository) | Phase | Runner | Aufgaben | Ergebnisdatei in `bench_results/` |
|---|---|---|---|---|
| 01-general-quality | `general` | `bench_top.py` (Modellliste `TOP`) + `bench_all.py` | `qtasks.py`, 3 Code-Aufgaben aus `coding_tasks.py`, Bilder aus `make_images.py` | `results_all.jsonl` |
| 02-german-passive | `german`, `german_fix` | `german_all.py`, `german_fix.py` (Wiederholung leerer Antworten), `qa_bench.py` | `qa_tasks.py` | `results_german.jsonl`, `results_german_fix.jsonl` |
| 03-max-context | `context` | `bench_ctx.py` + `mneedle.py` (3 versteckte Fakten bei 80 % Füllung) | Fülltext aus der Python-Standardbibliothek | `results_ctx.jsonl`, `results_ctx_trials.jsonl` |
| 04-soak-reliability | `soak` | `soak.py` (über das Gateway auf Port 8080) | Profile aus `config/llama-swap.yaml` | `results_soak.jsonl` |
| 05-math-physics-grade11 | `stem` | `bench_stem.py` | `stem_tasks.py` | `results_stem.jsonl` |
| 06-chemistry-grade11 | `chem` | `bench_chem.py` | `chem_tasks.py` | `results_chem.jsonl` |
| 07-coding-20 | `code20` | `bench_code20.py`, Tests in einer Sandbox ohne Netzwerk (`code_eval_harness.py`) | `coding_tasks.py` | `results_code20.jsonl` |
| 08-accelerators-embeddings | `accel` | `bench_accel.py` | Profile für spekulatives Dekodieren aus `config/llama-swap.yaml`, Embedding-Modelle | `results_accel.jsonl` |

`bench_top.py` und `bench_all.py` enthalten die gemeinsamen Teile: die Modellliste, den Start eines Modells in einem eigenen Container (`bench-srv`, Port 8090, Image `local/ai-server-llama-swap:260`, Modelle aus dem Docker-Volume `llm-models-fast`), den RAM-Wächter und die Prüfer.
Nach dem Kontexttest machen `gen_profiles_from_ctx.py` und `finalize_profiles.py` aus den gemessenen Fenstern Gateway-Profile (`config/llama-swap-ctx.yaml` → `config/llama-swap-final.yaml`; Kandidaten, die erst wirksam werden, wenn Sie sie kopieren); `exclude_not_gpu.md` listet die Modelle auf, die nach der 64K-Regel entfernt wurden.

## Ausführen (alles in Docker)

Bauen Sie zuerst die Gateway-Images (`docs/INSTALL.*`, Abschnitte zum Bauen), legen Sie die Modelle in das Volume `llm-models-fast` und tragen Sie die Pfade in `TOP` von `bench_top.py` ein. Dann:

```
docker compose --profile bench up -d --build bench-runner
```

Der Runner kopiert diese Skripte nach `bench_results/`, zeichnet die Bilder für die Sehaufgaben und führt die Phasen in der Reihenfolge von `BENCH_PHASES` aus (Standard `general german context german_fix accel stem chem code20`; fügen Sie `soak` hinzu, um die Gateway-Profile zu testen). Jede Phase schreibt ihr Protokoll (`bench_full.log`, `bench_ctx.log`, ...) mit der Abschlussmarkierung, die die Konsole erwartet, sodass die Konsole die Phase, den Fortschrittsbalken und die Restzeit anzeigt. Jede Phase überspringt fertige Modelle, sodass ein Neustart dort weitermacht, wo er aufgehört hat. Um andere Phasen auszuführen: `BENCH_PHASES="stem chem"` in `.env`, `bench_results/run_all.log` löschen und den Runner erneut starten. Anhalten mit `docker compose --profile bench stop bench-runner`.

Der Runner steuert Docker auf diesem PC über den Docker-Socket (er startet und stoppt die Modell-Container und das Gateway): Starten Sie ihn nur für einen Testlauf.

## Unterschiede zum veröffentlichten Lauf

- Die Bilder für die Sehaufgaben aus dem veröffentlichten Lauf wurden nicht aufbewahrt; `make_images.py` zeichnet denselben Inhalt neu (Formen, Bestellcode, 7 Punkte), daher sind die Bewertungen für das Sehen vergleichbar, aber nicht identisch.
- Die Code-Sandbox verwendet jetzt das einfache Image `python:3.12-slim` (`SANDBOX_IMAGE`) und kopiert die Dateien hinein, sodass sie im Runner-Container funktioniert.
- Der Fülltext des Kontexttests wird aus der Python-Standardbibliothek des Runner-Images neu aufgebaut; die Ergebnisse können sich zwischen Python-Versionen leicht unterscheiden.
- In der Cloud ohne GPU getestet: der Runner-Container, die Phasen, die Protokolle und Markierungen, die Code-Sandbox (Referenzlösungen bestehen, eine fehlerhafte scheitert) und die Bilder. Ein vollständiger Lauf braucht die NVIDIA-GPU und die Modelle.
