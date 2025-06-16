# Ask‑Intercom – Vision

> _A model‑agnostic assistant that turns raw Intercom conversations into actionable product, support, and roadmap insights—directly inside Slack._

---

## 1 · Purpose

Enable any team to interrogate its support history with natural language and receive clear, context‑rich answers, digests, and alerts—while keeping model choice, data ownership, and extension points fully open‑source.

## 2 · Problem Statement

- **Scattered knowledge** – Valuable customer signals hide in thousands of support threads.
    
- **Vendor lock‑in** – Existing AI add‑ons tie you to one model, one pricing plan, and rigid dashboards.
    
- **Slow feedback loops** – PMs wait days for manual tagging or BI exports; engineers miss emerging bugs.
    

## 3 · Differentiation

|Axis|Ask‑Intercom|Typical SaaS add‑on|
|---|---|---|
|Model choice|Plug‑in any OpenAI‑, Anthropic‑, Groq‑, or local Llama adapter|Fixed to vendor’s model|
|Deployment|Self‑host / cloud / on‑prem|Cloud only|
|Extensibility|Apache‑2.0 core + plugin SDK|Closed|
|Alert logic|DSL + schedule + thresholds|Limited presets|

## 4 · Core User Stories (v1)

1. **`/askintercom`** – Ad‑hoc NL query → threaded Slack answer.
    
2. **Scheduled digest** – “Every Friday 10 ET: angry‑customers summary.”
    
3. **Alert rule** – “> 10 tickets > 1 h unanswered → ping #support‑lead.”
    
4. **CLI** – Run the same asks locally for testing or automation.
    

## 5 · High‑Level Architecture

```
Slack Cmd  ─┐        +───────────────+
Scheduler ──┼─▶  API │ Ask‑Intercom  │───▶ Intercom API
CLI local  ─┘        +─────┬─────────+
                            │
       pgvector (embeddings)│  Postgres (raw JSON)
```

_Key tech_: FastAPI, LangChain agent tools, Temporal/Celery jobs, pgvector or Pinecone, HashiCorp Vault for secrets.

## 6 · Phased Roadmap

|Phase|Deliverable|Success signal|
|---|---|---|
|0|CLI prototype w/ local JSON ingest|Answers align ≥ 80 % with manual checks|
|1|Slack MVP (`/askintercom`)|Internal Spritz team uses daily|
|2|Scheduled digests & alert DSL|No manual weekly reporting needed|
|3|Multi‑tenant SaaS + billing|First external paying workspace|
|4|Plugin ecosystem|≥ 3 community integrations (Retool, email, Grafana)|

## 7 · Licensing & Monetisation

- **Code**: Apache‑2.0 (patent peace, business‑friendly)
    
- **Hosted tier**: Usage‑based Stripe metered billing (tokens + jobs).
    
- **Marketplace listings**: Slack App Directory free tier → paid upgrade; Intercom App Store link‑out.
    

## 8 · Community & "Build‑in‑Public" Plan

- Ship changelog threads on X, fortnightly.
    
- Product Hunt “coming soon” once Slack MVP stable.
    
- GitHub Discussions + CLA‑bot; label `good‑first‑issue`.
    

## 9 · Pre‑Mortem Highlights (top 5)

1. Schema drift / rate limits break ingest → **Mitigation**: raw JSON archive, versioned loaders.
    
2. LLM cost spike & latency > 10 s → streaming responses, per‑workspace quota.
    
3. Scheduler duplicates jobs on restart → idempotent run‑locks.
    
4. Slack review rejects scopes → least‑privilege OAuth & security white‑paper.
    
5. Multi‑tenant leak via shared cache → tenant prefix & automated secret scans.
    

## 10 · Success Metrics

- Average response time < 5 s P95.
    
- Token cost / digest < US$0.02.
    
- Weekly active queries per user ≥ 3.
    
- NPS from internal pilot ≥ 40.
    

## 11 · Open Questions (answer before next sprint)

1. **Pilot scope** – Internal Spritz only or include design‑partner teams?
    
2. **Data residency** – Any requirement for EU‑only hosting?
    
3. **Recall vs precision** – Is 90‑day conversation window sufficient, or full history?
    
4. **Alert DSL** – JSON rules v. lightweight YAML?
    
5. **Vector DB** – Start with `pgvector` or external Pinecone for simplicity?
    
6. **Auth strategy** – Single Slack app token per workspace or user‑level tokens?
    
7. **Budget guardrails** – Initial monthly LLM cost cap?
    
8. **Brand** – Stick with `ask-intercom` even if other CRMs added later?
    

---

_Document version 0.1 – Jun 15 2025.  Iterate freely._