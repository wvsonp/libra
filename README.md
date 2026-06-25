# Research Agent

A framework-free AI agent that turns a research goal into a structured TODO plan,
executes each task with real tools, and returns a sourced brief. No LangChain /
LangGraph / AutoGen — loop, prompts, and context are hand-written on the raw
OpenAI SDK.

## Quick start

```bash
uv sync --all-groups          # install deps into .venv
cp .env.example .env          # set OPENAI_API_KEY (+ model names)
uv run python -m src.cli "Compare managed Postgres options for a small SaaS"

uv run python -m src.cli --resume <run_id>   # resume an interrupted run
pytest tests/ -v                             # offline tests, no API key
```

## How the agent loop works

```
goal → plan → [ select → execute → update ]* → synthesize → brief
```

1. **Plan** — planner LLM returns a JSON `Plan` of `Task`s (ids, descriptions,
  dependency edges), schema-validated with Pydantic (`planner.py`).
2. **Select** — each iteration picks *ready* tasks (deps done) via
  `plan.ready_tasks()` (`loop.py`).
3. **Execute** — executor LLM runs a task with tool-calling, then calls
  `finish_task` (`executor.py`).
4. **Update** — status + summarized result written back, one JSONL line logged
  per step, run saved to disk (so it can resume).
5. **Synthesize** — combines all task results into a brief at
  `.runs/<run_id>/brief.md`.

**Guardrails** keep the loop terminating: max iterations (30), max tool calls
per task (4), per-task timeout (60s), and a no-progress breaker (3 idle
iterations). On a trip, remaining tasks are `skipped` and an honest partial brief
is still produced.

## Tools

Tools live in a registry (`name → callable + JSON schema`); adding one is a
single `register()` call, auto-discovered by the executor.


| Tool                             | What it does                                                                 | Status   |
| -------------------------------- | ---------------------------------------------------------------------------- | -------- |
| `web_search`                     | DuckDuckGo (keyless), retries on rate-limit. Prod swap: Tavily.              | **Real** |
| `fetch`                          | Fetches a URL, extracts readable text (`trafilatura`), capped at 4000 chars. | **Real** |
| `doc_search` / `academic_search` | RAG / scholarly lookup — mocks showing the one-line-add registry pattern.    | Mock     |


## Context strategy

Per-call tokens stay flat regardless of plan size — no growing transcript
(`context.py`):

- **Per-task context = task + dependency outputs + compact plan view** (ids +
statuses only). The full transcript and raw logs are never sent.
- **Dependency outputs are summarized** to ≤600 chars *before* storage (trimmed
to 800 when injected), so tasks read condensed facts, not raw dumps.
- **The in-task tool thread is ephemeral** — used for one task, then discarded.
Context is rebuilt per task from the saved run.

## Evaluation

`evaluation.runner` re-runs the agent on `golden.json` scenarios and scores each
with three metrics: **Tool Call Accuracy** (deterministic, offline),
**Task Success Rate** and **Answer Faithfulness** (both LLM-as-judge).

```bash
uv run python -m evaluation.runner              # full eval (needs API key)
uv run python -m evaluation.runner --no-judge   # skip LLM judges (tool-F1 only; still runs the agent)
```

### Scenarios and what "success" means

1. **Well-scoped comparison** (`postgres_compare`, `rust_vs_go`) — decomposes the
  goal, calls `web_search` + `fetch`, and cites the URLs used.
2. **Procedural research** (`germany_masters`) — finds current real-world steps
  and cites official sources rather than guessing.
3. **Ambiguous goal** (`ambiguous_cloud_migration`) — states an assumption,
  scopes to a concrete slice, flags missing details — not boilerplate.
4. **Empty / unanswerable** (`empty_results_obscure_product`) — does **not**
  invent facts or URLs; says no reliable source was found and suggests a next step.
5. **Overly broad goal** (`broad_ai_business`) — narrows to a useful scope, states
  what's in/out of scope, returns a concise grounded brief.

The runner prints a summary table and writes a JSON report to
`evaluation/reports/` (transient, gitignored); one curated run is committed as
`evaluation/reports/sample_eval_report.json`. See
`transcripts/example_session.md` for a full transcript.

## Known limitations

Understood issues, left documented rather than rushed (honesty over a half-fix):

1. **Task-success scores look low (~1–2 / 6).** The LLM judge is intentionally
  strict and penalizes breadth-over-depth on comparison goals; manual reads show
   the briefs are usually correct. The number is reported as-is, not tuned — the
   likely fix is a planner tweak (ask for explicit comparison dimensions), not a
   loop change. See `evaluation/reports/sample_eval_report.json`.
2. **Faithfulness can collapse to 0 when upstream tasks return no evidence.** If
  search/fetch fail or get rate-limited, the synthesizer can still write fluent
   prose from the goal alone, which the faithfulness judge correctly flags. The
   prompt forbids inventing facts but the guardrail is soft; the real fix is to
   refuse synthesis when no evidence was gathered.
3. **Synthesis happens twice.** The planner is told to make the final task a
  "summarize" step *and* a separate synthesizer runs — extra tokens, and the
   intermediate prose can leak in as ungrounded "evidence" (related to #2). The
   cleaner design is to drop the synthesis task and let the dedicated synthesizer
   own that step.

## What I'd do with more time

1. **Parallelize independent ready tasks.** The loop runs ready tasks serially
  for easy tracing; a bounded worker pool would cut wall-clock time.
2. **Real RAG for `doc_search`.** Swap the mock for a small local embedding +
  vector index over a provided doc set, so the  agent can ground answers in private documents.
3. **Production search/fetch + a cost budget.** Move from DuckDuckGo to
  Tavily/Brave behind the same tool signature, cache fetched pages, and add a
   per-run token/cost guardrail alongside the existing iteration/tool-call limits.
4. **Create A minimal UI using Streamlit**

