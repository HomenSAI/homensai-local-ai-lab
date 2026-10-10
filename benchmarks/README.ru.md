# Бенчмарки: раннеры тестов

Другие языки: [English](README.md) · [Deutsch](README.de.md)

Эти скрипты дали опубликованные результаты [rtx3080-local-ai-benchmarks](https://github.com/HomenSAI/rtx3080-local-ai-benchmarks) (23 модели на RTX 3080 / 10 ГБ, 2026-09-29 – 2026-10-06). В том репозитории хранятся только результаты; код, чтобы повторить тесты, — здесь.

## Тесты, скрипты и файлы результатов

| Тест (папка в репозитории результатов) | Этап | Раннер | Задачи | Файл результатов в `bench_results/` |
|---|---|---|---|---|
| 01-general-quality | `general` | `bench_top.py` (список моделей `TOP`) + `bench_all.py` | `qtasks.py`, 3 задачи по коду из `coding_tasks.py`, картинки из `make_images.py` | `results_all.jsonl` |
| 02-german-passive | `german`, `german_fix` | `german_all.py`, `german_fix.py` (повторный прогон пустых ответов), `qa_bench.py` | `qa_tasks.py` | `results_german.jsonl`, `results_german_fix.jsonl` |
| 03-max-context | `context` | `bench_ctx.py` + `mneedle.py` (3 спрятанных факта при заполнении 80 %) | текст-заполнитель из стандартной библиотеки Python | `results_ctx.jsonl`, `results_ctx_trials.jsonl` |
| 04-soak-reliability | `soak` | `soak.py` (через шлюз на порту 8080) | профили из `config/llama-swap.yaml` | `results_soak.jsonl` |
| 05-math-physics-grade11 | `stem` | `bench_stem.py` | `stem_tasks.py` | `results_stem.jsonl` |
| 06-chemistry-grade11 | `chem` | `bench_chem.py` | `chem_tasks.py` | `results_chem.jsonl` |
| 07-coding-20 | `code20` | `bench_code20.py`, тесты в песочнице без сети (`code_eval_harness.py`) | `coding_tasks.py` | `results_code20.jsonl` |
| 08-accelerators-embeddings | `accel` | `bench_accel.py` | профили спекулятивного декодирования из `config/llama-swap.yaml`, модели эмбеддингов | `results_accel.jsonl` |

В `bench_top.py` и `bench_all.py` лежат общие части: список моделей, запуск модели в собственном контейнере (`bench-srv`, порт 8090, образ `local/ai-server-llama-swap:260`, модели из тома Docker `llm-models-fast`), контроль оперативной памяти и чекеры.
После теста контекста `gen_profiles_from_ctx.py` и `finalize_profiles.py` превращают измеренные окна в профили шлюза (`config/llama-swap-ctx.yaml` → `config/llama-swap-final.yaml`; это кандидаты, которые не действуют, пока вы их не скопируете); в `exclude_not_gpu.md` перечислены модели, снятые по правилу 64K.

## Запуск (всё в Docker)

Сначала соберите образы шлюза (`docs/INSTALL.*`, разделы о сборке), положите модели в том `llm-models-fast` и заполните пути в `TOP` файла `bench_top.py`. Затем:

```
docker compose --profile bench up -d --build bench-runner
```

Раннер копирует эти скрипты в `bench_results/`, рисует картинки для задач на зрение и запускает этапы в порядке `BENCH_PHASES` (по умолчанию `general german context german_fix accel stem chem code20`; добавьте `soak`, чтобы проверить профили шлюза). Каждый этап пишет свой журнал (`bench_full.log`, `bench_ctx.log`, ...) с маркером завершения, которого ждёт консоль, поэтому консоль показывает этап, полосу прогресса и оставшееся время. Каждый этап пропускает уже готовые модели, так что после перезапуска работа продолжается с того места, где остановилась. Чтобы запустить другие этапы: `BENCH_PHASES="stem chem"` в `.env`, удалите `bench_results/run_all.log` и снова запустите раннер. Остановить его: `docker compose --profile bench stop bench-runner`.

Раннер управляет Docker на этом ПК через сокет Docker (запускает и останавливает контейнеры моделей и шлюз): запускайте его только на время прогона тестов.

## Отличия от опубликованного прогона

- Картинки для задач на зрение из опубликованного прогона не сохранились; `make_images.py` рисует заново то же содержание (фигуры, код заказа, 7 точек), поэтому оценки зрения сравнимы, но не идентичны.
- Песочница для кода теперь использует обычный образ `python:3.12-slim` (`SANDBOX_IMAGE`) и копирует в него файлы, поэтому работает внутри контейнера раннера.
- Текст-заполнитель теста контекста собирается заново из стандартной библиотеки Python образа раннера; результаты могут немного отличаться между версиями Python.
- Проверено в облаке без GPU: контейнер раннера, этапы, журналы и маркеры, песочница для кода (эталонные решения проходят, сломанное — не проходит) и картинки. Для полного прогона нужны видеокарта NVIDIA и модели.
