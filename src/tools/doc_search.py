"""Mock doc_search — swap for real RAG when needed."""
from __future__ import annotations

from src.tools.registry import ToolSpec, register

_MOCK = [
    ("docs/overview.md", "Managed Postgres options include Supabase, Neon, Railway, and AWS RDS."),
    ("docs/pricing.md", "Supabase Pro starts at $25/month. Neon offers serverless branching."),
    ("docs/notes.md", "Prioritize connection pooling and backup policy for early-stage products."),
]


def doc_search(query: str) -> str:
    return "\n\n".join(
        f"[{source} | MOCK]\nQuery: {query}\n{text}" for source, text in _MOCK
    )


def register_doc_search() -> None:
    register(
        "doc_search",
        ToolSpec(
            fn=doc_search,
            description="Search local documents; returns relevant text chunks with sources.",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Natural language query",                }
            },
        ),
    )
