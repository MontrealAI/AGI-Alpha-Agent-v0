# SPDX-License-Identifier: Apache-2.0
"""Offline FusionPlans and signed, reviewed native evidence for Ascension jobs."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from pydantic import Field, model_validator

from .engine import Engine, verify_export
from .models import Coding, Mission, StrictModel
from .store import Journal, canonical
from .work import verify_result

PLAN_SCHEMA = "agialpha.ascension.fusion-plan.v1"
DELIVERY_SCHEMA = "agialpha.ascension.reviewed-delivery.v1"
MAX_PLAN_BYTES = 250_000
MAX_DELIVERY_BYTES = 2 * 1024**2


def keccak(data: bytes) -> bytes:
    """Use Ethereum Keccak, never the different NIST SHA3 function."""
    try:
        from eth_hash.auto import keccak as ethereum_keccak
    except ImportError as exc:
        raise ValueError("Ascension requires the chain extra or the hash-locked operator environment") from exc
    return bytes(ethereum_keccak(data))


def parse(data: bytes, limit: int) -> Any:
    """Reject oversized, duplicate-key and non-finite JSON before processing."""
    if len(data) > limit:
        raise ValueError("Ascension input exceeds its size limit")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON keys are not accepted")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ValueError("Non-finite JSON numbers are not accepted")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)


class JobSpec(StrictModel):
    """The exact bounded specification committed by AscensionJobMarket.Spec."""

    goal: str = Field(min_length=1, max_length=512)
    successMetric: str = Field(min_length=1, max_length=512)
    bounty: str = Field(pattern=r"^[1-9][0-9]{0,28}$")
    duration: int = Field(ge=1, le=90 * 86400)
    priceWeight: int = Field(ge=0, le=10000)

    @model_validator(mode="after")
    def bounds(self) -> JobSpec:
        """Match Solidity's UTF-8 byte and uint96 bounds without float conversion."""
        if any(len(text.encode("utf-8")) > 512 for text in (self.goal, self.successMetric)):
            raise ValueError("Goal and success metric must each fit 512 UTF-8 bytes")
        if not 100 <= int(self.bounty) < 2**96:
            raise ValueError("Bounty must be 100 through uint96 maximum in AGIALPHA base units")
        return self


def leaf(index: int, spec: JobSpec) -> str:
    """Double-hash the six ABI words exactly as the shipped Solidity contracts."""
    encoded = b"".join(
        [
            index.to_bytes(32, "big"),
            keccak(spec.goal.encode("utf-8")),
            keccak(spec.successMetric.encode("utf-8")),
            int(spec.bounty).to_bytes(32, "big"),
            spec.duration.to_bytes(32, "big"),
            spec.priceWeight.to_bytes(32, "big"),
        ]
    )
    return "0x" + keccak(keccak(encoded)).hex()


def compile_plan(source: Any) -> dict[str, Any]:
    """Compile ordered jobs with sorted pairs and unpaired-node promotion."""
    if not isinstance(source, list) or not 1 <= len(source) <= 128:
        raise ValueError("A FusionPlan requires 1–128 ordered job specifications")
    specs = [JobSpec.model_validate(item) for item in source]
    levels = [[leaf(index, spec) for index, spec in enumerate(specs)]]
    while len(levels[-1]) > 1:
        previous = levels[-1]
        next_level = []
        for i in range(0, len(previous), 2):
            if i + 1 < len(previous):
                pair = sorted([previous[i], previous[i + 1]])
                next_level.append("0x" + keccak(b"".join(bytes.fromhex(item[2:]) for item in pair)).hex())
            else:
                next_level.append(previous[i])
        levels.append(next_level)
    jobs = []
    for index, spec in enumerate(specs):
        proof = []
        position = index
        for level in levels[:-1]:
            if (position ^ 1) < len(level):
                proof.append(level[position ^ 1])
            position //= 2
        jobs.append({"index": index, "spec": spec.model_dump(), "leaf": levels[0][index], "proof": proof})
    return {
        "schema": PLAN_SCHEMA,
        "token": "AGIALPHA",
        "decimals": 18,
        "planRoot": levels[-1][0],
        "totalBounty": str(sum(int(spec.bounty) for spec in specs)),
        "jobs": jobs,
    }


