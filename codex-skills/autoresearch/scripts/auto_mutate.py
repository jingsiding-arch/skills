#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import textwrap
from pathlib import Path

from mutate_candidate import append_mutation_row, atomic_write, resolve_candidate


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else {}


def latest_scorecard_path(run_dir: Path) -> Path | None:
    scorecards = sorted((run_dir / "scorecards").glob("experiment-*.json"))
    candidates = [path for path in scorecards if not path.name.endswith("-breakdown.json")]
    return candidates[-1] if candidates else None


def weakest_evals(run_dir: Path, limit: int = 2) -> list[dict]:
    scorecard_path = latest_scorecard_path(run_dir)
    if not scorecard_path:
        return []
    payload = load_json(scorecard_path)
    breakdown = payload.get("eval_breakdown", [])
    ranked = []
    for item in breakdown:
        total = int(item.get("total", 0))
        passed = int(item.get("pass_count", 0))
        rate = 1.0 if total == 0 else passed / total
        ranked.append(
            {
                "name": str(item.get("name", "")).strip(),
                "pass_count": passed,
                "total": total,
                "pass_rate": round(rate * 100, 1),
            }
        )
    ranked.sort(key=lambda item: (item["pass_rate"], item["name"]))
    imperfect = [item for item in ranked if item["pass_rate"] < 100.0]
    return (imperfect or ranked)[:limit]


def eval_lookup(run_dir: Path) -> dict[str, dict]:
    run_spec = load_json(run_dir / "run-spec.json")
    lookup = {}
    for item in run_spec.get("evals", []):
        name = str(item.get("name", "")).strip()
        if name:
            lookup[name] = item
    return lookup


def choose_reinforcement(name: str, question: str) -> tuple[str, str]:
    haystack = f"{name} {question}".lower()
    if any(token in haystack for token in ["sparse", "clarify", "underspecified", "question", "intake"]):
        return (
            "underspecified-input guardrail",
            "When the input is underspecified, do not produce a fully detailed final artifact first. Summarize what is known, list the missing high-impact facts, and either ask 1-3 clarifying questions or output a clearly labeled skeleton/draft.",
        )
    if any(token in haystack for token in ["closure", "conflict", "contradiction", "blocked", "risk"]):
        return (
            "conflict-first guardrail",
            "If the input contains a blocking contradiction, dependency gap, or responsibility conflict, surface that conflict near the top of the response before continuing. Explain why it blocks scope, acceptance, or execution, then offer candidate decisions.",
        )
    if any(token in haystack for token in ["reviewer", "structure", "format", "section", "table"]):
        return (
            "structured-output guardrail",
            "Prefer reviewer-ready structure over free-form advice. Use stable sections, labels, and tables so the output can be reviewed or handed off directly.",
        )
    if any(token in haystack for token in ["evidence", "material", "source", "fact", "known"]):
        return (
            "evidence-first guardrail",
            "Before asking follow-up questions, extract what is already known from the provided material, call out visible conflicts, and list only the missing facts that materially change the outcome.",
        )
    if any(token in haystack for token in ["incremental", "update", "revision", "delta"]):
        return (
            "incremental-update guardrail",
            "In follow-up turns, update only the affected sections, call out what changed, and avoid rewriting the entire artifact unless the user asks for a full refresh.",
        )
    return (
        "precision guardrail",
        "Tighten the instructions around the weakest eval so the expected behavior is explicit, observable, and hard to misread.",
    )


def build_reinforcement_block(experiment_id: int, reinforcements: list[tuple[str, str]]) -> str:
    bullets = "\n".join(f"- {title}: {body}" for title, body in reinforcements)
    return textwrap.dedent(
        f"""## Autoresearch Experiment {experiment_id} Reinforcement

Keep this experiment-specific reinforcement concise and focused on the current failures:

{bullets}
"""
    ).rstrip() + "\n"


