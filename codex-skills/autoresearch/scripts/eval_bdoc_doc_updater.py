#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SECTION_KEYWORDS = [
    "功能入口",
    "操作入口",
    "前置条件",
    "页面字段说明",
    "字段说明",
    "操作步骤",
    "操作结果",
    "结果说明",
    "注意事项",
    "异常提示",
    "常见问题",
]

HIGHLIGHT_MARKERS = ["【新增】", "【修改】", "==", "<mark>", "[高亮]", "（新增）", "(新增)"]


def contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def count_hits(text: str, needles: list[str]) -> int:
    return sum(1 for needle in needles if needle in text)


def has_table(text: str) -> bool:
    return text.count("|") >= 6


def prompt_has_source(prompt: str) -> bool:
    return contains_any(prompt, ["旧版手册", "旧版文档", "当前手册片段", "手册节选", "手册片段"])


def prompt_has_table_source(prompt: str) -> bool:
    return has_table(prompt)


def prompt_is_incremental(prompt: str) -> bool:
    return contains_any(prompt, ["不要重写整篇", "只更新受影响章节", "上一轮已经补写过", "本轮新增说明"])


def prompt_has_missing_source(prompt: str) -> bool:
    return contains_any(prompt, ["没有旧手册", "没有旧手册原文", "没有旧手册原文", "没有原文档", "不要假装你见过旧手册"])


def prompt_has_conflict(prompt: str) -> bool:
    return contains_any(prompt, ["待确认", "冲突信息", "研发备注", "销售说", "版本记录里没有同步", "不可撤回"])


def source_sections(prompt: str) -> list[str]:
    return [section for section in SECTION_KEYWORDS if section in prompt]


def eval_structure_inheritance(prompt: str, output: str) -> bool:
    sections = source_sections(prompt)
    if not sections and not prompt_has_table_source(prompt):
        return True
    overlap = count_hits(output, sections)
    table_ok = True
    if prompt_has_table_source(prompt):
        table_ok = has_table(output)
    return overlap >= 2 and table_ok


def eval_incremental(prompt: str, output: str) -> bool:
    if not prompt_is_incremental(prompt):
        return True
    markers = ["本轮修订点", "本轮更新", "受影响章节", "变更摘要", "更新的原有章节", "仅更新"]
    return contains_any(output, markers)


def eval_manual_completeness(prompt: str, output: str) -> bool:
    if prompt_has_missing_source(prompt) and not prompt_has_source(prompt):
        keywords = ["功能入口", "前置条件", "操作步骤", "操作结果", "注意事项", "常见问题"]
    else:
        keywords = SECTION_KEYWORDS
    structure_hits = count_hits(output, keywords)
    feature_hits = count_hits(output, ["批量", "导入", "导出", "撤回", "短信", "证件类型", "失败", "提示"])
    return structure_hits >= 4 and feature_hits >= 2


def eval_highlight(output: str) -> bool:
    return contains_any(output, HIGHLIGHT_MARKERS)


def eval_risk_honesty(prompt: str, output: str) -> bool:
    if prompt_has_missing_source(prompt):
        return contains_any(output, ["无法继承原格式", "无法保持原格式", "缺少旧手册", "只能先按通用模板起草", "手册草稿"])
    if prompt_has_conflict(prompt):
        has_risk_callout = contains_any(output, ["待确认项", "冲突", "需确认", "上线状态待确认", "版本记录"])
        fake_certainty = contains_any(output, ["该功能已上线", "已经正式上线", "客户已在用"])
        return has_risk_callout and not fake_certainty
    return contains_any(output, ["待确认项", "AI补全假设", "变更摘要"])


def eval_delivery_structure(output: str) -> bool:
    hits = count_hits(
        output,
        [
            "新版文档",
            "更新后的正文",
            "变更摘要",
            "本次新增内容",
            "本次更新内容",
            "待确认项",
            "AI补全假设",
        ],
    )
    return hits >= 3


def score_known_eval(name: str, prompt: str, output: str) -> bool:
    lowered = name.lower()
    if "结构" in name or "structure" in lowered:
        return eval_structure_inheritance(prompt, output)
    if "增量" in name or "incremental" in lowered or "修订" in name:
        return eval_incremental(prompt, output)
    if "步骤" in name or "完整性" in name or "manual" in lowered:
        return eval_manual_completeness(prompt, output)
    if "高亮" in name or "highlight" in lowered:
        return eval_highlight(output)
    if "材料" in name or "风险" in name or "honesty" in lowered:
        return eval_risk_honesty(prompt, output)
    if "交付" in name or "ready" in lowered or "结构 ready" in lowered:
        return eval_delivery_structure(output)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Heuristic evaluator for bdoc-doc-updater autoresearch runs.")
    parser.add_argument("--run-spec", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--eval-output", required=True)
    args = parser.parse_args()

    run_spec = json.loads(Path(args.run_spec).read_text(encoding="utf-8"))
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    output = Path(args.output_file).read_text(encoding="utf-8")

    evals: dict[str, bool] = {}
    for item in run_spec.get("evals", []):
        name = str(item.get("name", "")).strip()
        if name:
            evals[name] = score_known_eval(name, prompt, output)

    Path(args.eval_output).write_text(
        json.dumps({"evals": evals}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
