from __future__ import annotations

import time
from typing import Any

from ddgs import DDGS
from ddgs.exceptions import DDGSException

from src.config import cfg
from src.tools.registry import ToolSpec, register

_MAX_RETRIES = 2


def web_search(query: str) -> str:
    """
    Search the web and return a formatted list of results (title, snippet, url).
    Returns an error string on failure so the executor can handle it gracefully.
    """
    last_error: str = ""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            with DDGS() as ddgs:
                results: list[dict[str, Any]] = list(
                    ddgs.text(
                        query,
                        max_results=cfg.search_max_results,
                        safesearch="off",
                    )
                )
            if not results:
                return f"No results found for query: {query}"
            lines = []
            for r in results:
                title = r.get("title", "")
                body = r.get("body", "")
                href = r.get("href", "")
                lines.append(f"Title: {title}\nSnippet: {body}\nURL: {href}")
            return "\n\n".join(lines)
        except DDGSException as exc:
            last_error = str(exc)
            if attempt < _MAX_RETRIES:
                time.sleep(cfg.search_retry_delay * (attempt + 1))
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            break
    return f"web_search failed after {_MAX_RETRIES + 1} attempts: {last_error}"


register(
    "web_search",
    ToolSpec(
        fn=web_search,
        description=(
            "Search the web for current information. "
            "Returns a list of results with title, snippet, and URL. "
            "Use specific, targeted queries for best results."
        ),
        parameters={
            "query": {
                "type": "string",
                "description": "The search query string",
            }
        },
    ),
)
