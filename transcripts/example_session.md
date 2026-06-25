# Example Session Transcript

**Goal:** Compare managed Postgres options for a small SaaS (Supabase, Neon, RDS, PlanetScale)

**Run ID:** `a1b2c3d4`

**Note:** This is an illustrative transcript showing the intended information
flow. Real output will vary based on current web content. Tool outputs are
abbreviated for readability.

---

## Step 1 — Planning

**Input to planner:**
```
Research goal: Compare managed Postgres options for a small SaaS
(Supabase, Neon, RDS, PlanetScale)
```

**Planner output (structured JSON → validated Plan):**
```json
{
  "goal": "Compare managed Postgres options for a small SaaS (Supabase, Neon, RDS, PlanetScale)",
  "tasks": [
    {
      "id": "search_supabase",
      "description": "Search for Supabase pricing and features for small SaaS",
      "depends_on": []
    },
    {
      "id": "search_neon",
      "description": "Search for Neon Postgres pricing and features",
      "depends_on": []
    },
    {
      "id": "search_rds",
      "description": "Search for AWS RDS Postgres pricing and minimum cost for small deployments",
      "depends_on": []
    },
    {
      "id": "search_planetscale",
      "description": "Search for PlanetScale Postgres support and pricing",
      "depends_on": []
    },
    {
      "id": "compare_and_summarize",
      "description": "Compare all four options across pricing, scalability, and SaaS fit",
      "depends_on": ["search_supabase", "search_neon", "search_rds", "search_planetscale"]
    }
  ]
}
```

**Console output:**
```
━━━━━━━━━━━━━━━━━ Research Agent  run=a1b2c3d4 ━━━━━━━━━━━━━━━━━
Goal: Compare managed Postgres options for a small SaaS

━━━━━━━━━━━━━━━━━━━━━━━━━━ Plan ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[pending    ] search_supabase: Search for Supabase pricing and features for small SaaS
[pending    ] search_neon: Search for Neon Postgres pricing and features
[pending    ] search_rds: Search for AWS RDS Postgres pricing and minimum cost
[pending    ] search_planetscale: Search for PlanetScale Postgres support and pricing
[pending    ] compare_and_summarize: Compare all four options across pricing, scalability, and SaaS fit
```

---

## Step 2 — Execution loop

### Task: `search_supabase`

**Per-task context sent to executor (not the full transcript):**
- Current task: `search_supabase`
- Dependencies: none
- Compact plan view: 5 tasks, all pending

**Executor tool calls:**
1. `web_search(query="Supabase pricing managed Postgres 2024")`
   → 5 results with snippets + URLs
2. `fetch(url="https://supabase.com/pricing")`
   → Extracted text: "Free tier: 500MB database, 2 projects. Pro: $25/mo, 8GB database..."

**Executor calls `finish_task`:**
```
result: "Supabase offers a free tier (500MB, 2 projects) and a Pro plan at $25/month
         (8GB database, unlimited API requests). Includes auth, storage, and realtime
         out of the box — well suited for early-stage SaaS.
         Sources: https://supabase.com/pricing"
sources: ["https://supabase.com/pricing"]
```

**JSONL log entry:**
```json
{
  "run_id": "a1b2c3d4",
  "task_id": "search_supabase",
  "timestamp": "2024-11-15T14:22:03Z",
  "status": "done",
  "tool_calls": [
    {"name": "web_search", "arguments": {"query": "Supabase pricing managed Postgres 2024"}, "result": "..."},
    {"name": "fetch", "arguments": {"url": "https://supabase.com/pricing"}, "result": "..."},
    {"name": "finish_task", "arguments": {"result": "Supabase offers...", "sources": [...]}, "result": "..."}
  ],
  "result_summary": "Supabase offers a free tier...",
  "tokens_used": 842
}
```

**Console output:**
```
[search_supabase] DONE        tools=[web_search(...), fetch(...)] → Supabase offers a free tier…
```

---

*(Tasks `search_neon`, `search_rds`, `search_planetscale` execute the same way — omitted for brevity.)*

---

### Task: `compare_and_summarize` (runs after all search tasks complete)

**Per-task context:**
- Current task: `compare_and_summarize`
- Dependencies: outputs of all 4 search tasks (each ≤ 600 chars, trimmed)
- Compact plan view: 4 done, 1 in_progress

**Executor calls `finish_task` (no tool calls needed — synthesizes from dep outputs):**
```
result: "Supabase and Neon are the strongest fits for early-stage SaaS. Supabase
         bundles auth/storage/realtime at $25/mo; Neon offers serverless branching
         with a generous free tier. RDS is more expensive at the low end (~$15/mo
         minimum) but gives full AWS control. PlanetScale recently added Postgres
         support but its primary strength is MySQL/Vitess."
```

---

## Step 3 — Synthesis

**Synthesizer input:** all 5 task results concatenated (formatted Markdown).

**Final brief:**

---

### Managed Postgres Comparison for Small SaaS

**Overview**

Four leading managed Postgres options suit different stages and priorities for a
small SaaS product. Here is how they compare on pricing, features, and fit.

**Supabase** is the most feature-complete option for early-stage SaaS. Its free
tier provides 500MB of database storage across 2 projects, with the Pro plan at
$25/month offering 8GB and unlimited API calls. Critically, Supabase bundles
authentication, file storage, and realtime subscriptions — meaning you avoid
managing separate services. [Source: https://supabase.com/pricing]

**Neon** offers a serverless Postgres model with database branching (a
git-branch-like feature for schemas), making it particularly good for
development workflows and preview environments. Its free tier is generous, and
pay-as-you-go pricing scales without a large fixed cost. Ideal if you value
branching and low idle cost. [Source: https://neon.tech/pricing]

**AWS RDS Postgres** is the most operationally mature option and integrates
naturally with other AWS services. However, the minimum cost (a `db.t3.micro`
instance) is approximately $15–25/month before storage and I/O, and there is no
meaningful free tier for production. Suited to teams already in the AWS
ecosystem or expecting rapid growth. [Source: https://aws.amazon.com/rds/pricing]

**PlanetScale** recently added Postgres support but its core product is built
on MySQL/Vitess. Postgres compatibility is newer and less battle-tested. May be
worth watching but is not the strongest Postgres choice today.

**Recommendation**

For an early-stage SaaS: **Supabase** for teams who want batteries included,
**Neon** for teams who prioritize development workflow and low idle cost. Move to
**RDS** when operational control and AWS integration become priorities.

---

## Run summary

```
━━━━━━━━━━━━━━━━━━━━━━━━ Result ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[... brief printed above ...]

Brief saved to .runs/a1b2c3d4/brief.md
Run ID: a1b2c3d4
```

**Artefacts written:**
- `.runs/a1b2c3d4/plan.json` — full plan with final task statuses and results
- `.runs/a1b2c3d4/steps.jsonl` — one JSONL line per step (tools, tokens, timing)
- `.runs/a1b2c3d4/brief.md` — the final research brief

**To resume if interrupted:** `python -m src.cli --resume a1b2c3d4`
