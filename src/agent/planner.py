from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from src.config import cfg
from src.llm.client import llm
from src.models import Plan, Task

_PROMPT = Path(__file__).parent.parent.parent / "prompts" / "planner.md"

_PLAN_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "goal": {"type": "string"},
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "depends_on": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "description", "depends_on"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["goal", "tasks"],
    "additionalProperties": False,
}


def _raw_to_plan(goal: str, raw: dict) -> Plan:
    tasks = [
        Task(id=t["id"], description=t["description"], depends_on=t.get("depends_on", []))
        for t in raw["tasks"]
    ]
    return Plan(goal=goal, tasks=tasks)


def _validate_task_ids(plan: Plan) -> list[str]:
    ids = {t.id for t in plan.tasks}
    errors: list[str] = []
    if len(ids) != len(plan.tasks):
        errors.append("Duplicate task IDs found.")
    errors.extend(
        f"Task '{t.id}' depends on unknown id '{dep}'."
        for t in plan.tasks
        for dep in t.depends_on
        if dep not in ids
    )
    if not plan.tasks:
        errors.append("Plan has no tasks.")
    elif len(plan.tasks) > cfg.max_plan_tasks:
        errors.append(f"Plan has {len(plan.tasks)} tasks, max is {cfg.max_plan_tasks}.")
    return errors


def _build_plan(goal: str, raw: dict) -> Plan:
    try:
        plan = _raw_to_plan(goal, raw)
    except (ValidationError, KeyError) as exc:
        raise ValueError(f"Invalid plan: {exc}") from exc
    if issues := _validate_task_ids(plan):
        raise ValueError("Plan logic errors: " + "; ".join(issues))
    return plan


def create_plan(goal: str) -> Plan:
    system = _PROMPT.read_text().replace("{max_tasks}", str(cfg.max_plan_tasks))
    user = f"Research goal: {goal}"
    try:
        return _build_plan(goal, llm.plan_json(system, user, _PLAN_SCHEMA))
    except ValueError as err:
        retry = (
            f"{user}\n\nYour previous plan had errors:\n{err}\n\n"
            "Please produce a corrected plan."
        )
        return _build_plan(goal, llm.plan_json(system, retry, _PLAN_SCHEMA))
