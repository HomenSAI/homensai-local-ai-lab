#!/usr/bin/env python3
"""Verify Qwen Image asset sizes, pinned HF revisions and local SHA256 values."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ASSETS = [
    ("diffusion Q5_K_M", "qwen-image-2.1-Q5_K_M.gguf", 5_390_223_072,
     "2c31ccd392b367a6637841a143813320a02dff55"),
    ("Qwen3-VL encoder Q4_K_M", "text_encoder/Qwen3VL-8B-Instruct-Q4_K_M.gguf", 5_027_784_800,
     "f982a07559d4a2f6c8744d840bf6fccab30eea96"),
    ("Qwen3-VL edit mmproj F16", "text_encoder/mmproj-Qwen3VL-8B-Instruct-F16.gguf", 1_159_029_824,
     "f982a07559d4a2f6c8744d840bf6fccab30eea96"),
    ("Qwen Image 2.1 VAE BF16", "vae/qwen_image_2.1_vae_bf16.safetensors", 675_509_688,
     "9a44dbdb47cefd046be9c0a13476192f34c8db8e"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as f:
        while block := f.read(16 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def safe_metadata_path(root: Path, relative: str) -> Path:
    p = Path(relative)
    # HF local-dir caches retain the selected local-dir root and repository-relative filename.
    if p.parts[0] == "text_encoder":
        return root / "text_encoder" / ".cache" / "huggingface" / "download" / (p.name + ".metadata")
    return root / ".cache" / "huggingface" / "download" / (p.as_posix() + ".metadata")


def safetensors_header(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        size = int.from_bytes(f.read(8), "little")
        if size <= 0 or size > 16 * 1024 * 1024:
            raise ValueError(f"Unexpected safetensors header length: {size}")
        doc = json.loads(f.read(size).decode("utf-8"))
    return {"header_bytes": size, "tensor_count": sum(k != "__metadata__" for k in doc),
            "metadata": doc.get("__metadata__", {})}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", type=Path, default=Path(r"<ROOT>\Qwen-Image-2.1"))
    parser.add_argument("--only", action="append", help="verify only this exact asset label (repeatable)")
    args = parser.parse_args()
    results = []
    errors = []
    for label, rel, expected_size, expected_rev in ASSETS:
        if args.only and label not in args.only:
            continue
        path = args.model_root / rel
        meta_path = safe_metadata_path(args.model_root, rel)
        if not path.is_file() or not meta_path.is_file():
            errors.append(f"missing file or Hugging Face local metadata: {path}")
            continue
        lines = meta_path.read_text(encoding="utf-8").splitlines()
        if len(lines) < 2:
            errors.append(f"malformed Hugging Face metadata: {meta_path}")
            continue
        pinned_rev, expected_sha = lines[0].strip(), lines[1].strip().lower()
        actual_sha = sha256(path)
        row = {"name": label, "path": str(path), "bytes": path.stat().st_size,
               "expected_bytes": expected_size, "sha256": actual_sha,
               "hub_etag_sha256": expected_sha, "revision": pinned_rev,
               "expected_revision": expected_rev,
               "verified": path.stat().st_size == expected_size and actual_sha == expected_sha and pinned_rev == expected_rev}
        if path.suffix == ".safetensors":
            row["safetensors_header"] = safetensors_header(path)
        results.append(row)
        if not row["verified"]:
            errors.append(f"size/hash/revision mismatch: {path}")
    print(json.dumps({"model_root": str(args.model_root), "assets": results, "errors": errors},
                     ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
