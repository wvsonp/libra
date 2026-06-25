"""
Structured logging: JSONL step log + rich console output.

JSONL log: one StepLog JSON per line in .runs/<run_id>/steps.jsonl
Console: rich-formatted readable lines so the user can follow what's happening.
"""
from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.text import Text

from src.models import StepLog, TaskStatus

_console = Console()


def _run_log_path(run_id: str) -> Path:
    path = Path(".runs") / run_id / "steps.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def log_step(step: StepLog) -> None:
    """Append step to JSONL log and print a human-readable line to the console."""
    path = _run_log_path(step.run_id)
    with path.open("a") as f:
        f.write(step.model_dump_json() + "\n")

    _print_step(step)


def _status_color(status: TaskStatus) -> str:
    return {
        TaskStatus.pending: "dim",
        TaskStatus.in_progress: "cyan",
        TaskStatus.done: "green",
        TaskStatus.failed: "red",
        TaskStatus.skipped: "yellow",
    }.get(status, "white")


def _print_step(step: StepLog) -> None:
    color = _status_color(step.status)
    status_label = f"[{color}]{step.status.value.upper():<11}[/{color}]"

    line = Text()
    line.append(f"[{step.task_id}] ", style="bold")
    line.append_text(Text.from_markup(status_label))

    if step.tool_calls:
        calls = ", ".join(
            f"{tc.name}({_truncate(str(tc.arguments), 40)})"
            for tc in step.tool_calls
        )
        line.append(f" tools=[{calls}]", style="dim")

    if step.result_summary:
        line.append(f" → {_truncate(step.result_summary, 80)}", style="italic")

    if step.error:
        line.append(f" ERR: {_truncate(step.error, 60)}", style="red")

    _console.print(line)


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def print_header(run_id: str, goal: str) -> None:
    _console.rule(f"[bold cyan]Research Agent[/bold cyan]  run={run_id}")
    _console.print(f"[bold]Goal:[/bold] {goal}\n")


def print_plan(compact_view: str) -> None:
    _console.rule("[dim]Plan[/dim]")
    _console.print(compact_view)
    _console.print()


def print_result(brief: str) -> None:
    _console.rule("[bold green]Result[/bold green]")
    _console.print(brief)


def print_warning(msg: str) -> None:
    _console.print(f"[yellow]⚠ {msg}[/yellow]")


def print_error(msg: str) -> None:
    _console.print(f"[red]✗ {msg}[/red]")
