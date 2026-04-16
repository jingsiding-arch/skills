#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_lark_doc_from_md.py"
SAMPLES = ROOT / "evals" / "samples.jsonl"


def load_samples() -> list[dict]:
    return [json.loads(line) for line in SAMPLES.read_text(encoding="utf-8").splitlines()]


def run_sample(sample: dict) -> dict:
    input_path = ROOT / sample["input"]
    cmd = ["python3", str(SCRIPT), "--input", str(input_path), *sample["args"]]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {
            "id": sample["id"],
            "ok": False,
            "failures": [f"Command failed with exit code {result.returncode}", result.stderr[-1000:]],
            "warnings": [],
            "passes": [],
        }
    payload = json.loads(result.stdout)
    failures = []
    passes = []
    warnings = []
    expect = sample["expect"]

    if expect.get("preflight_ready") is not None:
        actual = payload.get("preflight", {}).get("ready")
        if actual == expect["preflight_ready"]:
            passes.append(f"preflight.ready == {actual}")
        else:
            failures.append(f"Expected preflight.ready == {expect['preflight_ready']}, got {actual}")

    if "beautify_mode" in expect:
        actual = payload.get("beautify_mode")
        if actual == expect["beautify_mode"]:
            passes.append(f"beautify_mode == {actual}")
        else:
            failures.append(f"Expected beautify_mode == {expect['beautify_mode']}, got {actual}")

    if "beautify_reason_contains" in expect:
        reason = payload.get("beautify_mode_reason", "")
        if expect["beautify_reason_contains"] in reason:
            passes.append("beautify_mode_reason contains expected text")
        else:
            failures.append(f"beautify_mode_reason missing `{expect['beautify_reason_contains']}`")

    if "omit_section_titles_applied" in expect:
        actual = payload.get("omit_section_titles_applied", [])
        if actual == expect["omit_section_titles_applied"]:
            passes.append("omit_section_titles_applied matches")
        else:
            failures.append(f"Expected omit_section_titles_applied == {expect['omit_section_titles_applied']}, got {actual}")

    if "flowchart_mode" in expect:
        actual = payload.get("flowchart_mode")
        if actual == expect["flowchart_mode"]:
            passes.append(f"flowchart_mode == {actual}")
        else:
            failures.append(f"Expected flowchart_mode == {expect['flowchart_mode']}, got {actual}")

    if "chunk_count_min" in expect:
        actual = payload.get("chunk_count", 0)
        if actual >= expect["chunk_count_min"]:
            passes.append(f"chunk_count >= {expect['chunk_count_min']}")
        else:
            failures.append(f"Expected chunk_count >= {expect['chunk_count_min']}, got {actual}")

    return {
        "id": sample["id"],
        "ok": not failures,
        "failures": failures,
        "warnings": warnings,
        "passes": passes,
    }


def main() -> int:
    samples = load_samples()
    results = [run_sample(sample) for sample in samples]
    summary = {
        "ok": all(item["ok"] for item in results),
        "sample_count": len(results),
        "passed": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
