#!/usr/bin/env python3
"""Scan Codex skills for common risk patterns.

This is a lightweight static scanner meant for post-install checks.
It does not prove a skill is safe; it highlights suspicious capabilities
that should be reviewed before use.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

TEXT_EXTENSIONS = {
    "",
    ".md",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".sh",
    ".bash",
    ".zsh",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".csv",
}

RULES = [
    {
        "id": "destructive_command",
        "severity": "critical",
        "description": "Potentially destructive shell command.",
        "pattern": re.compile(
            r"\b(rm\s+-rf|rm\s+-r|git\s+reset\s+--hard|git\s+clean\s+-fdx?|"
            r"mkfs|shred|dd\s+if=|diskutil\s+eraseDisk)\b",
            re.IGNORECASE,
        ),
    },
    {
        "id": "privilege_escalation",
        "severity": "high",
        "description": "Requests elevated privileges or system-level changes.",
        "pattern": re.compile(r"\b(sudo|doas|launchctl|systemctl)\b", re.IGNORECASE),
    },
    {
        "id": "network_download",
        "severity": "high",
        "description": "Downloads or fetches remote content.",
        "pattern": re.compile(
            r"\b(curl|wget|urllib\.request|urlopen\(|requests\.(get|post)|httpx\.(get|post)|"
            r"codeload\.github\.com|github\.com/.+\.git)\b",
            re.IGNORECASE,
        ),
    },
    {
        "id": "package_install",
        "severity": "medium",
        "description": "Installs dependencies or external tooling.",
        "pattern": re.compile(
            r"\b(npm\s+install|pnpm\s+(install|add)|yarn\s+(install|add)|"
            r"pip(?:3)?\s+install|uv\s+add|brew\s+install|cargo\s+install)\b",
            re.IGNORECASE,
        ),
    },
    {
        "id": "shell_execution",
        "severity": "medium",
        "description": "Executes shell or external commands.",
        "pattern": re.compile(
            r"(subprocess\.(run|Popen|call)|os\.system\(|execSync\(|spawnSync\(|"
            r"child_process\.|npm\s+run\b|pnpm\s+run\b|yarn\s+run\b|"
            r"(?:^|[`'\"(])(?:npx|python3?|node|bash|sh)\s+[./$A-Za-z0-9_-])",
            re.IGNORECASE,
        ),
    },
    {
        "id": "dynamic_eval",
        "severity": "high",
        "description": "Executes dynamic code or page JavaScript.",
        "pattern": re.compile(r"\b(eval\(|exec\(|camoufox-cli\s+eval\b)", re.IGNORECASE),
    },
    {
        "id": "browser_automation",
        "severity": "medium",
        "description": "Controls a browser or anti-detect automation tool.",
        "pattern": re.compile(
            r"\b(camoufox-cli|playwright|puppeteer|selenium|chrome devtools mcp|devtools mcp|headed open)\b",
            re.IGNORECASE,
        ),
    },
    {
        "id": "cookie_or_secret_access",
        "severity": "high",
        "description": "Touches cookies, tokens, or environment secrets.",
        "pattern": re.compile(
            r"\b(cookies?\s+(import|export)|GITHUB_TOKEN|GH_TOKEN|OPENAI_API_KEY|"
            r"os\.environ|getenv\(|Authorization)\b",
            re.IGNORECASE,
        ),
    },
    {
        "id": "filesystem_write",
        "severity": "medium",
        "description": "Writes, copies, or removes local files.",
        "pattern": re.compile(
            r"(write_text\(|write_bytes\(|copytree\(|rmtree\(|mkdir\(|rsync\s+-a\b|"
            r"\bcp\s+.+\s+.+|open\(.+['\"]w['\"])",
            re.IGNORECASE,
        ),
    },
    {
        "id": "permission_change",
        "severity": "medium",
        "description": "Changes executable bits or file permissions.",
        "pattern": re.compile(r"\b(chmod\(|chmod\s+)", re.IGNORECASE),
    },
]


@dataclass
class Finding:
    severity: str
    rule_id: str
    description: str
    file: str
    line: int
    snippet: str


def max_severity(levels: list[str]) -> str:
    if not levels:
        return "low"
    return max(levels, key=lambda value: SEVERITY_RANK[value])


def iter_skill_dirs(paths: list[str]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()

    for raw in paths:
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            continue
        if path.is_dir() and (path / "SKILL.md").exists():
            if path not in seen:
                found.append(path)
                seen.add(path)
            continue

        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.is_dir() and (child / "SKILL.md").exists() and child not in seen:
                    found.append(child)
                    seen.add(child)
    return found


def scan_skill(skill_dir: Path) -> dict:
    findings: list[Finding] = []
    metadata = {
        "skill": skill_dir.name,
        "path": str(skill_dir),
        "files_scanned": 0,
        "has_skill_md": (skill_dir / "SKILL.md").exists(),
        "findings": findings,
    }

    if not metadata["has_skill_md"]:
        findings.append(
            Finding(
                severity="high",
                rule_id="missing_skill_md",
                description="Missing SKILL.md.",
                file=str(skill_dir),
                line=0,
                snippet="",
            )
        )

    for current in skill_dir.rglob("*"):
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            continue

        if stat.S_ISLNK(info.st_mode):
            findings.append(
                Finding(
                    severity="medium",
                    rule_id="symlink_present",
                    description="Symlink present inside skill.",
                    file=str(current),
                    line=0,
                    snippet=os.readlink(current),
                )
            )
            continue

        if not current.is_file():
            continue

        metadata["files_scanned"] += 1

        perms = stat.S_IMODE(info.st_mode)
        if perms & 0o111:
            findings.append(
                Finding(
                    severity="low",
                    rule_id="executable_file",
                    description="Executable file present.",
                    file=str(current),
                    line=0,
                    snippet=oct(perms),
                )
            )

        if current.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        try:
            content = current.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            for rule in RULES:
                if rule["pattern"].search(line):
                    findings.append(
                        Finding(
                            severity=rule["severity"],
                            rule_id=rule["id"],
                            description=rule["description"],
                            file=str(current),
                            line=line_no,
                            snippet=line.strip()[:240],
                        )
                    )

    metadata["total_findings"] = len(findings)
    metadata["overall_risk"] = max_severity([item.severity for item in findings])
    return metadata


def render_text(report: dict) -> str:
    lines: list[str] = []
    lines.append("Skill Risk Scan Report")
    lines.append("=" * 72)
    lines.append(f"Scanned skills: {report['summary']['skills_scanned']}")
    lines.append(f"Highest risk:   {report['summary']['highest_risk'].upper()}")
    lines.append("")

    for skill in report["skills"]:
        lines.append(f"[{skill['overall_risk'].upper():8}] {skill['skill']}  ({skill['path']})")
        lines.append(f"  Files scanned: {skill['files_scanned']} | Findings: {skill['total_findings']}")
        grouped: dict[str, list[Finding]] = {}
        for finding in skill["findings"]:
            grouped.setdefault(finding.severity, []).append(finding)

        for severity in ("critical", "high", "medium", "low", "info"):
            items = grouped.get(severity, [])
            if not items:
                continue
            lines.append(f"  - {severity.upper()}: {len(items)}")
            for finding in items[:5]:
                location = f"{finding.file}:{finding.line}" if finding.line else finding.file
                lines.append(f"      • {finding.rule_id} @ {location}")
                if finding.snippet:
                    lines.append(f"        {finding.snippet}")
            if len(items) > 5:
                lines.append(f"      • ... {len(items) - 5} more")
        if skill["total_findings"] == 0:
            lines.append("  - No obvious risky patterns found.")
        lines.append("")

    lines.append("Notes:")
    lines.append("- This is a heuristic static scan, not a proof of safety.")
    lines.append("- Review HIGH/CRITICAL findings before trusting a new skill.")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan installed skills for common risk patterns.")
    parser.add_argument(
        "paths",
        nargs="+",
        help="Skill directories or a parent directory containing multiple skills.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--fail-on",
        choices=("none", "medium", "high", "critical"),
        default="none",
        help="Exit non-zero when the highest finding meets or exceeds this level.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_dirs = iter_skill_dirs(args.paths)
    if not skill_dirs:
        print("No skills found to scan.", file=sys.stderr)
        return 1

    scanned = [scan_skill(skill_dir) for skill_dir in skill_dirs]
    report = {
        "summary": {
            "skills_scanned": len(scanned),
            "highest_risk": max_severity([item["overall_risk"] for item in scanned]),
        },
        "skills": [],
    }

    for item in scanned:
        skill_copy = dict(item)
        skill_copy["findings"] = [asdict(finding) for finding in item["findings"]]
        report["skills"].append(skill_copy)

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        printable = {
            "summary": report["summary"],
            "skills": [],
        }
        for item in scanned:
            printable["skills"].append(item)
        print(render_text(printable))

    threshold = args.fail_on
    if threshold != "none":
        if SEVERITY_RANK[report["summary"]["highest_risk"]] >= SEVERITY_RANK[threshold]:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
