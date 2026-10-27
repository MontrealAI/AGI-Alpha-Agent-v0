# SPDX-License-Identifier: Apache-2.0
"""Opt-in protected resources on the existing native API; no public-demo dispatch."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from .flywheel_access import AccessRequest
from .flywheel_capsules import Invocation, ProtectedLibrary
from .protocol import Digest, StrictModel, digest


class ChallengeRequest(StrictModel):
    name: str
    wallet: str
    resource: Digest
    action: str
    request_digest: Digest


class InvokeRequest(StrictModel):
    proof: AccessRequest
    invocation: Invocation


def install_routes(app: FastAPI, library: ProtectedLibrary | None) -> None:
    """Resources fail closed unless the operator installs every trusted dependency."""

    def configured() -> ProtectedLibrary:
        if library is None:
            raise HTTPException(503, "Protected service is not provisioned")
        return library

    @app.get("/api/flywheel/status")
    def status() -> dict[str, Any]:
        return {
            "public_explore": "simulation",
            "protected_service": "configured-requires-operating-qualification" if library else "unprovisioned",
            "qualified_live_operation": False,
            "qualification_basis": "deployment-specific live identity, model, acceptance, cost and recovery evidence required",
            "export_policy": "controlled-invocation-only",
            "wallet_actions": False,
            "customer_contact": False,
        }

    @app.post("/api/flywheel/challenge")
    def challenge(request: ChallengeRequest) -> dict[str, Any]:
        service = configured()
        # Unknown and nonadmitted resources do not receive signing challenges.
        if request.resource == service.catalog_resource():
            if request.action != "discover":
                raise HTTPException(403, "Catalog authorization permits discovery only")
        else:
            with service.journal.transaction() as cx:
                _, network = service._state(cx)
                service._eligible(network, request.resource)
                service._dependencies(network, network["entries"][request.resource])
        return service.access.challenge(
            request.name, request.wallet, request.resource, request.action, request.request_digest
        )

    @app.post("/api/flywheel/catalog")
    def catalog(proof: AccessRequest) -> dict[str, Any]:
        return configured().catalog(proof)

    @app.post("/api/flywheel/capsules/{ident}/manifest")
    def manifest(ident: str, proof: AccessRequest) -> dict[str, Any]:
        return configured().manifest(ident, proof)

    @app.post("/api/flywheel/capsules/{ident}/invoke")
    def invoke(ident: str, request: InvokeRequest) -> dict[str, Any]:
        return configured().invoke(ident, request.invocation, request.proof)

    @app.get("/api/flywheel/protocol")
    def protocol() -> dict[str, Any]:
        return {
            "schema": "protected-flywheel/v1",
            "execution_digest": library.execution_digest if library else None,
            "catalog_resource": library.catalog_resource() if library else None,
            "request_commitments": {"discover": digest("flywheel-discover", {"candidate_digest": "0" * 64})},
            "note": "Example digest is an encoding example, never an admitted resource. Invoke commits the complete typed Invocation using successor-omega/v1 domain flywheel-invocation. No plaintext capsule endpoint exists.",
        }
