from __future__ import annotations

import httpx
import trafilatura

from src.tools.registry import ToolSpec, register

_MAX_CHARS = 4000
_TIMEOUT = 15


def fetch(url: str) -> str:
    try:
        response = httpx.get(
            url,
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "research-agent/1.0"},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return f"fetch failed: HTTP {exc.response.status_code} for {url}"
    except httpx.RequestError as exc:
        return f"fetch failed: {exc}"

    text = trafilatura.extract(response.text, include_links=False, include_tables=False)
    if not text:
        return f"fetch failed: no readable content at {url}"

    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS] + "\n[...truncated...]"

    return f"[Fetched: {url}]\n\n{text}"


register(
    "fetch",
    ToolSpec(
        fn=fetch,
        description="Fetch a URL and return up to 4000 chars of extracted text.",
        parameters={
            "url": {
                "type": "string",
                "description": "Full URL (http:// or https://)",
            }
        },
    ),
)
