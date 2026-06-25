"""Three evaluation metrics: tool call accuracy, task success, answer faithfulness."""
from __future__ import annotations

from typing import Any

from evaluation.judge import judge_faithfulness, judge_task_success
from evaluation.trace import evidence_text, tools_used
from src.models import Plan


def tool_call_accuracy(run_id: str, expected: list[str]) -> dict[str, Any]:
    """Deterministic set-diff of actual vs expected tools. Returns F1, missing, extra."""
    actual = set(tools_used(run_id))
    expected_set = set(expected)
    tp = len(actual & expected_set)
    precision = tp / len(actual) if actual else 0.0
    recall = tp / len(expected_set) if expected_set else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "actual_tools": sorted(actual),
        "expected_tools": sorted(expected_set),
        "missing": sorted(expected_set - actual),
        "extra": sorted(actual - expected_set),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


def task_success(plan: Plan, brief: str) -> dict[str, Any]:
    """LLM judge: did the agent fully answer the goal? Returns {success, reasoning}."""
    result = judge_task_success(
        goal=plan.goal,
        plan_status=plan.compact_view(),
        brief=brief,
    )
    return {
        "success": bool(result["success"]),
        "reasoning": result.get("reasoning", ""),
    }


def answer_faithfulness(plan: Plan, brief: str) -> dict[str, Any]:
    """LLM judge: is the brief grounded in gathered evidence? Returns {score, ...}."""
    evidence = evidence_text(plan)
    result = judge_faithfulness(brief=brief, evidence=evidence)
    return {
        "score": float(result["score"]),
        "unsupported_claims": result.get("unsupported_claims", []),
        "reasoning": result.get("reasoning", ""),
    }
