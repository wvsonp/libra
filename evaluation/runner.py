"""
Evaluation runner.

For each golden scenario: run the agent, then score with three metrics.

Usage:
  uv run python -m evaluation.runner                  # all scenarios
  uv run python -m evaluation.runner --scenario germany_masters
  uv run python -m evaluation.runner --limit 2
  uv run python -m evaluation.runner --no-judge       # tool accuracy only (offline)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

_console = Console()
_HERE = Path(__file__).parent


def _load_golden() -> list[dict[str, Any]]:
    return json.loads((_HERE / "golden.json").read_text())["scenarios"]


def _run_scenario(
    scenario: dict[str, Any],
    use_judge: bool,
) -> dict[str, Any]:
    # Import lazily so --no-judge never needs an API key for imports
    from src.agent.run import run_goal
    from evaluation.metrics import answer_faithfulness, task_success, tool_call_accuracy

    sid = scenario["id"]
    goal = scenario["goal"]
    expected = scenario.get("expected_tools", [])

    _console.rule(f"[cyan]Scenario: {sid}[/cyan]")
    _console.print(f"[dim]Goal:[/dim] {goal}\n")

    plan, brief = run_goal(goal)

    tool_result = tool_call_accuracy(plan.run_id, expected)
    _console.print(f"[bold]Tool accuracy:[/bold] F1={tool_result['f1']:.2f}  "
                   f"missing={tool_result['missing']}  extra={tool_result['extra']}")

    success_result: dict[str, Any] | None = None
    faith_result: dict[str, Any] | None = None

    if use_judge:
        _console.print("[dim]Running LLM judges...[/dim]")
        success_result = task_success(plan, brief)
        faith_result = answer_faithfulness(plan, brief)
        _console.print(
            f"[bold]Task success:[/bold] {success_result['success']}  "
            f"({success_result['reasoning']})"
        )
        _console.print(
            f"[bold]Faithfulness:[/bold] {faith_result['score']:.2f}  "
            f"({faith_result['reasoning']})"
        )

    return {
        "scenario_id": sid,
        "goal": goal,
        "run_id": plan.run_id,
        "tool_call_accuracy": tool_result,
        "task_success": success_result,
        "answer_faithfulness": faith_result,
    }


def _print_summary(results: list[dict[str, Any]], use_judge: bool) -> None:
    table = Table(title="Evaluation Summary", show_lines=True)
    table.add_column("Scenario", style="bold")
    table.add_column("Tool F1", justify="right")
    if use_judge:
        table.add_column("Success", justify="center")
        table.add_column("Faithfulness", justify="right")

    for r in results:
        tool_f1 = str(r["tool_call_accuracy"]["f1"])
        if use_judge:
            suc = r["task_success"] or {}
            fth = r["answer_faithfulness"] or {}
            table.add_row(
                r["scenario_id"],
                tool_f1,
                "✓" if suc.get("success") else "✗",
                f"{fth.get('score', 0.0):.2f}",
            )
        else:
            table.add_row(r["scenario_id"], tool_f1)

    _console.print()
    _console.print(table)

    if use_judge:
        successes = [r for r in results if (r["task_success"] or {}).get("success")]
        faith_scores = [
            (r["answer_faithfulness"] or {}).get("score", 0.0) for r in results
        ]
        mean_f1 = sum(r["tool_call_accuracy"]["f1"] for r in results) / len(results)
        _console.print(
            f"\n[bold]Aggregates:[/bold]  "
            f"task_success_rate={len(successes)}/{len(results)}  "
            f"mean_faithfulness={sum(faith_scores)/len(faith_scores):.2f}  "
            f"mean_tool_f1={mean_f1:.2f}"
        )


def _save_report(results: list[dict[str, Any]], use_judge: bool) -> Path:
    reports_dir = _HERE / "reports"
    reports_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = reports_dir / f"eval_{ts}.json"

    aggregates: dict[str, Any] = {
        "mean_tool_f1": sum(r["tool_call_accuracy"]["f1"] for r in results) / len(results),
    }
    if use_judge:
        successes = [r for r in results if (r["task_success"] or {}).get("success")]
        faith_scores = [
            (r["answer_faithfulness"] or {}).get("score", 0.0) for r in results
        ]
        aggregates["task_success_rate"] = len(successes) / len(results)
        aggregates["mean_faithfulness"] = sum(faith_scores) / len(faith_scores)

    path.write_text(
        json.dumps({"timestamp": ts, "aggregates": aggregates, "scenarios": results}, indent=2)
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluation runner for the research agent.")
    parser.add_argument("--scenario", metavar="ID", help="Run a single scenario by id.")
    parser.add_argument("--limit", type=int, default=None, metavar="N", help="Run only first N scenarios.")
    parser.add_argument("--no-judge", action="store_true", help="Skip LLM judges (offline, deterministic only).")
    args = parser.parse_args()

    # Register agent tools so run_goal works
    import src.tools.web_search  # noqa: F401
    import src.tools.fetch       # noqa: F401

    scenarios = _load_golden()
    if args.scenario:
        scenarios = [s for s in scenarios if s["id"] == args.scenario]
        if not scenarios:
            _console.print(f"[red]Unknown scenario '{args.scenario}'.[/red]")
            raise SystemExit(1)
    if args.limit:
        scenarios = scenarios[: args.limit]

    use_judge = not args.no_judge

    results: list[dict[str, Any]] = []
    for scenario in scenarios:
        try:
            results.append(_run_scenario(scenario, use_judge))
        except Exception as exc:  # noqa: BLE001
            _console.print(f"[red]Scenario '{scenario['id']}' failed: {exc}[/red]")
            results.append({
                "scenario_id": scenario["id"],
                "goal": scenario["goal"],
                "run_id": None,
                "error": str(exc),
                "tool_call_accuracy": None,
                "task_success": None,
                "answer_faithfulness": None,
            })

    if not results:
        _console.print("[yellow]No results.[/yellow]")
        return

    _print_summary(results, use_judge)
    report_path = _save_report(results, use_judge)
    _console.print(f"\n[dim]Report saved to {report_path}[/dim]")


if __name__ == "__main__":
    main()
