#!/usr/bin/env python3

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check_required_files() -> list[dict]:
    required = [
        "SKILL.md",
        "agents/openai.yaml",
        "assets/module-prd-template.md",
        "references/dev-effort-gantt-playbook.md",
        "references/module-discovery-checklist.md",
        "references/prd-quality-checklist.md",
        "references/requirement-fallacy-checklist.md",
        "references/requirements-intake.md",
        "scripts/create_lark_dev_gantt.py",
        "scripts/sync_lark_module_prd_doc.py",
        "scripts/lint_skill_consistency.py",
        "scripts/eval_dry_run_samples.py",
        "scripts/eval_gantt_plan_samples.py",
        "evals/README.md",
        "evals/samples.jsonl",
        "evals/gantt_samples.jsonl",
        "evals/fixtures/dev_gantt_plan.json",
        "evals/fixtures/minimal_module_prd.md",
    ]
    findings = []
    for rel in required:
        if not (ROOT / rel).exists():
            findings.append({"check": "required_file", "file": rel, "line": 1, "message": "Required file missing."})
    return findings


def check_default_prompt() -> list[dict]:
    path = ROOT / "agents" / "openai.yaml"
    text = path.read_text(encoding="utf-8")
    findings = []
    required_patterns = {
        "按模块展开": "default_prompt should require module-by-module expansion.",
        "不要输出空表头": "default_prompt should prohibit empty-table outputs.",
        "研发开发版": "default_prompt should mention dev-delivery mode.",
        "精简落地稿": "default_prompt should mention the concise default output mode.",
        "3 张核心表": "default_prompt should mention compact core-table output.",
        "dry-run": "default_prompt should mention dry-run before Feishu sync.",
        "工作量评估": "default_prompt should mention effort estimation.",
        "甘特图": "default_prompt should mention gantt generation.",
    }
    for pattern, message in required_patterns.items():
        if pattern not in text:
            findings.append({"check": "default_prompt", "file": "agents/openai.yaml", "line": 1, "message": message})
    return findings


def check_template_examples() -> list[dict]:
    path = ROOT / "assets" / "module-prd-template.md"
    text = path.read_text(encoding="utf-8")
    findings = []
    required_strings = [
        "### 7.1 模块 A：列表页 / 台账页",
        "### 7.2 模块 B：配置页 / 表单页 / 详情页",
        "## 10. 开发工作量评估与排期建议",
        "字段 / 配置 / 展示",
        "按钮 / 动作",
        "规则 / 异常 / 验收",
        "| 公共配置 | 配置页与规则校验 | 前后端 | 3.5 | 2026-04-21 | 2026-04-24 | 依赖组织主数据口径 |",
        "| 筛选项 | 学年学期 | 学期主数据/下拉 | 当前学期 | 影响班级、课程候选范围 |",
        "| 保存 | 页面底部 | 表单校验通过 | 管理员 | 保存成功并停留当前页 | 返回字段级错误提示 |",
    ]
    for required in required_strings:
        if required not in text:
            findings.append({"check": "template_examples", "file": "assets/module-prd-template.md", "line": 1, "message": f"Missing example content: {required[:30]}..."})
    if re.search(r'^\|\s*\|\s*\|\s*\|\s*\|', text, re.M):
        findings.append({"check": "template_examples", "file": "assets/module-prd-template.md", "line": 1, "message": "Template still contains empty table rows."})
    return findings


def check_jsonl() -> list[dict]:
    path = ROOT / "evals" / "samples.jsonl"
    findings = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            sample = json.loads(line)
        except json.JSONDecodeError as exc:
            findings.append({"check": "jsonl_valid", "file": "evals/samples.jsonl", "line": idx, "message": str(exc)})
            continue
        for key in ("id", "input", "args", "expect"):
            if key not in sample:
                findings.append({"check": "jsonl_schema", "file": "evals/samples.jsonl", "line": idx, "message": f"Missing key: {key}"})
    return findings


def main() -> int:
    findings = []
    findings.extend(check_required_files())
    findings.extend(check_default_prompt())
    findings.extend(check_template_examples())
    findings.extend(check_jsonl())
    result = {
        "ok": not findings,
        "root": str(ROOT),
        "finding_count": len(findings),
        "findings": findings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
