#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_TABLE_NAME = "开发排期"
DEFAULT_GRID_VIEW = "开发排期表"
DEFAULT_GANTT_VIEW = "开发甘特图"
DEFAULT_TIME_ZONE = "Asia/Shanghai"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a Feishu Base development gantt chart from a structured plan.")
    parser.add_argument("--plan", required=True, help="Path to the structured JSON plan file.")
    parser.add_argument("--base-name", help="Name for the new Base. Defaults to <project_name>_开发排期_<today>.")
    parser.add_argument("--base-token", help="Existing Base token. If omitted, a new Base will be created.")
    parser.add_argument("--folder-token", help="Optional destination folder token when creating a new Base.")
    parser.add_argument("--table-name", default=DEFAULT_TABLE_NAME, help="Target table name.")
    parser.add_argument("--grid-view-name", default=DEFAULT_GRID_VIEW, help="Grid view name.")
    parser.add_argument("--gantt-view-name", default=DEFAULT_GANTT_VIEW, help="Gantt view name.")
    parser.add_argument("--time-zone", default=DEFAULT_TIME_ZONE, help="Time zone for new Base creation.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print planned commands without calling lark-cli.")
    return parser.parse_args()


def load_plan(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Plan file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in plan file {path}: {exc}") from exc


def parse_date(value: str, *, is_end: bool) -> tuple[str, datetime]:
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            if fmt == "%Y-%m-%d":
                dt = dt.replace(hour=18 if is_end else 10, minute=0, second=0)
            elif fmt == "%Y-%m-%d %H:%M":
                dt = dt.replace(second=0)
            return dt.strftime("%Y-%m-%d %H:%M:%S"), dt
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value}")


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " / ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def validate_plan(raw_plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_plan, dict):
        raise ValueError("Top-level plan must be a JSON object.")

    project_name = stringify(raw_plan.get("project_name"))
    if not project_name:
        raise ValueError("`project_name` is required.")

    raw_tasks = raw_plan.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ValueError("`tasks` must be a non-empty array.")

    deadline_raw = stringify(raw_plan.get("required_end_date") or raw_plan.get("deadline"))
    deadline_norm = None
    deadline_dt = None
    if deadline_raw:
        deadline_norm, deadline_dt = parse_date(deadline_raw, is_end=True)

    validated_tasks: list[dict[str, Any]] = []
    errors: list[str] = []
    for idx, task in enumerate(raw_tasks, start=1):
        if not isinstance(task, dict):
            errors.append(f"Task #{idx} must be an object.")
            continue

        module = stringify(task.get("module") or task.get("module_name"))
        task_name = stringify(task.get("task_name") or task.get("name"))
        role = stringify(task.get("owner_role") or task.get("role") or task.get("assignee_role")) or "TBD"
        stage = stringify(task.get("stage")) or "开发"
        priority = stringify(task.get("priority")) or "TBD"
        start_raw = stringify(task.get("start_date") or task.get("planned_start"))
        end_raw = stringify(task.get("end_date") or task.get("planned_end"))

        if not module:
            errors.append(f"Task #{idx} is missing `module`.")
        if not task_name:
            errors.append(f"Task #{idx} is missing `task_name`.")
        try:
            effort_days = round(float(task.get("effort_days")), 1)
        except (TypeError, ValueError):
            errors.append(f"Task #{idx} has invalid `effort_days`.")
            effort_days = 0.0
        if effort_days <= 0:
            errors.append(f"Task #{idx} must have `effort_days` > 0.")
        if not start_raw:
            errors.append(f"Task #{idx} is missing `start_date`.")
        if not end_raw:
            errors.append(f"Task #{idx} is missing `end_date`.")
        if any(message.startswith(f"Task #{idx}") for message in errors):
            continue

        try:
            start_norm, start_dt = parse_date(start_raw, is_end=False)
            end_norm, end_dt = parse_date(end_raw, is_end=True)
        except ValueError as exc:
            errors.append(f"Task #{idx}: {exc}")
            continue

        if start_dt > end_dt:
            errors.append(f"Task #{idx} start_date must be <= end_date.")
            continue

        validated_tasks.append(
            {
                "module": module,
                "task_name": task_name,
                "owner_role": role,
                "stage": stage,
                "priority": priority,
                "effort_days": effort_days,
                "start_date": start_norm,
                "end_date": end_norm,
                "parallel_group": stringify(task.get("parallel_group")),
                "predecessors": stringify(task.get("predecessors") or task.get("dependencies")),
                "deliverable": stringify(task.get("deliverable") or task.get("deliverables")),
                "risk": stringify(task.get("risk") or task.get("risk_note")),
            }
        )

    if errors:
        raise ValueError("\n".join(errors))

    module_summary_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"task_count": 0, "effort_days": 0.0})
    all_start = min(datetime.strptime(task["start_date"], "%Y-%m-%d %H:%M:%S") for task in validated_tasks)
    all_end = max(datetime.strptime(task["end_date"], "%Y-%m-%d %H:%M:%S") for task in validated_tasks)
    total_effort = 0.0
    for task in validated_tasks:
        module_summary_map[task["module"]]["task_count"] += 1
        module_summary_map[task["module"]]["effort_days"] = round(
            module_summary_map[task["module"]]["effort_days"] + task["effort_days"], 1
        )
        total_effort = round(total_effort + task["effort_days"], 1)

    summary = {
        "task_count": len(validated_tasks),
        "module_count": len(module_summary_map),
        "total_effort_days": total_effort,
        "planned_start": all_start.strftime("%Y-%m-%d %H:%M:%S"),
        "planned_end": all_end.strftime("%Y-%m-%d %H:%M:%S"),
        "schedule_span_days": (all_end.date() - all_start.date()).days + 1,
    }
    if deadline_norm and deadline_dt:
        summary["required_end_date"] = deadline_norm
        summary["deadline_status"] = "meets_deadline" if all_end <= deadline_dt else "exceeds_deadline"

    module_summary = [
        {"module": module, **payload}
        for module, payload in sorted(module_summary_map.items(), key=lambda item: item[0])
    ]

    return {
        "project_name": project_name,
        "tasks": validated_tasks,
        "summary": summary,
        "module_summary": module_summary,
    }


