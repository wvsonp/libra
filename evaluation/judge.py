"""LLM-as-judge calls for task success and answer faithfulness."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config import cfg
from src.llm.client import llm

_PROMPTS = Path(__file__).parent / "prompts"

_SUCCESS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "reasoning": {"type": "string"},
    },
    "required": ["success", "reasoning"],
    "additionalProperties": False,
}

_FAITHFULNESS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "score": {"type": "number"},
        "unsupported_claims": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["score", "unsupported_claims", "reasoning"],
    "additionalProperties": False,
}


def judge_task_success(
    goal: str,
    plan_status: str,
    brief: str,
    success_criteria: list[str] | None = None,
) -> dict[str, Any]:
    template = (_PROMPTS / "task_success.md").read_text()
    criteria = "\n".join(f"- {item}" for item in success_criteria or [])
    if not criteria:
        criteria = "No scenario-specific criteria provided; judge against the goal."
    system = (
        template
        .replace("{goal}", goal)
        .replace("{success_criteria}", criteria)
        .replace("{plan_status}", plan_status)
        .replace("{brief}", brief)
    )
    return llm.plan_json(
        system=system,
        user="Evaluate now.",
        schema=_SUCCESS_SCHEMA,
        model=cfg.openai_eval_model,
    )


def judge_faithfulness(brief: str, evidence: str) -> dict[str, Any]:
    template = (_PROMPTS / "faithfulness.md").read_text()
    system = (
        template
        .replace("{brief}", brief)
        .replace("{evidence}", evidence)
    )
    return llm.plan_json(
        system=system,
        user="Evaluate now.",
        schema=_FAITHFULNESS_SCHEMA,
        model=cfg.openai_eval_model,
    )
