"""Enterprise AI Platform Planes — shared types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Plane(str, Enum):
    DATA = "data"
    MODEL = "model"
    KNOWLEDGE = "knowledge"
    ORCHESTRATION = "orchestration"
    CONTROL = "control"


class ModelCapability(str, Enum):
    CHAT = "chat"
    EMBEDDING = "embedding"
    RERANK = "rerank"


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    provider: str
    capability: ModelCapability
    version: str
    cost_per_1k_tokens_usd: float
    approved: bool = True
    max_context: int = 8192


@dataclass
class ChatRequest:
    messages: list[dict[str, str]]
    capability: ModelCapability = ModelCapability.CHAT
    route_preference: str = "balanced"  # cost | latency | quality | balanced
    correlation_id: str = ""


@dataclass
class ChatResponse:
    text: str
    model_id: str
    provider: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    correlation_id: str


@dataclass
class RetrieveRequest:
    query: str
    top_k: int = 5
    correlation_id: str = ""


@dataclass
class RetrievedChunk:
    doc_id: str
    text: str
    score: float
    source: str


@dataclass
class RetrieveResponse:
    chunks: list[RetrievedChunk]
    correlation_id: str


@dataclass
class OrchestrateRequest:
    goal: str
    role: str = "analyst"
    correlation_id: str = ""


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    decision: str  # allow | require_approval | deny
    outcome: str = ""


@dataclass
class OrchestrateResponse:
    answer: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    memory: list[str] = field(default_factory=list)
    approval_required: bool = False
    correlation_id: str = ""


@dataclass
class AuditEntry:
    plane: Plane
    action: str
    correlation_id: str
    subject: str
    decision: str
    detail: dict[str, Any] = field(default_factory=dict)
    prev_hash: str = ""
    entry_hash: str = ""
