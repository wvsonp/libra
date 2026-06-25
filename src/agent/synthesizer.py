from __future__ import annotations

from pathlib import Path

from src.llm.client import llm
from src.models import Plan, TaskStatus

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "synthesize.md"


def _format_task_outputs(plan: Plan) -> str:
    parts = []
    for task in plan.tasks:
        if task.status == TaskStatus.done and task.result:
            parts.append(f"## [{task.id}] {task.description}\n\n{task.result}")
        elif task.status == TaskStatus.failed:
            parts.append(
                f"## [{task.id}] {task.description}\n\n"
                f"*Failed: {task.error or 'unknown error'}*"
            )
        elif task.status == TaskStatus.skipped:
            parts.append(f"## [{task.id}] {task.description}\n\n*Skipped*")
    return "\n\n---\n\n".join(parts) if parts else "No task outputs available."


def synthesize(plan: Plan) -> str:
    template = _PROMPT_PATH.read_text()
    system = (
        template
        .replace("{goal}", plan.goal)
        .replace("{task_outputs}", _format_task_outputs(plan))
    )
    return llm.summarize(system=system, user="Produce the research brief now.")