def verify_plan(plan: Any) -> dict[str, Any]:
    """Rebuild every leaf, proof and total; reject unknown or altered metadata."""
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"), list):
        raise ValueError("Invalid FusionPlan structure")
    try:
        rebuilt = compile_plan([job["spec"] for job in plan["jobs"]])
    except (KeyError, TypeError) as exc:
        raise ValueError("Invalid FusionPlan job") from exc
    if canonical(plan) != canonical(rebuilt):
        raise ValueError("FusionPlan commitment, proofs or metadata do not match")
    return {
        "valid": True,
        "planRoot": rebuilt["planRoot"],
        "jobs": len(rebuilt["jobs"]),
        "totalBounty": rebuilt["totalBounty"],
    }


def delivery(journal: Journal, plan: Any, index: int, mission_id: str) -> bytes:
    """Sign the complete plan/result association only after explicit local review."""
    verify_plan(plan)
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(plan["jobs"]):
        raise ValueError("Job index is outside the FusionPlan")
    artifact = Engine(journal).export(mission_id)
    body = {"schema": DELIVERY_SCHEMA, "plan": plan, "jobIndex": index, "nativeExport": artifact}
    data = canonical(
        {
            "body": body,
            "publicKey": journal.public,
            "signature": base64.b64encode(journal.key.sign(hashlib.sha256(canonical(body)).digest())).decode("ascii"),
        }
    )
    verify_delivery(data, journal.public, plan["planRoot"], allow_code_replay=journal.config.allow_code_execution)
    return data


def verify_delivery(
    data: bytes, trusted_public_key: str, trusted_plan_root: str, *, allow_code_replay: bool = False
) -> dict[str, Any]:
    """Verify externally pinned identity/root, exact bytes and native arithmetic."""
    envelope = parse(data, MAX_DELIVERY_BYTES)
    if not isinstance(envelope, dict) or set(envelope) != {"body", "publicKey", "signature"}:
        raise ValueError("Invalid Ascension delivery envelope")
    if canonical(envelope) != data:
        raise ValueError("Delivery must retain its exact canonical bytes")
    if envelope["publicKey"] != trusted_public_key:
        raise ValueError("Delivery signer does not match the independently trusted key")
    body = envelope["body"]
    if not isinstance(body, dict) or set(body) != {"schema", "plan", "jobIndex", "nativeExport"}:
        raise ValueError("Invalid Ascension delivery body")
    if body["schema"] != DELIVERY_SCHEMA:
        raise ValueError("Unsupported Ascension delivery schema")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(trusted_public_key)).verify(
            base64.b64decode(envelope["signature"], validate=True), hashlib.sha256(canonical(body)).digest()
        )
    except InvalidSignature as exc:
        raise ValueError("Ascension delivery signature is invalid") from exc
    plan = body["plan"]
    verify_plan(plan)
    if plan["planRoot"] != trusted_plan_root:
        raise ValueError("Delivery plan does not match the independently trusted on-chain root")
    index = body["jobIndex"]
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(plan["jobs"]):
        raise ValueError("Job index is outside the FusionPlan")
    artifact = body["nativeExport"]
    verified = verify_export(artifact, trusted_public_key)
    document = artifact["receipt"]["body"]["document"]
    mission = Mission.model_validate(document["request"])
    if document["review"]["approved"] is not True or mission.goal != plan["jobs"][index]["spec"]["goal"]:
        raise ValueError("Approved native mission goal must exactly match the committed job")
    if isinstance(mission.work, Coding) and not allow_code_replay:
        raise ValueError("Code evidence requires explicit --replay-code permission and the isolated Docker runtime")
    verification = verify_result(mission, document["result"])
    return {
        "valid": True,
        "planRoot": trusted_plan_root,
        "jobIndex": index,
        "mission": verified["mission"],
        "publicKey": trusted_public_key,
        "resultHash": "0x" + keccak(data).hex(),
        "nativeVerification": verification,
        "reviewScope": "local operator; on-chain validators must assess the success metric and evidence separately",
    }
