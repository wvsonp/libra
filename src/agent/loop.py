"""
Orchestration loop: iterate the plan until done or a guardrail trips.

Guardrails (all checked every iteration):
  - max_iterations: hard ceiling on total loop turns
  - no-progress breaker: if N consecutive iterations advance no task, abort
  - per-task timeout and per-task tool-call cap (enforced inside executor)

On guardrail trip, the loop synthesizes an honest partial result rather than
returning nothing.
"""
from __future__ import annotations

from src.agent.executor import execute_task
from src.config import cfg
from src.logging import log_step, print_warning
from src.models import Plan, TaskStatus

_NO_PROGRESS_CAP = 3  # consecutive iterations without a task completing -> abort


def run_loop(plan: Plan) -> None:
    """
    Run the execution loop. Mutates plan tasks in-place (status, result).
    Logs every completed step to JSONL + console.
    """
    iterations = 0
    no_progress_streak = 0

    while not plan.is_complete():
        if iterations >= cfg.max_iterations:
            print_warning(
                f"Reached max_iterations ({cfg.max_iterations}). "
                "Stopping loop with partial results."
            )
            _mark_remaining_skipped(plan)
            break

        ready = plan.ready_tasks()

        if not ready:
            no_progress_streak += 1
            if no_progress_streak >= _NO_PROGRESS_CAP:
                print_warning(
                    f"No ready tasks for {_NO_PROGRESS_CAP} consecutive iterations "
                    "(possible dependency cycle or all tasks blocked). Stopping."
                )
                _mark_remaining_skipped(plan)
                break
            iterations += 1
            continue

        no_progress_streak = 0

        # Execute ready tasks (serial — simpler, easier to trace; parallel is a future opt)
        for task in ready:
            step = execute_task(plan, task, plan.run_id)
            log_step(step)

        iterations += 1


def _mark_remaining_skipped(plan: Plan) -> None:
    """Mark all still-pending tasks as skipped when the loop aborts early."""
    for task in plan.tasks:
        if task.status == TaskStatus.pending:
            task.status = TaskStatus.skipped
