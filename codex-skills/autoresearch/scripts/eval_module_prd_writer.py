#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def norm(text: str) -> str:
    return text.lower()


def contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def count_hits(text: str, needles: list[str]) -> int:
    return sum(1 for needle in needles if needle in text)


def is_sparse_prompt(prompt: str) -> bool:
    return "prd" in norm(prompt) and count_hits(prompt, ["角色", "流程", "规则", "一期", "依赖", "审批", "消息"]) <= 1 and len(prompt.strip()) <= 24


def is_draft_prompt(prompt: str) -> bool:
    return contains_any(prompt, ["先给我一版", "草案", "tbd", "TBD"])


def is_incremental_prompt(prompt: str) -> bool:
    return contains_any(prompt, ["上一版", "本轮", "改成", "新增", "修订"])


def has_materials(prompt: str) -> bool:
    return count_hits(prompt, ["角色", "学生", "辅导员", "教务", "OA", "站内信", "短信", "依赖"]) >= 2


def eval_sparse_input(prompt: str, output: str) -> bool:
    if not is_sparse_prompt(prompt):
        return True
    has_guard = contains_any(output, ["澄清问题", "素材清单", "目录骨架", "关键问题"])
    over_detailed = count_hits(output, ["功能需求", "业务规则", "字段与数据口径", "状态流转", "验收标准"]) >= 4
    return has_guard and not over_detailed


def eval_draft_mode(prompt: str, output: str) -> bool:
    if not is_draft_prompt(prompt):
        return True
    markers = ["已确认信息", "假设", "候选方案", "待确认问题"]
    return count_hits(output, markers) >= 3


def eval_closure(output: str) -> bool:
    return contains_any(output, ["冲突", "断点", "闭环", "阻塞", "高风险假设", "依赖", "责任真空"])


def eval_reviewer_ready(output: str) -> bool:
    structure_hits = count_hits(output, ["范围边界", "角色", "流程", "业务规则", "验收标准", "字段", "状态"])
    table_like = output.count("|") >= 6
    return structure_hits >= 3 and (table_like or "##" in output or "1." in output)


def eval_incremental(prompt: str, output: str) -> bool:
    if not is_incremental_prompt(prompt):
        return True
    return contains_any(output, ["本轮更新", "本轮关闭", "修订点", "受影响章节"])


def eval_evidence(prompt: str, output: str) -> bool:
    if not has_materials(prompt):
        return True
    return contains_any(output, ["已知信息", "当前已知", "已确认事实", "明显冲突", "关键缺口"])


def eval_page_elements(output: str) -> bool:
    keywords = ["筛选项", "列表字段", "字段", "数据来源", "展示", "表单", "输入方式"]
    hits = count_hits(output, keywords)
    table_like = output.count("|") >= 6
    return hits >= 3 and table_like


def eval_interaction_logic(output: str) -> bool:
    keywords = ["点击", "操作", "前端", "后端", "成功", "失败", "提示", "刷新", "触发"]
    return count_hits(output, keywords) >= 4


def eval_effect_scope(output: str) -> bool:
    keywords = ["全局", "局部", "生效范围", "生效时点", "影响对象", "优先级", "冲突处理", "是否追溯"]
    return count_hits(output, keywords) >= 3


def eval_editability(output: str) -> bool:
    keywords = ["可改", "不可改", "可编辑", "不可编辑", "限制原因", "改后影响", "草稿态", "已生效", "使用中"]
    return count_hits(output, keywords) >= 3


def eval_exceptions(output: str) -> bool:
    keywords = ["异常", "边界", "失败处理", "兜底", "回退", "超时", "冲突", "依赖缺失"]
    return count_hits(output, keywords) >= 3


def eval_dev_test_ready(output: str) -> bool:
    keywords = ["验收标准", "测试", "研发", "开发", "规则", "状态", "接口", "口径"]
    return count_hits(output, keywords) >= 4


def score_known_eval(name: str, prompt: str, output: str) -> bool:
    lowered = norm(name)
    if "页面元素" in name:
        return eval_page_elements(output)
    if "交互" in name and "逻辑" in name:
        return eval_interaction_logic(output)
    if "生效规则" in name or ("全局" in name and "生效" in name) or ("局部" in name and "生效" in name):
        return eval_effect_scope(output)
    if "配置可改边界" in name or ("可改" in name and "不可改" in name):
        return eval_editability(output)
    if "异常" in name and "边界" in name:
        return eval_exceptions(output)
    if "研发与测试验收" in name or ("研发" in name and "测试" in name and "验收" in name):
        return eval_dev_test_ready(output)
    if "sparse" in lowered or "澄清" in name or "输入" in name:
        return eval_sparse_input(prompt, output)
    if "draft" in lowered or "草案" in name or "假设" in name:
        return eval_draft_mode(prompt, output)
    if "closure" in lowered or "闭环" in name or "冲突" in name:
        return eval_closure(output)
    if "reviewer" in lowered or "评审" in name or "structure" in lowered or "结构" in name:
        return eval_reviewer_ready(output)
    if "incremental" in lowered or "增量" in name or "修订" in name:
        return eval_incremental(prompt, output)
    if "evidence" in lowered or "材料" in name or "已知" in name:
        return eval_evidence(prompt, output)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Heuristic evaluator for module-prd-writer autoresearch runs.")
    parser.add_argument("--run-spec", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--eval-output", required=True)
    args = parser.parse_args()

    run_spec = json.loads(Path(args.run_spec).read_text(encoding="utf-8"))
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    output = Path(args.output_file).read_text(encoding="utf-8")

    evals = {}
    for item in run_spec.get("evals", []):
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        evals[name] = score_known_eval(name, prompt, output)

    Path(args.eval_output).write_text(json.dumps({"evals": evals}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
