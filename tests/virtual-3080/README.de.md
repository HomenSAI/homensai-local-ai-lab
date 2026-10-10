# Virtuelle RTX 3080: das ganze System ohne GPU testen

Andere Sprachen: [English](README.md) · [Русский](README.ru.md)

Dieses Paket installiert Local AI Lab auf einem Linux-Rechner mit Docker, aber ohne NVIDIA-Karte, und lässt alle Teile so laufen, als wäre eine RTX 3080 (10 GB) vorhanden: Das Gateway lädt und wechselt Modelle, die Konsole zeigt Videospeicher und GPU-Last, der Test-Runner misst Geschwindigkeit, Kontext und Qualität, der Berichtsgenerator, die Fortschrittsseite und der Git-Versionierer arbeiten mit den Ergebnissen. **Kein Modell ist echt**: Die Antworten sind feste Texte und alle Zahlen sind simuliert. Nutzen Sie es, um das System kennenzulernen, eine Installation zu proben oder Änderungen zu testen, bevor Sie sie auf der echten Karte ausführen. Installieren Sie es nie auf einem Computer mit einer echten NVIDIA-GPU.

## Was simuliert wird

| Teil | Ersatz | Datei |
|---|---|---|
| NVIDIA-Treiber in Docker (`--gpus all`, `gpus: all`) | ein Hook mit dem Namen, nach dem Docker sucht; er kopiert das virtuelle `nvidia-smi` in jeden GPU-Container | `nvidia-container-runtime-hook` |
| `nvidia-smi` | „NVIDIA GeForce RTX 3080, 10240 MiB“; belegter Speicher und Last stammen von den laufenden virtuellen Modellservern | `nvidia-smi` |
| llama.cpp `llama-server`, `llama-bench` und `llama-swap` | ein Python-Programm mit denselben Pfaden und APIs (`/health`, `/v1/chat/completions` mit `timings`, `/tokenize`, `/slots`, `/metrics`, `/v1/embeddings`, `/v1/models`, `/running`, Entladen); Videospeicher = Dateigröße + KV-Cache für den Kontext und den Cache-Typ; ein Modell, das nicht passt, bricht wie das echte mit „out of memory“ ab | `fake_llama.py`, `Dockerfile`, `curl` |
| Modelldateien | Sparse-Dateien `.gguf` mit plausiblen Größen (sie belegen fast keinen Speicherplatz) | `make_models.py` |

## Schritte (Linux, Docker Engine, als root oder mit sudo)

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

Öffnen Sie dann http://localhost:8766/ (Konsole), http://localhost:8766/report/progress.html (Testfortschritt) und http://localhost:3010/ (Versionen).

Testbericht vom 10.10.2026 (auf Russisch): [REPORT.ru.md](REPORT.ru.md).

**Entfernen:** `docker compose --profile bench --profile gateway down`, `docker volume rm llm-models-fast`, `/usr/local/bin/nvidia-container-runtime-hook` und `/usr/local/bin/nvidia-smi` löschen, Docker neu starten.
