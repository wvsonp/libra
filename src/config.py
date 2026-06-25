from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    # Defaults keep import side-effect-free so offline use (tests, --list-runs)
    # works with no .env. The API key is validated lazily via require_api_key()
    # at the start of a real run, not at import time.
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.1")
    openai_eval_model: str = os.getenv("OPENAI_EVAL_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.1"))

    max_plan_tasks: int = int(os.getenv("MAX_PLAN_TASKS", "12"))
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "30"))
    max_tool_calls_per_task: int = int(os.getenv("MAX_TOOL_CALLS_PER_TASK", "4"))
    task_timeout_seconds: int = int(os.getenv("TASK_TIMEOUT_SECONDS", "60"))

    search_max_results: int = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
    search_retry_delay: float = float(os.getenv("SEARCH_RETRY_DELAY", "2.0"))

    runs_dir: Path = Path(".runs")

    def require_api_key(self) -> None:
        """Fail fast with a clear message before any real LLM call."""
        if not self.openai_api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and fill in values."
            )


cfg = Config()
