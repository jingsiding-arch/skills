#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def normalize_samples(payload: object) -> list[dict]:
    if isinstance(payload, dict):
        samples = payload.get("samples", [])
    else:
        samples = payload
    if not isinstance(samples, list):
        raise SystemExit("results payload must be a list or an object with a 'samples' list")
    return [item for item in samples if isinstance(item, dict)]


def iter_evals(sample: dict) -> list[tuple[str, bool]]:
    evals = sample.get("evals", {})
    if isinstance(evals, dict):
        return [(str(name), bool(value)) for name, value in evals.items()]
    if isinstance(evals, list):
        normalized = []
        for item in evals:
            if not isinstance(item, dict):
                continue
            normalized.append((str(item.get("name", "")), bool(item.get("passed", False))))
        return normalized
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Score one experiment from per-sample eval results and update autoresearch logs.")
    parser.add_argument("--run-dir", required=True, help="Path to autoresearch run directory")
    parser.add_argument("--experiment-id", required=True, type=int, help="Experiment number")
    parser.add_argument("--status", required=True, choices=["baseline", "keep", "discard"], help="Experiment outcome")
    parser.add_argument("--description", required=True, help="Short description of the experiment")
    parser.add_argument("--results-file", required=True, help="Path to JSON file with per-sample eval results")
    parser.add_argument("--run-status", default="running", choices=["running", "idle", "complete"], help="Overall run status")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    results_file = Path(args.results_file).expanduser().resolve()
    if not results_file.exists():
        raise SystemExit(f"Results file does not exist: {results_file}")

    payload = json.loads(results_file.read_text(encoding="utf-8"))
    samples = normalize_samples(payload)
    breakdown: dict[str, dict[str, int]] = {}
    score = 0
    max_score = 0

    for sample in samples:
        for name, passed in iter_evals(sample):
            if not name:
                continue
            bucket = breakdown.setdefault(name, {"name": name, "pass_count": 0, "total": 0})
            bucket["total"] += 1
            max_score += 1
            if passed:
                bucket["pass_count"] += 1
                score += 1

    breakdown_list = list(breakdown.values())
    scorecards_dir = run_dir / "scorecards"
    scorecards_dir.mkdir(parents=True, exist_ok=True)
    scorecard_file = scorecards_dir / f"experiment-{args.experiment_id}.json"
    scorecard_payload = {
        "experiment_id": args.experiment_id,
        "score": score,
        "max_score": max_score,
        "pass_rate": 0.0 if max_score == 0 else round((score / max_score) * 100, 1),
        "samples": samples,
        "eval_breakdown": breakdown_list,
    }
    atomic_write(scorecard_file, json.dumps(scorecard_payload, ensure_ascii=False, indent=2) + "\n")

    breakdown_file = scorecards_dir / f"experiment-{args.experiment_id}-breakdown.json"
    atomic_write(breakdown_file, json.dumps(breakdown_list, ensure_ascii=False, indent=2) + "\n")

    log_script = Path(__file__).with_name("log_experiment.py")
    command = [
        sys.executable,
        str(log_script),
        "--run-dir",
        str(run_dir),
        "--experiment-id",
        str(args.experiment_id),
        "--score",
        str(score),
        "--max-score",
        str(max_score),
        "--status",
        args.status,
        "--description",
        args.description,
        "--run-status",
        args.run_status,
        "--eval-breakdown",
        str(breakdown_file),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    print(result.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
