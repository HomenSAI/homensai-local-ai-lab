# Виртуальная RTX 3080: проверка всей системы без GPU

Другие языки: [English](README.md) · [Deutsch](README.de.md)

Этот набор ставит Local AI Lab на Linux-машину с Docker, но без видеокарты NVIDIA, и позволяет всем частям работать так, будто стоит RTX 3080 (10 ГБ): шлюз загружает и переключает модели, консоль показывает видеопамять и загрузку GPU, раннер тестов измеряет скорость, контекст и качество, сборщик отчётов, страница хода тестов и версионер Git работают с результатами. **Настоящих моделей нет**: ответы — заготовленные тексты, все числа условные. Набор нужен, чтобы освоить систему, отрепетировать установку или проверить изменения до запуска на настоящей видеокарте. Никогда не ставьте его на компьютер с настоящей видеокартой NVIDIA.

## Что подменено

| Часть | Замена | Файл |
|---|---|---|
| Драйвер NVIDIA в Docker (`--gpus all`, `gpus: all`) | хук с именем, которое ищет Docker; он копирует виртуальную `nvidia-smi` в каждый контейнер с GPU | `nvidia-container-runtime-hook` |
| `nvidia-smi` | «NVIDIA GeForce RTX 3080, 10240 MiB»; занятая память и загрузка берутся от работающих виртуальных серверов моделей | `nvidia-smi` |
| llama.cpp `llama-server`, `llama-bench` и `llama-swap` | одна программа на Python с теми же путями и API (`/health`, `/v1/chat/completions` с `timings`, `/tokenize`, `/slots`, `/metrics`, `/v1/embeddings`, `/v1/models`, `/running`, выгрузка); видеопамять = размер файла + KV-кэш для контекста и типа кэша; модель, которая не помещается, останавливается с «out of memory», как настоящая | `fake_llama.py`, `Dockerfile`, `curl` |
| файлы моделей | разреженные файлы `.gguf` правдоподобного размера (почти не занимают диск) | `make_models.py` |

## Шаги (Linux, Docker Engine, от root или через sudo)

```
# 1. the virtual driver: Docker must find it when it starts
sudo cp tests/virtual-3080/nvidia-container-runtime-hook tests/virtual-3080/nvidia-smi /usr/local/bin/
sudo systemctl restart docker
docker run --rm --gpus all python:3.12-slim nvidia-smi      # must print the RTX 3080 line

# 2. the system, as in the guide (Linux path)
python3 scripts/install.py doctor
python3 scripts/install.py init                              # then set MODEL_DIR in .env to any empty folder
docker build -t local/ai-server-llama-swap:260 tests/virtual-3080    # the virtual gateway instead of the CUDA builds
docker run --rm -v llm-models-fast:/models -v "$PWD":/lab:ro python:3.12-slim \
    python /lab/tests/virtual-3080/make_models.py /lab /models          # the virtual model files
python3 scripts/install.py build --no-gpu                    # console and versioner (the CUDA images are not needed)
python3 scripts/install.py up
python3 scripts/install.py git
python3 scripts/install.py verify                            # every line [ok]

# 3. the tests
docker compose --profile bench up -d --build bench-runner
```

Затем откройте http://localhost:8766/ (консоль), http://localhost:8766/report/progress.html (ход тестов) и http://localhost:3010/ (версии).

Отчёт о проверке 10.10.2026 (на русском языке): [REPORT.ru.md](REPORT.ru.md).

**Как удалить:** `docker compose --profile bench --profile gateway down`, `docker volume rm llm-models-fast`, удалите `/usr/local/bin/nvidia-container-runtime-hook` и `/usr/local/bin/nvidia-smi`, перезапустите Docker.
