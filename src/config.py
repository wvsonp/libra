from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Copy .env.example to .env and fill in values."
        )
    return val


class Config:
    openai_api_key: str = _require("OPENAI_API_KEY")
    openai_model: str = os.environ["OPENAI_MODEL"]

    max_plan_tasks: int = int(os.environ["MAX_PLAN_TASKS"])
    max_iterations: int = int(os.environ["MAX_ITERATIONS"])
    max_tool_calls_per_task: int = int(os.environ["MAX_TOOL_CALLS_PER_TASK"])
    task_timeout_seconds: int = int(os.environ["TASK_TIMEOUT_SECONDS"])

    search_max_results: int = int(os.environ["SEARCH_MAX_RESULTS"])
    search_retry_delay: float = float(os.environ["SEARCH_RETRY_DELAY"])

    runs_dir: Path = Path(".runs")


cfg = Config()
