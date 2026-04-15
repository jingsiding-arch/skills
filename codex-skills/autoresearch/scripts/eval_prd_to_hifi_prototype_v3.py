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
    return sum(1 for line in text.splitlines() if line.strip() and ("?" in line or "？" in line))


def has_confirmed_markers(output: str) -> bool:
    return contains_any(
        output,
        ["confirmed", "assumptions", "tbd", "已确认", "已知信息", "假设", "待定", "待确认"],
    )


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


def eval_prd_coverage(output: str) -> bool:
    page_hits = count_hits(output, ["p0", "页面", "列表", "详情", "审批", "弹窗", "抽屉", "表单"])
    flow_hits = count_hits(output, ["流程", "状态", "流转", "主流程", "提交", "审批"])
    exception_hits = count_hits(output, ["异常", "空态", "失败", "权限", "校验", "超时", "边界"])
    return page_hits >= 3 and flow_hits >= 2 and exception_hits >= 1


def eval_traceability(output: str) -> bool:
    return has_confirmed_markers(output)


def eval_information_architecture(output: str) -> bool:
    page_types = sum(
        1
        for group in [
            ["列表", "list"],
            ["详情", "detail"],
            ["审批", "流程页", "flow"],
            ["编辑", "新增", "表单"],
            ["配置", "规则配置"],
        ]
        if contains_any(output, group)
    )
    has_structure = contains_any(output, ["导航", "入口", "页面清单", "信息架构", "ui manifest", "pagekey"])
    return page_types >= 2 and has_structure


def eval_flow_closure(output: str) -> bool:
    flow = count_hits(output, ["主流程", "流程", "状态流转", "提交", "审批", "回写"])
    feedback = count_hits(output, ["成功", "提示", "反馈", "状态变化", "返回", "回写", "message"]) >= 1
    return flow >= 2 and feedback


def eval_exception_demo(output: str) -> bool:
    exception = count_hits(output, ["异常", "空态", "失败", "权限", "校验", "超时", "重试"]) >= 2
    feedback = count_hits(output, ["提示", "反馈", "toast", "error", "占位", "重试"]) >= 1
    return exception and feedback


def eval_b_side_habit(output: str) -> bool:
    buckets = 0
    if contains_any(output, ["搜索", "筛选", "查询", "筛选项", "工具栏"]):
        buckets += 1
    if contains_any(output, ["列表", "表格", "行操作", "批量操作"]):
        buckets += 1
    if contains_any(output, ["详情", "抽屉", "弹窗", "表单"]):
        buckets += 1
    if contains_any(output, ["确认", "二次确认", "提示", "反馈", "驳回原因必填"]):
        buckets += 1
    return buckets >= 3


def eval_efficiency(output: str) -> bool:
    signal_hits = count_hits(
        output,
        ["主次", "重点", "高效", "简洁", "任务", "优先", "信息密度", "导航壳", "快速切页", "核心交互", "p0"],
    )
    clutter = count_hits(output, ["品牌系统", "装饰", "宣传", "炫", "视觉优先"]) >= 2
    return signal_hits >= 2 and not clutter


def eval_older_users(output: str) -> bool:
    return count_hits(
        output,
        ["清晰", "直白", "易懂", "低认知负担", "可读", "稳定", "路径短", "明确反馈", "不要隐藏", "少打断"],
    ) >= 2


def eval_engineering(output: str) -> bool:
    buckets = 0
    if contains_any(output, ["src/prototypes", "pages", "components", "types", "mock"]):
        buckets += 1
    if contains_any(output, ["路由", "router", "route", "hash", "pagekey"]):
        buckets += 1
    if contains_any(output, ["mock api", "mock 数据", "内存 store", "promise delay", "mock"]):
        buckets += 1
    if contains_any(output, ["接入现有", "现有仓库", "react + vite", "独立 demo", "目录"]):
        buckets += 1
    return buckets >= 3


def eval_context_fit(prompt: str, output: str) -> bool:
    repo_prompt = contains_any(prompt, ["react + vite", "react+vite", "现成 router", "已有 react", "现有 router", "仓库"])
    figma_prompt = contains_any(prompt, ["figma", "1:1", "高保真", "frame"])
    design_prompt = contains_any(prompt, ["设计系统", "token", "组件库"])

    repo_ok = True
    figma_ok = True
    design_ok = True
    if repo_prompt:
        repo_ok = mentions_existing_repo(output) and not pushes_new_project(output)
    if figma_prompt:
        figma_ok = contains_any(output, ["figma", "视觉真源", "token", "1:1", "还原", "frame", "样式对齐"])
    if design_prompt:
        design_ok = contains_any(output, ["设计系统", "token", "变量", "复用现有", "组件库"])
    return repo_ok and figma_ok and design_ok


def score_known_eval(name: str, prompt: str, output: str) -> bool:
    lowered = norm(name)
    if "p0" in lowered or "完整落地" in name:
        return eval_prd_coverage(output)
    if "可追溯" in name or "trace" in lowered:
        return eval_traceability(output)
    if "信息架构" in name or "架构合理" in name:
        return eval_information_architecture(output)
    if "主流程" in name or "闭环" in name:
        return eval_flow_closure(output)
    if "异常" in name or "边界" in name:
        return eval_exception_demo(output)
    if "b端习惯" in name or ("交互" in name and "习惯" in name):
        return eval_b_side_habit(output)
    if "高效简洁" in name or "效率" in name:
        return eval_efficiency(output)
    if "30到50" in name or "30-50" in lowered or "易用性考虑" in name:
        return eval_older_users(output)
    if "工程可落地" in name or "落地" in name:
        return eval_engineering(output)
    if "上下文适配" in name or "context" in lowered:
        return eval_context_fit(prompt, output)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Heuristic evaluator v3 for prd-to-hifi-prototype autoresearch runs.")
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
