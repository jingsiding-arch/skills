#!/usr/bin/env python3

import argparse
import bisect
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from shutil import which


DEFAULT_CHUNK_CHARS = 12000
DEFAULT_WIKI_SPACE = "my_library"
DEFAULT_THEME = "editorial-warm"
EDITORIAL_WARM_ACCENT_BACKGROUND = "light-orange"
EDITORIAL_WARM_ACCENT_BORDER = "orange"
EDITORIAL_WARM_MUTED_BACKGROUND = "light-yellow"
EDITORIAL_WARM_MUTED_BORDER = "yellow"
EDITORIAL_WARM_NOTE_BACKGROUND = "light-gray"
EDITORIAL_WARM_NOTE_BORDER = "gray"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
CALLOUT_TAG_RE = re.compile(r"<callout\b", re.IGNORECASE)
INLINE_COLOR_RULES = {
    "semantic": (
        ("red", ("高风险", "风险", "禁止", "失败", "冲突", "超时", "驳回")),
        ("orange", ("待确认", "待复核", "需复核", "前置条件", "依赖", "注意")),
        ("green", ("已确认", "已完成", "已关闭", "成功", "生效", "通过")),
    ),
    "semantic-conservative": (
        ("red", ("高风险", "风险", "禁止", "失败", "冲突", "超时", "驳回")),
        ("orange", ("待确认", "待复核", "需复核", "前置条件", "依赖", "注意")),
    ),
}
PRD_HINTS = ("prd", "研发交付", "需求", "方案", "spec", "设计说明", "交互")
MEETING_HINTS = ("会议纪要", "会议记录", "复盘", "周报", "日报", "同步", "通知")
LABEL_PREFIX_RE = re.compile(
    r"^(?P<prefix>\s*(?:>\s*)?(?:[-*+]\s+|\d+\.\s+)?)"
    r"(?P<label>[^：:\n`<|]{1,24}?)"
    r"(?P<colon>[：:])"
    r"(?P<rest>\s*.*)$"
)
FLOW_SECTION_KEYWORDS = ("流程", "流转")
FLOWCHART_ALLOWED_PARENT_KEYWORDS = ("功能需求明细",)
FLOW_DECISION_KEYWORDS = ("是否", "如需", "若", "如果", "未", "无", "失败", "冲突", "不足", "超时", "命中", "允许", "存在")
FLOW_ACTION_SPLIT_PATTERNS = ("且未", "且无", "且如需")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a well-formatted Lark doc from a Markdown file without changing the original body content."
    )
    parser.add_argument("--input", required=True, help="Absolute path to the source Markdown file")
    parser.add_argument("--title", help="Document title; defaults to the source file stem")
    parser.add_argument("--folder-token", help="Parent folder token")
    parser.add_argument("--wiki-node", help="Parent wiki node token")
    parser.add_argument("--wiki-space", help="Target wiki space ID, e.g. my_library")
    parser.add_argument("--as", dest="identity", default="user", choices=("user", "bot"), help="Lark identity")
    parser.add_argument(
        "--chunk-chars",
        type=int,
        default=DEFAULT_CHUNK_CHARS,
        help="Preferred maximum characters per Markdown chunk",
    )
    parser.add_argument("--encoding", default="utf-8", help="Source file encoding")
    parser.add_argument("--dry-run", action="store_true", help="Pass --dry-run to lark-cli and print the plan")
    parser.add_argument(
        "--inline-color-mode",
        default="off",
        choices=("off", "auto", "semantic", "semantic-conservative"),
        help="Inline text color mode for the source body; only use semantic when the user explicitly allows body styling",
    )
    parser.add_argument(
        "--label-prefix-style",
        default="off",
        choices=("off", "blue-bold"),
        help="Style short label prefixes before a colon, e.g. 页面定位： -> blue bold label + normal body text",
    )
    parser.add_argument(
        "--beautify-mode",
        default="light",
        choices=("off", "light"),
        help="Document beautify mode. light applies the selected theme with restrained dividers/callouts/grid blocks.",
    )
    parser.add_argument(
        "--theme",
        default=DEFAULT_THEME,
        choices=(DEFAULT_THEME,),
        help="Visual theme used when beautify mode is enabled.",
    )
    parser.add_argument(
        "--omit-section-title",
        action="append",
        default=[],
        help="Exact heading title to omit as a whole section; may be passed multiple times",
    )
    parser.add_argument(
        "--preface-mode",
        default="off",
        choices=("off", "auto"),
        help="Deprecated compatibility flag. Preface blocks are no longer generated and this option is ignored.",
    )
    parser.add_argument(
        "--navigation-mode",
        default="off",
        choices=("off", "auto"),
        help="Deprecated compatibility flag. Reading navigation is no longer generated and this option is ignored.",
    )
    parser.add_argument(
        "--mindmap-mode",
        default="off",
        choices=("off", "auto"),
        help="Whether to add a structural mind map whiteboard; off by default, auto tries to create and upload one without failing the whole document if rendering is unavailable",
    )
    parser.add_argument(
        "--section-hint-mode",
        default="off",
        choices=("off", "auto"),
        help="Whether to insert AI-generated section hint callouts before detected requirement/mobile sections; off by default",
    )
    parser.add_argument(
        "--flowchart-mode",
        default="auto",
        choices=("off", "auto"),
        help="Whether to insert flowchart whiteboards for sections whose headings mention 流程/流转",
    )
    parser.add_argument(
        "--no-preface",
        action="store_true",
        help="Deprecated compatibility alias. Has no effect because preface blocks are no longer generated.",
    )
    args = parser.parse_args()

    destinations = [args.folder_token, args.wiki_node, args.wiki_space]
    if sum(value is not None for value in destinations) > 1:
        parser.error("Only one of --folder-token, --wiki-node, or --wiki-space may be provided")
    if args.chunk_chars < 1000:
        parser.error("--chunk-chars must be at least 1000")
    if sum(value is not None for value in destinations) == 0:
        args.wiki_space = DEFAULT_WIKI_SPACE
        args.defaulted_destination = True
    else:
        args.defaulted_destination = False
    return args


def load_source(path: Path, encoding: str) -> str:
    if not path.is_absolute():
        raise ValueError("--input must be an absolute path")
    if path.suffix.lower() != ".md":
        raise ValueError("Source file must end with .md")
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Source path is not a file: {path}")
    return path.read_text(encoding=encoding)


