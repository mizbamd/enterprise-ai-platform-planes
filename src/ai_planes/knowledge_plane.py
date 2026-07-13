"""
Knowledge plane — ingestion, chunking, vector + keyword indexes, retrieval, reranking.

Production implementation: agentic-rag-engine (hybrid RRF + rerank + grounded answers).
Entity resolution patterns: supplier-golden-record-platform.
This adapter is the contract surface for the platform facade.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from ai_planes.model_plane import ModelGateway
from ai_planes.types import RetrievedChunk, RetrieveRequest, RetrieveResponse


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class KnowledgePlane:
    def __init__(self, gateway: ModelGateway | None = None) -> None:
        self._gateway = gateway or ModelGateway()
        self._docs: list[tuple[str, str, str]] = []  # doc_id, text, source
        self._seed_corpus()

    def _seed_corpus(self) -> None:
        samples = [
            ("cost-ledger-1", "Item cost ledger uses CQRS and Temporal for effective-dated cost changes.", "item-cost-ledger"),
            ("supplier-1", "Supplier golden record merges multi-source MDM via Kafka CDC.", "supplier-golden-record"),
            ("rag-1", "Hybrid retrieval fuses vector ANN and BM25 with reciprocal rank fusion.", "agentic-rag-engine"),
            ("mcp-1", "Governed MCP requires human approval for write tools and hash-chained audit.", "governed-mcp-gateway"),
            ("finops-1", "FinOps landing zone enforces cost-center tags, budgets, and Azure Policy.", "finops-platform-landing-zone"),
            ("lakehouse-1", "Medallion lakehouse builds bronze silver gold Delta tables from Kafka events.", "streaming-lakehouse"),
        ]
        for doc_id, text, source in samples:
            self._docs.append((doc_id, text, source))

    def ingest(self, doc_id: str, text: str, source: str = "upload") -> None:
        chunks = self.chunk(text)
        for i, chunk in enumerate(chunks):
            self._docs.append((f"{doc_id}:{i}", chunk, source))

    def chunk(self, text: str, size: int = 120) -> list[str]:
        words = text.split()
        if not words:
            return []
        return [" ".join(words[i : i + size]) for i in range(0, len(words), size)]

    def retrieve(self, request: RetrieveRequest) -> RetrieveResponse:
        query_tokens = _tokenize(request.query)
        query_vecs, _ = self._gateway.embed([request.query], preference="latency")
        qv = query_vecs[0]

        scored: list[RetrievedChunk] = []
        for doc_id, text, source in self._docs:
            # keyword (BM25-lite)
            doc_tokens = _tokenize(text)
            overlap = sum((Counter(query_tokens) & Counter(doc_tokens)).values())
            bm25 = overlap / (1.0 + math.log(1 + len(doc_tokens)))

            # dense
            dv, _ = self._gateway.embed([text], preference="latency")
            dense = sum(a * b for a, b in zip(qv, dv[0]))

            # RRF-style fuse on ranks will be approximated by weighted sum for local demo
            score = 0.55 * dense + 0.45 * bm25
            scored.append(RetrievedChunk(doc_id, text, score, source))

        scored.sort(key=lambda c: c.score, reverse=True)
        fused = scored[: max(request.top_k * 2, request.top_k)]
        reranked = self._rerank(request.query, fused)[: request.top_k]
        return RetrieveResponse(chunks=reranked, correlation_id=request.correlation_id)

    def _rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        q = set(_tokenize(query))
        def key(c: RetrievedChunk) -> float:
            overlap = len(q & set(_tokenize(c.text)))
            return overlap + c.score
        return sorted(chunks, key=key, reverse=True)

    def entity_resolve(self, alias: str) -> dict:
        """Stub — production: supplier-golden-record-platform."""
        table = {
            "acme": {"entity_id": "SUP-1001", "canonical_name": "ACME Wholesale Inc"},
            "acme wholesale": {"entity_id": "SUP-1001", "canonical_name": "ACME Wholesale Inc"},
        }
        key = alias.strip().lower()
        return table.get(key, {"entity_id": None, "canonical_name": alias, "resolved": False})
