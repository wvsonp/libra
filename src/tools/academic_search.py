"""Mock academic_search tool — swap for Semantic Scholar / Crossref in prod."""
from __future__ import annotations

from src.tools.registry import ToolSpec, register

_MOCK_PAPERS = [
    {
        "title": "A Survey of Large Language Models",
        "authors": "Zhao et al.",
        "year": 2023,
        "abstract": "Comprehensive review of pre-trained language models, scaling laws, and emergent capabilities.",
        "doi": "10.48550/arXiv.2303.18223",
    },
    {
        "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "authors": "Lewis et al.",
        "year": 2020,
        "abstract": "RAG combines parametric memory with non-parametric retrieval for open-domain QA.",
        "doi": "10.48550/arXiv.2005.11401",
    },
    {
        "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
        "authors": "Wei et al.",
        "year": 2022,
        "abstract": "Series of intermediate reasoning steps substantially improves complex reasoning tasks.",
        "doi": "10.48550/arXiv.2201.11903",
    },
]


def academic_search(query: str) -> str:
    results = "\n\n".join(
        f"Title: {p['title']}\n"
        f"Authors: {p['authors']} ({p['year']})\n"
        f"Abstract: {p['abstract']}\n"
        f"DOI: {p['doi']} [MOCK]"
        for p in _MOCK_PAPERS
    )
    return f"Academic search results for '{query}':\n\n{results}"


register(
    "academic_search",
    ToolSpec(
        fn=academic_search,
        description=(
            "Search peer-reviewed academic papers, journals, and research publications. "
            "Returns titles, authors, abstracts, and DOIs. "
            "Use when the goal requires scholarly evidence, citations, or technical papers "
            "rather than general web content."
        ),
        parameters={
            "query": {
                "type": "string",
                "description": "Research query to search academic databases for.",
            }
        },
    ),
)
