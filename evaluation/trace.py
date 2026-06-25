"""Read agent run artifacts for scoring."""
from __future__ import annotations

import json
from pathlib import Path

from src.config import cfg
from src.models import Plan, TaskStatus


def tools_used(run_id: str) -> list[str]:
    """Return unique tool names (excluding finish_task) called during a run."""
    path = cfg.runs_dir / run_id / "steps.jsonl"
    if not path.exists():
        return []
    names: set[str] = set()
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        step = json.loads(line)
        for tc in step.get("tool_calls", []):
            name = tc.get("name", "")
            if name and name != "finish_task":
                names.add(name)
    return sorted(names)


def evidence_text(plan: Plan) -> str:
    """Compact text of all task results + source URLs for faithfulness scoring."""
    parts: list[str] = []
    for task in plan.tasks:
        if task.status == TaskStatus.done and task.result:
            parts.append(f"[{task.id}] {task.result}")
        elif task.status == TaskStatus.failed and task.error:
            parts.append(f"[{task.id}] FAILED: {task.error}")
    return "\n\n".join(parts) if parts else "(no evidence)"
