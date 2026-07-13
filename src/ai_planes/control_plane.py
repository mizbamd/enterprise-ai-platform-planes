"""
Control plane — identity, policy, prompt/model governance, evaluation, tracing, audit, FinOps.

Spans: governed-mcp-gateway audit/policy, agentic-rag eval harness,
item-cost-ledger OpenTelemetry, finops-platform-landing-zone tags/budgets.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict
from typing import Any

from ai_planes.types import AuditEntry, Plane


class IdentityContext:
    def __init__(self, principal: str, roles: list[str] | None = None) -> None:
        self.principal = principal
        self.roles = roles or ["analyst"]


class PromptGovernance:
    """Approved system prompts / blocked patterns — model governance companion."""

    BLOCKED = ("ignore previous instructions", "exfiltrate", "disable safety")

    def validate(self, prompt: str) -> tuple[bool, str]:
        lower = prompt.lower()
        for pattern in self.BLOCKED:
            if pattern in lower:
                return False, f"blocked pattern: {pattern}"
        return True, "ok"


class EvaluationHarness:
    """Minimal retrieval eval — production: agentic-rag-engine/eval."""

    def precision_at_k(self, relevant: set[str], retrieved: list[str], k: int) -> float:
        top = retrieved[:k]
        if not top:
            return 0.0
        hits = sum(1 for d in top if d in relevant)
        return hits / len(top)

    def mrr(self, relevant: set[str], retrieved: list[str]) -> float:
        for i, doc_id in enumerate(retrieved, start=1):
            if doc_id in relevant:
                return 1.0 / i
        return 0.0


class TraceSpan:
    def __init__(self, name: str, correlation_id: str) -> None:
        self.name = name
        self.correlation_id = correlation_id
        self.started = time.time()
        self.ended: float | None = None
        self.attributes: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def end(self) -> dict[str, Any]:
        self.ended = time.time()
        return {
            "name": self.name,
            "correlation_id": self.correlation_id,
            "duration_ms": round((self.ended - self.started) * 1000, 2),
            "attributes": self.attributes,
        }


class HashChainedAudit:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._prev = "GENESIS"

    def append(
        self,
        plane: Plane,
        action: str,
        correlation_id: str,
        subject: str,
        decision: str,
        detail: dict[str, Any] | None = None,
    ) -> AuditEntry:
        payload = {
            "plane": plane.value,
            "action": action,
            "correlation_id": correlation_id,
            "subject": subject,
            "decision": decision,
            "detail": detail or {},
            "prev_hash": self._prev,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        entry = AuditEntry(
            plane=plane,
            action=action,
            correlation_id=correlation_id,
            subject=subject,
            decision=decision,
            detail=detail or {},
            prev_hash=self._prev,
            entry_hash=digest,
        )
        self._entries.append(entry)
        self._prev = digest
        return entry

    def verify(self) -> bool:
        prev = "GENESIS"
        for entry in self._entries:
            payload = {
                "plane": entry.plane.value,
                "action": entry.action,
                "correlation_id": entry.correlation_id,
                "subject": entry.subject,
                "decision": entry.decision,
                "detail": entry.detail,
                "prev_hash": prev,
            }
            digest = hashlib.sha256(
                json.dumps(payload, sort_keys=True, default=str).encode()
            ).hexdigest()
            if digest != entry.entry_hash or entry.prev_hash != prev:
                return False
            prev = entry.entry_hash
        return True

    def entries(self) -> list[dict[str, Any]]:
        return [asdict(e) for e in self._entries]


class FinOpsMeter:
    def __init__(self) -> None:
        self._spend: list[dict[str, Any]] = []

    def record(self, correlation_id: str, model_id: str, cost_usd: float, tokens: int) -> None:
        self._spend.append(
            {
                "correlation_id": correlation_id,
                "model_id": model_id,
                "cost_usd": cost_usd,
                "tokens": tokens,
                "cost_center_tag": "CC-AI-PLATFORM",
            }
        )

    def summary(self) -> dict[str, Any]:
        total = sum(s["cost_usd"] for s in self._spend)
        return {
            "calls": len(self._spend),
            "total_cost_usd": round(total, 6),
            "by_model": self._by_model(),
        }

    def _by_model(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for s in self._spend:
            out[s["model_id"]] = round(out.get(s["model_id"], 0.0) + s["cost_usd"], 6)
        return out


class ControlPlane:
    def __init__(self) -> None:
        self.prompts = PromptGovernance()
        self.eval = EvaluationHarness()
        self.audit = HashChainedAudit()
        self.finops = FinOpsMeter()
        self.traces: list[dict[str, Any]] = []

    def start_span(self, name: str, correlation_id: str) -> TraceSpan:
        return TraceSpan(name, correlation_id)

    def end_span(self, span: TraceSpan) -> None:
        self.traces.append(span.end())
