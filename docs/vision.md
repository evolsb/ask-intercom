# Ask‑Intercom – Vision

> **What this document is:** The north star for Ask-Intercom. Defines what we're building, why it matters, and how it's different from existing solutions. Use this as the reference for all strategic decisions.

> _A model‑agnostic assistant that turns raw Intercom conversations into actionable product, support, and roadmap insights—directly inside Slack._

---

## 1 · Purpose

Enable any team to interrogate its support history with natural language and receive clear, context‑rich answers, digests, and alerts—while keeping model choice, data ownership, and extension points fully open‑source.

## 2 · Problem Statement

- **Scattered knowledge** – Valuable customer signals hide in thousands of support threads.

- **Slow feedback loops** – PMs wait days for manual tagging or BI exports; engineers miss emerging bugs.


## 3 · Differentiation


|Axis|Ask‑Intercom|Typical SaaS add‑on|
|---|---|---|
|Model choice|Plug‑in any OpenAI‑, Anthropic‑, Groq‑, or local Llama adapter|Fixed to vendor's model|
|Deployment|Docker self‑host → optional managed hosting|Cloud only|
|Extensibility|Apache‑2.0 core + plugin SDK|Closed|
|Alert logic|DSL + schedule + thresholds|Limited presets|
|Intercom integration|Native MCP protocol support|Basic API polling|
|Agentic workflows|Multi‑step reasoning with tool‑calling|Simple keyword matching|

## 4 · Core User Stories (v1)

1. **`/askintercom`** – Ad‑hoc NL query → threaded Slack answer.
   - _"Are there any recent patterns or spikes in activity from users?"_
   - _"What are the top 3 customer pain points mentioned in the last 90 days?"_
   - _"Summarize the problem that jon@gmail.com has been having?"_
   - _"Based on conversations in the last 120 days, what are the top 4 things we should add to our roadmap?"_

2. **Scheduled digest** – "Every Friday 10 ET: angry‑customers summary."
   - _"Were there any angry customers this week?"_
   - _"How many customer service messages were opened this week?"_
   - _"Summarize the engineering related tickets this week"_

3. **Alert rule** – "> 10 tickets > 1 h unanswered → ping #support‑lead."
   - _"This ticket has been open more than 3 days and no one has responded!"_
   - _"More than 10 tickets open > 1 hour from CS agent Lucas"_

4. **CLI** – Run the same asks locally for testing or automation.


## 5 · High‑Level Architecture

```
Slack Cmd  ─┐        +───────────────+
Scheduler ──┼─▶  API │ Ask‑Intercom  │───▶ Intercom API
CLI local  ─┘        +─────┬─────────+
                            │
       pgvector (embeddings)│  Postgres (raw JSON)
```

**Key tech choices:**

- **FastAPI** – High‑performance async Python API framework with auto‑generated OpenAPI docs
- **LangChain agentic workflows** – Multi‑step reasoning with tool‑calling for complex query orchestration
- **Intercom MCP integration** – Native Model Context Protocol support for efficient, real‑time data access
- **Temporal/Celery** – Reliable job scheduling and workflow orchestration for digests and alerts
- **pgvector or Pinecone** – Vector embeddings storage for semantic search across conversation history
- **HashiCorp Vault** – Secure secrets management for API keys and sensitive configuration

## 6 · Phased Roadmap

|Phase|Deliverable|Success signal|
|---|---|---|
|0|CLI prototype w/ local JSON ingest|Answers align ≥ 80 % with manual checks|
|1|Slack MVP (`/askintercom`)|Test team uses daily|
|2|Docker self‑host package|First external organization deploys successfully|
|3|Scheduled digests & alert DSL|No manual weekly reporting needed|
|4|Optional managed hosting + agent marketplace|Revenue from hosted tier or marketplace|

## 7 · Licensing & Monetisation

- **Code**: Apache‑2.0 open source (patent peace, business‑friendly)

- **Self‑hosted**: Free forever with user‑provided API keys

- **Managed hosting**: Optional convenience tier with usage‑based billing

- **Agent marketplace**: Revenue sharing on OpenAI GPT Store, Anthropic Claude Apps, etc.

- **Enterprise**: Professional services for custom integrations and support


## 8 · Pre‑Mortem Highlights (top 5)

1. Schema drift / rate limits break ingest → **Mitigation**: raw JSON archive, versioned loaders.

2. LLM cost spike & latency > 10 s → streaming responses, per‑workspace quota.

3. Scheduler duplicates jobs on restart → idempotent run‑locks.

4. Slack review rejects scopes → least‑privilege OAuth & security white‑paper.

5. Multi‑tenant leak via shared cache → tenant prefix & automated secret scans.


## 9 · Success Metrics

- Average response time < 5 s P95.

- Token cost / digest < US$0.02.

- Weekly active queries per user ≥ 3.

- NPS from internal pilot ≥ 40.


---

_Document version 0.1 – Jun 15 2025.  Iterate freely._
