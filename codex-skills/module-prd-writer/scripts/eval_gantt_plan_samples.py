#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_lark_dev_gantt.py"
SAMPLES = ROOT / "evals" / "gantt_samples.jsonl"


def load_samples() -> list[dict]:
    return [json.loads(line) for line in SAMPLES.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_sample(sample: dict) -> dict:
    plan_path = ROOT / sample["plan"]
    cmd = ["python3", str(SCRIPT), "--plan", str(plan_path), *sample["args"]]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {
            "id": sample["id"],
            "ok": False,
            "failures": [f"Command failed with exit code {result.returncode}", result.stderr[-1000:], result.stdout[-1000:]],
            "passes": [],
        }
    payload = json.loads(result.stdout)
    expect = sample["expect"]
    failures = []
    passes = []

    if payload.get("mode") == expect["mode"]:
        passes.append(f"mode == {expect['mode']}")
    else:
        failures.append(f"Expected mode == {expect['mode']}, got {payload.get('mode')}")

    summary = payload.get("summary", {})
    if summary.get("task_count") == expect["task_count"]:
        passes.append(f"task_count == {expect['task_count']}")
    else:
        failures.append(f"Expected task_count == {expect['task_count']}, got {summary.get('task_count')}")

    if summary.get("module_count") == expect["module_count"]:
        passes.append(f"module_count == {expect['module_count']}")
    else:
        failures.append(f"Expected module_count == {expect['module_count']}, got {summary.get('module_count')}")

    if summary.get("total_effort_days") == expect["total_effort_days"]:
        passes.append(f"total_effort_days == {expect['total_effort_days']}")
    else:
        failures.append(
            f"Expected total_effort_days == {expect['total_effort_days']}, got {summary.get('total_effort_days')}"
        )

    if payload.get("command_count", 0) >= expect["command_count_min"]:
        passes.append(f"command_count >= {expect['command_count_min']}")
    else:
        failures.append(f"Expected command_count >= {expect['command_count_min']}, got {payload.get('command_count')}")

    if payload.get("gantt_view_name") == expect["gantt_view_name"]:
        passes.append(f"gantt_view_name == {expect['gantt_view_name']}")
    else:
        failures.append(
            f"Expected gantt_view_name == {expect['gantt_view_name']}, got {payload.get('gantt_view_name')}"
        )

    return {
        "id": sample["id"],
        "ok": not failures,
        "failures": failures,
        "passes": passes,
    }


def main() -> int:
    results = [run_sample(sample) for sample in load_samples()]
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
