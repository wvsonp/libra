"""Reusable pipeline: goal -> plan -> loop -> synthesize -> brief."""
from __future__ import annotations

from src.agent.loop import run_loop
from src.agent.planner import create_plan
from src.agent.synthesizer import synthesize
from src.config import cfg
from src.models import Plan
from src.store import save


def run_goal(goal: str) -> tuple[Plan, str]:
    plan = create_plan(goal)
    save(plan)
    run_loop(plan, after_step=save)
    brief = synthesize(plan)
    save(plan)
    brief_path = cfg.runs_dir / plan.run_id / "brief.md"
    brief_path.write_text(f"# Research Brief\n\n**Goal:** {plan.goal}\n\n{brief}\n")
    return plan, brief
