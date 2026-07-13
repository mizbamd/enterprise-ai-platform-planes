"""
Data plane — governed lakehouse, operational APIs, Kafka events, metadata, lineage, access.

In production this plane is implemented by streaming-lakehouse-platform,
supplier-golden-record-platform, and item-cost-ledger-platform.
This module is the platform contract + local stub so apps never couple to lakehouse internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DatasetRef:
    name: str
    layer: str  # bronze | silver | gold
    owner_domain: str
    classification: str  # public | internal | confidential | regulated


@dataclass
class LineageEdge:
    upstream: str
    downstream: str
    transform: str


@dataclass
class AccessDecision:
    allowed: bool
    reason: str
    policy: str


class DataPlane:
    """Versioned data capabilities exposed to the platform facade."""

    def __init__(self) -> None:
        self._datasets: dict[str, DatasetRef] = {
            "cost.current": DatasetRef(
                "cost.current", "gold", "merchandising", "confidential"
            ),
            "supplier.golden": DatasetRef(
                "supplier.golden", "gold", "merchandising", "confidential"
            ),
            "features.ai": DatasetRef(
                "features.ai", "gold", "data-ai", "internal"
            ),
            "events.cost.facts": DatasetRef(
                "events.cost.facts", "bronze", "merchandising", "internal"
            ),
        }
        self._lineage: list[LineageEdge] = [
            LineageEdge("events.cost.facts", "cost.current", "cqrs-projection"),
            LineageEdge("supplier.golden", "features.ai", "feature-join"),
            LineageEdge("features.ai", "knowledge.index", "chunk-embed"),
        ]
        self._kafka_topics = [
            "cost.facts",
            "cost.events",
            "supplier.cdc",
            "negotiation.events",
        ]

    def list_datasets(self) -> list[DatasetRef]:
        return list(self._datasets.values())

    def lineage(self) -> list[LineageEdge]:
        return list(self._lineage)

    def kafka_topics(self) -> list[str]:
        return list(self._kafka_topics)

    def authorize(self, principal: str, dataset: str, action: str = "read") -> AccessDecision:
        ref = self._datasets.get(dataset)
        if ref is None:
            return AccessDecision(False, f"unknown dataset {dataset}", "deny-unknown")
        if ref.classification == "regulated" and principal not in {"compliance", "platform-admin"}:
            return AccessDecision(False, "regulated data requires elevated role", "abac-regulated")
        if action == "write" and principal not in {"platform-admin", "pipeline"}:
            return AccessDecision(False, "writes restricted to pipeline identities", "least-privilege")
        return AccessDecision(True, "ok", "abac-default")

    def operational_api_catalog(self) -> dict[str, Any]:
        """Portfolio wiring — apps call platform SDKs/APIs, not lakehouse jobs."""
        return {
            "GET /v1/data/datasets": "Catalog of governed datasets",
            "GET /v1/data/lineage": "Upstream/downstream transforms",
            "POST /v1/data/authorize": "Access policy check",
            "implements": [
                "https://github.com/mizbamd/streaming-lakehouse-platform",
                "https://github.com/mizbamd/supplier-golden-record-platform",
                "https://github.com/mizbamd/item-cost-ledger-platform",
            ],
        }