def build_fields() -> list[dict[str, Any]]:
    return [
        {"name": "任务名称", "type": "text"},
        {"name": "所属模块", "type": "text"},
        {"name": "责任角色", "type": "text"},
        {"name": "任务阶段", "type": "text"},
        {"name": "优先级", "type": "text"},
        {
            "name": "工作量(人天)",
            "type": "number",
            "style": {"type": "plain", "precision": 1, "percentage": False, "thousands_separator": True},
        },
        {"name": "计划开始", "type": "datetime", "style": {"format": "yyyy-MM-dd HH:mm"}},
        {"name": "计划结束", "type": "datetime", "style": {"format": "yyyy-MM-dd HH:mm"}},
        {"name": "并行组", "type": "text"},
        {"name": "前置任务", "type": "text"},
        {"name": "交付说明", "type": "text"},
        {"name": "风险备注", "type": "text"},
    ]


def build_record(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "任务名称": task["task_name"],
        "所属模块": task["module"],
        "责任角色": task["owner_role"],
        "任务阶段": task["stage"],
        "优先级": task["priority"],
        "工作量(人天)": task["effort_days"],
        "计划开始": task["start_date"],
        "计划结束": task["end_date"],
        "并行组": task["parallel_group"] or None,
        "前置任务": task["predecessors"] or None,
        "交付说明": task["deliverable"] or None,
        "风险备注": task["risk"] or None,
    }


def command_preview(argv: list[str]) -> dict[str, Any]:
    return {
        "argv": argv,
        "shell": " ".join(shlex.quote(part) for part in argv),
    }


def build_command_plan(args: argparse.Namespace, validated: dict[str, Any], base_name: str) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    if not args.base_token:
        commands.append({"step": "doctor", **command_preview(["lark-cli", "doctor"])})
        base_create = ["lark-cli", "base", "+base-create", "--name", base_name, "--time-zone", args.time_zone]
        if args.folder_token:
            base_create.extend(["--folder-token", args.folder_token])
        commands.append({"step": "base_create", **command_preview(base_create)})

    base_token = args.base_token or "<new-base-token>"
    table_create = [
        "lark-cli",
        "base",
        "+table-create",
        "--base-token",
        base_token,
        "--name",
        args.table_name,
        "--fields",
        json.dumps(build_fields(), ensure_ascii=False),
        "--view",
        json.dumps(
            [{"name": args.grid_view_name, "type": "grid"}, {"name": args.gantt_view_name, "type": "gantt"}],
            ensure_ascii=False,
        ),
    ]
    commands.append({"step": "table_create", **command_preview(table_create)})
    timebar = [
        "lark-cli",
        "base",
        "+view-set-timebar",
        "--base-token",
        base_token,
        "--table-id",
        args.table_name,
        "--view-id",
        args.gantt_view_name,
        "--json",
        json.dumps({"start_time": "计划开始", "end_time": "计划结束", "title": "任务名称"}, ensure_ascii=False),
    ]
    commands.append({"step": "gantt_timebar", **command_preview(timebar)})
    for index, task in enumerate(validated["tasks"], start=1):
        record_cmd = [
            "lark-cli",
            "base",
            "+record-upsert",
            "--base-token",
            base_token,
            "--table-id",
            args.table_name,
            "--json",
            json.dumps(build_record(task), ensure_ascii=False),
        ]
        commands.append({"step": f"record_upsert_{index}", **command_preview(record_cmd)})
    return commands


