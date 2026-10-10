#!/usr/bin/env python3
"""Read GGUF header/metadata only; tensor payloads are not loaded."""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import BinaryIO, Any

FMT = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f",
       7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
SIZE = {k: struct.calcsize(v) for k, v in FMT.items()}
KEEP_SUFFIXES = ("architecture", "name", "file_type", "quantization_version", "context_length",
                 "block_count", "embedding_length", "feed_forward_length", "head_count",
                 "head_count_kv", "rope.dimension_count", "vocab_size")


def read_exact(f: BinaryIO, count: int) -> bytes:
    data = f.read(count)
    if len(data) != count:
        raise EOFError(f"Unexpected EOF: requested {count} bytes, got {len(data)}")
    return data


def scalar(f: BinaryIO, kind: int) -> Any:
    if kind == 8:
        size = struct.unpack("<Q", read_exact(f, 8))[0]
        return read_exact(f, size).decode("utf-8", errors="replace")
    if kind not in FMT:
        raise ValueError(f"Unknown GGUF metadata type {kind}")
    return struct.unpack(FMT[kind], read_exact(f, SIZE[kind]))[0]


def discard(f: BinaryIO, kind: int) -> None:
    if kind == 8:
        size = struct.unpack("<Q", read_exact(f, 8))[0]
        f.seek(size, 1)
    elif kind in FMT:
        f.seek(SIZE[kind], 1)
    else:
        raise ValueError(f"Unknown GGUF metadata type {kind}")


def parse(path: Path) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    with path.open("rb") as f:
        if read_exact(f, 4) != b"GGUF":
            raise ValueError(f"Not a GGUF file: {path}")
        version, = struct.unpack("<I", read_exact(f, 4))
        tensor_count, = struct.unpack("<Q", read_exact(f, 8))
        metadata_count, = struct.unpack("<Q", read_exact(f, 8))
        for _ in range(metadata_count):
            key_len, = struct.unpack("<Q", read_exact(f, 8))
            key = read_exact(f, key_len).decode("utf-8", errors="replace")
            kind, = struct.unpack("<I", read_exact(f, 4))
            keep = key.startswith("general.") or key.endswith(KEEP_SUFFIXES)
            if kind == 9:
                item_type, = struct.unpack("<I", read_exact(f, 4))
                count, = struct.unpack("<Q", read_exact(f, 8))
                if keep and item_type in FMT and count <= 4096:
                    value = [scalar(f, item_type) for _ in range(count)]
                else:
                    for _ in range(count):
                        discard(f, item_type)
                    value = f"<array:{count} type:{item_type}>"
            else:
                value = scalar(f, kind) if keep else (discard(f, kind) or None)
            if keep:
                selected[key] = value
    return {"path": str(path), "size_bytes": path.stat().st_size, "gguf_version": version,
            "tensor_count": tensor_count, "metadata_count": metadata_count, "metadata": selected}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.files:
        print(json.dumps(parse(path), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
