#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
import tomllib
import shutil


def read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_user_config() -> dict:
    path = Path.home() / ".codex" / "config.toml"
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def load_auth_env() -> dict[str, str]:
    path = Path.home() / ".codex" / "auth.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    env = {}
    if data.get("auth_mode") == "apikey" and data.get("OPENAI_API_KEY"):
        env["OPENAI_API_KEY"] = str(data["OPENAI_API_KEY"])
    return env


def copy_auth_file(codex_home: Path) -> None:
    source = Path.home() / ".codex" / "auth.json"
    if not source.exists():
        return
    shutil.copy2(source, codex_home / "auth.json")


def select_references(skill_root: Path, prompt_text: str) -> list[Path]:
    # Keep generation prompts lean. The candidate SKILL should carry the main instructions;
    # large reference dumps were causing long-tail timeouts on richer prompts.
    return []


def build_prompt(candidate_file: Path, skill_root: Path, prompt_text: str) -> str:
    reference_sections = []
    for ref in select_references(skill_root, prompt_text):
        reference_sections.append(f"[Reference: {ref.name}]\n{ref.read_text(encoding='utf-8')}")

    return textwrap.dedent(
        f"""You are generating one sample output for a candidate skill under evaluation.

Follow the candidate SKILL.md and supporting files as the operating instructions.
Do not mention the evaluation harness, candidate file, or that you are being tested.
Output only the final user-facing response in Chinese unless the instructions require otherwise.
Prefer concise but complete output over unnecessarily long prose.
Keep the answer compact. Default target: under 1200 Chinese characters unless the instructions clearly require more.
Prefer dense tables and bullet points over explanatory paragraphs.
If information is insufficient, still output a compact development-ready skeleton with `TBD` placeholders instead of a long discussion.

[Candidate SKILL.md]
{candidate_file.read_text(encoding='utf-8')}

{os.linesep.join(reference_sections)}

[User request]
{prompt_text.strip()}
"""
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one sample response by executing a candidate skill through codex exec.")
    parser.add_argument("--candidate-file", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--skill-root", required=True, help="Root directory of the source skill with references/assets")
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--force-http", action="store_true", default=True)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()

    candidate_file = Path(args.candidate_file).expanduser().resolve()
    prompt_file = Path(args.prompt_file).expanduser().resolve()
    output_file = Path(args.output_file).expanduser().resolve()
    skill_root = Path(args.skill_root).expanduser().resolve()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    codex_home = output_file.parent / ".codex-home"
    codex_home.mkdir(parents=True, exist_ok=True)
    copy_auth_file(codex_home)
    log_file = output_file.parent / "generate.log"

    prompt_text = prompt_file.read_text(encoding="utf-8")
    full_prompt = build_prompt(candidate_file, skill_root, prompt_text)

    command = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write",
        "--output-last-message",
        str(output_file),
        "--add-dir",
        str(output_file.parent),
        "--add-dir",
        str(candidate_file.parent),
    ]
    config = load_user_config()
    provider_name = str(config.get("model_provider", "OpenAI"))
    providers = config.get("model_providers", {})
    provider = providers.get(provider_name, {}) if isinstance(providers, dict) else {}
    if args.force_http and provider_name and provider:
        name = str(provider.get("name", provider_name))
        base_url = str(provider.get("base_url", ""))
        wire_api = str(provider.get("wire_api", "responses"))
        requires_auth = bool(provider.get("requires_openai_auth", True))
        override = (
            f'model_providers.{provider_name}={{name="{name}",base_url="{base_url}",wire_api="{wire_api}",'
            f'requires_openai_auth={str(requires_auth).lower()},supports_websockets=false}}'
        )
        command.extend(["-c", f'model_provider="{provider_name}"', "-c", override])
    if args.model:
        command.extend(["--model", args.model])
    command.append("-")

    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    env.update(load_auth_env())
    attempts = max(1, args.retries)
    logs: list[str] = []
    had_failure = False
    for attempt in range(1, attempts + 1):
        had_failure = False
        if output_file.exists():
            output_file.unlink()
        try:
            cp = subprocess.run(
                command,
                cwd=str(skill_root),
                input=full_prompt,
                text=True,
                env=env,
                check=True,
                capture_output=True,
                timeout=args.timeout_seconds,
            )
            logs.append(
                f"=== Attempt {attempt} success ===\n"
                + (cp.stdout or "")
                + ("\n--- STDERR ---\n" + cp.stderr if cp.stderr else "")
            )
        except subprocess.TimeoutExpired as exc:
            had_failure = True
            logs.append(
                f"=== Attempt {attempt} timeout after {args.timeout_seconds}s ===\n"
                f"STDOUT:\n{exc.stdout or ''}\n\nSTDERR:\n{exc.stderr or ''}\n"
            )
        except subprocess.CalledProcessError as exc:
            had_failure = True
            logs.append(
                f"=== Attempt {attempt} exit {exc.returncode} ===\n"
                f"STDOUT:\n{exc.stdout or ''}\n\nSTDERR:\n{exc.stderr or ''}\n"
            )
        if output_file.exists() and output_file.read_text(encoding="utf-8").strip():
            log_file.write_text("\n\n".join(logs), encoding="utf-8")
            break
        if attempt == attempts and not output_file.exists():
            output_file.write_text("", encoding="utf-8")
        if attempt == attempts:
            log_file.write_text("\n\n".join(logs), encoding="utf-8")
    if not output_file.exists():
        raise SystemExit(f"codex exec did not produce {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
