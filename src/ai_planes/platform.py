"""
Platform facade — versioned capabilities. Product teams integrate here, not with providers.
"""

from __future__ import annotations

import uuid
from typing import Any

from ai_planes.control_plane import ControlPlane, IdentityContext
from ai_planes.data_plane import DataPlane
from ai_planes.knowledge_plane import KnowledgePlane
from ai_planes.model_plane import ModelGateway
from ai_planes.orchestration_plane import OrchestrationPlane
from ai_planes.types import (
    ChatRequest,
    ModelCapability,
    OrchestrateRequest,
    Plane,
    RetrieveRequest,
)


class PlatformFacade:
    """
    Separation of concerns:
    - Product teams own use cases and outcomes.
    - Platform supplies reusable, governed capabilities across five planes.
    Model or framework changes stay behind this facade.
    """

    API_VERSION = "v1"

    def __init__(self) -> None:
        self.data = DataPlane()
        self.models = ModelGateway()
        self.knowledge = KnowledgePlane(self.models)
        self.orchestration = OrchestrationPlane(self.models, self.knowledge)
        self.control = ControlPlane()

    def _cid(self, correlation_id: str | None) -> str:
        return correlation_id or str(uuid.uuid4())

    def describe(self) -> dict[str, Any]:
        return {
            "api_version": self.API_VERSION,
            "principle": (
                "Product teams own use cases and outcomes; "
                "the platform supplies reusable, governed capabilities."
            ),
            "planes": {
                Plane.DATA.value: self.data.operational_api_catalog(),
                Plane.MODEL.value: {"catalog": self.models.catalog_payload()},
                Plane.KNOWLEDGE.value: {
                    "implements": "https://github.com/mizbamd/agentic-rag-engine"
                },
                Plane.ORCHESTRATION.value: {
                    "tools": self.orchestration.tools.list_tools(),
                    "implements": "https://github.com/mizbamd/governed-mcp-gateway",
                },
                Plane.CONTROL.value: {
                    "audit": "hash-chained",
                    "finops": "CC-AI-PLATFORM",
                    "implements": [
                        "https://github.com/mizbamd/finops-platform-landing-zone",
                        "https://github.com/mizbamd/governed-mcp-gateway",
                    ],
                },
            },
        }

    def chat(
        self,
        messages: list[dict[str, str]],
        identity: IdentityContext,
        route_preference: str = "balanced",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        cid = self._cid(correlation_id)
        span = self.control.start_span("model.chat", cid)
        ok, reason = self.control.prompts.validate(
            " ".join(m.get("content", "") for m in messages)
        )
        if not ok:
            self.control.audit.append(
                Plane.CONTROL, "prompt.validate", cid, identity.principal, "deny", {"reason": reason}
            )
            span.set("decision", "deny")
            self.control.end_span(span)
            return {"error": reason, "correlation_id": cid}

        response = self.models.chat(
            ChatRequest(
                messages=messages,
                capability=ModelCapability.CHAT,
                route_preference=route_preference,
                correlation_id=cid,
            )
        )
        self.control.finops.record(
            cid, response.model_id, response.cost_usd, response.tokens_in + response.tokens_out
        )
        self.control.audit.append(
            Plane.MODEL,
            "chat",
            cid,
            identity.principal,
            "allow",
            {"model_id": response.model_id, "provider": response.provider},
        )
        span.set("model_id", response.model_id)
        self.control.end_span(span)
        return {
            "text": response.text,
            "model_id": response.model_id,
            "provider": response.provider,
            "tokens_in": response.tokens_in,
            "tokens_out": response.tokens_out,
            "cost_usd": response.cost_usd,
            "correlation_id": cid,
        }

    def retrieve(
        self,
        query: str,
        identity: IdentityContext,
        top_k: int = 5,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        cid = self._cid(correlation_id)
        span = self.control.start_span("knowledge.retrieve", cid)
        result = self.knowledge.retrieve(
            RetrieveRequest(query=query, top_k=top_k, correlation_id=cid)
        )
        self.control.audit.append(
            Plane.KNOWLEDGE,
            "retrieve",
            cid,
            identity.principal,
            "allow",
            {"hits": len(result.chunks)},
        )
        span.set("hits", len(result.chunks))
        self.control.end_span(span)
        return {
            "chunks": [
                {"doc_id": c.doc_id, "text": c.text, "score": c.score, "source": c.source}
                for c in result.chunks
            ],
            "correlation_id": cid,
        }

    def orchestrate(
        self,
        goal: str,
        identity: IdentityContext,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        cid = self._cid(correlation_id)
        span = self.control.start_span("orchestration.run", cid)
        role = identity.roles[0] if identity.roles else "analyst"
        result = self.orchestration.run(
            OrchestrateRequest(goal=goal, role=role, correlation_id=cid)
        )
        decision = "require_approval" if result.approval_required else "allow"
        self.control.audit.append(
            Plane.ORCHESTRATION,
            "run",
            cid,
            identity.principal,
            decision,
            {"tools": [t.name for t in result.tool_calls]},
        )
        span.set("approval_required", result.approval_required)
        self.control.end_span(span)
        return {
            "answer": result.answer,
            "tool_calls": [
                {
                    "name": t.name,
                    "arguments": t.arguments,
                    "decision": t.decision,
                    "outcome": t.outcome,
                }
                for t in result.tool_calls
            ],
            "memory": result.memory,
            "approval_required": result.approval_required,
            "correlation_id": cid,
        }

    def authorize_dataset(
        self, principal: str, dataset: str, action: str = "read"
    ) -> dict[str, Any]:
        decision = self.data.authorize(principal, dataset, action)
        self.control.audit.append(
            Plane.DATA,
            "authorize",
            self._cid(None),
            principal,
            "allow" if decision.allowed else "deny",
            {"dataset": dataset, "policy": decision.policy},
        )
        return {
            "allowed": decision.allowed,
            "reason": decision.reason,
            "policy": decision.policy,
        }
