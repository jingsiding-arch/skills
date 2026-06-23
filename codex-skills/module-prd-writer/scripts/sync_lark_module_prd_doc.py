#!/usr/bin/env python3

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from shutil import which

DEFAULT_CHUNK_CHARS = 12000
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)\s*$")
FENCE_RE = re.compile(r"^\s*```")
SEPARATOR = "\n\n---\n\n"
CREATE_SCRIPT = Path("/Users/homg/Documents/Codex/skills/lark-md-pretty-doc/scripts/create_lark_doc_from_md.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create, replace, or append a module PRD Markdown file into a Feishu/Lark doc."
    )
    parser.add_argument("--input", required=True, help="Absolute path to the source Markdown file")
    parser.add_argument("--doc", help="Existing Feishu doc URL or token; required for replace-all/append")
    parser.add_argument("--title", help="Document title when creating a new doc; defaults to input stem")
    parser.add_argument("--mode", choices=("auto", "create", "replace-all", "append"), default="auto")
    parser.add_argument("--folder-token", help="Parent folder token when creating")
    parser.add_argument("--wiki-node", help="Parent wiki node token when creating")
    parser.add_argument("--wiki-space", help="Target wiki space ID when creating, e.g. my_library")
    parser.add_argument("--as", dest="identity", default="user", choices=("user", "bot"))
    parser.add_argument("--chunk-chars", type=int, default=DEFAULT_CHUNK_CHARS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prepend-separator", action="store_true", help="Prepend a markdown separator before append content")
    args = parser.parse_args()

    destinations = [args.folder_token, args.wiki_node, args.wiki_space]
    if sum(value is not None for value in destinations) > 1:
        parser.error("Only one of --folder-token, --wiki-node, or --wiki-space may be provided")
    if args.mode in ("replace-all", "append") and not args.doc:
        parser.error("--doc is required when --mode replace-all or --mode append")
    if args.chunk_chars < 1000:
        parser.error("--chunk-chars must be at least 1000")
    return args


def load_markdown(path_str: str) -> tuple[Path, str]:
    path = Path(path_str).expanduser().resolve()
    if not path.is_absolute():
        raise ValueError("--input must be an absolute path")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Input markdown not found: {path}")
    if path.suffix.lower() != ".md":
        raise ValueError("Input file must end with .md")
    return path, path.read_text(encoding="utf-8")


def find_boundaries(text: str) -> list[int]:
    boundaries = {len(text)}
    inside_fence = False
    offset = 0
    for line in text.splitlines(keepends=True):
        if FENCE_RE.match(line):
            if not inside_fence and 0 < offset < len(text):
                boundaries.add(offset)
            elif inside_fence and 0 < offset + len(line) < len(text):
                boundaries.add(offset + len(line))
            inside_fence = not inside_fence
            offset += len(line)
            continue
        if not inside_fence:
            if HEADING_RE.match(line) and 0 < offset < len(text):
                boundaries.add(offset)
            if re.match(r"^\s*$", line) and 0 < offset < len(text):
                boundaries.add(offset)
            if re.match(r"^---\s*$", line.rstrip("\n")) and 0 < offset < len(text):
                boundaries.add(offset)
        offset += len(line)
    return sorted(boundaries)


def split_markdown(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    boundaries = find_boundaries(text)
    chunks = []
    start = 0
    while start < len(text):
        target = min(start + max_chars, len(text))
        if target >= len(text):
            chunks.append(text[start:])
            break
        candidates = [b for b in boundaries if start + max_chars // 2 <= b <= target]
        split_at = candidates[-1] if candidates else target
        if split_at <= start:
            split_at = target
        chunks.append(text[start:split_at])
        start = split_at
    return [chunk for chunk in chunks if chunk]


def parse_json_payload(text: str):
    stripped = text.strip()
    if not stripped:
        return None
    try:
        payload = json.loads(stripped)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(stripped[start:end + 1])
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def extract_doc_refs(stdout: str) -> tuple[str | None, str | None]:
    payload = parse_json_payload(stdout)
    doc_id = None
    doc_url = None
    if isinstance(payload, dict):
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        for key in ("doc_id", "docId"):
            value = data.get(key)
            if isinstance(value, str) and value:
                doc_id = value
                break
        for key in ("doc_url", "docUrl", "url"):
            value = data.get(key)
            if isinstance(value, str) and value:
                doc_url = value
                break
    if not doc_url:
        match = re.search(r"https?://\S+/(?:docx|doc|wiki)/[A-Za-z0-9]+", stdout)
        if match:
            doc_url = match.group(0)
    if not doc_id:
        match = re.search(r"\b(?:doxcn|doccn|wikcn)[A-Za-z0-9]+\b", stdout)
        if match:
            doc_id = match.group(0)
    return doc_id, doc_url


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True)


def run_lark_preflight(identity: str) -> dict:
    doctor_command = ["lark-cli", "doctor"]
    doctor_result = run(doctor_command)
    doctor_payload = parse_json_payload(doctor_result.stdout)

    auth_command = ["lark-cli", "auth", "status"]
    auth_result = run(auth_command) if identity == "user" else None
    auth_payload = parse_json_payload(auth_result.stdout) if auth_result else None

    issues: list[str] = []
    remediation: list[str] = []

    if doctor_result.returncode != 0:
        issues.append("lark-cli doctor failed")
        remediation.append("Run `lark-cli config init --new` to complete app configuration.")

    if identity == "user" and auth_result and auth_result.returncode != 0:
        issues.append("lark-cli auth status failed")
        remediation.append("Run `lark-cli auth login --domain docs` after config is ready to authorize the user identity.")

    return {
        "ready": doctor_result.returncode == 0 and (identity != "user" or (auth_result is not None and auth_result.returncode == 0)),
        "doctor": {
            "command": doctor_command,
            "returncode": doctor_result.returncode,
            "payload": doctor_payload,
            "stderr": doctor_result.stderr.strip(),
        },
        "auth_status": {
            "command": auth_command,
            "returncode": auth_result.returncode if auth_result else None,
            "payload": auth_payload,
            "stderr": auth_result.stderr.strip() if auth_result else "",
        } if identity == "user" else None,
        "issues": issues,
        "remediation": remediation,
    }


def build_create_command(args: argparse.Namespace, source: Path) -> list[str]:
    cmd = [
        "python3", str(CREATE_SCRIPT),
        "--input", str(source),
        "--as", args.identity,
        "--chunk-chars", str(args.chunk_chars),
        "--label-prefix-style", "blue-bold",
        "--flowchart-mode", "auto",
    ]
    if args.title:
        cmd.extend(["--title", args.title])
    if args.folder_token:
        cmd.extend(["--folder-token", args.folder_token])
    elif args.wiki_node:
        cmd.extend(["--wiki-node", args.wiki_node])
    elif args.wiki_space:
        cmd.extend(["--wiki-space", args.wiki_space])
    else:
        cmd.extend(["--folder-token", "VH3rffK9llwobHdAMt1cUSnfnHf"])
    if args.dry_run:
        cmd.append("--dry-run")
    return cmd


def build_update_command(args: argparse.Namespace, doc_ref: str, markdown: str, mode: str) -> list[str]:
    cmd = [
        "lark-cli", "docs", "+update",
        "--as", args.identity,
        "--doc", doc_ref,
        "--mode", mode,
        "--markdown", markdown,
    ]
    if args.dry_run:
        cmd.append("--dry-run")
    return cmd


def main() -> int:
    args = parse_args()
    if which("lark-cli") is None:
        print(json.dumps({"ok": False, "error": "lark-cli not found in PATH"}, ensure_ascii=False, indent=2))
        return 1

    try:
        source_path, body = load_markdown(args.input)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    preflight = run_lark_preflight(args.identity)
    if not preflight["ready"]:
        print(json.dumps({
            "ok": False,
            "mode": args.mode,
            "source": str(source_path),
            "identity": args.identity,
            "preflight": preflight,
        }, ensure_ascii=False, indent=2))
        return 1

    effective_mode = args.mode
    if effective_mode == "auto":
        effective_mode = "replace-all" if args.doc else "create"

    if effective_mode == "create":
        if not CREATE_SCRIPT.exists():
            print(json.dumps({"ok": False, "error": f"Create script not found: {CREATE_SCRIPT}"}, ensure_ascii=False, indent=2))
            return 1
        cmd = build_create_command(args, source_path)
        result = run(cmd)
        if result.returncode != 0:
            print(json.dumps({
                "ok": False,
                "mode": effective_mode,
                "command": cmd,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "preflight": preflight,
            }, ensure_ascii=False, indent=2))
            return result.returncode
        payload = parse_json_payload(result.stdout)
        doc_id, doc_url = extract_doc_refs(result.stdout)
        print(json.dumps({
            "ok": True,
            "mode": effective_mode,
            "source": str(source_path),
            "title": args.title or source_path.stem,
            "identity": args.identity,
            "doc_id": doc_id,
            "doc_url": doc_url,
            "payload": payload,
            "preflight": preflight,
        }, ensure_ascii=False, indent=2))
        return 0

    if effective_mode == "append":
        text = body
        if args.prepend_separator:
            stripped = text.lstrip()
            if not stripped.startswith("---"):
                text = SEPARATOR + text.lstrip("\n")
        chunks = split_markdown(text, args.chunk_chars)
        if args.dry_run:
            print(json.dumps({
                "ok": True,
                "dry_run": True,
                "mode": effective_mode,
                "source": str(source_path),
                "doc": args.doc,
                "identity": args.identity,
                "chunk_count": len(chunks),
                "first_chunk_preview": chunks[0][:800] if chunks else "",
                "preflight": preflight,
            }, ensure_ascii=False, indent=2))
            return 0

        successes = 0
        for index, chunk in enumerate(chunks, start=1):
            cmd = build_update_command(args, args.doc, chunk, "append")
            result = run(cmd)
            if result.returncode != 0:
                print(json.dumps({
                    "ok": False,
                    "mode": effective_mode,
                    "chunk_index": index,
                    "command": cmd,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "preflight": preflight,
                }, ensure_ascii=False, indent=2))
                return result.returncode
            successes += 1

        print(json.dumps({
            "ok": True,
            "mode": effective_mode,
            "source": str(source_path),
            "doc": args.doc,
            "identity": args.identity,
            "chunk_count": len(chunks),
            "updated_chunks": successes,
            "prepended_separator": args.prepend_separator,
            "preflight": preflight,
        }, ensure_ascii=False, indent=2))
        return 0

    if args.dry_run:
        print(json.dumps({
            "ok": True,
            "dry_run": True,
            "mode": effective_mode,
            "source": str(source_path),
            "doc": args.doc,
            "identity": args.identity,
            "final_length": len(body),
            "preview": body[:1200],
            "preflight": preflight,
        }, ensure_ascii=False, indent=2))
        return 0

    cmd = build_update_command(args, args.doc, body, "replace_all")
    result = run(cmd)
    if result.returncode != 0:
        print(json.dumps({
            "ok": False,
            "mode": effective_mode,
            "command": cmd,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "preflight": preflight,
        }, ensure_ascii=False, indent=2))
        return result.returncode

    print(json.dumps({
        "ok": True,
        "mode": effective_mode,
        "source": str(source_path),
        "doc": args.doc,
        "identity": args.identity,
        "final_length": len(body),
        "preflight": preflight,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
