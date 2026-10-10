# HTTP-интерфейсы (для операторов и ИИ-супервизоров)

Другие языки: [English](API.md) · [Deutsch](API.de.md)

Всё, что описано ниже, — обычный HTTP на локальной машине. У шлюза нет аутентификации: используйте только `127.0.0.1` или доверенную локальную сеть. Замените `localhost` на LAN-адрес, если вы открыли консоль в сеть (см. `AI_CONSOLE_BIND_IP`).

## Правила, которым должен следовать каждый запрос к консоли

Консоль проверяет каждый запрос (см. [SECURITY.ru.md](../SECURITY.ru.md)); скрипт или ИИ-супервизор обязан их соблюдать:

| Правило | Подробности |
|---|---|
| Заголовок `Host` | `localhost`, IP-адрес или имя из `AI_CONSOLE_ALLOWED_HOSTS`; иначе `421`. `/health` не проверяется |
| Пароль | Если задан `AI_CONSOLE_PASSWORD`, отправляйте учётные данные HTTP Basic (имя пользователя любое): `curl -u any:PASSWORD ...`; иначе `401`. `/health` не проверяется |
| Тип содержимого `POST` | **Всегда** `Content-Type: application/json`, в том числе для вызовов без тела (`/api/timer/cancel`); иначе `415`. С `curl` используйте `-H "Content-Type: application/json"` |
| Источник `POST` | Скрипты не отправляют заголовок `Origin`, и это нормально. Запрос браузера с другого источника получает `403` |
| Тело | Объект JSON. Пустое или слишком большое: `413`; недопустимый JSON или не объект: `400` |
| Методы | Только `GET` и `POST` (`HEAD`, `OPTIONS` отвечают `501`); консоль никогда не отправляет заголовки CORS |

Каждый ответ содержит `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` и `Referrer-Policy: no-referrer`. Ответы с ошибкой имеют вид `{"error": "..."}`.

```
curl -X POST http://localhost:8766/api/start -H "Content-Type: application/json" -d '{"model_key":"MiniCPM5-2B-Q8_0"}'
```

## Шлюз — совместимый с OpenAI, порт 8080

| Метод и путь | Назначение |
|---|---|
| `GET /v1/models` | профили моделей из `config/llama-swap.yaml` |
| `POST /v1/chat/completions` | чат; `"model"` — имя профиля; первый запрос к модели загружает её (до минуты). Ответ содержит `usage` и, от llama.cpp, `timings` (`prompt_per_second`, `predicted_per_second`, `prompt_n`, `predicted_n`) |
| `POST /v1/embeddings` | эмбеддинги с профилями `Qwen3-Embedding-*` |
| `GET /running` | модели, загруженные сейчас: `{"running": [...]}` |
| `POST /api/models/unload` | выгрузить все модели; `POST /api/models/unload/<model>` выгружает одну |
| `GET /health` | состояние шлюза |

Подойдёт любой OpenAI SDK с `base_url="http://localhost:8080/v1"` и произвольным ключом API. Чтобы отключить размышление у моделей, которые его поддерживают, добавьте в запрос `"chat_template_kwargs": {"enable_thinking": false}`.

```
curl http://localhost:8080/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"MiniCPM5-2B-Q8_0","messages":[{"role":"user","content":"Say hello in one word"}],"max_tokens":16,"temperature":0}'
```

## Консоль — порт 8766

| Метод и путь | Назначение |
|---|---|
| `GET /health` | `{"ok": true}` (не требует пароля и известного `Host`) |
| `GET /api/version` | `{"name", "version", "author", "url", "repo"}` |
| `GET /api/status` | состояние Docker и GPU, модели в памяти (`active_models`), контейнеры `host_ai`, `issues` (в исправной системе должен быть пуст), выполняемое задание |
| `GET /api/models` | каталог с наличием файла (`exists`), размером, контекстом, квантованием, настроенными параметрами |
| `POST /api/start` | тело `{"model_key": "<profile>"}`: загружает модель в видеопамять; возвращает `{"job_id"}`; опрашивайте `GET /api/jobs/<job_id>`, пока `status` не станет `complete` или `error` |
| `POST /api/unload` | тело `{"model_key": "<profile>"}`: выгружает одну модель |
| `POST /api/chat` | тело `{"model_key", "payload": {OpenAI chat request}}`: то же, что шлюз, но с защитой видеопамяти |
| `GET /api/timer`, `POST /api/timer` `{"seconds": 900}`, `POST /api/timer/cancel` | таймер выгрузки всех моделей |
| `GET /api/tests` | все результаты тестов, сведённые по моделям, план этапов (`plan.stages`, `plan.overall`), список наборов тестов; именно это показывает таблица консоли |
| `GET /report/` | страница отчёта; `GET /report/live-data.json` — её данные |
| `GET /legal/<file>` | файлы лицензий и уведомлений |

`/api/start` и `/api/chat` отвечают `409`, пока контейнер Video Studio держит видеокарту.

## Данные отчёта

- `report/live-data.json` — каждые 15 секунд записывается сборщиком отчёта: `entries` (по одной на модель с блоками `general`, `german`, `context`, `stem`, `chem`, `code20`), `plan` (этапы, прогресс, оставшееся время), `suites`, `status`.
- `results-db/llm-results.sqlite` — архив (`raw_rows`, `results`, `history`, `model_scores`); открывайте его только для чтения.
- Git: локальный Gitea (`http://localhost:3010/`) хранит каждую версию отчёта в виде тегов `vNNNN`, `stage-<id>-done`, `final-<date>`.

## Файлы, которые пишет оператор

Инструменты тестов пишут `bench_results/results_*.jsonl` и `bench_results/<stage>.log`: см. [RESULTS_FORMAT.ru.md](RESULTS_FORMAT.ru.md).
