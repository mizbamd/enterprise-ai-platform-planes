"""
Model plane — approved catalog, gateway, routing, versioning, embeddings, endpoints.

Apps never import provider SDKs. They call ModelGateway via the platform facade.
Swap Azure OpenAI / local extractive / etc. without rewriting product code.
"""

from __future__ import annotations

import hashlib
import math
from typing import Iterable

from ai_planes.types import (
    ChatRequest,
    ChatResponse,
    ModelCapability,
    ModelSpec,
)


APPROVED_CATALOG: list[ModelSpec] = [
    ModelSpec(
        model_id="azure-gpt-4o-mini",
        provider="azure-openai",
        capability=ModelCapability.CHAT,
        version="2024-07",
        cost_per_1k_tokens_usd=0.00015,
        max_context=128000,
    ),
    ModelSpec(
        model_id="platform-extractive-v1",
        provider="platform-local",
        capability=ModelCapability.CHAT,
        version="1.0.0",
        cost_per_1k_tokens_usd=0.0,
        max_context=8192,
    ),
    ModelSpec(
        model_id="azure-text-embedding-3-small",
        provider="azure-openai",
        capability=ModelCapability.EMBEDDING,
        version="1",
        cost_per_1k_tokens_usd=0.00002,
        max_context=8191,
    ),
    ModelSpec(
        model_id="platform-hash-embed-v1",
        provider="platform-local",
        capability=ModelCapability.EMBEDDING,
        version="1.0.0",
        cost_per_1k_tokens_usd=0.0,
        max_context=512,
    ),
    ModelSpec(
        model_id="platform-rerank-v1",
        provider="platform-local",
        capability=ModelCapability.RERANK,
        version="1.0.0",
        cost_per_1k_tokens_usd=0.0,
    ),
]


class ModelCatalog:
    def __init__(self, specs: Iterable[ModelSpec] | None = None) -> None:
        self._specs = {s.model_id: s for s in (specs or APPROVED_CATALOG) if s.approved}

    def list(self, capability: ModelCapability | None = None) -> list[ModelSpec]:
        specs = list(self._specs.values())
        if capability:
            specs = [s for s in specs if s.capability == capability]
        return specs

    def get(self, model_id: str) -> ModelSpec:
        if model_id not in self._specs:
            raise KeyError(f"model not in approved catalog: {model_id}")
        return self._specs[model_id]


class ModelRouter:
    """Route by cost / latency / quality without exposing providers to callers."""

    def __init__(self, catalog: ModelCatalog) -> None:
        self._catalog = catalog

    def choose(
        self,
        capability: ModelCapability,
        preference: str = "balanced",
    ) -> ModelSpec:
        candidates = self._catalog.list(capability)
        if not candidates:
            raise ValueError(f"no approved models for {capability}")

        local = [c for c in candidates if c.provider == "platform-local"]
        cloud = [c for c in candidates if c.provider != "platform-local"]

        if preference == "cost":
            return min(candidates, key=lambda s: s.cost_per_1k_tokens_usd)
        if preference == "latency" and local:
            return local[0]
        if preference == "quality" and cloud:
            return max(cloud, key=lambda s: s.max_context)
        # balanced: prefer local for embeddings/rerank, cloud for chat when available
        if capability == ModelCapability.CHAT and cloud:
            return cloud[0]
        return local[0] if local else candidates[0]


class EmbeddingEndpoint:
    def __init__(self, model: ModelSpec) -> None:
        self.model = model

    def embed(self, texts: list[str], dim: int = 64) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(f"{self.model.model_id}:{text}".encode()).digest()
            raw = [((digest[i % len(digest)] / 255.0) * 2 - 1) for i in range(dim)]
            norm = math.sqrt(sum(x * x for x in raw)) or 1.0
            vectors.append([x / norm for x in raw])
        return vectors


class ChatEndpoint:
    def __init__(self, model: ModelSpec) -> None:
        self.model = model

    def complete(self, messages: list[dict[str, str]]) -> tuple[str, int, int]:
        user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        # Deterministic local completion — production swaps to Azure OpenAI behind same interface
        text = (
            f"[{self.model.model_id}] "
            f"Grounded platform response for: {user[:200]}"
        )
        tokens_in = max(1, sum(len(m.get("content", "").split()) for m in messages))
        tokens_out = max(1, len(text.split()))
        return text, tokens_in, tokens_out


class ModelGateway:
    """Single entry for chat / embed / rerank — versioned, routed, metered."""

    def __init__(self, catalog: ModelCatalog | None = None) -> None:
        self.catalog = catalog or ModelCatalog()
        self.router = ModelRouter(self.catalog)

    def chat(self, request: ChatRequest) -> ChatResponse:
        model = self.router.choose(request.capability, request.route_preference)
        text, tin, tout = ChatEndpoint(model).complete(request.messages)
        cost = model.cost_per_1k_tokens_usd * (tin + tout) / 1000.0
        return ChatResponse(
            text=text,
            model_id=model.model_id,
            provider=model.provider,
            tokens_in=tin,
            tokens_out=tout,
            cost_usd=cost,
            correlation_id=request.correlation_id,
        )

    def embed(self, texts: list[str], preference: str = "latency") -> tuple[list[list[float]], ModelSpec]:
        model = self.router.choose(ModelCapability.EMBEDDING, preference)
        return EmbeddingEndpoint(model).embed(texts), model

    def catalog_payload(self) -> list[dict]:
        return [
            {
                "model_id": s.model_id,
                "provider": s.provider,
                "capability": s.capability.value,
                "version": s.version,
                "cost_per_1k_tokens_usd": s.cost_per_1k_tokens_usd,
            }
            for s in self.catalog.list()
        ]
