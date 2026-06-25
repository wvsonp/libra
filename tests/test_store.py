"""
Tests for the run store: save/load round-trip, list_runs.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from src.models import TaskStatus
from tests.conftest import make_plan


@pytest.fixture(autouse=True)
def tmp_runs_dir(tmp_path, monkeypatch):
    """Redirect .runs to a temp directory so tests don't write to the workspace."""
    runs = tmp_path / ".runs"
    runs.mkdir()
    monkeypatch.chdir(tmp_path)
    return runs


class TestStore:
    def test_save_and_load_round_trip(self):
        from src.store import save, load

        plan = make_plan([
            {"id": "t1", "description": "Search", "depends_on": []},
        ])
        plan.tasks[0].status = TaskStatus.done
        plan.tasks[0].result = "Found stuff."

        save(plan)
        loaded = load(plan.run_id)

        assert loaded.run_id == plan.run_id
        assert loaded.goal == plan.goal
        assert loaded.tasks[0].status == TaskStatus.done
        assert loaded.tasks[0].result == "Found stuff."

    def test_load_missing_raises(self):
        from src.store import load

        with pytest.raises(FileNotFoundError):
            load("nonexistent_run_id")

    def test_list_runs_empty(self):
        from src.store import list_runs

        assert list_runs() == []

    def test_list_runs_returns_saved_ids(self):
        from src.store import save, list_runs

        plan_a = make_plan([{"id": "a", "description": "A", "depends_on": []}])
        plan_b = make_plan([{"id": "b", "description": "B", "depends_on": []}])
        save(plan_a)
        save(plan_b)

        runs = list_runs()
        assert plan_a.run_id in runs
        assert plan_b.run_id in runs
