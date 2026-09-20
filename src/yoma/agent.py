"""Deterministic, inspectable planning for bounded M9 orchestration."""

from dataclasses import dataclass
import json
import re
import uuid


class PlannerError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class PlannedStep:
    step_index: int
    action_type: str
    tool_name: str
    arguments: dict
    approval_required: bool


@dataclass(frozen=True)
class Plan:
    steps: tuple[PlannedStep, ...]
    approval_required: bool


_ROOT = re.compile(r"\broot\s*(?:id\s*)?(\d+)\b", re.IGNORECASE)
_PATH = re.compile(r"\bpath\s*[:=]\s*(.*?)(?:\s+content\s*[:=].*)?$", re.IGNORECASE)
_CONTENT = re.compile(r"\bcontent\s*[:=]\s*(.+)$", re.IGNORECASE)


def _root_id(goal: str) -> int | None:
    match = _ROOT.search(goal)
    return int(match.group(1)) if match else None


def _path(goal: str) -> str | None:
    match = _PATH.search(goal)
    return match.group(1).strip() if match else None


def _single_step(tool_name: str, arguments: dict, approval_required: bool) -> Plan:
    return Plan((PlannedStep(1, tool_name, tool_name, arguments, approval_required),), approval_required)


def plan_goal(goal: str, max_steps: int, max_goal_length: int, max_plan_size: int) -> tuple[str, Plan]:
    if not isinstance(goal, str) or not goal.strip():
        raise PlannerError("invalid_goal", "goal is required")
    normalized = goal.strip()
    if len(normalized) > max_goal_length:
        raise PlannerError("goal_too_long", "goal exceeds the configured limit")
    root_id = _root_id(normalized)
    path_match = _path(normalized)
    lower = normalized.casefold()
    if "list" in lower and "file" in lower:
        plan = _single_step("workspace.list_files", {"workspace_root_id": root_id} if root_id is not None else {}, False)
    elif "read" in lower and ("file" in lower or "text" in lower):
        plan = _single_step("workspace.read_text", {"workspace_root_id": root_id, "relative_path": path_match} if root_id is not None and path_match else {}, False)
    elif "create" in lower and "director" in lower:
        plan = _single_step("workspace.create_directory", {"workspace_root_id": root_id, "relative_path": path_match} if root_id is not None and path_match else {}, True)
    elif ("write" in lower or "create" in lower) and ("file" in lower or "text" in lower):
        content_match = _CONTENT.search(normalized)
        arguments = {"workspace_root_id": root_id, "relative_path": path_match, "content": content_match.group(1).strip() if content_match else None} if root_id is not None and path_match and content_match else {}
        plan = _single_step("workspace.write_text", arguments, True)
    else:
        raise PlannerError("unsupported_goal", "goal pattern is not supported by the deterministic planner")
    if len(plan.steps) > max_steps:
        raise PlannerError("plan_too_large", "plan exceeds the configured step limit")
    serialized = json.dumps({"steps": [step.__dict__ for step in plan.steps]}, ensure_ascii=False, default=list)
    if len(serialized.encode("utf-8")) > max_plan_size:
        raise PlannerError("plan_too_large", "plan exceeds the configured size limit")
    return normalized, plan


def new_run_id() -> str:
    return uuid.uuid4().hex
