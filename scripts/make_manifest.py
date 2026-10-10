#!/usr/bin/env python3
"""Writes or checks MANIFEST.json: size and SHA-256 of every file that Git tracks.

  python scripts/make_manifest.py            # rewrite MANIFEST.json
  python scripts/make_manifest.py --check    # exit 1 and list the differences (used by CI)

Text files are hashed with Windows line endings turned into Unix ones, so that the same commit gives the same
manifest on Windows (where Git may check out CRLF) and on Linux. Binary files are hashed as they are.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.json"


def tracked_files() -> list[str]:
    done = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    names = [name for name in done.stdout.decode("utf-8").split("\0") if name]
    return sorted(name for name in names if name != MANIFEST.name and (ROOT / name).is_file())


def describe(path: Path) -> dict:
    data = path.read_bytes()
    if b"\0" not in data:
        data = data.replace(b"\r\n", b"\n")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def build() -> dict:
    return {"files": {name: describe(ROOT / name) for name in tracked_files()}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare with MANIFEST.json instead of writing it")
    args = parser.parse_args()
    fresh = build()
    if not args.check:
        MANIFEST.write_text(json.dumps(fresh, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"{len(fresh['files'])} files -> {MANIFEST.name}")
        return 0
    try:
        stored = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    except (OSError, ValueError, KeyError) as exc:
        print(f"cannot read {MANIFEST.name}: {exc}")
        return 1
    problems = [f"changed: {name}" for name, info in fresh["files"].items() if name in stored and stored[name] != info]
    problems += [f"not in the manifest: {name}" for name in fresh["files"] if name not in stored]
    problems += [f"listed but not tracked: {name}" for name in stored if name not in fresh["files"]]
    for line in problems:
        print(line)
    print("MANIFEST.json is up to date" if not problems else f"{len(problems)} difference(s): run python scripts/make_manifest.py")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
