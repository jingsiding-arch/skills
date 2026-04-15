#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from score_run import atomic_write, iter_evals, normalize_samples


def resolve_candidate(run_dir: Path, override: str | None, payload: dict) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    candidate_name = payload.get("candidate_file")
    if candidate_name:
        return run_dir / str(candidate_name)
    matches = [path for path in run_dir.glob("*.md") if path.name not in {"SKILL.md.baseline", "run-spec.md", "changelog.md", "mutations.md"}]
    if not matches:
        raise SystemExit("Could not determine candidate file; pass --candidate-file explicitly")
    return matches[0]


def archive_samples(run_dir: Path, experiment_id: int, sources: list[str]) -> list[str]:
    dest_dir = run_dir / "outputs" / f"experiment-{experiment_id}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source_str in sources:
        source = Path(source_str).expanduser().resolve()
        if not source.exists():
            raise SystemExit(f"Sample source does not exist: {source}")
        target = dest_dir / source.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        copied.append(str(target))
    return copied


def build_scorecard(run_dir: Path, experiment_id: int, results_file: Path) -> tuple[int, int, list[dict], Path]:
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

    scorecards_dir = run_dir / "scorecards"
    scorecards_dir.mkdir(parents=True, exist_ok=True)
    scorecard_path = scorecards_dir / f"experiment-{experiment_id}.json"
    breakdown_path = scorecards_dir / f"experiment-{experiment_id}-breakdown.json"
    scorecard = {
        "experiment_id": experiment_id,
        "score": score,
        "max_score": max_score,
        "pass_rate": 0.0 if max_score == 0 else round((score / max_score) * 100, 1),
        "samples": samples,
        "eval_breakdown": list(breakdown.values()),
    }
    atomic_write(scorecard_path, json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n")
    atomic_write(breakdown_path, json.dumps(scorecard["eval_breakdown"], ensure_ascii=False, indent=2) + "\n")
    return score, max_score, scorecard["eval_breakdown"], breakdown_path


def decide_status(experiment_id: int, explicit: str, pass_rate: float, current_payload: dict, keep_on_tie: bool) -> str:
    if explicit != "auto":
        return explicit
    if experiment_id == 0:
        return "baseline"
    previous = [
        item["pass_rate"]
        for item in current_payload.get("experiments", [])
        if int(item.get("id", -1)) < experiment_id and item.get("status") in {"baseline", "keep"}
    ]
    if not previous:
        return "keep"
    best_previous = max(previous)
    if pass_rate > best_previous:
        return "keep"
    if keep_on_tie and pass_rate == best_previous:
        return "keep"
    return "discard"


def append_markdown(path: Path, block: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    atomic_write(path, existing + block)


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive, score, and decide one autoresearch experiment.")
    parser.add_argument("--run-dir", required=True, help="Path to autoresearch run directory")
    parser.add_argument("--experiment-id", required=True, type=int, help="Experiment number")
    parser.add_argument("--description", required=True, help="Short mutation description")
    parser.add_argument("--results-file", required=True, help="JSON file with per-sample eval results")
    parser.add_argument("--candidate-file", default=None, help="Optional candidate file under evaluation")
    parser.add_argument("--decision", default="auto", choices=["auto", "baseline", "keep", "discard"], help="Outcome decision mode")
    parser.add_argument("--keep-on-tie", action="store_true", help="Keep equal-scoring experiments when decision=auto")
    parser.add_argument("--sample-source", action="append", default=[], help="Optional raw sample outputs to archive; repeatable")
    parser.add_argument("--run-status", default="running", choices=["running", "idle", "complete"], help="Overall run status")
    parser.add_argument("--mutation-note", default=None, help="Optional detailed mutation note")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    results_json = run_dir / "results.json"
    payload = json.loads(results_json.read_text(encoding="utf-8")) if results_json.exists() else {}
    candidate_file = resolve_candidate(run_dir, args.candidate_file, payload)
    if not candidate_file.exists():
        raise SystemExit(f"Candidate file does not exist: {candidate_file}")

    copied_outputs = archive_samples(run_dir, args.experiment_id, args.sample_source) if args.sample_source else []
    score, max_score, breakdown, breakdown_path = build_scorecard(run_dir, args.experiment_id, Path(args.results_file).expanduser().resolve())
    pass_rate = 0.0 if max_score == 0 else round((score / max_score) * 100, 1)
    status = decide_status(args.experiment_id, args.decision, pass_rate, payload, args.keep_on_tie)

    history_dir = run_dir / "candidate-history"
    history_dir.mkdir(parents=True, exist_ok=True)
    evaluated_snapshot = history_dir / f"experiment-{args.experiment_id}-evaluated.md"
    shutil.copy2(candidate_file, evaluated_snapshot)

    current_candidate = history_dir / "current-candidate.md"
    if status in {"baseline", "keep"}:
        kept_snapshot = history_dir / f"experiment-{args.experiment_id}-kept.md"
        shutil.copy2(candidate_file, kept_snapshot)
        shutil.copy2(candidate_file, current_candidate)
    elif status == "discard" and current_candidate.exists():
        discarded_snapshot = history_dir / f"experiment-{args.experiment_id}-discarded.md"
        shutil.copy2(candidate_file, discarded_snapshot)
        shutil.copy2(current_candidate, candidate_file)

    log_script = Path(__file__).with_name("log_experiment.py")
    subprocess.run(
        [
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
            status,
            "--description",
            args.description,
            "--run-status",
            args.run_status,
            "--eval-breakdown",
            str(breakdown_path),
        ],
        check=True,
    )

    mutation_note = args.mutation_note or args.description
    append_markdown(
        run_dir / "mutations.md",
        f"| {args.experiment_id} | {status} | {mutation_note.replace('|', '/')} | `{evaluated_snapshot.name}` |\n",
    )
    append_markdown(
        run_dir / "changelog.md",
        "\n".join(
            [
                f"## Experiment {args.experiment_id} — {status}",
                "",
                f"**Score:** {score}/{max_score} ({pass_rate:.1f}%)",
                f"**Change:** {args.description}",
                f"**Mutation note:** {mutation_note}",
                f"**Raw outputs:** {', '.join(copied_outputs) if copied_outputs else 'none archived'}",
                "",
            ]
        ),
    )

    summary = {
        "experiment_id": args.experiment_id,
        "status": status,
        "score": score,
        "max_score": max_score,
        "pass_rate": pass_rate,
        "archived_outputs": copied_outputs,
        "candidate_file": str(candidate_file),
        "evaluated_snapshot": str(evaluated_snapshot),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
