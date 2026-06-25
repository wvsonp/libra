from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from src.config import cfg


class LLMClient:
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=cfg.openai_api_key,
        )

    def plan_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        response = self._client.chat.completions.create(
            model=cfg.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "plan", "strict": True, "schema": schema},
            },
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Model returned no content")
        return json.loads(content)

    def act(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> tuple[Any, int]:
        response = self._client.chat.completions.create(
            model=cfg.openai_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        usage = response.usage
        return response.choices[0].message, usage.total_tokens if usage else 0

    def summarize(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=cfg.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


llm = LLMClient()
