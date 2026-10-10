# Ergebnisdateien und Phasenplan

Andere Sprachen: [English](RESULTS_FORMAT.md) · [Русский](RESULTS_FORMAT.ru.md)

Ein Testwerkzeug (ein Skript oder ein KI-Supervisor, der von Hand arbeitet) kommuniziert mit dem Berichtsgenerator ausschließlich über Dateien in `bench_results/`. Der Generator liest `results*.jsonl` alle 15 Sekunden; sonst muss nichts aufgerufen werden. Ein JSON-Objekt pro Zeile, UTF-8, **nur anhängen**.

## 1. Ergebniszeilen (der Dateiname bestimmt die Art)

| Datei | Art | Pflichtfelder | Optionale Felder |
|---|---|---|---|
| `results_all.jsonl` | Allgemeintest | `model`, `load_ok` (bool), `quality`: Liste von `{task, cat, score, max}` (`cat` ist eines von `Русский`, `Логика`, `Код`, `Инструкции`, `Зрение`); `quality` darf fehlen, wenn `load_ok` `false` ist | `file`, `quant`, `size_gb`, `mode`, `ngl`, `placement`, `pp`, `tg`, `vram_peak_8k`, `vram_bench`, `load_s`, `max_ctx`, `ctx`, `host_free_min_gb`, `guard_killed`, `error` |
| `results_german.jsonl` | Deutsch | `model`, `score`, `n`, `items`: Liste von `{cat, ok}` | `tokens`, `minutes`, `mode` |
| `results_ctx.jsonl` | maximaler Kontext | `model`, `best_ctx`, `cfgs`: `{config: {best_ctx, tg, vram}}` | `native_ctx`, `cap`, `ref_tg_8k`, `best_cfg`, `recommended_cfg`, `minutes` |
| `results_ctx_trials.jsonl` | einzelne Kontextversuche | `model`, `ctx`, `stable` (bool) | `cfg`, `hits`, `pp`, `tg`, `vram_peak` |
| `results_stem.jsonl` | Mathematik + Physik | `model`, `math`, `phys`, `total`, `n` | `think`, `tokens`, `truncated`, `minutes`, `items` |
| `results_chem.jsonl` | Chemie | `model`, `score` (von 10) | `think`, `truncated`, `minutes`, `items` |
| `results_code20.jsonl` | Code, 20 Aufgaben | `model`, `passed`, `n` | `by_level` (`{"1": [passed, total], ...}`), `failed` (Aufgabennamen), `tokens`, `minutes`, `request_errors` |
| `results_accel.jsonl` | Beschleuniger / Embeddings | `kind` (`spec` oder `embed`), `profile` | `baseline`, `spec_flags`, `dim`, `top1`, `verdict` |
| `results_soak.jsonl` | Zuverlässigkeit | `model`, `ctx`, `steps` | `problems`, `vram_peak`, `gpu_util_peak`, `host_free_min_gb`, `load_s` |

Eine neuere Zeile für dasselbe `(suite, model)` ersetzt den im Bericht angezeigten Wert, **der ältere Wert bleibt im SQLite-Archiv und in Git**. Eine bereits geschriebene Zeile nie bearbeiten; eine neue anhängen.

### Modelle, die nicht geladen wurden, und ungültige Punktzahlen

- Ein Modell, das nicht geladen wurde, wird als `{"model": "...", "load_ok": false, "error": "short reason"}` geschrieben. Die Zeile bleibt erhalten: Das Modell erscheint im Bericht und im öffentlichen Snapshot als **nicht geladen** (nie als „zugelassen“). Keine Pfade oder personenbezogenen Daten in `error` schreiben.
- In `quality` muss `score` eine Zahl von 0 bis `max` sein und `max` eine Zahl größer als 0 (ein fehlendes `max` zählt als 1). Der Generator **ignoriert** ein Element, das dagegen verstößt (ein falscher Prüfer würde sonst als 500 % erscheinen), und begrenzt ein `score` über `max` auf `max`. Die Zahl der ignorierten Elemente wird als `invalid_items` in der Modellzeile gespeichert: Taucht sie auf, den Prüfer korrigieren und eine neue Zeile anhängen.
- Zeilen, die kein gültiges JSON sind (eine Zeile, die gerade noch geschrieben wird), werden übersprungen.

Modellnamen müssen zwischen den Dateien gleich bleiben: Derselbe `model`-String führt die Zeilen verschiedener Tests zu einer Tabellenzeile zusammen. Namen, die in der Modelllistendatei `bench_top.py` (`TOP`) stehen, legen fest, welche Modelle zum aktuellen Plan gehören; andere Namen bleiben erhalten, werden aber nicht mitgezählt.

## 2. Phasen-Log und Marken

Jede Phase kann ein Log `bench_results/<name>.log` haben (vom Werkzeug geschrieben):

```
=== <model name> (anything)     # starts a model: the console shows "now testing <model>"
PROGRESS 7/20                   # tasks done of all, before every task: gives an exact progress bar
DONE ... / STEM ... / CTX ...   # one result line per model (free text, shown as "last result")
<NAME>-FINISHED                 # last line: marks the whole stage as done
```

Ohne `PROGRESS`-Zeilen schätzt die Konsole den Fortschritt aus der durchschnittlichen Zeit pro Modell.

## 3. Der Phasenplan

`scripts/build_live_report.py` definiert `DEFAULT_PLAN`; um ihn ohne Codeänderung anzupassen, `bench_results/benchmark_plan.json` anlegen:

```json
{"stages": [
  {"id": "stem", "title": "Math and physics", "per_model": false, "scope": "eligible",
   "results": ["results_stem.jsonl"], "log": "bench_stem.log", "finish_marker": "STEM-FINISHED",
   "after": "accel", "est_minutes_per_model": 6, "what": "short description shown in the console"}
]}
```

| Feld | Bedeutung |
|---|---|
| `id`, `title`, `what`, `note` | Kennung, Name, Beschreibung und Hinweis, die in der Phasenliste angezeigt werden |
| `results` | Ergebnisdateien, die für diese Phase zählen (Zeilen anderer Dateien werden hier ignoriert) |
| `log`, `finish_marker` | Log-Datei und die Zeile, die den Abschluss markiert |
| `per_model` | true: Fortschritt ist „fertige Modelle von allen Modellen des Plans“ |
| `scope: "eligible"` | die Phase zählt nur Modelle, die nicht durch die 64K-Regel entfernt wurden |
| `fixed_total` | Phase mit einer festen Zahl von Elementen (zum Beispiel 16 Gateway-Profile) |
| `est_minutes_per_model`, `est_total_minutes` | Schätzungen für den Balken „bis alle Tests fertig sind“, solange es noch keine echten Zeitmessungen gibt |
| `after` | Phase, die vorher abgeschlossen sein muss (wird nur dem Leser angezeigt) |

Entfernte Modelle: Ein Modell gilt als entfernt, wenn `results_ctx.jsonl` ein `best_ctx` unter 65536 hat und das Modell nicht in `bench_results/ctx_recheck.txt` steht (ein Name pro Zeile, für Modelle, die für eine erneute Prüfung behalten werden).

## 4. Der öffentliche Snapshot

`python scripts/make_public_results.py [OUT_DIR] [--live FILE]` schreibt `results-public/RESULTS.md`, `results-summary.csv` und `results-summary.json` aus `report/live-data.json`: nur aggregierte Zahlen, keine Prompts oder Antworten.
