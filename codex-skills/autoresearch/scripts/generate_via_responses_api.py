#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import subprocess
import textwrap
import tomllib
from pathlib import Path


def load_user_config() -> dict:
    path = Path.home() / ".codex" / "config.toml"
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def load_api_key() -> str:
    path = Path.home() / ".codex" / "auth.json"
    if not path.exists():
        raise SystemExit("Missing ~/.codex/auth.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    api_key = data.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY in ~/.codex/auth.json")
    return str(api_key)


def build_prompt(candidate_file: Path, skill_root: Path, prompt_text: str) -> str:
    template = skill_root / "assets" / "module-prd-template.md"
    template_text = template.read_text(encoding="utf-8") if template.exists() else ""
    return textwrap.dedent(
        f"""You are generating one sample output for a candidate skill under evaluation.

Follow the candidate SKILL.md as the operating instructions.
Do not mention the evaluation harness, candidate file, or that you are being tested.
Output only the final user-facing response in Chinese unless the instructions require otherwise.
Prefer concise but complete output over unnecessarily long prose.

[Candidate SKILL.md]
{candidate_file.read_text(encoding='utf-8')}

[Asset: module-prd-template.md]
{template_text}

[User request]
{prompt_text.strip()}
"""
    )


def extract_output_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunk for chunk in chunks if chunk).strip()


def extract_chat_completion_text(payload: dict) -> str:
    choices = payload.get("choices", [])
    if not isinstance(choices, list):
        return ""
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message", {})
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def post_json(url: str, request_path: Path, response_path: Path, api_key: str, timeout_seconds: int) -> tuple[int | None, str]:
    curl_command = [
        "curl",
        "-sS",
        "--max-time",
        str(timeout_seconds),
        "-o",
        str(response_path),
        "-w",
        "%{http_code}",
        "-X",
        "POST",
        url,
        "-H",
        "Content-Type: application/json",
        "-H",
        f"Authorization: Bearer {api_key}",
        "--data-binary",
        f"@{request_path}",
    ]
    cp = subprocess.run(curl_command, capture_output=True, text=True, check=False)
    if cp.returncode != 0:
        raise RuntimeError(f"curl exit {cp.returncode}: {(cp.stderr or '').strip()[:300]}")
    http_code_raw = (cp.stdout or "").strip()
    http_code = int(http_code_raw) if http_code_raw.isdigit() else None
    raw = response_path.read_text(encoding="utf-8") if response_path.exists() else ""
    return http_code, raw


def prefer_responses_api(base_url: str) -> bool:
    normalized = base_url.rstrip("/").lower()
    return "api.openai.com" in normalized


def split_base_urls(raw: str | None) -> list[str]:
    if not raw:
        return []
    urls: list[str] = []
    for part in raw.split(","):
        value = part.strip().rstrip("/")
        if value:
            urls.append(value)
    return urls


def resolve_base_urls(primary: str, fallback_raw: str | None) -> list[str]:
    urls: list[str] = []
    for candidate in [primary.rstrip("/"), *split_base_urls(fallback_raw)]:
        if candidate and candidate not in urls:
            urls.append(candidate)
    return urls


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one sample response via Responses HTTP API.")
    parser.add_argument("--candidate-file", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--skill-root", required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-output-tokens", type=int, default=1600)
    parser.add_argument("--base-url", default=None, help="Optional primary base URL override")
    parser.add_argument("--fallback-base-urls", default=None, help="Optional comma-separated fallback base URLs")
    args = parser.parse_args()

    candidate_file = Path(args.candidate_file).expanduser().resolve()
    prompt_file = Path(args.prompt_file).expanduser().resolve()
    output_file = Path(args.output_file).expanduser().resolve()
    skill_root = Path(args.skill_root).expanduser().resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    log_file = output_file.parent / "generate.log"

    config = load_user_config()
    provider_name = str(config.get("model_provider", "OpenAI"))
    providers = config.get("model_providers", {})
    provider = providers.get(provider_name, {}) if isinstance(providers, dict) else {}
    configured_base_url = str(provider.get("base_url", "https://api.openai.com/v1")).rstrip("/")
    base_urls = resolve_base_urls(
        args.base_url or configured_base_url,
        args.fallback_base_urls or os.environ.get("AUTORESEARCH_FALLBACK_BASE_URLS"),
    )
    model = args.model or str(config.get("model", "gpt-5.4"))
    api_key = load_api_key()

    prompt = build_prompt(candidate_file, skill_root, prompt_file.read_text(encoding="utf-8"))
    responses_request_path = output_file.parent / "request.json"
    chat_request_path = output_file.parent / "request-chat.json"
    responses_body = {
        "model": model,
        "input": prompt,
        "reasoning": {"effort": "none"},
        "text": {"verbosity": "low"},
        "max_output_tokens": args.max_output_tokens,
        "store": False,
    }
    chat_body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": args.max_output_tokens,
        "temperature": 1,
    }
    responses_request_path.write_text(json.dumps(responses_body, ensure_ascii=False, indent=2), encoding="utf-8")
    chat_request_path.write_text(json.dumps(chat_body, ensure_ascii=False, indent=2), encoding="utf-8")
    logs: list[str] = []
    for attempt in range(1, max(1, args.retries) + 1):
        for base_url in base_urls:
            endpoint_plan = [
                {
                    "name": "responses",
                    "url": f"{base_url}/responses",
                    "request_path": responses_request_path,
                    "extractor": extract_output_text,
                    "token_label": "max_output_tokens",
                },
                {
                    "name": "chat",
                    "url": f"{base_url}/v1/chat/completions",
                    "request_path": chat_request_path,
                    "extractor": extract_chat_completion_text,
                    "token_label": "max_tokens",
                },
            ]
            if not prefer_responses_api(base_url):
                endpoint_plan.reverse()

            for endpoint in endpoint_plan:
                name = str(endpoint["name"])
                response_path = output_file.parent / f"{name}-{base_url.replace('https://', '').replace('http://', '').replace('/', '_')}-attempt-{attempt}.json"
                try:
                    http_code, raw = post_json(
                        url=str(endpoint["url"]),
                        request_path=Path(endpoint["request_path"]),
                        response_path=response_path,
                        api_key=api_key,
                        timeout_seconds=args.timeout_seconds,
                    )
                    logs.append(
                        f"=== Attempt {attempt} base_url={base_url} {name} HTTP {http_code} ===\n"
                        f"prompt_chars={len(prompt)} {endpoint['token_label']}={args.max_output_tokens}\n"
                        f"{raw}\n"
                    )
                    if http_code != 200:
                        raise RuntimeError(f"HTTP {http_code}: {raw[:500]}")
                    payload = json.loads(raw)
                    text = endpoint["extractor"](payload)
                    if not text:
                        if name == "responses":
                            status = payload.get("status")
                            raise RuntimeError(f"empty responses output text with status={status!r}")
                        raise RuntimeError("empty chat completion text")
                    output_file.write_text(text, encoding="utf-8")
                    log_file.write_text("".join(logs), encoding="utf-8")
                    return 0
                except Exception as exc:
                    logs.append(
                        f"Attempt {attempt} base_url={base_url} {name} failed: {exc}\n"
                        f"prompt_chars={len(prompt)} {endpoint['token_label']}={args.max_output_tokens}\n"
                    )

    log_file.write_text("".join(logs), encoding="utf-8")
    output_file.write_text("", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
