"""
Orchestration plane — workflow state, agents, tool registry, memory, HITL, deterministic services.

Production: governed-mcp-gateway (policy + HITL + audit), Temporal workflows in item-cost-ledger,
LangGraph agent in agentic-rag-engine, pricing-orchestration SAGA.
"""

from __future__ import annotations

from ai_planes.knowledge_plane import KnowledgePlane
from ai_planes.model_plane import ModelGateway
from ai_planes.types import (
    ChatRequest,
    ModelCapability,
    OrchestrateRequest,
    OrchestrateResponse,
    RetrieveRequest,
    ToolCall,
)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools = {
            "lookup_item_cost": {"sensitivity": "read", "backend": "item-cost-ledger-platform"},
            "lookup_supplier": {"sensitivity": "read", "backend": "supplier-golden-record-platform"},
            "propose_price_change": {"sensitivity": "write", "backend": "pricing-orchestration"},
            "search_knowledge": {"sensitivity": "read", "backend": "agentic-rag-engine"},
        }

    def list_tools(self) -> dict:
        return dict(self._tools)

    def classify(self, name: str) -> str:
        meta = self._tools.get(name)
        if meta is None:
            return "unknown"
        return meta["sensitivity"]


class OrchestrationPlane:
    def __init__(
        self,
        gateway: ModelGateway | None = None,
        knowledge: KnowledgePlane | None = None,
        tools: ToolRegistry | None = None,
    ) -> None:
        self.gateway = gateway or ModelGateway()
        self.knowledge = knowledge or KnowledgePlane(self.gateway)
        self.tools = tools or ToolRegistry()
        self._memory: list[str] = []

    def run(self, request: OrchestrateRequest) -> OrchestrateResponse:
        goal = request.goal.strip()
        self._memory.append(f"goal:{goal}")

        # deterministic service path for known intents
        if goal.lower().startswith("resolve supplier:"):
            alias = goal.split(":", 1)[1].strip()
            entity = self.knowledge.entity_resolve(alias)
            return OrchestrateResponse(
                answer=f"Resolved supplier → {entity}",
                tool_calls=[
                    ToolCall("lookup_supplier", {"alias": alias}, "allow", "resolved")
                ],
                memory=list(self._memory),
                correlation_id=request.correlation_id,
            )

        # agent path: retrieve → chat via model gateway → optional write tool gate
        retrieved = self.knowledge.retrieve(
            RetrieveRequest(query=goal, top_k=3, correlation_id=request.correlation_id)
        )
        context = "\n".join(f"- {c.text}" for c in retrieved.chunks)
        chat = self.gateway.chat(
            ChatRequest(
                messages=[
                    {"role": "system", "content": "Answer using only the provided context."},
                    {"role": "user", "content": f"Context:\n{context}\n\nGoal: {goal}"},
                ],
                capability=ModelCapability.CHAT,
                route_preference="balanced",
                correlation_id=request.correlation_id,
            )
        )

        tool_calls = [
            ToolCall("search_knowledge", {"query": goal}, "allow", f"hits={len(retrieved.chunks)}")
        ]

        approval_required = False
        if "propose price" in goal.lower() or "change price" in goal.lower():
            decision = "require_approval" if request.role != "pricing-admin" else "allow"
            approval_required = decision == "require_approval"
            tool_calls.append(
                ToolCall(
                    "propose_price_change",
                    {"goal": goal},
                    decision,
                    "pending" if approval_required else "submitted",
                )
            )

        return OrchestrateResponse(
            answer=chat.text,
            tool_calls=tool_calls,
            memory=list(self._memory),
            approval_required=approval_required,
            correlation_id=request.correlation_id,
        )
