#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sync_lark_module_prd_doc.py"
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
    expect = sample["expect"]
    failures = []
    passes = []

    if "mode" in expect:
        actual = payload.get("mode")
        if actual == expect["mode"]:
            passes.append(f"mode == {actual}")
        else:
            failures.append(f"Expected mode == {expect['mode']}, got {actual}")

    if "preflight_ready" in expect:
        actual = payload.get("preflight", {}).get("ready")
        if actual == expect["preflight_ready"]:
            passes.append(f"preflight.ready == {actual}")
        else:
            failures.append(f"Expected preflight.ready == {expect['preflight_ready']}, got {actual}")

    if "label_prefix_style" in expect:
        actual = payload.get("payload", {}).get("label_prefix_style")
        if actual == expect["label_prefix_style"]:
            passes.append(f"label_prefix_style == {actual}")
        else:
            failures.append(f"Expected label_prefix_style == {expect['label_prefix_style']}, got {actual}")

    if "flowchart_mode" in expect:
        actual = payload.get("payload", {}).get("flowchart_mode")
        if actual == expect["flowchart_mode"]:
            passes.append(f"flowchart_mode == {actual}")
        else:
            failures.append(f"Expected flowchart_mode == {expect['flowchart_mode']}, got {actual}")

    if "chunk_count_min" in expect:
        actual = payload.get("payload", {}).get("chunk_count", 0)
        if actual >= expect["chunk_count_min"]:
            passes.append(f"chunk_count >= {expect['chunk_count_min']}")
        else:
            failures.append(f"Expected chunk_count >= {expect['chunk_count_min']}, got {actual}")

    if "final_length_min" in expect:
        actual = payload.get("final_length", 0)
        if actual >= expect["final_length_min"]:
            passes.append(f"final_length >= {expect['final_length_min']}")
        else:
            failures.append(f"Expected final_length >= {expect['final_length_min']}, got {actual}")

    return {
        "id": sample["id"],
        "ok": not failures,
        "failures": failures,
        "warnings": [],
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