def insert_reinforcement(candidate_text: str, block: str) -> str:
    marker = "## Example requests"
    lower = candidate_text.lower()
    index = lower.find(marker.lower())
    if index == -1:
        return candidate_text.rstrip() + "\n\n" + block
    return candidate_text[:index].rstrip() + "\n\n" + block + "\n" + candidate_text[index:]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and optionally apply an automatic mutation proposal for an autoresearch run.")
    parser.add_argument("--run-dir", required=True, help="Path to autoresearch run directory")
    parser.add_argument("--experiment-id", required=True, type=int, help="Experiment number to prepare")
    parser.add_argument("--candidate-file", default=None, help="Optional candidate file path override")
    parser.add_argument("--apply", action="store_true", help="Apply the proposal directly to the candidate file")
    parser.add_argument("--max-weak-evals", type=int, default=2, help="How many weak evals to target")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    candidate_file = resolve_candidate(run_dir, args.candidate_file)
    if not candidate_file.exists():
        raise SystemExit(f"Candidate file does not exist: {candidate_file}")

    weakest = weakest_evals(run_dir, args.max_weak_evals)
    lookup = eval_lookup(run_dir)
    reinforcements = []
    targeted = []
    for item in weakest:
        name = item["name"]
        question = str(lookup.get(name, {}).get("question", ""))
        title, body = choose_reinforcement(name, question)
        reinforcements.append((title, body))
        targeted.append(
            {
                "eval_name": name,
                "pass_rate": item["pass_rate"],
                "question": question,
                "reinforcement_title": title,
                "reinforcement_body": body,
            }
        )

    if not reinforcements:
        title, body = choose_reinforcement("generic", "")
        reinforcements.append((title, body))
        targeted.append(
            {
                "eval_name": "generic",
                "pass_rate": None,
                "question": "",
                "reinforcement_title": title,
                "reinforcement_body": body,
            }
        )

    mutation_note = "; ".join(item["reinforcement_title"] for item in targeted)
    proposal_dir = run_dir / "auto-mutations"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_md = proposal_dir / f"experiment-{args.experiment_id}.md"
    proposal_json = proposal_dir / f"experiment-{args.experiment_id}.json"

    block = build_reinforcement_block(args.experiment_id, reinforcements)
    proposal_markdown = "# Auto mutation proposal\n\n" + "\n".join(
        [
            f"- Experiment: `{args.experiment_id}`",
            f"- Candidate: `{candidate_file.name}`",
            f"- Mutation note: `{mutation_note}`",
            "",
            "## Targeted weak evals",
            *[
                f"- `{item['eval_name']}` ({item['pass_rate']}%): {item['reinforcement_title']}"
                for item in targeted
            ],
            "",
            "## Proposed reinforcement block",
            "",
            "```md",
            block.rstrip(),
            "```",
            "",
        ]
    )
    atomic_write(proposal_md, proposal_markdown)
    atomic_write(
        proposal_json,
        json.dumps(
            {
                "experiment_id": args.experiment_id,
                "candidate_file": str(candidate_file),
                "mutation_note": mutation_note,
                "targeted_evals": targeted,
                "reinforcement_block": block,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )

    applied = False
    before_snapshot = None
    working_snapshot = None
    if args.apply:
        history_dir = run_dir / "candidate-history"
        history_dir.mkdir(parents=True, exist_ok=True)
        before_snapshot = history_dir / f"experiment-{args.experiment_id}-before.md"
        working_snapshot = history_dir / f"experiment-{args.experiment_id}-working.md"
        shutil.copy2(candidate_file, before_snapshot)
        new_text = insert_reinforcement(candidate_file.read_text(encoding="utf-8"), block)
        atomic_write(candidate_file, new_text)
        shutil.copy2(candidate_file, working_snapshot)
        append_mutation_row(run_dir, args.experiment_id, "prepared", mutation_note, working_snapshot.name)
        applied = True

    print(
        json.dumps(
            {
                "proposal_md": str(proposal_md),
                "proposal_json": str(proposal_json),
                "mutation_note": mutation_note,
                "targeted_evals": targeted,
                "applied": applied,
                "before_snapshot": str(before_snapshot) if before_snapshot else None,
                "working_snapshot": str(working_snapshot) if working_snapshot else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
