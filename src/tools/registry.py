from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolSpec:
    fn: Callable[..., str]
    description: str
    parameters: dict[str, Any]


_registry: dict[str, ToolSpec] = {}


def register(name: str, spec: ToolSpec) -> None:
    _registry[name] = spec


def call(name: str, arguments: dict[str, Any]) -> str:
    spec = _registry.get(name)
    if spec is None:
        raise KeyError(f"Unknown tool '{name}'. Registered: {list(_registry)}")
    return spec.fn(**arguments)


def get_tools_for_openai() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": spec.description,
                "parameters": {
                    "type": "object",
                    "properties": spec.parameters,
                    "required": list(spec.parameters.keys()),
                    "additionalProperties": False,
                },
            },
        }
        for name, spec in _registry.items()
    ]


def registered_names() -> list[str]:
    return list(_registry.keys())
