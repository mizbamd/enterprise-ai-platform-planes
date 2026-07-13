# ADR 0002: Model gateway — never call providers from apps

## Status
Accepted

## Context
Direct Azure OpenAI / OpenAI / local LLM client usage in every microservice makes
governance, FinOps metering, and version rollbacks impossible at enterprise scale.

## Decision
Applications call `ModelGateway` (and `/v1/chat`, `/v1/models`) only.

- **Approved catalog** lists models, capabilities, versions, unit costs.
- **Router** selects by `cost | latency | quality | balanced`.
- **Endpoints** are pluggable behind the same interface (`platform-local` for tests; Azure OpenAI in prod).

## Consequences
- Prompt injection checks and cost metering sit in the control plane once.
- Eval and canary of new models are catalog changes, not application redeploys.
