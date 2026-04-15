#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDNAMES = ["experiment", "score", "max_score", "pass_rate", "status", "description"]


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def load_experiments(results_tsv: Path) -> list[dict]:
    if not results_tsv.exists():
        return []
    with results_tsv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return list(reader)


def dump_experiments(results_tsv: Path, rows: list[dict]) -> None:
    with results_tsv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def parse_breakdown(raw: str | None) -> list[dict] | None:
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    if raw.startswith("{") or raw.startswith("["):
        return json.loads(raw)
    candidate = Path(raw).expanduser()
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    return json.loads(raw)


def load_payload(results_json: Path) -> dict:
    if not results_json.exists():
        raise SystemExit(f"results.json not found in {results_json.parent}")
    text = results_json.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Log one autoresearch experiment and refresh results.json.")
    parser.add_argument("--run-dir", required=True, help="Path to autoresearch-<skill-name> directory")
    parser.add_argument("--experiment-id", required=True, type=int, help="Experiment number")
    parser.add_argument("--score", required=True, type=int, help="Achieved score")
    parser.add_argument("--max-score", required=True, type=int, help="Max possible score")
    parser.add_argument("--status", required=True, choices=["baseline", "keep", "discard"], help="Outcome status")
    parser.add_argument("--description", required=True, help="Short mutation description")
    parser.add_argument("--run-status", default="running", choices=["running", "idle", "complete"], help="Overall run status")
    parser.add_argument("--eval-breakdown", default=None, help="JSON string or path to JSON file for eval breakdown")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    results_tsv = run_dir / "results.tsv"
    results_json = run_dir / "results.json"

    pass_rate = 0.0 if args.max_score == 0 else (args.score / args.max_score) * 100
    row = {
        "experiment": str(args.experiment_id),
        "score": str(args.score),
        "max_score": str(args.max_score),
        "pass_rate": f"{pass_rate:.1f}%",
        "status": args.status,
        "description": args.description,
    }

    rows = load_experiments(results_tsv)
    replaced = False
    for index, existing in enumerate(rows):
        if int(existing["experiment"]) == args.experiment_id:
            rows[index] = row
            replaced = True
            break
    if not replaced:
        rows.append(row)
    rows.sort(key=lambda item: int(item["experiment"]))
    dump_experiments(results_tsv, rows)

    payload = load_payload(results_json)
    breakdown = parse_breakdown(args.eval_breakdown)

    experiments = [
        {
            "id": int(item["experiment"]),
            "score": int(item["score"]),
            "max_score": int(item["max_score"]),
            "pass_rate": float(item["pass_rate"].rstrip("%")),
            "status": item["status"],
            "description": item["description"],
        }
        for item in rows
    ]

    baseline_row = next((item for item in experiments if item["status"] == "baseline"), None)
    payload["status"] = args.run_status
    payload["current_experiment"] = args.experiment_id
    payload["experiments"] = experiments
    payload["baseline_score"] = baseline_row["pass_rate"] if baseline_row else None
    payload["best_score"] = max((item["pass_rate"] for item in experiments), default=None)
    if breakdown is not None:
        payload["eval_breakdown"] = breakdown
    else:
        payload.setdefault("eval_breakdown", [])

    atomic_write(results_json, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