def normalize_heading_title(value: str) -> str:
    value = re.sub(r"^#{1,6}\s+", "", value.strip())
    return re.sub(r"\s+", " ", value).strip()


def heading_display_title(value: str) -> str:
    return value.replace("`", "").strip()


def omit_sections_by_title(text: str, section_titles: list[str]) -> tuple[str, list[str]]:
    if not section_titles:
        return text, []

    requested = {normalize_heading_title(title) for title in section_titles if normalize_heading_title(title)}
    if not requested:
        return text, []

    lines = text.splitlines(keepends=True)
    headings: list[tuple[int, int, str]] = []

    for index, line in enumerate(lines):
        match = HEADING_RE.match(line.rstrip("\n"))
        if not match:
            continue
        level = len(match.group(1))
        title = normalize_heading_title(match.group(2))
        headings.append((index, level, title))

    ranges: list[tuple[int, int, str]] = []
    for idx, (line_index, level, title) in enumerate(headings):
        if title not in requested:
            continue
        end_index = len(lines)
        for next_line_index, next_level, _next_title in headings[idx + 1 :]:
            if next_level <= level:
                end_index = next_line_index
                break
        ranges.append((line_index, end_index, title))

    if not ranges:
        return text, []

    keep_lines: list[str] = []
    cursor = 0
    omitted_titles: list[str] = []
    for start, end, title in ranges:
        if start < cursor:
            continue
        keep_lines.extend(lines[cursor:start])
        cursor = end
        omitted_titles.append(title)
    keep_lines.extend(lines[cursor:])

    return "".join(keep_lines), omitted_titles


def extract_headings(text: str) -> list[tuple[int, str]]:
    headings: list[tuple[int, str]] = []
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if not match:
            continue
        headings.append((len(match.group(1)), normalize_heading_title(match.group(2))))
    return headings


def extract_sections(text: str) -> list[tuple[int, str, str]]:
    lines = text.splitlines(keepends=True)
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line.rstrip("\n"))
        if not match:
            continue
        headings.append((index, len(match.group(1)), heading_display_title(normalize_heading_title(match.group(2)))))

    sections: list[tuple[int, str, str]] = []
    for idx, (line_index, level, title) in enumerate(headings):
        end_index = len(lines)
        for next_line_index, next_level, _ in headings[idx + 1 :]:
            if next_level <= level:
                end_index = next_line_index
                break
        body = "".join(lines[line_index + 1 : end_index])
        sections.append((level, title, body))
    return sections


def wrap_semantic_keyword(segment: str, color: str, keyword: str) -> str:
    pattern = re.escape(keyword)
    replacement = f'<text color="{color}">{keyword}</text>'
    return re.sub(pattern, replacement, segment)


def apply_semantic_inline_color(text: str, mode: str) -> str:
    colored_lines: list[str] = []
    inside_fence = False
    color_rules = INLINE_COLOR_RULES.get(mode, ())

    for line in text.splitlines(keepends=True):
        if re.match(r"^\s*```", line):
            inside_fence = not inside_fence
            colored_lines.append(line)
            continue

        if inside_fence or line.lstrip().startswith("|") or "<text " in line:
            colored_lines.append(line)
            continue

        parts = re.split(r"(`[^`]*`)", line)
        for index, part in enumerate(parts):
            if index % 2 == 1:
                continue
            for color, keywords in color_rules:
                for keyword in keywords:
                    part = wrap_semantic_keyword(part, color, keyword)
            parts[index] = part
        colored_lines.append("".join(parts))

    return "".join(colored_lines)


def apply_label_prefix_style(text: str, style: str) -> str:
    if style == "off":
        return text

    styled_lines: list[str] = []
    inside_fence = False

    for line in text.splitlines(keepends=True):
        if re.match(r"^\s*```", line):
            inside_fence = not inside_fence
            styled_lines.append(line)
            continue

        stripped = line.lstrip()
        if inside_fence or stripped.startswith("|") or stripped.startswith("#") or "<text " in line:
            styled_lines.append(line)
            continue

        has_newline = line.endswith("\n")
        content = line[:-1] if has_newline else line
        match = LABEL_PREFIX_RE.match(content)
        if not match:
            styled_lines.append(line)
            continue

        label = match.group("label").strip()
        if label.startswith(("http", "/")):
            styled_lines.append(line)
            continue

        prefix = match.group("prefix") or ""
        colon = match.group("colon")
        rest = match.group("rest")
        styled = f'{prefix}<text color="blue">**{label}**</text>{colon}{rest}'
        styled_lines.append(styled + ("\n" if has_newline else ""))

    return "".join(styled_lines)


def choose_inline_color_mode(source_text: str, source_path: Path, requested_mode: str) -> tuple[str, str]:
    if requested_mode != "auto":
        return requested_mode, ""

    lowered_name = source_path.name.lower()
    lowered_text = source_text[:8000].lower()

    if any(hint in lowered_name or hint in lowered_text for hint in PRD_HINTS):
        return "semantic-conservative", "Detected PRD/spec-style content; using the restrained profile."
    if any(hint in source_path.name or hint in source_text[:8000] for hint in MEETING_HINTS):
        return "semantic", "Detected meeting/report-style content; using the stronger prompt-oriented profile."
    return "semantic-conservative", "No strong content signal found; defaulting to the restrained profile."


def build_mindmap_intro_markdown() -> str:
    return "\n".join(
        [
            "## 结构导图",
            "",
            f'<callout emoji="🗺️" background-color="{EDITORIAL_WARM_ACCENT_BACKGROUND}" border-color="{EDITORIAL_WARM_ACCENT_BORDER}">',
            "下方思维导图用于快速把握全文结构；详细规则与字段仍以正文章节为准。",
            "</callout>",
            "",
            '<whiteboard type="blank"></whiteboard>',
            "",
            "---",
            "",
        ]
    )


def build_section_hint_markdown(text: str) -> str:
    return "\n".join(
        [
            f'<callout emoji="🗂️" background-color="{EDITORIAL_WARM_ACCENT_BACKGROUND}" border-color="{EDITORIAL_WARM_ACCENT_BORDER}">',
            text,
            "</callout>",
            "",
        ]
    )


def find_first_heading_title(headings: list[tuple[int, str]]) -> str | None:
    return heading_display_title(headings[0][1]) if headings else None


