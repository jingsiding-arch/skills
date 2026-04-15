#!/usr/bin/env python3
"""Print companion skill suggestions declared in SKILL.md frontmatter."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Iterable


def parse_scalar(raw: str) -> str:
    value = raw.strip()
    if not value:
        return ""
    if (value[0] == value[-1]) and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def extract_frontmatter(skill_md: pathlib.Path) -> list[str]:
    try:
        content = skill_md.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"failed to read {skill_md}: {exc}") from exc

    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return []

    frontmatter: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return frontmatter
        frontmatter.append(line.rstrip("\n"))

    return []


def parse_recommended_skills(frontmatter: Iterable[str]) -> tuple[str | None, list[dict[str, str]]]:
    lines = list(frontmatter)
    name: str | None = None
    recommendations: list[dict[str, str]] = []

    top_level_pattern = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
    item_name_pattern = re.compile(r"^\s*-\s+name:\s*(.+)$")
    purpose_pattern = re.compile(r"^\s+purpose:\s*(.+)$")

    index = 0
    while index < len(lines):
      line = lines[index]
      top_level = top_level_pattern.match(line)
      if top_level and top_level.group(1) == "name":
          name = parse_scalar(top_level.group(2))
          index += 1
          continue

      if line.strip() != "recommended-skills:":
          index += 1
          continue

      index += 1
      current: dict[str, str] | None = None
      while index < len(lines):
          child_line = lines[index]
          if not child_line.strip():
              index += 1
              continue

          if re.match(r"^[A-Za-z0-9_-]+:", child_line):
              break

          item_name = item_name_pattern.match(child_line)
          if item_name:
              if current and current.get("name") and current.get("purpose"):
                  recommendations.append(current)
              current = {"name": parse_scalar(item_name.group(1))}
              index += 1
              continue

          purpose = purpose_pattern.match(child_line)
          if purpose and current is not None:
              current["purpose"] = parse_scalar(purpose.group(1))
              index += 1
              continue

          index += 1

      if current and current.get("name") and current.get("purpose"):
          recommendations.append(current)

    return name, recommendations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show recommended companion skills declared in SKILL.md frontmatter."
    )
    parser.add_argument(
        "--installed-root",
        type=pathlib.Path,
        default=pathlib.Path.home() / ".codex" / "skills",
        help="Directory that contains installed skill folders.",
    )
    parser.add_argument("skill_dirs", nargs="+", help="Installed skill directories to inspect.")
    args = parser.parse_args()

    suggestions: list[tuple[str, str, str, bool]] = []
    for raw_dir in args.skill_dirs:
        skill_dir = pathlib.Path(raw_dir)
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        try:
            frontmatter = extract_frontmatter(skill_md)
            skill_name, recommendations = parse_recommended_skills(frontmatter)
        except RuntimeError as exc:
            print(f"Warning: {exc}", file=sys.stderr)
            continue

        if not skill_name or not recommendations:
            continue

        for recommendation in recommendations:
            companion_name = recommendation["name"]
            companion_installed = (args.installed_root / companion_name).is_dir()
            suggestions.append(
                (
                    skill_name,
                    companion_name,
                    recommendation["purpose"],
                    companion_installed,
                )
            )

    if not suggestions:
        print("No companion skill recommendations declared for this install.")
        return 0

    print("Companion skill suggestions:")
    for skill_name, companion_name, purpose, installed in suggestions:
        if installed:
            print(
                f"- `{skill_name}` recommends `{companion_name}` (already installed): {purpose}"
            )
        else:
            print(f"- `{skill_name}` recommends also installing `{companion_name}`: {purpose}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
