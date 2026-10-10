# Файлы результатов и план этапов

Другие языки: [English](RESULTS_FORMAT.md) · [Deutsch](RESULTS_FORMAT.de.md)

Инструмент тестирования (скрипт или ИИ-супервизор, работающий вручную) общается со сборщиком отчёта только через файлы в `bench_results/`. Сборщик читает `results*.jsonl` каждые 15 секунд; больше ничего вызывать не нужно. Один JSON-объект на строку, UTF-8, **только дописывать**.

## 1. Строки результатов (вид определяется именем файла)

| Файл | Вид | Обязательные поля | Необязательные поля |
|---|---|---|---|
| `results_all.jsonl` | общий тест | `model`, `load_ok` (bool), `quality`: список `{task, cat, score, max}` (`cat` — одно из `Русский`, `Логика`, `Код`, `Инструкции`, `Зрение`); `quality` можно не указывать, если `load_ok` равно `false` | `file`, `quant`, `size_gb`, `mode`, `ngl`, `placement`, `pp`, `tg`, `vram_peak_8k`, `vram_bench`, `load_s`, `max_ctx`, `ctx`, `host_free_min_gb`, `guard_killed`, `error` |
| `results_german.jsonl` | немецкий язык | `model`, `score`, `n`, `items`: список `{cat, ok}` | `tokens`, `minutes`, `mode` |
| `results_ctx.jsonl` | максимальный контекст | `model`, `best_ctx`, `cfgs`: `{config: {best_ctx, tg, vram}}` | `native_ctx`, `cap`, `ref_tg_8k`, `best_cfg`, `recommended_cfg`, `minutes` |
| `results_ctx_trials.jsonl` | отдельные пробы контекста | `model`, `ctx`, `stable` (bool) | `cfg`, `hits`, `pp`, `tg`, `vram_peak` |
| `results_stem.jsonl` | математика + физика | `model`, `math`, `phys`, `total`, `n` | `think`, `tokens`, `truncated`, `minutes`, `items` |
| `results_chem.jsonl` | химия | `model`, `score` (из 10) | `think`, `truncated`, `minutes`, `items` |
| `results_code20.jsonl` | код, 20 задач | `model`, `passed`, `n` | `by_level` (`{"1": [passed, total], ...}`), `failed` (имена задач), `tokens`, `minutes`, `request_errors` |
| `results_accel.jsonl` | ускорители / эмбеддинги | `kind` (`spec` или `embed`), `profile` | `baseline`, `spec_flags`, `dim`, `top1`, `verdict` |
| `results_soak.jsonl` | надёжность | `model`, `ctx`, `steps` | `problems`, `vram_peak`, `gpu_util_peak`, `host_free_min_gb`, `load_s` |

Более новая строка для той же пары `(suite, model)` заменяет значение, показанное в отчёте, **прежнее значение остаётся в архиве SQLite и в Git**. Никогда не редактируйте уже записанную строку; дописывайте новую.

### Модели, которые не загрузились, и недопустимые баллы

- Модель, которая не загрузилась, записывается как `{"model": "...", "load_ok": false, "error": "short reason"}`. Строка сохраняется: модель появляется в отчёте и в публичном снимке как **не загрузилась** (никогда как «допущена»). Не помещайте в `error` пути и личные данные.
- В `quality` значение `score` должно быть числом от 0 до `max`, а `max` — числом больше 0 (отсутствующий `max` считается равным 1). Сборщик **игнорирует** элемент, который нарушает это правило (иначе ошибочная проверка показала бы 500 %), и ограничивает `score` больше `max` значением `max`. Число проигнорированных элементов сохраняется как `invalid_items` в строке модели: если оно появилось, исправьте проверку и допишите новую строку.
- Строки, которые не являются корректным JSON (строка, которая ещё записывается), пропускаются.

Имена моделей должны быть одинаковыми во всех файлах: одна и та же строка `model` объединяет строки разных тестов в одну строку таблицы. Имена, которые есть в файле списка моделей `bench_top.py` (`TOP`), определяют, какие модели входят в текущий план; остальные имена сохраняются, но не учитываются.

## 2. Журнал этапа и маркеры

У каждого этапа может быть журнал `bench_results/<name>.log` (его пишет инструмент):

```
=== <model name> (anything)     # starts a model: the console shows "now testing <model>"
PROGRESS 7/20                   # tasks done of all, before every task: gives an exact progress bar
DONE ... / STEM ... / CTX ...   # one result line per model (free text, shown as "last result")
<NAME>-FINISHED                 # last line: marks the whole stage as done
```

Без строк `PROGRESS` консоль оценивает прогресс по среднему времени на модель.

## 3. План этапов

`scripts/build_live_report.py` задаёт `DEFAULT_PLAN`; чтобы изменить его, не правя код, создайте `bench_results/benchmark_plan.json`:

```json
{"stages": [
  {"id": "stem", "title": "Math and physics", "per_model": false, "scope": "eligible",
   "results": ["results_stem.jsonl"], "log": "bench_stem.log", "finish_marker": "STEM-FINISHED",
   "after": "accel", "est_minutes_per_model": 6, "what": "short description shown in the console"}
]}
```

| Поле | Значение |
|---|---|
| `id`, `title`, `what`, `note` | идентификатор, название, описание и подсказка, показываемые в списке этапов |
| `results` | файлы результатов, которые учитываются для этого этапа (строки других файлов здесь игнорируются) |
| `log`, `finish_marker` | файл журнала и строка, отмечающая завершение |
| `per_model` | true: прогресс — «готово моделей из всех моделей плана» |
| `scope: "eligible"` | этап учитывает только модели, которые не были сняты по правилу 64K |
| `fixed_total` | этап с фиксированным числом элементов (например, 16 профилей шлюза) |
| `est_minutes_per_model`, `est_total_minutes` | оценки, используемые для полосы «до окончания всех тестов», пока нет реальных замеров времени |
| `after` | этап, который должен завершиться раньше (только показывается читателю) |

Снятые модели: модель считается снятой, если в `results_ctx.jsonl` значение `best_ctx` меньше 65536 и модели нет в `bench_results/ctx_recheck.txt` (одно имя на строку, для моделей, оставленных для повторной проверки).

## 4. Публичный снимок

`python scripts/make_public_results.py [OUT_DIR] [--live FILE]` записывает `results-public/RESULTS.md`, `results-summary.csv` и `results-summary.json` из `report/live-data.json`: только агрегированные числа, без промптов и ответов.
