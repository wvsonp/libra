"""Per-task executor context: task, deps, compact plan — not the full transcript."""
from __future__ import annotations

from pathlib import Path

from src.llm.client import LLMClient
from src.models import Plan, Task

_PROMPT = Path(__file__).parent.parent.parent / "prompts" / "executor.md"
_MAX_DEP_OUTPUT_CHARS = 800
_SUMMARY_CAP = 600


def _trim(text: str, max_chars: int, tag: str = "trimmed") -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n[...{tag}...]"


def build_executor_messages(
    plan: Plan,
    task: Task,
    max_tool_calls: int,
) -> list[dict[str, str]]:
    deps = _format_dep_outputs(plan, task)
    system = (
        _PROMPT.read_text()
        .replace("{goal}", plan.goal)
        .replace("{compact_plan}", plan.compact_view())
        .replace("{task_id}", task.id)
        .replace("{task_description}", task.description)
        .replace("{dependency_outputs}", deps)
        .replace("{max_tool_calls}", str(max_tool_calls))
    )
    return [{"role": "system", "content": system}]


def _format_dep_outputs(plan: Plan, task: Task) -> str:
    if not task.depends_on:
        return "None (this task has no dependencies)."

    by_id = {t.id: t for t in plan.tasks}
    lines = []
    for dep_id in task.depends_on:
        dep = by_id.get(dep_id)
        if dep is None:
            lines.append(f"[{dep_id}]: (unknown dependency)")
            continue
        raw = dep.result or "(no result — task may have failed)"
        lines.append(f"[{dep_id}]: {_trim(raw, _MAX_DEP_OUTPUT_CHARS)}")
    return "\n\n".join(lines)


def summarize_result(raw_result: str, llm_client: LLMClient | None = None) -> str:
    if len(raw_result) <= _SUMMARY_CAP:
        return raw_result

    if llm_client is not None:
        try:
            return llm_client.summarize(
                system="Summarize in 3–5 sentences; keep key facts and URLs.",
                user=raw_result[:3000],
            )
        except Exception:  # noqa: BLE001
            pass

    return _trim(raw_result, _SUMMARY_CAP, tag="summarized/trimmed")
