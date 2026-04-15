#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def norm(text: str) -> str:
    return text.lower()


def plain(text: str) -> str:
    lowered = norm(text)
    lowered = re.sub(r"[`*_~#>\[\]\(\)\{\}|]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def contains_any(text: str, needles: list[str]) -> bool:
    haystack = plain(text)
    return any(plain(needle) in haystack for needle in needles)


def count_hits(text: str, needles: list[str]) -> int:
    haystack = plain(text)
    return sum(1 for needle in needles if plain(needle) in haystack)


def count_question_lines(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "?" in stripped or "？" in stripped:
            count += 1
    return count


def has_confirmed_markers(output: str) -> bool:
    return contains_any(
        output,
        [
            "confirmed",
            "assumptions",
            "tbd",
            "已确认",
            "确认信息",
            "已知信息",
            "假设",
            "待定",
            "待确认",
        ],
    )


def is_direct_prompt(prompt: str) -> bool:
    return contains_any(prompt, ["直接开始", "直接做", "不用先等我确认", "直接开始实现"])


def is_vague_prompt(prompt: str) -> bool:
    stripped = plain(prompt)
    if len(stripped) > 24:
        return False
    return count_hits(stripped, ["模块", "原型", "页面", "流程"]) >= 1 and count_hits(
        stripped, ["角色", "字段", "状态", "react", "vite", "figma", "router", "页面清单"]
    ) <= 1


def is_partial_prompt(prompt: str) -> bool:
    return contains_any(prompt, ["半成品", "v0.1", "先出", "先给你这些"])


def is_repo_prompt(prompt: str) -> bool:
    return contains_any(prompt, ["react + vite", "react+vite", "现成 router", "已有 react", "现有 router", "react + vite 仓库"])


def is_figma_prompt(prompt: str) -> bool:
    return contains_any(prompt, ["figma", "1:1", "高保真"])


def mentions_existing_repo(output: str) -> bool:
    return (
        (contains_any(output, ["react + vite", "react+vite", "已有 react + vite", "现有 react + vite", "react + vite 仓库"])
         and contains_any(output, ["router", "路由", "接入"]))
        or contains_any(output, ["接入现有", "复用现有", "已有项目", "按现有 router 接入", "按现有路由接入"])
    )


def pushes_new_project(output: str) -> bool:
    if contains_any(output, ["不新建项目", "不另起炉灶", "不要新建项目"]):
        return False
    return contains_any(output, ["建议新建项目", "新建项目", "另起炉灶", "重新搭一个项目"])


def eval_direct_mode(prompt: str, output: str) -> bool:
    if not is_direct_prompt(prompt):
        return True
    blocked = contains_any(
        output,
        [
            "等你确认后再",
            "确认后我再",
            "先确认 manifest",
            "先等你确认",
            "补齐这些我再开始",
        ],
    )
    has_action = count_hits(output, ["manifest", "页面", "p0", "实现", "接入", "原型"]) >= 2
    return has_confirmed_markers(output) and has_action and not blocked


def eval_vague_guard(prompt: str, output: str) -> bool:
    if not is_vague_prompt(prompt):
        return True
    has_guard = contains_any(
        output,
        [
            "澄清问题",
            "素材清单",
            "页面骨架",
            "流程骨架",
            "页面/流程骨架",
            "关键问题",
            "请先确认",
            "页面清单",
        ],
    )
    overcommit = count_hits(output, ["src/prototypes", "mock api", "npm run dev", "react-router", "hash/pagekey"]) >= 2
    return has_guard and not overcommit


def eval_partial_progress(prompt: str, output: str) -> bool:
    if not is_partial_prompt(prompt):
        return True
    has_progress = contains_any(output, ["v0.1", "先出一版", "p0", "先做", "先覆盖", "原型方案"])
    disciplined = count_question_lines(output) <= 3 or contains_any(
        output, ["只问最关键", "只问关键", "最阻塞的", "仅问 1-3 个关键问题", "不阻塞"]
    )
    return has_progress and disciplined


def eval_prototype_closure(output: str) -> bool:
    buckets = 0
    if contains_any(output, ["p0", "页面清单", "入口页", "原型首页", "导航"]):
        buckets += 1
    if contains_any(output, ["主流程", "流程", "状态流转", "提交", "审批"]):
        buckets += 1
    if contains_any(output, ["异常", "边界", "空态", "失败", "权限"]):
        buckets += 1
    if contains_any(output, ["mock", "mock 数据", "mock api", "内存 store", "promise delay"]):
        buckets += 1
    if contains_any(output, ["详情页", "列表页", "表单", "抽屉", "弹窗"]):
        buckets += 1
    return buckets >= 3


def eval_context_fit(prompt: str, output: str) -> bool:
    repo_ok = True
    figma_ok = True
    if is_repo_prompt(prompt):
        repo_ok = mentions_existing_repo(output) and not pushes_new_project(output)
    if is_figma_prompt(prompt):
        figma_ok = contains_any(output, ["figma", "视觉真源", "token", "1:1", "还原", "frame", "样式对齐"])
    return repo_ok and figma_ok


def score_known_eval(name: str, prompt: str, output: str) -> bool:
    lowered = norm(name)
    if "直接开做" in name or "direct" in lowered:
        return eval_direct_mode(prompt, output)
    if "模糊输入" in name or "vague" in lowered:
        return eval_vague_guard(prompt, output)
    if "半成品" in name or "v0.1" in lowered:
        return eval_partial_progress(prompt, output)
    if "闭环" in name or "closure" in lowered:
        return eval_prototype_closure(output)
    if "视觉与仓库" in name or "上下文" in name or "context" in lowered:
        return eval_context_fit(prompt, output)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Heuristic evaluator v2 for prd-to-hifi-prototype autoresearch runs.")
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

    Path(args.eval_output).write_text(
        json.dumps({"evals": evals}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
