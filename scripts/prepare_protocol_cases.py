#!/usr/bin/env python3
"""Build a stable server-test case manifest from the user's verified reference bundle.

The archive is preserved verbatim. This file only creates a sidecar manifest so
the same prompts and case IDs can be replayed against each server model.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "test-data" / "reference-bundle" / "server-test-reference-bundle-20260927"
RESULTS = BUNDLE / "results"
OUTPUT = ROOT / "test-data" / "protocol-cases.jsonl"


def verify_source_manifest() -> None:
    manifest = BUNDLE / "SOURCE-MANIFEST-SHA256.txt"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([A-Fa-f0-9]{64})\s+(.+)", line.strip())
        if not match:
            continue
        expected, filename = match.groups()
        path = BUNDLE / filename
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual.lower() != expected.lower():
            raise RuntimeError(f"Source manifest mismatch: {filename}")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def pick_reference(pattern: str) -> Path:
    found = sorted(RESULTS.glob(pattern))
    if len(found) != 1:
        raise RuntimeError(f"Expected one canonical reference for {pattern}, got {[p.name for p in found]}")
    return found[0]


def cases_from_reference(pattern: str, suite: str, duration: int, default_cap: int) -> list[dict]:
    rows = read_jsonl(pick_reference(pattern))
    result: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        # The notebook German log includes a second, paraphrased round. The
        # protocol defines the first 48 canonical cases as the score set; do
        # not treat the round-two paraphrases as additional unique cases.
        if suite == "german_practical" and int(row.get("round") or 1) != 1:
            continue
        prompt = row.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            continue
        source_id = row.get("case_id")
        if not source_id:
            source_id = "prompt_" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
        case_id = str(source_id)
        if case_id in seen:
            continue
        seen.add(case_id)
        result.append({
            "suite": suite,
            "case_id": case_id,
            "sequence": len(result) + 1,
            "messages": [{"role": "user", "content": prompt}],
            "prompt": prompt,
            "max_tokens": int(row.get("max_tokens") or default_cap),
            "expected": row.get("expected"),
            "key": row.get("key"),
            "patterns": row.get("patterns"),
            "category": row.get("category"),
            "label": row.get("label") or row.get("task"),
            "suite_seconds": duration,
            "source_file": pick_reference(pattern).name,
        })
    if not result:
        raise RuntimeError(f"No prompt cases found for {suite}")
    return result


def literal(node: ast.AST, names: dict[str, object]) -> object:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in names:
        return names[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [literal(item, names) for item in node.elts]
        return values if isinstance(node, ast.List) else tuple(values)
    if isinstance(node, ast.Dict):
        return {literal(k, names): literal(v, names) for k, v in zip(node.keys, node.values)}
    raise RuntimeError(f"Unsupported smoke-prompt expression: {ast.dump(node, include_attributes=False)}")


def smoke_cases() -> list[dict]:
    path = BUNDLE / "benchmark-upstream.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    assignments: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"BENCHMARK", "TESTS"}:
                    assignments[target.id] = node.value
    names: dict[str, object] = {}
    names["BENCHMARK"] = literal(assignments["BENCHMARK"], names)
    tests = literal(assignments["TESTS"], names)
    cases = []
    for seq, (name, messages, cap) in enumerate(tests, 1):
        prompt = "\n".join(str(m.get("content", "")) for m in messages)
        cases.append({
            "suite": "technical_smoke", "case_id": "smoke_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_"),
            "sequence": seq, "messages": messages, "prompt": prompt, "max_tokens": int(cap),
            "expected": None, "key": None, "patterns": None, "category": "smoke", "label": name,
            "suite_seconds": None, "source_file": path.name,
        })
    return cases


def official_c1_cases() -> list[dict]:
    path = BUNDLE / "run-goethe-c1-official.ps1"
    source = path.read_text(encoding="utf-8-sig")
    system_match = re.search(r"\$systemPrompt\s*=\s*'([^']*)'", source)
    if not system_match:
        raise RuntimeError("Official C1 system prompt not found in the supplied script")
    cases = []
    for seq, (var, case_id, label, cap) in enumerate([
        ("readPrompt", "official_c1_reading", "Goethe C1 full Lesen", 800),
        ("writePrompt", "official_c1_writing", "Goethe C1 full Schreiben", 1200),
    ], 1):
        match = re.search(rf"\${var}\s*=\s*@\"\r?\n(.*?)\r?\n\"@", source, re.S)
        if not match:
            raise RuntimeError(f"Official C1 prompt not found: ${var}")
        prompt = match.group(1).replace("`\"", '"').strip()
        cases.append({
            "suite": "goethe_c1_official", "case_id": case_id, "sequence": seq,
            "messages": [{"role": "system", "content": system_match.group(1)}, {"role": "user", "content": prompt}],
            "prompt": prompt, "max_tokens": cap, "expected": None, "key": None, "patterns": None,
            "category": "official Goethe C1", "label": label, "suite_seconds": None,
            "source_file": path.name,
        })
    return cases


def main() -> None:
    verify_source_manifest()
    cases = smoke_cases()
    cases.extend(cases_from_reference("german-15min-*-minicpm.jsonl", "german_practical", 900, 420))
    cases.extend(cases_from_reference("goethe_c1-15min-*-minicpm.jsonl", "goethe_c1_15min", 900, 320))
    cases.extend(cases_from_reference("goethe_c2-15min-*-minicpm.jsonl", "goethe_c2_15min", 900, 560))
    cases.extend(cases_from_reference("c2-science-15min-*-minicpm.jsonl", "scientific_c2", 900, 360))
    cases.extend(cases_from_reference("math-10min-*-minicpm.jsonl", "math_10min", 600, 160))
    cases.extend(official_c1_cases())
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as stream:
        for case in cases:
            stream.write(json.dumps(case, ensure_ascii=False) + "\n")
    by_suite: dict[str, int] = {}
    for case in cases:
        by_suite[case["suite"]] = by_suite.get(case["suite"], 0) + 1
    print(json.dumps({"output": str(OUTPUT), "cases": len(cases), "by_suite": by_suite}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
