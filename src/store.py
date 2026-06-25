"""Persist and load Plan state under .runs/<run_id>/plan.json."""
from __future__ import annotations

from pathlib import Path

from src.models import Plan

_RUNS = Path(".runs")


def _plan_path(run_id: str) -> Path:
    return _RUNS / run_id / "plan.json"


def save(plan: Plan) -> None:
    path = _plan_path(plan.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan.model_dump_json(indent=2))


def load(run_id: str) -> Plan:
    return Plan.model_validate_json(_plan_path(run_id).read_text())


def list_runs() -> list[str]:
    if not _RUNS.is_dir():
        return []
    plans = sorted(_RUNS.glob("*/plan.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [p.parent.name for p in plans]
