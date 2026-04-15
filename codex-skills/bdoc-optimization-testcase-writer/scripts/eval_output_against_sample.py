#!/usr/bin/env python3

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLES_PATH = ROOT / 'evals' / 'samples.jsonl'
OLD_TESTCASE_HEADER = re.compile(r'\|\s*用例类型\s*\|\s*用例标题\s*\|\s*前置条件\s*\|\s*操作步骤\s*\|\s*预期结果\s*\|')
NEW_TESTCASE_HEADER = re.compile(r'\|\s*用例类型\s*\|\s*操作步骤\s*\|\s*预期结果\s*\|')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Evaluate an output markdown/text file against a sample prompt spec.')
    parser.add_argument('--sample-id', help='Sample id from evals/samples.jsonl')
    parser.add_argument('--output', help='Path to a single output file to evaluate')
    parser.add_argument('--outputs-dir', help='Directory containing <sample-id>.md or <sample-id>.txt outputs')
    args = parser.parse_args()

    if args.outputs_dir:
        if args.sample_id or args.output:
            parser.error('--outputs-dir cannot be combined with --sample-id/--output')
    else:
        if not args.sample_id or not args.output:
            parser.error('Provide --sample-id and --output, or use --outputs-dir')
    return args


def load_samples() -> dict[str, dict]:
    samples: dict[str, dict] = {}
    for line in SAMPLES_PATH.read_text(encoding='utf-8').splitlines():
        sample = json.loads(line)
        samples[sample['id']] = sample
    return samples


def load_output(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def contains_in_order(text: str, first: str, second: str) -> bool:
    a = text.find(first)
    b = text.find(second)
    return a >= 0 and b >= 0 and a < b


def prompt_explicitly_requests_screenshot(sample: dict) -> bool:
    prompt = sample.get('prompt', '')
    return '截图' in prompt or '直接标出来' in prompt


def evaluate_sample(sample: dict, output_text: str, output_file: str) -> dict:
    failures: list[str] = []
    warnings: list[str] = []
    passes: list[str] = []

    if contains_in_order(output_text, '直接执行', '深度交互'):
        passes.append('Sections `直接执行` and `深度交互` appear in the expected order.')
    else:
        failures.append('Output must contain `直接执行` before `深度交互`.')

    for item in sample.get('must_include', []):
        if item in output_text:
            passes.append(f'Contains required marker: {item}')
        else:
            failures.append(f'Missing required marker: {item}')

    if '测试用例' in output_text:
        if NEW_TESTCASE_HEADER.search(output_text):
            passes.append('Uses the new testcase table header.')
        else:
            failures.append('Output contains `测试用例` but is missing the new testcase table header `用例类型 | 操作步骤 | 预期结果`.')

    if OLD_TESTCASE_HEADER.search(output_text):
        failures.append('Output still uses the old testcase table header with `用例标题` / `前置条件`.')

    if '【待补截图' in output_text:
        if prompt_explicitly_requests_screenshot(sample):
            warnings.append('Output includes screenshot placeholder; allowed because the prompt explicitly mentions screenshots.')
        else:
            failures.append('Output includes screenshot placeholder even though the prompt did not explicitly require it.')
    else:
        passes.append('No unnecessary screenshot placeholder detected.')

    if '测试用例' in output_text and '当前文档下的待确认项' not in output_text:
        failures.append('When testcase section exists, `当前文档下的待确认项` should also exist.')

    if '操作流程' in output_text and '流程图待落白板' not in output_text and '<whiteboard' not in output_text and '```mermaid' not in output_text:
        warnings.append('Output mentions `操作流程` but does not show a visible flow artifact marker; confirm this was a light-demand case or that the flow section was intentionally omitted.')

    unverifiable = [f'Needs human review: {item}' for item in sample.get('must_reason_about', [])]
    unverifiable.extend(f'Needs human review: avoid {item}' for item in sample.get('must_avoid', []))

    ok = not failures
    return {
        'sample_id': sample['id'],
        'output_file': output_file,
        'ok': ok,
        'failure_count': len(failures),
        'warning_count': len(warnings),
        'pass_count': len(passes),
        'failures': failures,
        'warnings': warnings,
        'passes': passes,
        'manual_review': unverifiable,
    }


def resolve_output_for_sample(outputs_dir: Path, sample_id: str) -> Path | None:
    candidates = [
        outputs_dir / f'{sample_id}.md',
        outputs_dir / f'{sample_id}.txt',
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def main() -> int:
    args = parse_args()
    samples = load_samples()

    results = []
    if args.outputs_dir:
        outputs_dir = Path(args.outputs_dir).expanduser().resolve()
        for sample_id, sample in samples.items():
            output_path = resolve_output_for_sample(outputs_dir, sample_id)
            if output_path is None:
                results.append({
                    'sample_id': sample_id,
                    'output_file': None,
                    'ok': False,
                    'failure_count': 1,
                    'warning_count': 0,
                    'pass_count': 0,
                    'failures': ['Missing output file; expected <sample-id>.md or <sample-id>.txt'],
                    'warnings': [],
                    'passes': [],
                    'manual_review': [],
                })
                continue
            output_text = load_output(output_path)
            results.append(evaluate_sample(sample, output_text, str(output_path)))
    else:
        sample = samples.get(args.sample_id)
        if sample is None:
            print(json.dumps({'ok': False, 'error': f'Unknown sample id: {args.sample_id}'}, ensure_ascii=False, indent=2))
            return 1
        output_path = Path(args.output).expanduser().resolve()
        output_text = load_output(output_path)
        results.append(evaluate_sample(sample, output_text, str(output_path)))

    ok = all(item['ok'] for item in results)
    summary = {
        'ok': ok,
        'sample_count': len(results),
        'passed': sum(1 for item in results if item['ok']),
        'failed': sum(1 for item in results if not item['ok']),
        'results': results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
