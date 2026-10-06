FROM nvidia/cuda:12.9.1-base-ubuntu22.04@sha256:cfab6d524036220368d0665013dd79ddc8cd3516298dc12f031de62c8481f87e
RUN apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY app.py /app/app.py
USER 65532:65532
EXPOSE 9835
ENTRYPOINT ["python3", "/app/app.py"]
