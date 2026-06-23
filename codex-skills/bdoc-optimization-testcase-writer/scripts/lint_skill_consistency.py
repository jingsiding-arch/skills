#!/usr/bin/env python3

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


CHECKS = [
    {
        'id': 'old_testcase_columns',
        'pattern': r'\|\s*用例类型\s*\|\s*用例标题\s*\|\s*前置条件\s*\|\s*操作步骤\s*\|\s*预期结果\s*\|',
        'message': 'Old testcase table columns found; use mind-map style testcase structure instead of the old table.',
        'paths': ('SKILL.md', 'assets', 'references'),
    },
    {
        'id': 'old_button_permission_heading',
        'pattern': r'^#{1,6}\s+.*按钮权限',
        'message': 'Old heading 按钮权限 found; use 权限控制.',
        'paths': ('assets', 'references'),
    },
    {
        'id': 'screenshot_as_required_eval',
        'pattern': r'"must_include"\s*:\s*\[[^\n\]]*待补截图',
        'message': 'Eval requires screenshot placeholder; screenshot should be conditional.',
        'paths': ('evals',),
    },
    {
        'id': 'forced_flow_minimum',
        'pattern': r'至少\s*1\s*个页面级标题且包含.*操作流程.*权限控制',
        'message': 'Minimum deliverable still forces 操作流程/权限控制.',
        'paths': ('SKILL.md', 'references'),
    },
    {
        'id': 'removed_solution_overview',
        'pattern': r'^#{1,6}\s+.*实现方案概览|`实现方案概览`',
        'message': '实现方案概览 has been removed; fold summary content into 需求背景 or 页面改动点总览.',
        'paths': ('SKILL.md', 'assets', 'references', 'agents'),
    },
    {
        'id': 'old_testcase_numbering',
        'pattern': r'4\.[12]\s+(建议优先回归场景|具体测试用例)',
        'message': 'Old testcase numbering found; use 3.1 具体测试用例（思维导图） after removing 实现方案概览.',
        'paths': ('SKILL.md', 'assets', 'references'),
    },
    {
        'id': 'split_page_logic_headings',
        'pattern': r'^#{1,6}\s+\d+(?:\.\d+)*\s+(页面 / 交互|逻辑 / 规则)$',
        'message': 'Do not split page content into 页面 / 交互 and 逻辑 / 规则 headings; use 改动点 headings with 页面表现/规则口径 inside.',
        'paths': ('assets', 'references'),
    },
    {
        'id': 'misleading_whiteboard_claim',
        'pattern': r'已插入白板流程图|已生成飞书文档',
        'message': 'Avoid wording that may claim external side effects without tool execution.',
        'paths': ('assets', 'references', 'evals', 'agents'),
    },
]


def iter_files(scope: str) -> list[Path]:
    path = ROOT / scope
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(p for p in path.rglob('*') if p.is_file())
    return []


def check_patterns() -> list[dict]:
    findings = []
    for check in CHECKS:
        regex = re.compile(check['pattern'], re.M)
        files: list[Path] = []
        for scope in check['paths']:
            files.extend(iter_files(scope))
        for path in files:
            text = path.read_text(encoding='utf-8')
            for match in regex.finditer(text):
                line = text.count('\n', 0, match.start()) + 1
                findings.append({
                    'check': check['id'],
                    'file': str(path.relative_to(ROOT)),
                    'line': line,
                    'message': check['message'],
                })
    return findings


def check_jsonl() -> list[dict]:
    findings = []
    path = ROOT / 'evals' / 'samples.jsonl'
    if not path.exists():
        return [{'check': 'jsonl_exists', 'file': 'evals/samples.jsonl', 'line': 1, 'message': 'samples.jsonl missing.'}]
    for index, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
        try:
            sample = json.loads(line)
        except json.JSONDecodeError as exc:
            findings.append({
                'check': 'jsonl_valid',
                'file': str(path.relative_to(ROOT)),
                'line': index,
                'message': str(exc),
            })
            continue
        required = ('id', 'domain', 'should_route_to', 'prompt', 'must_include', 'must_reason_about', 'must_avoid')
        for key in required:
            if key not in sample:
                findings.append({
                    'check': 'jsonl_schema',
                    'file': str(path.relative_to(ROOT)),
                    'line': index,
                    'message': f'Missing key: {key}',
                })
        if sample.get('should_route_to') != 'bdoc-optimization-testcase-writer':
            findings.append({
                'check': 'jsonl_route',
                'file': str(path.relative_to(ROOT)),
                'line': index,
                'message': 'should_route_to must be bdoc-optimization-testcase-writer.',
            })
        for key in ('must_include', 'must_reason_about', 'must_avoid'):
            if key in sample and not isinstance(sample[key], list):
                findings.append({
                    'check': 'jsonl_schema',
                    'file': str(path.relative_to(ROOT)),
                    'line': index,
                    'message': f'{key} must be a list.',
                })
    return findings


def check_required_files() -> list[dict]:
    required = [
        'SKILL.md',
        'assets/optimization-doc-template.md',
        'assets/optimization-doc-template-light.md',
        'assets/testcase-bottom-template.md',
        'evals/README.md',
        'evals/samples.jsonl',
        'references/final-doc-style-baseline.md',
        'references/final-doc-mini-example.md',
        'references/opening-turn-template.md',
        'references/routing-decision-table.md',
        'scripts/eval_output_against_sample.py',
        'scripts/update_lark_optimization_doc.py',
    ]
    findings = []
    for rel in required:
        if not (ROOT / rel).exists():
            findings.append({'check': 'required_file', 'file': rel, 'line': 1, 'message': 'Required file missing.'})
    return findings


def main() -> int:
    findings = []
    findings.extend(check_required_files())
    findings.extend(check_jsonl())
    findings.extend(check_patterns())
    result = {
        'ok': not findings,
        'root': str(ROOT),
        'finding_count': len(findings),
        'findings': findings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not findings else 1


if __name__ == '__main__':
    sys.exit(main())
