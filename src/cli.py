"""
CLI entrypoint.

Usage:
  python -m src.cli "Compare managed Postgres options for a small SaaS"
  python -m src.cli --resume <run_id>
  python -m src.cli "RAG goal" --docs ./docs
  python -m src.cli "goal" --max-iters 20

Tools are registered by importing their modules.
RAG doc_search is mocked; pass --docs to register the tool (no index build).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

_console = Console()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="research-agent",
        description="Research assistant: goal → plan → execute → brief",
    )
    parser.add_argument(
        "goal",
        nargs="?",
        help="Research goal (required unless --resume is used)",
    )
    parser.add_argument(
        "--resume",
        metavar="RUN_ID",
        help="Resume a previous run by its ID",
    )
    parser.add_argument(
        "--docs",
        metavar="DIR",
        help="Path to a local documents directory (enables RAG doc_search tool)",
    )
    parser.add_argument(
        "--max-iters",
        type=int,
        default=None,
        help="Override MAX_ITERATIONS for this run",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List all saved runs and exit",
    )
    return parser.parse_args()


def _register_tools(docs_dir: Path | None) -> None:
    """Import tool modules to trigger their register() calls."""
    import src.tools.web_search  # noqa: F401
    import src.tools.fetch       # noqa: F401

    if docs_dir is not None:
        from src.tools.doc_search import register_doc_search

        register_doc_search()
        _console.print(
            f"[yellow]doc_search enabled (mock) — docs dir {docs_dir} ignored.[/yellow]"
        )


def main() -> None:
    args = _parse_args()

    # ── list-runs shortcut ───────────────────────────────────────────────────
    if args.list_runs:
        from src.store import list_runs

        runs = list_runs()
        if not runs:
            _console.print("[dim]No saved runs found.[/dim]")
        else:
            _console.print("[bold]Saved runs (newest first):[/bold]")
            for rid in runs:
                _console.print(f"  {rid}")
        sys.exit(0)

    # ── validate args ────────────────────────────────────────────────────────
    if not args.goal and not args.resume:
        _console.print("[red]Error: provide a goal or --resume <run_id>[/red]")
        sys.exit(1)

    docs_dir = Path(args.docs) if args.docs else None
    if docs_dir and not docs_dir.is_dir():
        _console.print(f"[red]--docs path does not exist or is not a directory: {docs_dir}[/red]")
        sys.exit(1)

    # ── apply runtime overrides ──────────────────────────────────────────────
    if args.max_iters is not None:
        from src.config import cfg
        cfg.max_iterations = args.max_iters

    # ── register tools ───────────────────────────────────────────────────────
    _register_tools(docs_dir)

    # ── load or create plan ──────────────────────────────────────────────────
    if args.resume:
        from src.store import load

        _console.print(f"[cyan]Resuming run {args.resume} ...[/cyan]")
        plan = load(args.resume)
        remaining = sum(1 for t in plan.tasks if t.status == "pending")
        _console.print(f"[dim]{remaining} task(s) still pending.[/dim]")
    else:
        from src.agent.run import run_goal
        from src.logging import print_header, print_plan, print_result

        goal = args.goal
        _console.print()
        plan, brief = run_goal(goal)
        print_header(plan.run_id, plan.goal)
        print_plan(plan.compact_view())
        print_result(brief)
        _console.print(f"\n[dim]Brief saved to .runs/{plan.run_id}/brief.md[/dim]")
        _console.print(f"[dim]Run ID: {plan.run_id}[/dim]")
        return

    # ── resume path: run the loop ────────────────────────────────────────────
    from src.agent.loop import run_loop
    from src.agent.synthesizer import synthesize
    from src.logging import print_result
    from src.store import save

    run_loop(plan, after_step=save)
    brief = synthesize(plan)
    print_result(brief)
    save(plan)
    brief_path = Path(".runs") / plan.run_id / "brief.md"
    brief_path.write_text(f"# Research Brief\n\n**Goal:** {plan.goal}\n\n{brief}\n")
    _console.print(f"\n[dim]Brief saved to {brief_path}[/dim]")
    _console.print(f"[dim]Run ID: {plan.run_id}[/dim]")


if __name__ == "__main__":
    main()
