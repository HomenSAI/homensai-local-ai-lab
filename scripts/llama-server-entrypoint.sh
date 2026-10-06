#!/usr/bin/env sh
set -eu

SERVER="${LLAMA_SERVER_BIN:-/app/llama-server}"

if [ "$#" -gt 0 ]; then
    exec "$SERVER" "$@"
fi

set -- \
    --model "${LLAMA_MODEL:?LLAMA_MODEL is required}" \
    --host "${LLAMA_HOST:-0.0.0.0}" \
    --port "${LLAMA_PORT:-8080}" \
    --ctx-size "${LLAMA_CTX_SIZE:-8192}" \
    --n-gpu-layers "${LLAMA_GPU_LAYERS:-all}" \
    --threads "${LLAMA_THREADS:-4}" \
    --threads-batch "${LLAMA_THREADS_BATCH:-8}" \
    --flash-attn "${LLAMA_FLASH_ATTN:-on}" \
    --parallel "${LLAMA_PARALLEL:-1}" \
    --batch-size "${LLAMA_BATCH_SIZE:-512}" \
    --ubatch-size "${LLAMA_UBATCH_SIZE:-128}"

if [ "${LLAMA_JINJA:-1}" = "1" ]; then set -- "$@" --jinja; fi
if [ "${LLAMA_METRICS:-1}" = "1" ]; then set -- "$@" --metrics; fi
if [ -n "${LLAMA_MODEL_ALIAS:-}" ]; then set -- "$@" --alias "$LLAMA_MODEL_ALIAS"; fi
if [ -n "${LLAMA_MMPROJ:-}" ]; then set -- "$@" --mmproj "$LLAMA_MMPROJ"; fi
if [ -n "${LLAMA_CACHE_TYPE_K:-}" ]; then set -- "$@" --cache-type-k "$LLAMA_CACHE_TYPE_K"; fi
if [ -n "${LLAMA_CACHE_TYPE_V:-}" ]; then set -- "$@" --cache-type-v "$LLAMA_CACHE_TYPE_V"; fi
if [ -n "${LLAMA_TEMPERATURE:-}" ]; then set -- "$@" --temp "$LLAMA_TEMPERATURE"; fi
if [ -n "${LLAMA_TOP_P:-}" ]; then set -- "$@" --top-p "$LLAMA_TOP_P"; fi
if [ -n "${LLAMA_TOP_K:-}" ]; then set -- "$@" --top-k "$LLAMA_TOP_K"; fi
if [ -n "${LLAMA_MIN_P:-}" ]; then set -- "$@" --min-p "$LLAMA_MIN_P"; fi

SPEC_TYPE="${LLAMA_SPEC_TYPE:-none}"
if [ "$SPEC_TYPE" != "none" ]; then
    set -- "$@" --spec-type "$SPEC_TYPE"
    if [ -n "${LLAMA_SPEC_DRAFT_MODEL:-}" ]; then
        set -- "$@" --spec-draft-model "$LLAMA_SPEC_DRAFT_MODEL"
    fi
    if [ -n "${LLAMA_SPEC_DRAFT_N_MAX:-}" ]; then
        set -- "$@" --spec-draft-n-max "$LLAMA_SPEC_DRAFT_N_MAX"
    fi
    if [ -n "${LLAMA_SPEC_DRAFT_NGL:-}" ]; then
        set -- "$@" --spec-draft-ngl "$LLAMA_SPEC_DRAFT_NGL"
    fi
fi

exec "$SERVER" "$@"
