"""Versioned HTTP facade — apps integrate with /v1/*, never provider SDKs."""

from __future__ import annotations

from typing import Any

from ai_planes.control_plane import IdentityContext
from ai_planes.platform import PlatformFacade

try:
    from fastapi import FastAPI, Header
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - fastapi optional for unit tests
    FastAPI = None  # type: ignore
    Header = None  # type: ignore
    BaseModel = object  # type: ignore
    Field = None  # type: ignore


facade = PlatformFacade()


if FastAPI is not None:

    class ChatBody(BaseModel):
        messages: list[dict[str, str]]
        route_preference: str = "balanced"
        correlation_id: str | None = None

    class RetrieveBody(BaseModel):
        query: str
        top_k: int = 5
        correlation_id: str | None = None

    class OrchestrateBody(BaseModel):
        goal: str
        correlation_id: str | None = None

    class AuthorizeBody(BaseModel):
        principal: str
        dataset: str
        action: str = "read"

    app = FastAPI(
        title="Enterprise AI Platform Planes",
        version="1.0.0",
        description=(
            "Five-plane enterprise AI architecture. Applications access capabilities "
            "through versioned APIs rather than integrating directly with model providers."
        ),
    )

    def _identity(x_principal: str | None, x_roles: str | None) -> IdentityContext:
        roles = [r.strip() for r in (x_roles or "analyst").split(",") if r.strip()]
        return IdentityContext(principal=x_principal or "anonymous", roles=roles)

    @app.get("/v1/platform")
    def describe_platform() -> dict[str, Any]:
        return facade.describe()

    @app.get("/v1/models")
    def list_models() -> dict[str, Any]:
        return {"models": facade.models.catalog_payload()}

    @app.post("/v1/chat")
    def chat(
        body: ChatBody,
        x_principal: str | None = Header(default="demo-user"),
        x_roles: str | None = Header(default="analyst"),
    ) -> dict[str, Any]:
        return facade.chat(
            body.messages,
            _identity(x_principal, x_roles),
            body.route_preference,
            body.correlation_id,
        )

    @app.post("/v1/retrieve")
    def retrieve(
        body: RetrieveBody,
        x_principal: str | None = Header(default="demo-user"),
        x_roles: str | None = Header(default="analyst"),
    ) -> dict[str, Any]:
        return facade.retrieve(body.query, _identity(x_principal, x_roles), body.top_k, body.correlation_id)

    @app.post("/v1/orchestrate")
    def orchestrate(
        body: OrchestrateBody,
        x_principal: str | None = Header(default="demo-user"),
        x_roles: str | None = Header(default="analyst"),
    ) -> dict[str, Any]:
        return facade.orchestrate(body.goal, _identity(x_principal, x_roles), body.correlation_id)

    @app.get("/v1/data/datasets")
    def datasets() -> dict[str, Any]:
        return {
            "datasets": [
                {
                    "name": d.name,
                    "layer": d.layer,
                    "owner_domain": d.owner_domain,
                    "classification": d.classification,
                }
                for d in facade.data.list_datasets()
            ]
        }

    @app.get("/v1/data/lineage")
    def lineage() -> dict[str, Any]:
        return {
            "edges": [
                {"upstream": e.upstream, "downstream": e.downstream, "transform": e.transform}
                for e in facade.data.lineage()
            ]
        }

    @app.post("/v1/data/authorize")
    def authorize(body: AuthorizeBody) -> dict[str, Any]:
        return facade.authorize_dataset(body.principal, body.dataset, body.action)

    @app.get("/v1/control/audit")
    def audit() -> dict[str, Any]:
        return {"entries": facade.control.audit.entries(), "valid": facade.control.audit.verify()}

    @app.get("/v1/control/finops")
    def finops() -> dict[str, Any]:
        return facade.control.finops.summary()

    @app.get("/v1/control/traces")
    def traces() -> dict[str, Any]:
        return {"spans": facade.control.traces}

else:
    app = None  # type: ignore