def run_plain(argv: list[str]) -> None:
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(argv)}\nSTDOUT:\n{result.stdout[-1000:]}\nSTDERR:\n{result.stderr[-1000:]}"
        )


def run_json(argv: list[str]) -> dict[str, Any]:
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(argv)}\nSTDOUT:\n{result.stdout[-1000:]}\nSTDERR:\n{result.stderr[-1000:]}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Command did not return valid JSON: {' '.join(argv)}\nSTDOUT:\n{result.stdout[-1000:]}") from exc


def extract_base_info(payload: dict[str, Any]) -> dict[str, Any]:
    base = payload.get("base") if isinstance(payload.get("base"), dict) else payload
    token = base.get("base_token") or base.get("app_token") or payload.get("base_token") or payload.get("app_token")
    if not token:
        raise RuntimeError(f"Unable to find base token in response: {json.dumps(payload, ensure_ascii=False)}")
    return {
        "name": base.get("name"),
        "token": token,
        "url": base.get("url") or payload.get("url"),
    }


def main() -> int:
    args = parse_args()
    raw_plan = load_plan(Path(args.plan))
    try:
        validated = validate_plan(raw_plan)
    except ValueError as exc:
        print(json.dumps({"ok": False, "mode": "validation-error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    base_name = args.base_name or f"{validated['project_name']}_开发排期_{datetime.now().strftime('%Y%m%d')}"
    command_plan = build_command_plan(args, validated, base_name)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "dry-run",
                    "base_name": base_name,
                    "base_token": args.base_token,
                    "table_name": args.table_name,
                    "gantt_view_name": args.gantt_view_name,
                    "summary": validated["summary"],
                    "module_summary": validated["module_summary"],
                    "task_preview": validated["tasks"],
                    "command_count": len(command_plan),
                    "commands": command_plan,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    try:
        base_info = {"name": None, "token": args.base_token, "url": None}
        if not args.base_token:
            run_plain(["lark-cli", "doctor"])
            base_create = ["lark-cli", "base", "+base-create", "--name", base_name, "--time-zone", args.time_zone]
            if args.folder_token:
                base_create.extend(["--folder-token", args.folder_token])
            base_info = extract_base_info(run_json(base_create))

        base_token = base_info["token"]
        table_payload = run_json(
            [
                "lark-cli",
                "base",
                "+table-create",
                "--base-token",
                base_token,
                "--name",
                args.table_name,
                "--fields",
                json.dumps(build_fields(), ensure_ascii=False),
                "--view",
                json.dumps(
                    [{"name": args.grid_view_name, "type": "grid"}, {"name": args.gantt_view_name, "type": "gantt"}],
                    ensure_ascii=False,
                ),
            ]
        )
        timebar_payload = run_json(
            [
                "lark-cli",
                "base",
                "+view-set-timebar",
                "--base-token",
                base_token,
                "--table-id",
                args.table_name,
                "--view-id",
                args.gantt_view_name,
                "--json",
                json.dumps({"start_time": "计划开始", "end_time": "计划结束", "title": "任务名称"}, ensure_ascii=False),
            ]
        )

        records = []
        for task in validated["tasks"]:
            record_payload = run_json(
                [
                    "lark-cli",
                    "base",
                    "+record-upsert",
                    "--base-token",
                    base_token,
                    "--table-id",
                    args.table_name,
                    "--json",
                    json.dumps(build_record(task), ensure_ascii=False),
                ]
            )
            record = record_payload.get("record") if isinstance(record_payload.get("record"), dict) else {}
            records.append(
                {
                    "task_name": task["task_name"],
                    "record_id": record.get("record_id") or record_payload.get("record_id"),
                    "created": record_payload.get("created", False),
                }
            )

        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "apply",
                    "base": base_info,
                    "table": table_payload.get("table") or {"name": args.table_name},
                    "timebar": timebar_payload,
                    "summary": validated["summary"],
                    "module_summary": validated["module_summary"],
                    "record_count": len(records),
                    "records": records,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "mode": "runtime-error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
