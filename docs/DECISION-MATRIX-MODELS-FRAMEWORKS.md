# Decision matrix — models & frameworks (sample)

> **Principle:** Use a **decision matrix**, not the most fashionable model or framework.  
> Product teams consume capabilities through an **approved model catalog + model gateway**  
> (`enterprise-ai-platform-planes`) — they do not hard-code one provider.  
> For simple extraction/classification, prefer a **smaller model**. Escalate to a more capable  
> model **only when evaluations prove incremental business value**.

---

## 1. Model decision matrix (sample scores)

**Scale:** 1 = poor fit · 3 = acceptable · 5 = strong fit for *this* use case  
**Weights:** tune per program (example below = regulated merchandising / platform AI)

| Criterion | Weight | Small / fast<br/>(e.g. GPT-4o-mini, Phi) | Mid capability<br/>(e.g. GPT-4o) | Large reasoning<br/>(flagship) | Local / extractive<br/>(CI / air-gap) | How to measure |
|---|---:|---:|---:|---:|---:|---|
| **Task quality & reasoning** | 20% | 3 | 4 | **5** | 2 | Golden-set accuracy / judge+human |
| **Latency & throughput** | 15% | **5** | 3 | 2 | **5** | p95 latency, QPS @ SLO |
| **Context size** | 10% | 3 | **5** | **5** | 2 | Max tokens vs corpus pack |
| **Data residency & privacy** | 15% | **4**† | **4**† | 3† | **5** | Region, retention, DLP/BAA |
| **Tool calling & structured output** | 10% | 4 | **5** | **5** | 1 | Tool success rate, JSON schema pass |
| **Cost per successful transaction** | 15% | **5** | 3 | 1 | **5** | `$ / completed task` (not $ / token) |
| **Evaluation performance** | 10% | 3 | **4** | **5** | 2 | Eval harness gate (MRR, groundedness, …) |
| **Portability & vendor concentration** | 5% | 4 | 3 | 2 | **5** | Multi-provider catalog coverage |
| **Weighted total (example)** | 100% | **4.05** | **3.85** | **3.45** | **3.40** | Pick highest *that passes go/no-go* |

† Assumes Azure OpenAI in approved region with enterprise terms; adjust down if data leaves controlled boundary.

### Go / no-go overrides (any score → reject)

| Gate | Fail if… |
|---|---|
| Privacy / residency | Model cannot run in approved Azure region / contract |
| Tool calling needed | No reliable structured tool/JSON support for the use case |
| Eval gate | New model does not beat incumbent on **business metric**, only on blog benches |
| Cost ceiling | Cost per successful txn exceeds FinOps budget for the product |

### Worked example — when to use which

| Use case | Default choice | Escalate when… |
|---|---|---|
| Classification / tagging / PII redaction labels | **Small / fast** | F1 on hard classes &lt; SLO after prompt+rules |
| Extraction to schema (cost terms, IDs) | **Small + structured out** | Schema pass rate &lt; 95% on eval set |
| Grounded RAG answer (assistant) | **Mid** via gateway | Groundedness/citation fail OR judge score gap &gt; threshold |
| Multi-step planning / hard reasoning | **Large** (route `quality`) | Eval proves Δ business value (e.g. fewer HITL escalations) |
| CI / deterministic offline | **Local extractive** | Always for unit tests; prod only if air-gap |

---

## 2. Framework decision matrix (sample scores)

Same scale. Architecture owns **bounded autonomy**; framework is an implementation option.

| Criterion | Weight | LangGraph | CrewAI | Agno | Google ADK | Temporal‡ | Pure Python ref. |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Workflow & state management** | 20% | **5** | 3 | 3 | 4 | **5** | 3 |
| **Checkpointing & recovery** | 15% | **5** | 2 | 2 | 4 | **5** | 2 |
| **Tool authorization** | 15% | 4 | 3 | 3 | 4 | 4§ | **5** (explicit allow-list) |
| **Human-in-the-loop support** | 15% | **4** | 3 | 3 | 4 | **5** | **4** |
| **Tracing & evaluation integration** | 10% | **5** | 3 | 3 | **5** | 4 | 4 |
| **Deployment & operational maturity** | 10% | 4 | 3 | 3 | 4 (GCP) | **5** | 4 |
| **Developer learning curve** | 5% | 3 | **4** | **4** | 3 | 2 | **5** |
| **Vendor portability (Azure-first)** | 10% | **5** | **5** | **5** | 2 | **5** | **5** |
| **Weighted total (example)** | 100% | **4.50** | **3.25** | **3.25** | **3.85** | **4.60** | **3.95** |

‡ Temporal is **not** an LLM agent framework — use for durable workflows / long HITL. Often **combined** with LangGraph.  
§ Tool auth still enforced in your policy layer; Temporal orchestrates timing/state.

### Recommended stance (this portfolio)

| Role | Choice | Why |
|---|---|---|
| Agent graph / planning nodes | **LangGraph** (or pure-Python nodes first) | State, checkpoints, testability |
| Long-running HITL / workflows | **Temporal** | Recoverability |
| Tools + policy + audit | **governed-mcp-gateway** | Framework-agnostic |
| Model access | **Model gateway + catalog** | No provider hard-coding |
| Multi-agent | Only via **supervisor** (`bounded-agentic-orchestration`) | No free-form A2A |

---

## 3. Catalog + gateway operating model

```
Product team  →  versioned API / SDK  →  Model Gateway  →  Approved catalog
                      │                      │
                      │                      ├─ route: cost | latency | quality | balanced
                      │                      ├─ meter FinOps ($ / success)
                      │                      └─ policy + audit wrap
                      └─ never: from openai import ... in product services
```

| Catalog field | Example |
|---|---|
| `model_id` | `azure-gpt-4o-mini` |
| `capability` | chat · embedding · rerank |
| `version` | `2024-07` |
| `unit_cost` | USD / 1k tokens |
| `residency` | `eastus2` |
| `approved` | true / false |
| `eval_baseline` | link to last gate run |

**Promotion rule:** Candidate model stays in *shadow* until eval Δ on **successful business transactions** clears the bar — not until a vendor launches a new name.

---

## 4. One-page interview answer (optional)

> I use a decision matrix rather than the most fashionable model. For models I score task quality, latency, context, residency/privacy, tool/structured output, **cost per successful transaction**, eval performance, and portability. For frameworks I score workflow/state, checkpointing, tool authorization, HITL, tracing/eval, deployment maturity, and learning curve. An **approved catalog and model gateway** mean product teams take policy-routed capabilities—not a hard-coded provider. Small models for extraction/classification; larger models only when evaluations prove incremental business value.

---

## Related repos

| Repo | Role |
|---|---|
| [enterprise-ai-platform-planes](https://github.com/mizbamd/enterprise-ai-platform-planes) | Catalog + gateway + five planes |
| [bounded-agentic-orchestration](https://github.com/mizbamd/bounded-agentic-orchestration) | Framework eval matrix + mode selection |
| [scalable-enterprise-rag](https://github.com/mizbamd/scalable-enterprise-rag) | Eval metrics for RAG quality |
| [finops-platform-landing-zone](https://github.com/mizbamd/finops-platform-landing-zone) | Cost tags / budgets for AI spend |
