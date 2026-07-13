# ADR 0004: Control plane wraps every request

## Status
Accepted

## Context
Governance bolted on after agents ship becomes theater. Audit gaps and unmetered
model spend are the two failure modes that kill enterprise AI programs.

## Decision
Every facade call:

1. Validates prompts (blocked patterns)
2. Starts a correlation-scoped span
3. Appends a hash-chained audit entry
4. Records FinOps cost when models run
5. Propagates approval decisions from orchestration (HITL)

## Consequences
- Aligns with `governed-mcp-gateway` audit and `finops-platform-landing-zone` tags.
- Adds per-request overhead that is intentional and measurable.
