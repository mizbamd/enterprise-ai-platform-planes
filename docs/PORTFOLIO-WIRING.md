# Portfolio wiring — planes → existing repos

| Plane | This repo (contract) | Production implementation |
|---|---|---|
| **1 · Data** | `DataPlane` datasets, lineage, authorize, Kafka topic list | [streaming-lakehouse-platform](https://github.com/mizbamd/streaming-lakehouse-platform) · [supplier-golden-record-platform](https://github.com/mizbamd/supplier-golden-record-platform) · [item-cost-ledger-platform](https://github.com/mizbamd/item-cost-ledger-platform) · [finops-platform-landing-zone](https://github.com/mizbamd/finops-platform-landing-zone) Event Hubs |
| **2 · Model** | `ModelCatalog` · `ModelGateway` · router · embed/chat endpoints | Azure OpenAI / platform-local adapters (new surface — filled here) |
| **3 · Knowledge** | ingest · chunk · hybrid retrieve · rerank · entity resolve stub | [agentic-rag-engine](https://github.com/mizbamd/agentic-rag-engine) · entity: [supplier-golden-record-platform](https://github.com/mizbamd/supplier-golden-record-platform) |
| **4 · Orchestration** | tool registry · agent run · HITL for writes · memory | [governed-mcp-gateway](https://github.com/mizbamd/governed-mcp-gateway) · Temporal in ledger · LangGraph in RAG · [pricing-orchestration](https://github.com/mizbamd/pricing-orchestration) |
| **5 · Control** | prompt gov · hash audit · eval · spans · FinOps meter | MCP audit/redaction · RAG eval · ledger OTel · [finops-platform-landing-zone](https://github.com/mizbamd/finops-platform-landing-zone) |

## Facade endpoints vs planes

```
GET  /v1/platform          → discovery of all five
GET  /v1/models            → Model
POST /v1/chat              → Model + Control
POST /v1/retrieve          → Knowledge (+ Model embeddings)
POST /v1/orchestrate       → Orchestration (+ Knowledge + Model + Control)
GET  /v1/data/datasets     → Data
GET  /v1/data/lineage      → Data
POST /v1/data/authorize    → Data + Control
GET  /v1/control/audit     → Control
GET  /v1/control/finops    → Control
GET  /v1/control/traces    → Control
```
