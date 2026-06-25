"""Run one task via LLM tool-calling; persist only the summarized result."""
from __future__ import annotations

import json
import signal
from contextlib import contextmanager
from typing import Any

from src.agent.context import build_executor_messages, summarize_result
from src.config import cfg
from src.llm.client import llm
from src.models import Plan, StepLog, Task, TaskStatus, ToolCall
from src.tools import registry

_FINISH_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "finish_task",
        "description": "Call this when you have a complete result for the current task.",
        "parameters": {
            "type": "object",
            "properties": {
                "result": {"type": "string", "description": "Concise 2–5 sentence summary."},
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "URLs used as sources.",
                },
            },
            "required": ["result", "sources"],
            "additionalProperties": False,
        },
    },
}


@contextmanager
def _task_timeout(seconds: int):
    def _handler(signum, frame):
        raise TimeoutError(f"Task timed out after {seconds}s")

    try:
        signal.signal(signal.SIGALRM, _handler)
        signal.alarm(seconds)
        yield
    finally:
        signal.alarm(0)


def _step_log(
    run_id: str,
    task: Task,
    tool_call_log: list[ToolCall],
    total_tokens: int,
    **extra: Any,
) -> StepLog:
    return StepLog(
        run_id=run_id,
        task_id=task.id,
        status=task.status,
        tool_calls=tool_call_log,
        tokens_used=total_tokens,
        **extra,
    )


def _complete(task: Task, text: str) -> None:
    task.status = TaskStatus.done
    task.result = summarize_result(text, llm)


def _parse_args(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _assistant_turn(msg) -> dict[str, Any]:
    turn: dict[str, Any] = {"role": "assistant", "content": msg.content}
    if msg.tool_calls:
        turn["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ]
    return turn


def _run_tool(fn_name: str, args: dict[str, Any], log: list[ToolCall]) -> str:
    try:
        result = registry.call(fn_name, args)
        log.append(ToolCall(name=fn_name, arguments=args, result=result))
        return result
    except Exception as exc:  # noqa: BLE001
        error = f"Tool '{fn_name}' error: {exc}"
        log.append(ToolCall(name=fn_name, arguments=args, error=error))
        return error


def execute_task(plan: Plan, task: Task, run_id: str) -> StepLog:
    messages = build_executor_messages(plan, task, cfg.max_tool_calls_per_task)
    tools = registry.get_tools_for_openai() + [_FINISH_TOOL]
    tool_call_log: list[ToolCall] = []
    tool_calls_made = 0
    total_tokens = 0
    task.status = TaskStatus.in_progress

    try:
        with _task_timeout(cfg.task_timeout_seconds):
            while tool_calls_made <= cfg.max_tool_calls_per_task:
                msg, tokens = llm.act(messages, tools)
                total_tokens += tokens
                messages.append(_assistant_turn(msg))

                if not msg.tool_calls:
                    _complete(task, msg.content or "No result returned.")
                    break

                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    args = _parse_args(tc.function.arguments)

                    if fn_name == "finish_task":
                        text = args.get("result", "")
                        sources = args.get("sources", [])
                        if sources:
                            text += "\n\nSources: " + ", ".join(sources)
                        _complete(task, text)
                        tool_call_log.append(
                            ToolCall(name=fn_name, arguments=args, result=task.result)
                        )
                        return _step_log(
                            run_id, task, tool_call_log, total_tokens, result_summary=task.result
                        )

                    tool_calls_made += 1
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": _run_tool(fn_name, args, tool_call_log),
                    })

                if tool_calls_made >= cfg.max_tool_calls_per_task:
                    messages.append({
                        "role": "user",
                        "content": (
                            "You have reached the tool call limit for this task. "
                            "Call finish_task now with what you have."
                        ),
                    })

    except TimeoutError as exc:
        task.status = TaskStatus.failed
        task.error = str(exc)
        return _step_log(run_id, task, tool_call_log, total_tokens, error=task.error)
    except Exception as exc:  # noqa: BLE001
        task.status = TaskStatus.failed
        task.error = f"Unexpected executor error: {exc}"
        return _step_log(run_id, task, tool_call_log, total_tokens, error=task.error)

    return _step_log(run_id, task, tool_call_log, total_tokens, result_summary=task.result)
