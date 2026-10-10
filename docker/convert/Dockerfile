# HF -> GGUF converter pinned to the same llama.cpp source as the runtime image (commit 81bc6b8, 2026-09-26).
# Used to turn DFlash draft heads (safetensors) into GGUF:
#   python convert_hf_to_gguf.py <dflash-dir> --target-model-dir <target-config-dir> --outtype q8_0 --outfile <out.gguf>
FROM python:3.12-slim
WORKDIR /opt/llama-convert
COPY requirements ./requirements
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
      torch==2.11.0 "numpy~=2.2.6" "sentencepiece>=0.1.98,<0.3.0" transformers==4.57.6 "protobuf>=4.21.0,<5.0.0" safetensors
COPY gguf-py ./gguf-py
RUN pip install --no-cache-dir ./gguf-py
COPY conversion ./conversion
COPY convert_hf_to_gguf.py ./
ENTRYPOINT ["python", "convert_hf_to_gguf.py"]