def find_requirements_heading(headings: list[tuple[int, str]]) -> str | None:
    for _level, title in headings:
        clean_title = heading_display_title(title)
        if "功能需求" in clean_title or "需求明细" in clean_title:
            return clean_title
    return None


def find_mobile_heading(headings: list[tuple[int, str]]) -> str | None:
    for _level, title in headings:
        clean_title = heading_display_title(title)
        if any(keyword in clean_title for keyword in ("我的考勤", "移动", "动态二维码打卡", "蓝牙打卡")):
            return clean_title
    return None


def build_mermaid_mindmap(headings: list[tuple[int, str]], root_title: str) -> str:
    lines = ["mindmap", f"  root(({root_title}))"]
    current_level2 = None
    level2_children_count = 0
    level3_count_for_current = 0

    for level, title in headings:
        clean_title = heading_display_title(title)
        if level == 1:
            continue
        if level == 2:
            current_level2 = clean_title
            level2_children_count += 1
            level3_count_for_current = 0
            lines.append(f"    {clean_title}")
        elif level == 3 and current_level2 and level3_count_for_current < 8:
            level3_count_for_current += 1
            lines.append(f"      {clean_title}")

    return "\n".join(lines) + "\n"


def normalize_flow_text(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value.strip(" -:：")


def split_flow_step_segments(step: str) -> list[str]:
    parts = re.split(r"\s*(?:；|;|->|→|⇒)\s*", step)
    return [normalize_flow_text(part) for part in parts if normalize_flow_text(part)]


def is_decision_label(label: str) -> bool:
    if not label:
        return False
    if label.endswith(("?", "？")) or "是否" in label:
        return True
    return any(keyword in label for keyword in FLOW_DECISION_KEYWORDS)


def to_decision_label(label: str) -> str:
    clean = normalize_flow_text(label)
    if clean.endswith(("?", "？")) or "是否" in clean:
        return clean
    if clean.startswith("如需"):
        return clean + "？"
    if clean.startswith(("未", "无")):
        return clean + "？"
    if any(keyword in clean for keyword in ("失败", "冲突", "不足", "超时", "命中", "允许", "存在")):
        return clean + "？"
    return clean


def decompose_flow_segment(segment: str) -> list[tuple[str, str]]:
    normalized = normalize_flow_text(segment)
    if not normalized:
        return []

    conditional_match = re.match(r"^(如需|若|如果)(.+?)则(.+)$", normalized)
    if conditional_match:
        decision = normalize_flow_text(conditional_match.group(1) + conditional_match.group(2))
        action = normalize_flow_text(conditional_match.group(3))
        parts: list[tuple[str, str]] = []
        if decision:
            parts.append(("decision", to_decision_label(decision)))
        if action:
            parts.append(("process", action))
        return parts

    for token in FLOW_ACTION_SPLIT_PATTERNS:
        if token in normalized:
            action, condition = normalized.split(token, 1)
            action = normalize_flow_text(action)
            condition = normalize_flow_text(token[1:] + condition)
            parts: list[tuple[str, str]] = []
            if action:
                parts.append(("process", action))
            if condition:
                parts.append(("decision", to_decision_label(condition)))
            return parts

    if is_decision_label(normalized):
        return [("decision", to_decision_label(normalized))]
    return [("process", normalized)]


def extract_flow_steps_from_body(body: str) -> list[str]:
    ordered_steps: list[str] = []
    bullet_steps: list[str] = []
    for line in body.splitlines():
        ordered_match = re.match(r"^\s*\d+\.\s+(.+?)\s*$", line)
        if ordered_match:
            step = normalize_flow_text(ordered_match.group(1))
            if step:
                ordered_steps.append(step)
            continue

        bullet_match = re.match(r"^\s*[-*+]\s+(.+?)\s*$", line)
        if not bullet_match:
            continue
        if "**" in line:
            continue
        match = bullet_match
        if not match:
            continue
        step = normalize_flow_text(match.group(1))
        if step:
            bullet_steps.append(step)
    if len(ordered_steps) >= 2:
        return ordered_steps[:10]
    if len(bullet_steps) >= 2:
        return bullet_steps[:8]

    table_rows: list[str] = []
    for line in body.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [normalize_flow_text(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) < 1:
            continue
        if all(set(cell) <= {"-"} for cell in cells if cell):
            continue
        first = cells[0] if cells else ""
        if not first or first in {"异常场景", "触发条件", "系统处理", "人工处理", "场景", "验收标准", "验收方式"}:
            continue
        table_rows.append(first)
    if len(table_rows) >= 2:
        return table_rows[:8]

    sentences = re.split(r"[。；\n]+", body)
    fallback = [normalize_flow_text(sentence) for sentence in sentences if normalize_flow_text(sentence)]
    return fallback[:6] if len(fallback) >= 2 else []


def build_mermaid_flowchart(title: str, body: str) -> str | None:
    steps = extract_flow_steps_from_body(body)
    if len(steps) < 2:
        return None

    special = build_special_branching_flowchart(steps)
    if special:
        return special

    lines = ["flowchart TD"]
    lines.append('  START(["开始"])')
    lines.append('  END(["结束"])')

    node_index = 1
    previous_node = "START"
    previous_shape = "start"

    for step in steps:
        segments = split_flow_step_segments(step)
        if not segments:
            continue
        for segment in segments:
            for shape, label in decompose_flow_segment(segment):
                node_name = f"N{node_index}"
                node_index += 1
                safe = label.replace('"', "'")
                if shape == "decision":
                    lines.append(f'  {node_name}{{"{safe}"}}')
                    edge = f"  {previous_node} --> {node_name}" if previous_shape != "decision" else f'  {previous_node} -->|"是"| {node_name}'
                else:
                    lines.append(f'  {node_name}["{safe}"]')
                    edge = f"  {previous_node} --> {node_name}" if previous_shape != "decision" else f'  {previous_node} -->|"是"| {node_name}'
                lines.append(edge)
                previous_node = node_name
                previous_shape = shape

    if previous_node == "START":
        return None

    lines.append(f"  {previous_node} --> END")
    return "\n".join(lines) + "\n"


def build_special_branching_flowchart(steps: list[str]) -> str | None:
    review = build_review_branch_flowchart(steps)
    if review:
        return review

    confirm = build_confirm_timeout_flowchart(steps)
    if confirm:
        return confirm

    return None


def mermaid_safe_label(label: str) -> str:
    return normalize_flow_text(label).replace('"', "'")


def build_review_branch_flowchart(steps: list[str]) -> str | None:
    if len(steps) < 4:
        return None
    if not any("审批通过" in step for step in steps):
        return None
    if not any("审批驳回" in step for step in steps):
        return None
    if not any("超限" in step or "不足" in step for step in steps):
        return None

    first = steps[0]
    approve = next((step for step in steps if "审批通过" in step), None)
    reject = next((step for step in steps if "审批驳回" in step), None)
    limited = next((step for step in steps if step != first and ("超限自动驳回" in step or "次数不足" in step or step.startswith("系统发现"))), None)
    if not first or not approve or not reject or not limited:
        return None

    first_segments = split_flow_step_segments(first)
    approve_segments = split_flow_step_segments(approve)
    reject_segments = split_flow_step_segments(reject)
    limited_segments = split_flow_step_segments(limited)
    if len(first_segments) < 3:
        return None

    submit_label = normalize_flow_text(first_segments[0].split("且", 1)[0])
    decision_label = "未超限？"
    pending_label = first_segments[1]
    waiting_label = first_segments[2]

    approve_action = approve_segments[0] if approve_segments else "管理员审批通过"
    approve_result = approve_segments[1] if len(approve_segments) > 1 else "申请进入已通过"
    approve_follow = approve_segments[2] if len(approve_segments) > 2 else ""

    reject_action = reject_segments[0] if reject_segments else "管理员审批驳回"
    reject_result = reject_segments[1] if len(reject_segments) > 1 else "申请进入已驳回"
    reject_follow = reject_segments[2] if len(reject_segments) > 2 else ""

    limited_action = limited_segments[0] if limited_segments else "系统发现剩余次数不足"
    limited_result = limited_segments[1] if len(limited_segments) > 1 else "申请进入超限自动驳回"
    limited_follow = limited_segments[2] if len(limited_segments) > 2 else ""

    submit_label = mermaid_safe_label(submit_label)
    pending_label = mermaid_safe_label(pending_label)
    waiting_label = mermaid_safe_label(waiting_label)
    approve_action = mermaid_safe_label(approve_action)
    approve_result = mermaid_safe_label(approve_result)
    approve_follow = mermaid_safe_label(approve_follow) if approve_follow else ""
    reject_action = mermaid_safe_label(reject_action)
    reject_result = mermaid_safe_label(reject_result)
    reject_follow = mermaid_safe_label(reject_follow) if reject_follow else ""
    limited_action = mermaid_safe_label(limited_action)
    limited_result = mermaid_safe_label(limited_result)
    limited_follow = mermaid_safe_label(limited_follow) if limited_follow else ""

    lines = [
        "flowchart TD",
        '  START(["开始"])',
        '  END(["结束"])',
        f'  N1["{submit_label}"]',
        f'  N2{{"{decision_label}"}}',
        f'  N3["{pending_label}"]',
        f'  N4["{waiting_label}"]',
        '  N5{"审批结果？"}',
        f'  N6["{approve_action}"]',
        f'  N7["{approve_result}"]',
        f'  N8["{reject_action}"]',
        f'  N9["{reject_result}"]',
        f'  N10["{limited_action}"]',
        f'  N11["{limited_result}"]',
        "  START --> N1",
        "  N1 --> N2",
        '  N2 -->|"是"| N3',
        '  N2 -->|"否"| N10',
        "  N3 --> N4",
        "  N4 --> N5",
        '  N5 -->|"通过"| N6',
        '  N5 -->|"驳回"| N8',
        "  N6 --> N7",
        "  N8 --> N9",
        "  N10 --> N11",
    ]

    next_index = 12
    if approve_follow:
        approve_parts = decompose_flow_segment(approve_follow)
        if len(approve_parts) == 2 and approve_parts[0][0] == "decision" and approve_parts[1][0] == "process":
            decision_node = f"N{next_index}"
            process_node = f"N{next_index + 1}"
            next_index += 2
            lines.extend([
                f'  {decision_node}{{"{mermaid_safe_label(approve_parts[0][1])}"}}',
                "  N7 --> " + decision_node,
                f'  {process_node}["{mermaid_safe_label(approve_parts[1][1])}"]',
                f'  {decision_node} -->|"是"| {process_node}',
                f'  {decision_node} -->|"否"| END',
                f"  {process_node} --> END",
            ])
        else:
            lines.extend([
                f'  N{next_index}{{"{mermaid_safe_label(to_decision_label(approve_follow))}"}}',
                "  N7 --> " + f"N{next_index}",
                f'  N{next_index} -->|"否"| END',
            ])
            next_index += 1
    else:
        lines.append("  N7 --> END")

    if reject_follow:
        lines.extend([
            f'  N{next_index}["{reject_follow}"]',
            "  N9 --> " + f"N{next_index}",
            f"  N{next_index} --> END",
        ])
        next_index += 1
    else:
        lines.append("  N9 --> END")

    if limited_follow:
        lines.extend([
            f'  N{next_index}["{limited_follow}"]',
            "  N11 --> " + f"N{next_index}",
            f"  N{next_index} --> END",
        ])
    else:
        lines.append("  N11 --> END")

    return "\n".join(lines) + "\n"


def build_confirm_timeout_flowchart(steps: list[str]) -> str | None:
    if len(steps) < 3:
        return None
    timeout_step = next((step for step in steps if "超时" in step), None)
    confirm_step = next((step for step in steps if "提交确认" in step), None)
    if not timeout_step or not confirm_step:
        return None

    wait_index = None
    for idx, step in enumerate(steps):
        if "等待" in step and ("结单" in step or "确认" in step):
            wait_index = idx
            break
    if wait_index is None:
        return None

    timeout_index = steps.index(timeout_step)
    confirm_index = steps.index(confirm_step)
    if confirm_index <= wait_index:
        return None

    lines = ["flowchart TD", '  START(["开始"])', '  END(["结束"])']
    node_index = 1
    previous = "START"

    for step in steps[: wait_index + 1]:
        for segment in split_flow_step_segments(step):
            label = mermaid_safe_label(segment)
            node = f"N{node_index}"
            node_index += 1
            lines.append(f'  {node}["{label}"]')
            lines.append(f"  {previous} --> {node}")
            previous = node

    decision_node = f"N{node_index}"
    node_index += 1
    lines.append(f'  {decision_node}{{"超时未确认？"}}')
    lines.append(f"  {previous} --> {decision_node}")

    confirm_segments = split_flow_step_segments(confirm_step)
    confirm_branch_start = None
    prev_confirm = None
    for segment in confirm_segments:
        label = mermaid_safe_label(segment)
        node = f"N{node_index}"
        node_index += 1
        lines.append(f'  {node}["{label}"]')
        if confirm_branch_start is None:
            confirm_branch_start = node
            lines.append(f'  {decision_node} -->|"否"| {node}')
        else:
            lines.append(f"  {prev_confirm} --> {node}")
        prev_confirm = node

    timeout_segments = split_flow_step_segments(timeout_step)
    timeout_branch_start = None
    prev_timeout = None
    for segment in timeout_segments:
        label = mermaid_safe_label(segment)
        node = f"N{node_index}"
        node_index += 1
        lines.append(f'  {node}["{label}"]')
        if timeout_branch_start is None:
            timeout_branch_start = node
            lines.append(f'  {decision_node} -->|"是"| {node}')
        else:
            lines.append(f"  {prev_timeout} --> {node}")
        prev_timeout = node

    continuation_steps = steps[max(confirm_index, timeout_index) + 1 :]
    if continuation_steps:
        merge_node = f"N{node_index}"
        node_index += 1
        lines.append(f'  {merge_node}["{mermaid_safe_label(continuation_steps[0].split("->")[0])}"]')
        if prev_confirm:
            lines.append(f"  {prev_confirm} --> {merge_node}")
        if prev_timeout:
            lines.append(f"  {prev_timeout} --> {merge_node}")
        previous = merge_node

        for step in continuation_steps:
            segments = split_flow_step_segments(step)
            if previous == merge_node and segments:
                segments = segments[1:]
            for segment in segments:
                label = mermaid_safe_label(segment)
                node = f"N{node_index}"
                node_index += 1
                lines.append(f'  {node}["{label}"]')
                lines.append(f"  {previous} --> {node}")
                previous = node
        lines.append(f"  {previous} --> END")
    else:
        if prev_confirm:
            lines.append(f"  {prev_confirm} --> END")
        if prev_timeout:
            lines.append(f"  {prev_timeout} --> END")

    return "\n".join(lines) + "\n"


def section_path_allows_flowchart(path_titles: list[str]) -> bool:
    return any(
        any(keyword in title for keyword in FLOWCHART_ALLOWED_PARENT_KEYWORDS)
        for title in path_titles
    )


def find_flow_sections(sections: list[tuple[int, str, str]]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    path_stack: list[tuple[int, str]] = []
    for level, title, body in sections:
        while path_stack and path_stack[-1][0] >= level:
            path_stack.pop()
        path_stack.append((level, title))
        path_titles = [item_title for _item_level, item_title in path_stack]
        if not section_path_allows_flowchart(path_titles):
            continue
        if not any(keyword in title for keyword in FLOW_SECTION_KEYWORDS):
            continue
        if build_mermaid_flowchart(title, body) is None:
            continue
        result.append((title, body))
    return result


def find_boundaries(text: str) -> list[int]:
    boundaries = {len(text)}
    inside_fence = False
    offset = 0

    for line in text.splitlines(keepends=True):
        if re.match(r"^\s*```", line):
            if not inside_fence and 0 < offset < len(text):
                boundaries.add(offset)
            elif inside_fence and 0 < offset + len(line) < len(text):
                boundaries.add(offset + len(line))
            inside_fence = not inside_fence
            offset += len(line)
            continue

        if not inside_fence:
            if re.match(r"^#{1,6}\s", line) and 0 < offset < len(text):
                boundaries.add(offset)
            if re.match(r"^\s*$", line) and 0 < offset < len(text):
                boundaries.add(offset)
            if re.match(r"^---\s*$", line.rstrip("\n")) and 0 < offset < len(text):
                boundaries.add(offset)

        offset += len(line)

    return sorted(boundaries)


def split_markdown(text: str, max_chars: int, first_chunk_budget: int | None = None) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    boundaries = find_boundaries(text)
    chunks: list[str] = []
    start = 0

    while start < len(text):
        current_budget = first_chunk_budget if not chunks and first_chunk_budget is not None else max_chars
        target = min(start + current_budget, len(text))
        if target >= len(text):
            chunks.append(text[start:])
            break

        lower_bound = start + current_budget // 2
        right = bisect.bisect_right(boundaries, target)
        left = bisect.bisect_left(boundaries, lower_bound)

        if right > left:
            split_at = boundaries[right - 1]
        elif right < len(boundaries):
            # Keep fenced code blocks intact even if that means a temporary oversize chunk.
            split_at = boundaries[right]
        else:
            split_at = target
        if split_at <= start:
            split_at = target

        chunks.append(text[start:split_at])
        start = split_at

    return [chunk for chunk in chunks if chunk]


def source_has_fenced_code(text: str) -> bool:
    return bool(re.search(r"(?m)^```", text))


def source_contains_callout_tag(text: str) -> bool:
    return CALLOUT_TAG_RE.search(text) is not None


def build_callout(markdown: str, emoji: str, background_color: str, border_color: str) -> str:
    body = markdown.strip()
    if not body:
        return ""
    return "\n".join(
        [
            f'<callout emoji="{emoji}" background-color="{background_color}" border-color="{border_color}">',
            body,
            "</callout>",
            "",
        ]
    )


def parse_level2_sections(text: str) -> tuple[str, list[tuple[str, str, str]]]:
    lines = text.splitlines(keepends=True)
    preamble: list[str] = []
    sections: list[tuple[str, str, str]] = []
    current_heading_line: str | None = None
    current_title: str | None = None
    current_body: list[str] = []

    for line in lines:
        match = HEADING_RE.match(line.rstrip("\n"))
        is_level2 = bool(match and len(match.group(1)) == 2)
        if is_level2:
            if current_heading_line is None:
                current_heading_line = line
                current_title = normalize_heading_title(match.group(2))
                continue
            sections.append((current_heading_line, current_title or "", "".join(current_body)))
            current_heading_line = line
            current_title = normalize_heading_title(match.group(2))
            current_body = []
            continue

        if current_heading_line is None:
            preamble.append(line)
        else:
            current_body.append(line)

    if current_heading_line is not None:
        sections.append((current_heading_line, current_title or "", "".join(current_body)))

    return "".join(preamble), sections


def extract_leading_heading_block(text: str) -> tuple[str | None, str]:
    lines = text.splitlines(keepends=True)
    if not lines:
        return None, ""

    match = HEADING_RE.match(lines[0].rstrip("\n"))
    if not match or len(match.group(1)) != 1:
        return None, text

    return lines[0], "".join(lines[1:])


def body_looks_like_meta_block(body: str) -> bool:
    if re.search(r"(?m)^\|", body):
        return False

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if len(lines) < 2 or len(lines) > 8:
        return False

    score = 0
    for line in lines:
        if len(line) <= 36:
            score += 1
        if any(marker in line for marker in ("：", ":", "·", "|")):
            score += 1
        if line.startswith(("-", "*")):
            score += 1

    return score >= len(lines) + 1


def strip_boundary_separators(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^(?:---\s*)+", "", cleaned)
    cleaned = re.sub(r"(?:\s*---)+$", "", cleaned)
    return cleaned.strip()


def build_editorial_warm_intro(preamble: str) -> str:
    heading_line, remainder = extract_leading_heading_block(preamble.lstrip("\n"))
    if not heading_line:
        body = strip_boundary_separators(preamble)
        if not body:
            return ""
        if body_looks_like_meta_block(body):
            return build_callout(body, "✦", EDITORIAL_WARM_MUTED_BACKGROUND, EDITORIAL_WARM_ACCENT_BORDER)
        return body + "\n\n"

    output = [heading_line.rstrip() + "\n\n"]
    body = strip_boundary_separators(remainder)
    if body:
        if body_looks_like_meta_block(body):
            output.append(build_callout(body, "✦", EDITORIAL_WARM_MUTED_BACKGROUND, EDITORIAL_WARM_ACCENT_BORDER))
        else:
            output.append(body + "\n\n")
    output.append("---\n\n")
    return "".join(output)


def build_two_column_sections(left_heading: str, left_body: str, right_heading: str, right_body: str) -> str:
    left = f"{left_heading.rstrip()}\n\n{strip_boundary_separators(left_body)}".strip()
    right = f"{right_heading.rstrip()}\n\n{strip_boundary_separators(right_body)}".strip()
    return "\n".join(
        [
            '<grid cols="2">',
            '<column>',
            "",
            left,
            "",
            '</column>',
            '<column>',
            "",
            right,
            "",
            '</column>',
            '</grid>',
            "",
        ]
    )


def wrap_editorial_warm_section_body(title: str, body: str) -> str:
    stripped = strip_boundary_separators(body)
    if not stripped:
        return ""

    if re.search(r"(?m)^\|", stripped):
        return stripped + "\n\n"

    if "实现方案" in title:
        return build_callout(stripped, "✦", EDITORIAL_WARM_ACCENT_BACKGROUND, EDITORIAL_WARM_ACCENT_BORDER)
    if "当前文档下的待确认项" in title or "待确认" in title:
        return build_callout(stripped, "!", EDITORIAL_WARM_MUTED_BACKGROUND, EDITORIAL_WARM_MUTED_BORDER)
    if any(keyword in title for keyword in ("适用版本", "版本信息", "摘要", "说明", "作者", "花叔")) or body_looks_like_meta_block(stripped):
        return build_callout(stripped, "·", EDITORIAL_WARM_NOTE_BACKGROUND, EDITORIAL_WARM_NOTE_BORDER)
    return stripped + "\n\n"


def apply_editorial_warm_theme(text: str) -> str:
    preamble, sections = parse_level2_sections(text)
    if not sections:
        return text

    output: list[str] = []
    if preamble.strip():
        output.append(build_editorial_warm_intro(preamble))

    index = 0
    rendered_any = False
    while index < len(sections):
        heading_line, title, body = sections[index]

        if rendered_any:
            output.append("---\n\n")

        if "建议优先回归场景" in title and index + 1 < len(sections):
            next_heading, next_title, next_body = sections[index + 1]
            if "当前文档下的待确认项" in next_title:
                output.append(build_two_column_sections(heading_line, body, next_heading, next_body))
                rendered_any = True
                index += 2
                continue

        output.append(heading_line.rstrip() + "\n\n")
        output.append(wrap_editorial_warm_section_body(title, body))

        rendered_any = True
        index += 1

    return "".join(output).rstrip() + "\n"


def apply_theme_beautify(text: str, theme: str) -> str:
    if theme == "editorial-warm":
        return apply_editorial_warm_theme(text)
    return text


def plan_source_chunks(source_text: str, max_chars: int) -> list[str]:
    return split_markdown(source_text, max_chars)


def build_create_markdown(source_chunks: list[str]) -> str:
    return source_chunks[0]


def build_command(args: argparse.Namespace, markdown: str, doc_ref: str | None = None) -> list[str]:
    if doc_ref is None:
        command = [
            "lark-cli",
            "docs",
            "+create",
            "--as",
            args.identity,
            "--title",
            args.title,
            "--markdown",
            markdown,
        ]
        if args.folder_token:
            command.extend(["--folder-token", args.folder_token])
        elif args.wiki_node:
            command.extend(["--wiki-node", args.wiki_node])
        elif args.wiki_space:
            command.extend(["--wiki-space", args.wiki_space])
    else:
        command = [
            "lark-cli",
            "docs",
            "+update",
            "--as",
            args.identity,
            "--doc",
            doc_ref,
            "--mode",
            "append",
            "--markdown",
            markdown,
        ]

    if args.dry_run:
        command.append("--dry-run")

    return command


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True)


def run_lark_preflight(identity: str) -> dict:
    doctor_command = ["lark-cli", "doctor"]
    doctor_result = run_command(doctor_command)
    doctor_payload = parse_json_payload(doctor_result.stdout)

    auth_command = ["lark-cli", "auth", "status"]
    auth_result = run_command(auth_command) if identity == "user" else None
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
        }
        if identity == "user"
        else None,
        "issues": issues,
        "remediation": remediation,
    }


def parse_json_payload(text: str) -> dict | None:
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
            payload = json.loads(stripped[start : end + 1])
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def extract_field(payload: dict | None, *keys: str) -> str | None:
    if not payload:
        return None
    for container in (payload, payload.get("data")):
        if isinstance(container, dict):
            for key in keys:
                value = container.get(key)
                if isinstance(value, str) and value:
                    return value
    return None


def extract_doc_refs(stdout: str) -> tuple[str | None, str | None]:
    payload = parse_json_payload(stdout)
    doc_id = extract_field(payload, "doc_id", "docId")
    doc_url = extract_field(payload, "doc_url", "docUrl", "url")

    if not doc_id:
        token_match = re.search(r"\b(?:doxcn|doccn|wikcn)[A-Za-z0-9]+\b", stdout)
        if token_match:
            doc_id = token_match.group(0)
    if not doc_url:
        url_match = re.search(r"https?://\S+/(?:docx|doc|wiki)/[A-Za-z0-9]+", stdout)
        if url_match:
            doc_url = url_match.group(0)

    return doc_id, doc_url


def print_failure(command: list[str], result: subprocess.CompletedProcess[str], chunk_index: int | None = None) -> None:
    message = {
        "ok": False,
        "chunk_index": chunk_index,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    print(json.dumps(message, ensure_ascii=False, indent=2))


def run_update_command(doc_ref: str, markdown: str, mode: str, args: argparse.Namespace, selection_by_title: str | None = None) -> subprocess.CompletedProcess[str]:
    command = [
        "lark-cli",
        "docs",
        "+update",
        "--as",
        args.identity,
        "--doc",
        doc_ref,
        "--mode",
        mode,
        "--markdown",
        markdown,
    ]
    if selection_by_title:
        command.extend(["--selection-by-title", selection_by_title])
    return run_command(command)


def upload_whiteboard_mermaid(board_token: str, mermaid: str, args: argparse.Namespace) -> str | None:
    if which("npx") is None:
        return "Whiteboard render skipped: `npx` is not available in PATH."
    with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False, encoding="utf-8") as handle:
        handle.write(mermaid)
        temp_path = handle.name

    try:
        whiteboard_result = subprocess.run(
            ["npx", "-y", "@larksuite/whiteboard-cli@^0.1.0", "--to", "openapi", "-i", temp_path, "--format", "json"],
            capture_output=True,
            text=True,
        )
        if whiteboard_result.returncode != 0:
            return f"Whiteboard render skipped: {whiteboard_result.stderr.strip() or whiteboard_result.stdout.strip()}"

        upload_result = subprocess.run(
            [
                "lark-cli",
                "docs",
                "+whiteboard-update",
                "--whiteboard-token",
                board_token,
                "--as",
                args.identity,
                "--yes",
            ],
            input=whiteboard_result.stdout,
            capture_output=True,
            text=True,
        )
        if upload_result.returncode != 0:
            return f"Whiteboard upload skipped: {upload_result.stderr.strip() or upload_result.stdout.strip()}"
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    return None


def upload_mindmap(doc_ref: str, board_token: str, headings: list[tuple[int, str]], root_title: str, args: argparse.Namespace) -> str | None:
    mermaid = build_mermaid_mindmap(headings, root_title)
    return upload_whiteboard_mermaid(board_token, mermaid, args)


def main() -> int:
    args = parse_args()

    if which("lark-cli") is None:
        print(json.dumps({"ok": False, "error": "lark-cli not found in PATH"}, ensure_ascii=False, indent=2))
        return 1

    source_path = Path(args.input).resolve()
    try:
        source_text = load_source(source_path, args.encoding)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    filtered_text, omitted_titles = omit_sections_by_title(source_text, args.omit_section_title)
    preflight = run_lark_preflight(args.identity)
    headings = extract_headings(filtered_text)
    sections = extract_sections(filtered_text)
    flow_sections = find_flow_sections(sections) if args.flowchart_mode == "auto" else []
    effective_color_mode, color_mode_reason = choose_inline_color_mode(filtered_text, source_path, args.inline_color_mode)
    body_text = apply_label_prefix_style(filtered_text, args.label_prefix_style)
    body_text = apply_semantic_inline_color(body_text, effective_color_mode) if effective_color_mode != "off" else body_text
    effective_beautify_mode = args.beautify_mode
    beautify_mode_reason = ""
    compatibility_warnings: list[str] = []
    if args.preface_mode != "off" or args.no_preface:
        compatibility_warnings.append("Preface blocks are deprecated and ignored.")
    if args.navigation_mode != "off":
        compatibility_warnings.append("Reading navigation is deprecated and ignored.")
    if args.beautify_mode == "light" and source_contains_callout_tag(body_text):
        effective_beautify_mode = "off"
        beautify_mode_reason = "Detected hand-authored <callout> blocks in the source Markdown, so beautify mode was downgraded to off to avoid nested callout rendering issues in Lark."
    if effective_beautify_mode == "light":
        body_text = apply_theme_beautify(body_text, args.theme)

    args.title = args.title or source_path.stem
    source_chunks = plan_source_chunks(body_text, args.chunk_chars)
    create_markdown = build_create_markdown(source_chunks)

    if args.dry_run:
        summary = {
            "ok": True,
            "dry_run": True,
            "source": str(source_path),
            "title": args.title,
            "identity": args.identity,
            "target": {
                "folder_token": args.folder_token,
                "wiki_node": args.wiki_node,
                "wiki_space": args.wiki_space,
                "defaulted_to_my_library": args.defaulted_destination,
            },
            "preflight": preflight,
            "inline_color_mode_requested": args.inline_color_mode,
            "inline_color_mode": effective_color_mode,
            "inline_color_mode_reason": color_mode_reason,
            "label_prefix_style": args.label_prefix_style,
            "beautify_mode_requested": args.beautify_mode,
            "beautify_mode": effective_beautify_mode,
            "beautify_mode_reason": beautify_mode_reason,
            "theme": args.theme,
            "omit_section_titles_requested": args.omit_section_title,
            "omit_section_titles_applied": omitted_titles,
            "section_hint_mode": args.section_hint_mode,
            "flowchart_mode": args.flowchart_mode,
            "flowchart_headings": [title for title, _body in flow_sections],
            "source_contains_code_block": source_has_fenced_code(body_text),
            "chunk_count": len(source_chunks),
            "planned_commands": len(source_chunks),
            "deprecated_layers_ignored": compatibility_warnings,
            "first_request_chars": len(create_markdown),
            "chunk_budget": args.chunk_chars,
            "create_command": build_command(args, create_markdown),
            "append_command_template": build_command(args, "<next_chunk>", doc_ref="<doc_id_or_url>") if len(source_chunks) > 1 else None,
            "first_chunk_preview": create_markdown[:600],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    if not preflight["ready"]:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "lark-cli preflight failed",
                    "identity": args.identity,
                    "target": {
                        "folder_token": args.folder_token,
                        "wiki_node": args.wiki_node,
                        "wiki_space": args.wiki_space,
                        "defaulted_to_my_library": args.defaulted_destination,
                    },
                    "preflight": preflight,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    create_command = build_command(args, create_markdown)
    create_result = run_command(create_command)
    if create_result.returncode != 0:
        print_failure(create_command, create_result)
        return create_result.returncode

    doc_id, doc_url = extract_doc_refs(create_result.stdout)

    if not doc_id and not doc_url:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "Document was created but no doc_id/doc_url could be parsed from lark-cli output",
                    "stdout": create_result.stdout,
                    "stderr": create_result.stderr,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    doc_ref = doc_id or doc_url
    warnings: list[str] = compatibility_warnings.copy()

    first_heading_title = find_first_heading_title(headings)

    if first_heading_title and args.mindmap_mode == "auto":
        mindmap_intro = build_mindmap_intro_markdown()
        mindmap_result = run_update_command(doc_ref, mindmap_intro, "insert_before", args, selection_by_title=first_heading_title)
        if mindmap_result.returncode != 0:
            warnings.append(f"Mind map placeholder insert failed: {mindmap_result.stderr.strip() or mindmap_result.stdout.strip()}")
        else:
            board_payload = parse_json_payload(mindmap_result.stdout)
            board_tokens = []
            data = board_payload.get("data") if isinstance(board_payload, dict) else None
            if isinstance(data, dict):
                board_tokens = data.get("board_tokens") or []
            if board_tokens:
                root_title = heading_display_title(headings[0][1]) if headings else args.title
                warning = upload_mindmap(doc_ref, board_tokens[0], headings, root_title, args)
                if warning:
                    warnings.append(warning)
            else:
                warnings.append("Mind map placeholder inserted but no board token was returned.")

    successful_appends = 0
    for index, chunk in enumerate(source_chunks[1:], start=2):
        update_command = build_command(args, chunk, doc_ref=doc_ref)
        update_result = run_command(update_command)
        if update_result.returncode != 0:
            print_failure(update_command, update_result, chunk_index=index)
            return update_result.returncode
        successful_appends += 1

    if args.flowchart_mode == "auto":
        for flow_title, flow_body in flow_sections:
            placeholder = "<whiteboard type=\"blank\"></whiteboard>\n"
            flow_result = run_update_command(doc_ref, placeholder, "insert_after", args, selection_by_title=flow_title)
            if flow_result.returncode != 0:
                warnings.append(f"Flowchart insert failed for {flow_title}: {flow_result.stderr.strip() or flow_result.stdout.strip()}")
                continue

            flow_payload = parse_json_payload(flow_result.stdout)
            board_tokens = []
            data = flow_payload.get("data") if isinstance(flow_payload, dict) else None
            if isinstance(data, dict):
                board_tokens = data.get("board_tokens") or []
            if not board_tokens:
                warnings.append(f"Flowchart insert returned no board token for {flow_title}.")
                continue

            mermaid = build_mermaid_flowchart(flow_title, flow_body)
            if mermaid is None:
                warnings.append(f"Flowchart skipped for {flow_title}: unable to derive at least two steps from section body.")
                continue

            warning = upload_whiteboard_mermaid(board_tokens[0], mermaid, args)
            if warning:
                warnings.append(f"{flow_title}: {warning}")

    if args.section_hint_mode == "auto":
        requirements_heading = find_requirements_heading(headings)
        if requirements_heading:
            hint_markdown = build_section_hint_markdown(
                "这一章适合按“模块标题 -> 字段/按钮/规则/交互/异常/验收”来拆研发与测试任务。\n\n建议先看三级标题确定模块边界，再看四级标题拆实现清单。"
            )
            requirements_result = run_update_command(doc_ref, hint_markdown, "insert_before", args, selection_by_title=requirements_heading)
            if requirements_result.returncode != 0:
                warnings.append(f"Requirements hint insert failed: {requirements_result.stderr.strip() or requirements_result.stdout.strip()}")

        mobile_heading = find_mobile_heading(headings)
        if mobile_heading:
            mobile_markdown = build_section_hint_markdown(
                "从这一节开始进入移动端章节，适合单独按移动端包、执行页、确认页和轻量查询页拆任务。"
            )
            mobile_result = run_update_command(doc_ref, mobile_markdown, "insert_before", args, selection_by_title=mobile_heading)
            if mobile_result.returncode != 0:
                warnings.append(f"Mobile hint insert failed: {mobile_result.stderr.strip() or mobile_result.stdout.strip()}")

    summary = {
        "ok": True,
        "dry_run": False,
        "source": str(source_path),
        "title": args.title,
        "identity": args.identity,
        "target": {
            "folder_token": args.folder_token,
            "wiki_node": args.wiki_node,
            "wiki_space": args.wiki_space,
            "defaulted_to_my_library": args.defaulted_destination,
        },
        "preflight": preflight,
        "doc_id": doc_id,
        "doc_url": doc_url,
        "inline_color_mode_requested": args.inline_color_mode,
        "inline_color_mode": effective_color_mode,
        "inline_color_mode_reason": color_mode_reason,
        "label_prefix_style": args.label_prefix_style,
        "beautify_mode_requested": args.beautify_mode,
        "beautify_mode": effective_beautify_mode,
        "beautify_mode_reason": beautify_mode_reason,
        "theme": args.theme,
        "mindmap_mode": args.mindmap_mode,
        "section_hint_mode": args.section_hint_mode,
        "omit_section_titles_requested": args.omit_section_title,
        "omit_section_titles_applied": omitted_titles,
        "source_contains_code_block": source_has_fenced_code(body_text),
        "chunk_count": len(source_chunks),
        "appended_chunks": successful_appends,
        "warnings": warnings,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
