# База результатов тестов моделей

Файл: `llm-results.sqlite` (SQLite, режим WAL). Заполняется автоматически контейнером `ai-report-builder`
каждые ~15 секунд из `bench_results/*.jsonl`. Бенчмаркам ничего менять не нужно. Записи не удаляются:
если бенчмарк перезапишет или удалит свой файл, результаты остаются здесь.

| Таблица | Что хранит |
|---|---|
| `raw_rows` | Каждая исходная строка результатов как есть (`results`, `code_eval`, `fallback`), без дублей. |
| `results` | Актуальный итог по тесту и модели: `suite` = `general` (общий), `german` (немецкий), `context` (длинный контекст). |
| `history` | Все версии результатов: повторный тест не затирает предыдущий, а добавляет запись. |
| `model_scores` | Плоская таблица «одна строка на модель» для SQL и таблиц: итог, русский/логика/код/инструкции/зрение, скорость, VRAM, немецкий, контекст. |
| `meta` | Служебное (время обновления `model_scores`). |

Примеры запросов:

```sql
-- рейтинг по общему тесту
SELECT model, total_pct, tg_tokens_s, vram_peak_mib FROM model_scores ORDER BY total_pct DESC;
-- лучшие по немецкому
SELECT model, german_score, german_n, german_pct FROM model_scores WHERE german_pct IS NOT NULL ORDER BY german_pct DESC;
-- как менялся результат модели
SELECT recorded_utc, suite, json_extract(row_json,'$.total') AS total FROM history WHERE model='Qwen3.5-9B' ORDER BY id;
```
