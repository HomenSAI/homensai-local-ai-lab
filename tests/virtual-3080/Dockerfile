# Local AI Lab - (c) 2026 Serhii Khomenko - https://homensai.com/
# Virtual gateway image: stands in for local/ai-server-llama-swap:260 (llama.cpp + llama-swap with CUDA) on a test
# machine without a GPU. Same program paths and entrypoint as the real image; no network needed to build.
FROM python:3.12-slim
COPY fake_llama.py /opt/virtual-3080/fake_llama.py
COPY curl nvidia-smi /usr/local/bin/
RUN chmod 0755 /opt/virtual-3080/fake_llama.py /usr/local/bin/curl /usr/local/bin/nvidia-smi \
 && mkdir -p /app /opt/prism /etc/llama-swap \
 && for p in /app/llama-server /app/llama-bench /opt/prism/llama-server /opt/prism/llama-bench /usr/local/bin/llama-swap; do \
      ln -s /opt/virtual-3080/fake_llama.py "$p"; done
LABEL org.opencontainers.image.title="Local AI Lab virtual RTX 3080 gateway" \
      org.opencontainers.image.description="Test stand-in for llama.cpp and llama-swap; answers are fixed texts, numbers are simulated"
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/llama-swap", "-config", "/etc/llama-swap/config.yaml", "-listen", "0.0.0.0:8080"]
