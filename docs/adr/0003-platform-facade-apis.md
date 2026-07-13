# ADR 0003: Versioned platform facade APIs

## Status
Accepted

## Context
"Use the right SDK" guidance fails when every team picks a different client library,
auth pattern, and retry policy.

## Decision
Expose a single **v1** HTTP facade (and matching Python facade class):

| API | Plane |
|---|---|
| `GET /v1/platform` | all — discovery |
| `GET /v1/models` | model |
| `POST /v1/chat` | model + control |
| `POST /v1/retrieve` | knowledge |
| `POST /v1/orchestrate` | orchestration |
| `GET /v1/data/*` | data |
| `GET /v1/control/*` | control |

Breaking changes require `/v2`.

## Consequences
- Product teams integrate once; platform evolves planes independently.
- OpenAPI becomes the contract review artifact for architecture boards.
