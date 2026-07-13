# ADR 0001: Five-plane separation of concerns

## Status
Accepted

## Context
Enterprise AI programs collapse when apps wire directly to model providers, vector DBs,
and agent runtimes. Product delivery then couples to every model/version change.

## Decision
Organize the platform into **five planes**, accessed only through a versioned facade:

1. **Data** — lakehouse, APIs, Kafka, metadata, lineage, access
2. **Model** — catalog, gateway, routing, versioning, embeddings, endpoints
3. **Knowledge** — ingest, chunk, indexes, entity resolution, retrieve, rerank
4. **Orchestration** — agents, tools, memory, HITL, deterministic services
5. **Control** — identity, policy, prompt/model gov, eval, tracing, audit, FinOps

Product teams own use cases and outcomes. The platform owns reusable governed capabilities.

## Consequences
- Model/provider swaps happen in the model plane without rewriting applications.
- Portfolio repos map cleanly to planes (`streaming-lakehouse`, `agentic-rag`, `governed-mcp`, `finops-landing-zone`).
- Requires discipline: no provider SDK imports in product services.
