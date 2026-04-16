#!/usr/bin/env python3

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


CHECKS = [
    {
        "id": "default_prompt_zero_rewrite",
        "pattern": r"零改写|正文零改写",
        "message": "default_prompt should mention zero-rewrite preservation.",
        "paths": ("agents/openai.yaml",),
    },
    {
        "id": "default_prompt_dry_run",
        "pattern": r"dry-run|--dry-run",
        "message": "default_prompt should mention preflight and dry-run.",
        "paths": ("agents/openai.yaml",),
    },
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_files() -> list[dict]:
    required = [
        "SKILL.md",
        "agents/openai.yaml",
        "references/preservation-contract.md",
        "scripts/create_lark_doc_from_md.py",
        "scripts/lint_skill_consistency.py",
        "scripts/eval_dry_run_samples.py",
        "evals/README.md",
        "evals/samples.jsonl",
        "evals/fixtures/plain_prd.md",
        "evals/fixtures/hand_authored_callout.md",
    ]
    findings = []
    for rel in required:
        if not (ROOT / rel).exists():
            findings.append({"check": "required_file", "file": rel, "line": 1, "message": "Required file missing."})
    return findings


def check_jsonl() -> list[dict]:
    path = ROOT / "evals" / "samples.jsonl"
    findings = []
    if not path.exists():
        return findings
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            sample = json.loads(line)
        except json.JSONDecodeError as exc:
            findings.append({"check": "jsonl_valid", "file": str(path.relative_to(ROOT)), "line": idx, "message": str(exc)})
            continue
        for key in ("id", "input", "args", "expect"):
            if key not in sample:
                findings.append({"check": "jsonl_schema", "file": str(path.relative_to(ROOT)), "line": idx, "message": f"Missing key: {key}"})
        if "args" in sample and not isinstance(sample["args"], list):
            findings.append({"check": "jsonl_schema", "file": str(path.relative_to(ROOT)), "line": idx, "message": "args must be a list."})
        if "expect" in sample and not isinstance(sample["expect"], dict):
            findings.append({"check": "jsonl_schema", "file": str(path.relative_to(ROOT)), "line": idx, "message": "expect must be an object."})
    return findings


def line_no(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def check_patterns() -> list[dict]:
    findings = []
    for check in CHECKS:
        regex = re.compile(check["pattern"], re.M)
        for rel in check["paths"]:
            path = ROOT / rel
            text = read(path)
            matches = list(regex.finditer(text))
            if not matches:
                findings.append({"check": check["id"], "file": rel, "line": 1, "message": check["message"]})
    return findings


def main() -> int:
    findings = []
    findings.extend(check_required_files())
    findings.extend(check_jsonl())
    findings.extend(check_patterns())
    result = {
        "ok": not findings,
        "root": str(ROOT),
        "finding_count": len(findings),
        "findings": findings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
