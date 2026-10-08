# SPDX-License-Identifier: Apache-2.0
"""Exact Ascension settlement adapter; richer work terms stay off chain.

The reader is deliberately read-only. Its transport and code-hash trust anchors
must be supplied by the operator; neither receipts nor a claimed chain ID select
trust roots. Settlement acceptance never issues proof, memory admission or grants.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import Field, model_validator

from .. import ascension as legacy
from ..models import StrictModel
from ..store import Journal
from .protocol import ExecutionAuthorization, JobContract, canonical, digest

TOKEN = "0xa61a3b3a130a9c20768eebf97e21515a6046a1fa"
TOKEN_DECIMALS = 18
PROTOCOL = "agialpha.ascension.v1"
AGENT_NAMESPACE = "*.alpha.agent.agi.eth"
VALIDATOR_NAMESPACE = "*.alpha.club.agi.eth"
ZERO_ADDRESS = "0x" + "00" * 20
ZERO_HASH = "0x" + "00" * 32
MAX_ARTIFACT_BYTES = 2 * 1024**2
RPC = Callable[[str, list[Any]], Any]


def uint(value: Any, bits: int, name: str, *, positive: bool = False) -> int:
    """Validate integers without accepting booleans, floats or lossy coercion."""
    if (
        isinstance(value, str)
        and len(value) <= 78
        and value.isascii()
        and value.isdecimal()
        and (value == "0" or not value.startswith("0"))
    ):
        number = int(value)
    elif type(value) is int:
        number = value
    else:
        raise ValueError(f"{name} requires a canonical unsigned integer")
    if not int(positive) <= number < 2**bits:
        raise ValueError(f"{name} is outside uint{bits}")
    return number


def address(value: Any) -> str:
    """Normalize a nonzero Ethereum address only after strict syntax checks."""
    if not isinstance(value, str) or len(value) != 42 or not value.startswith("0x"):
        raise ValueError("Invalid nonzero Ethereum address")
    try:
        raw = bytes.fromhex(value[2:])
    except ValueError as exc:
        raise ValueError("Invalid nonzero Ethereum address") from exc
    if len(raw) != 20 or raw == bytes(20):
        raise ValueError("Invalid nonzero Ethereum address")
    return value.lower()


def hash32(value: Any) -> str:
    """Validate a bytes32 commitment, preserving Ethereum's hex convention."""
    if not isinstance(value, str) or len(value) != 66 or not value.startswith("0x"):
        raise ValueError("Invalid bytes32 commitment")
    try:
        raw = bytes.fromhex(value[2:])
    except ValueError as exc:
        raise ValueError("Invalid bytes32 commitment") from exc
    if len(raw) != 32:
        raise ValueError("Invalid bytes32 commitment")
    return value.lower()


def indexed_leaf(index: int, spec: legacy.JobSpec | dict[str, Any]) -> str:
    """Compute the actual uint32 plan-index leaf; never substitute hashSpec(0)."""
    if type(index) is not int:
        raise ValueError("Plan index must be an integer")
    uint(index, 32, "plan index")
    value = legacy.JobSpec.model_validate(spec.model_dump() if isinstance(spec, legacy.JobSpec) else spec)
    return legacy.leaf(index, value)


def market_spec_hash(spec: legacy.JobSpec | dict[str, Any]) -> str:
    """Compute only the zero-index commitment stored by the existing market."""
    return indexed_leaf(0, spec)


class MarketContext(StrictModel):
    """Operator-pinned identities, never asserted by an imported settlement."""

    schema_version: Literal[1] = 1
    chain_id: str
    market: str
    market_code_hash: str
    token_code_hash: str
    protocol: Literal["agialpha.ascension.v1"] = "agialpha.ascension.v1"
    scope: Literal["disposable-local-fixture", "operator-configured-chain"]
    confirmations: int = Field(ge=1, le=1024)
    mark: str | None = None
    mark_code_hash: str | None = None
    seed: str | None = None
    seed_code_hash: str | None = None
    seed_id: str | None = None

    @model_validator(mode="after")
    def validate_context(self) -> MarketContext:
        """Separate explicit standalone jobs from complete MARK/seed bindings."""
        uint(self.chain_id, 256, "chain ID", positive=True)
        address(self.market)
        hash32(self.market_code_hash)
        hash32(self.token_code_hash)
        values = (self.mark, self.mark_code_hash, self.seed, self.seed_code_hash, self.seed_id)
        if any(value is not None for value in values):
            if not all(value is not None for value in values):
                raise ValueError("MARK, seed and their pinned code hashes must all be supplied")
            address(self.mark)
            address(self.seed)
            hash32(self.mark_code_hash)
            hash32(self.seed_code_hash)
            uint(self.seed_id, 256, "seed ID", positive=True)
        return self


def _words(value: Any, count: int) -> list[bytes]:
    if not isinstance(value, str) or not value.startswith("0x") or len(value) != 2 + 64 * count:
        raise ValueError("Malformed ABI response")
    try:
        data = bytes.fromhex(value[2:])
    except ValueError as exc:
        raise ValueError("Malformed ABI response") from exc
    words = []
    for start in range(0, len(data), 32):
        end = start + 32
        words.append(data[start:end])
    return words


def _quantity(value: Any) -> int:
    if not isinstance(value, str) or not value.startswith("0x") or len(value) > 66:
        raise ValueError("Malformed RPC quantity")
    try:
        number = int(value, 16)
    except ValueError as exc:
        raise ValueError("Malformed RPC quantity") from exc
    if number < 0 or hex(number) != value.lower():
        raise ValueError("Noncanonical RPC quantity")
    return number


def _abi_address(word: bytes, *, zero: bool = False) -> str:
    if word[:12] != bytes(12):
        raise ValueError("Malformed ABI address")
    value = "0x" + word[12:].hex()
    return value if zero and value == ZERO_ADDRESS else address(value)


def _topic(signature: str) -> str:
    return "0x" + legacy.keccak(signature.encode()).hex()


@dataclass(frozen=True)
class MarketReader:
    """Inspect pinned contracts through an operator-supplied read-only RPC.

    Transport authenticity/finality remain properties of the configured node.
    Local fixture evidence is explicitly local, regardless of signer count.
    """

    context: MarketContext
    rpc: RPC

    def block(self, number: str = "latest") -> dict[str, Any]:
        """Read an exact block identity and timestamp for subsequent calls."""
        value = self.rpc("eth_getBlockByNumber", [number, False])
        if not isinstance(value, dict):
            raise ValueError("Block is unavailable")  # noqa: TRY004 - malformed external data is a validation error
        return {
            "number": _quantity(value["number"]),
            "hash": hash32(value["hash"]),
            "timestamp": _quantity(value["timestamp"]),
        }

    def call(self, target: str, signature: str, arguments: tuple[int, ...], block: int, count: int) -> list[bytes]:
        """Read a fixed-width ABI function at the selected block."""
        encoded = legacy.keccak(signature.encode())[:4] + b"".join(
            uint(item, 256, "ABI argument").to_bytes(32, "big") for item in arguments
        )
        return _words(self.rpc("eth_call", [{"to": address(target), "data": "0x" + encoded.hex()}, hex(block)]), count)

    def verify_identity(self, block: int) -> None:
        """Verify actual bytecode and graph edges, not merely a claimed chain ID."""
        c = self.context
        if _quantity(self.rpc("eth_chainId", [])) != int(c.chain_id):
            raise ValueError("Wrong chain")
        identities: list[tuple[str, str | None]] = [(c.market, c.market_code_hash), (TOKEN, c.token_code_hash)]
        if c.mark is not None and c.seed is not None:
            identities += [(c.mark, c.mark_code_hash), (c.seed, c.seed_code_hash)]
        for target, expected in identities:
            code = self.rpc("eth_getCode", [address(target), hex(block)])
            if not isinstance(code, str) or not code.startswith("0x") or not 4 <= len(code) <= 131074:
                raise ValueError("Contract code is missing")
            if "0x" + legacy.keccak(bytes.fromhex(code[2:])).hex() != expected:
                raise ValueError("Contract identity differs from the operator-pinned bytecode")
        if int.from_bytes(self.call(TOKEN, "decimals()", (), block, 1)[0], "big") != 18:
            raise ValueError("Wrong AGIALPHA decimals")
        if _abi_address(self.call(c.market, "token()", (), block, 1)[0]) != TOKEN:
            raise ValueError("Wrong AGIALPHA token")
        if (
            c.mark is not None
            and c.seed is not None
            and (
                _abi_address(self.call(c.market, "mark()", (), block, 1)[0]) != address(c.mark)
                or _abi_address(self.call(c.mark, "jobs()", (), block, 1)[0]) != address(c.market)
                or _abi_address(self.call(c.mark, "seed()", (), block, 1)[0]) != address(c.seed)
            )
        ):
            raise ValueError("MARK/seed/market graph mismatch")

    def job(self, ident: str, block: int) -> dict[str, Any]:
        """Decode the existing nineteen-word public Job getter strictly."""
        values = self.call(
            self.context.market, "jobs(uint256)", (uint(ident, 256, "job ID", positive=True),), block, 19
        )
        names = (
            "client",
            "business",
            "worker",
            "bounty",
            "price",
            "bond",
            "auction_end",
            "execution_end",
            "review_end",
            "due",
            "duration",
            "price_weight",
            "yes",
            "no",
            "state",
            "spec_hash",
            "result_hash",
            "refund",
            "claimed",
        )
        widths = {3: 96, 4: 96, 5: 96, 6: 64, 7: 64, 8: 64, 9: 64, 10: 32, 11: 16, 12: 8, 13: 8, 14: 8, 18: 1}
        result: dict[str, Any] = {}
        for index, (name, value) in enumerate(zip(names, values, strict=True)):
            if index < 3:
                result[name] = _abi_address(value, zero=index == 2)
            elif index in (15, 16):
                result[name] = "0x" + value.hex()
            else:
                result[name] = uint(int.from_bytes(value, "big"), widths.get(index, 256), name)
        if result["state"] > 6:
            raise ValueError("Unsupported job state")
        return result

    def receipt(self, tx: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """Require successful canonical-block inclusion and configured finality."""
        value = self.rpc("eth_getTransactionReceipt", [hash32(tx)])
        if not isinstance(value, dict) or _quantity(value.get("status")) != 1:
            raise ValueError("Successful mined transaction required")
        if hash32(value.get("transactionHash")) != tx:
            raise ValueError("Transaction identity mismatch")
        number = _quantity(value["blockNumber"])
        block = self.block(hex(number))
        if block["hash"] != hash32(value["blockHash"]):
            raise ValueError("Transaction was reorganized")
        if self.block()["number"] - number + 1 < self.context.confirmations:
            raise ValueError("Insufficient settlement confirmations")
        if not isinstance(value.get("logs"), list) or len(value["logs"]) > 4096:
            raise ValueError("Receipt logs exceed bounded import")
        for event in value["logs"]:
            if (
                event.get("removed", False) is not False
                or hash32(event["transactionHash"]) != tx
                or hash32(event["blockHash"]) != block["hash"]
                or _quantity(event["blockNumber"]) != number
            ):
                raise ValueError("Receipt log provenance mismatch")
        self.verify_identity(number)
        return value, block


def _events(receipt: dict[str, Any], target: str, signature: str, ident: str) -> list[dict[str, Any]]:
    topic = "0x" + uint(ident, 256, "job ID").to_bytes(32, "big").hex()
    return [
        event
        for event in receipt["logs"]
        if address(event["address"]) == address(target) and event.get("topics", [])[:2] == [_topic(signature), topic]
    ]


def _signed(journal: Journal, domain: str, body: dict[str, Any]) -> dict[str, Any]:
    hashed = digest(domain, body)
    return {
        "domain": domain,
        "body": body,
        "digest": hashed,
        "public_key": journal.public,
        "signature": base64.b64encode(journal.key.sign(bytes.fromhex(hashed))).decode("ascii"),
    }


def _verified(envelope: dict[str, Any], domain: str, public_key: str) -> dict[str, Any]:
    if (
        set(envelope) != {"domain", "body", "digest", "public_key", "signature"}
        or not isinstance(envelope["body"], dict)
        or type(envelope["body"].get("schema_version")) is not int
        or envelope["body"]["schema_version"] != 1
    ):
        raise ValueError("Unexpected signed adapter fields")
    if envelope["domain"] != domain or envelope["public_key"] != public_key:
        raise ValueError("Adapter signer/domain differs from configured trust")
    if digest(domain, envelope["body"]) != envelope["digest"]:
        raise ValueError("Adapter commitment changed")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key)).verify(
            base64.b64decode(envelope["signature"], validate=True), bytes.fromhex(envelope["digest"])
        )
    except (InvalidSignature, TypeError, ValueError) as exc:
        raise ValueError("Adapter signature is invalid") from exc
    return dict(envelope["body"])


def _binding(
    plan: dict[str, Any] | None, index: int | None, spec: legacy.JobSpec, context: MarketContext
) -> dict[str, Any]:
    if context.mark is None:
        if plan is not None or index is not None:
            raise ValueError("Standalone jobs cannot claim a MARK FusionPlan")
        return {"kind": "standalone", "plan_root": None, "plan_index": None, "indexed_leaf": None}
    if plan is None or type(index) is not int:
        raise ValueError("MARK jobs require a verified FusionPlan and actual index")
    legacy.verify_plan(plan)
    if not 0 <= index < len(plan["jobs"]) or plan["jobs"][index]["spec"] != spec.model_dump():
        raise ValueError("Specification/index differs from the FusionPlan")
    return {
        "kind": "mark-seed",
        "plan_root": plan["planRoot"],
        "plan_index": index,
        "indexed_leaf": indexed_leaf(index, spec),
    }


def seal_terms(
    journal: Journal,
    job: JobContract | dict[str, Any],
    spec: legacy.JobSpec | dict[str, Any],
    reader: MarketReader,
    *,
    plan: dict[str, Any] | None = None,
    index: int | None = None,
) -> dict[str, Any]:
    """Persist rich terms before posting; a future market ID/worker is unresolved."""
    contract = JobContract.model_validate(job)
    if contract.institution_id is None or contract.mission_id is None:
        raise ValueError("Ascension attribution requires an institution and mission")
    legacy_spec = legacy.JobSpec.model_validate(spec)
    if contract.goal != legacy_spec.goal:
        raise ValueError("Rich work terms and legacy goal differ")
    relation = _binding(plan, index, legacy_spec, reader.context)
    checkpoint = reader.block()
    reader.verify_identity(checkpoint["number"])
    next_id = int.from_bytes(reader.call(reader.context.market, "nextId()", (), checkpoint["number"], 1)[0], "big")
    if reader.context.seed is not None:
        seed_plan = reader.call(
            reader.context.seed, "plan(uint256)", (int(reader.context.seed_id or "0"),), checkpoint["number"], 2
        )
        if "0x" + seed_plan[0].hex() != relation["plan_root"] or int.from_bytes(seed_plan[1], "big") != len(
            (plan or {})["jobs"]
        ):
            raise ValueError("NovaSeed does not bind the supplied FusionPlan")
    body = {
        "schema_version": 1,
        "job_contract": contract.model_dump(mode="json"),
        "job_terms_digest": digest("job-terms", contract.model_dump(mode="json")),
        "legacy_spec": legacy_spec.model_dump(),
        "market_context": reader.context.model_dump(),
        "market_spec_hash": market_spec_hash(legacy_spec),
        "plan_binding": relation,
        "preposting_checkpoint": checkpoint,
        "prior_market_next_id": str(next_id),
        "market_job_id": None,
        "assigned_worker": None,
    }
    record_key = "@successor:ascension:terms:" + digest(
        "logical-job", {"institution": contract.institution_id, "job": contract.job_id}
    )
    with journal.transaction() as cx:
        try:
            prior = journal.latest(record_key, cx)
        except KeyError:
            envelope = _signed(journal, "ascension-terms", body)
            journal.append(cx, record_key, {"state": "sealed", "seal": envelope})
            return envelope
        old = prior["seal"]
        compared = {
            key: value for key, value in body.items() if key not in {"preposting_checkpoint", "prior_market_next_id"}
        }
        original = {
            key: value
            for key, value in old["body"].items()
            if key not in {"preposting_checkpoint", "prior_market_next_id"}
        }
        if canonical(compared) != canonical(original):
            raise ValueError("Logical job terms were already sealed; issue a new authorized job")
        return dict(old)


def bind_assignment(
    journal: Journal,
    seal: dict[str, Any],
    reader: MarketReader,
    *,
    market_job_id: str,
    posting_tx: str,
    assignment_tx: str,
    execution_authorization: dict[str, Any],
) -> dict[str, Any]:
    """Bind an observed award and the full frozen execution scope before execution."""
    body = _verified(seal, "ascension-terms", journal.public)
    if canonical(body["market_context"]) != canonical(reader.context.model_dump()):
        raise ValueError("Market context changed")
    contract = JobContract.model_validate(body["job_contract"])
    if digest("job-terms", contract.model_dump(mode="json")) != body["job_terms_digest"]:
        raise ValueError("Rich work terms changed")
    checkpoint = body["preposting_checkpoint"]
    if reader.block(hex(checkpoint["number"]))["hash"] != checkpoint["hash"]:
        raise ValueError("Preposting checkpoint was reorganized")
    job_id = uint(market_job_id, 256, "job ID", positive=True)
    if job_id <= int(body["prior_market_next_id"]):
        raise ValueError("Historical job cannot receive retroactive rich obligations")
    posting, posted_block = reader.receipt(posting_tx)
    assignment, assigned_block = reader.receipt(assignment_tx)
    if posted_block["number"] <= checkpoint["number"] or assigned_block["number"] < posted_block["number"]:
        raise ValueError("Terms must be sealed before the posting and award")
    posted = _events(
        posting,
        reader.context.market,
        "JobPosted(uint256,address,bytes32,string,string,uint96,uint64,uint64)",
        market_job_id,
    )
    assigned = _events(assignment, reader.context.market, "Assigned(uint256,address,uint96,uint64)", market_job_id)
    if len(posted) != 1 or len(assigned) != 1:
        raise ValueError("Exact posting and assignment events are required")
    job = reader.job(market_job_id, assigned_block["number"])
    if job["state"] != 2 or job["spec_hash"] != body["market_spec_hash"]:
        raise ValueError("Job is not assigned to the sealed legacy specification")
    if len(assigned[0]["topics"]) != 3 or _abi_address(_words(assigned[0]["topics"][2], 1)[0]) != job["worker"]:
        raise ValueError("Assigned worker event mismatch")
    award_data = _words(assigned[0]["data"], 2)
    if [int.from_bytes(word, "big") for word in award_data] != [job["price"], job["due"]]:
        raise ValueError("Assignment price/due mismatch")
    context = reader.context
    relation = body["plan_binding"]
    if context.mark is not None:
        if job["client"] != address(context.mark):
            raise ValueError("Wrong MARK client")
        routed = _events(posting, context.mark, "MissionRouted(uint256,uint32,uint256,bytes32)", context.seed_id or "0")
        routed = [event for event in routed if len(event["topics"]) == 4 and int(event["topics"][3], 16) == job_id]
        if len(routed) != 1 or int(routed[0]["topics"][2], 16) != relation["plan_index"]:
            raise ValueError("Wrong seed/plan index/market job route")
        if hash32(routed[0]["data"]) != relation["indexed_leaf"]:
            raise ValueError("Indexed plan leaf differs from the MARK route")
        actual_seed = reader.call(context.mark, "jobSeed(uint256)", (job_id,), assigned_block["number"], 1)
        if int.from_bytes(actual_seed[0], "big") != int(context.seed_id or "0"):
            raise ValueError("Wrong MARK seed")
    elif job["client"] != job["business"]:
        raise ValueError("Standalone job unexpectedly routed through a MARK client")
    authorization = ExecutionAuthorization.model_validate(execution_authorization)
    if (
        (contract.worker is not None and contract.worker.lower() != job["worker"])
        or authorization.job_terms_digest != body["job_terms_digest"]
        or authorization.acting_identity.lower() != job["worker"]
        or authorization.release_digest != contract.release_digest
        or authorization.environment_digest != contract.environment_digest
    ):
        raise ValueError("Authorization differs from exact job/worker/release/environment")
    current = reader.block()
    current_job = reader.job(market_job_id, current["number"])
    expiration = datetime.fromisoformat(authorization.expires_at).timestamp()
    terms_expiration = datetime.fromisoformat(contract.valid_until).timestamp()
    if (
        current_job["state"] != 2
        or current_job["worker"] != job["worker"]
        or current["timestamp"] > current_job["due"]
        or min(expiration, terms_expiration) <= max(current["timestamp"], datetime.now(UTC).timestamp())
        or expiration > min(terms_expiration, job["due"])
    ):
        raise ValueError("Assignment or exact execution authorization is no longer executable")
    if authorization.market_binding_digest is not None:
        raise ValueError("Create the market binding before attaching its digest to runtime authorization")
    binding = {
        "schema_version": 1,
        "terms_seal_digest": seal["digest"],
        "job_terms_digest": body["job_terms_digest"],
        "institution_id": contract.institution_id,
        "mission_id": contract.mission_id,
        "logical_job_id": contract.job_id,
        "market_context": context.model_dump(),
        "plan_binding": relation,
        "market_spec_hash": body["market_spec_hash"],
        "market_job_id": market_job_id,
        "selected_worker": job["worker"],
        "posting_tx": posting_tx,
        "assignment_tx": assignment_tx,
        "assignment_block": assigned_block,
        "execution_authorization": authorization.model_dump(mode="json"),
    }
    envelope = _signed(journal, "ascension-execution-binding", binding)
    key = "@successor:ascension:assignment:" + digest(
        "settlement-job", {"chain": context.chain_id, "market": context.market.lower(), "job": market_job_id}
    )
    with journal.transaction() as cx:
        try:
            old = journal.latest(key, cx)
        except KeyError:
            journal.append(cx, key, {"state": "assigned", "binding": envelope})
            return envelope
        if canonical(old["binding"]) != canonical(envelope):
            raise ValueError("Assignment already belongs to another authorization")
        return dict(old["binding"])


def verify_execution_binding(
    binding: dict[str, Any], trusted_public_key: str, authorization: ExecutionAuthorization | dict[str, Any]
) -> dict[str, Any]:
    """Verify a separately trusted chain observation before controller-authorized dispatch.

    The runtime must validate its own controller signature and authority; this
    function authenticates the exact market binding and creates no permission.
    """
    body = _verified(binding, "ascension-execution-binding", trusted_public_key)
    auth = ExecutionAuthorization.model_validate(authorization)
    if auth.market_binding_digest != binding["digest"]:
        raise ValueError("Runtime authorization does not bind this observed assignment")
    proposed = auth.model_dump(mode="json")
    proposed["market_binding_digest"] = None
    if canonical(proposed) != canonical(body["execution_authorization"]):
        raise ValueError("Runtime authorization changed after assignment binding")
    if auth.acting_identity.lower() != body["selected_worker"]:
        raise ValueError("Runtime actor differs from the observed selected worker")
    if datetime.fromisoformat(auth.expires_at) <= datetime.now(UTC):
        raise ValueError("Market-bound execution authorization expired")
    return body


def bind_delivery(
    journal: Journal, binding: dict[str, Any], artifact: bytes, *, candidate_verdict: str
) -> dict[str, Any]:
    """Commit exact result bytes and an evaluation verdict without admitting a candidate."""
    _verified(binding, "ascension-execution-binding", journal.public)
    if not artifact or len(artifact) > MAX_ARTIFACT_BYTES:
        raise ValueError("Artifact is empty or exceeds the delivery limit")
    if candidate_verdict not in {"PASS", "FAIL", "TIE", "INSUFFICIENT_EVIDENCE", "RETAIN_INCUMBENT", "NOT_APPLICABLE"}:
        raise ValueError("Unsupported candidate verdict")
    return _signed(
        journal,
        "ascension-delivery-binding",
        {
            "schema_version": 1,
            "execution_binding_digest": binding["digest"],
            "artifact_keccak256": "0x" + legacy.keccak(artifact).hex(),
            "artifact_size": len(artifact),
            "candidate_verdict": candidate_verdict,
        },
    )


def payout_breakdown(price: int, bounty: int) -> dict[str, Any]:
    """Mirror per-recipient integer rounding, including tiny validator payouts."""
    uint(price, 96, "price", positive=True)
    uint(bounty, 96, "bounty", positive=True)
    if not 100 <= price <= bounty:
        raise ValueError("Price must satisfy the existing bid bounds")
    each = price * 500 // 10000 // 2
    gross = [price - 2 * each, each, each]
    burned = [amount // 100 for amount in gross]
    return {
        "gross": gross,
        "burned": burned,
        "net": [g - b for g, b in zip(gross, burned, strict=True)],
        "refund": bounty - price,
    }


def import_settlement(
    journal: Journal,
    binding: dict[str, Any],
    delivery: dict[str, Any],
    artifact: bytes,
    reader: MarketReader,
    *,
    settlement_tx: str,
) -> dict[str, Any]:
    """Import authentic terminal contract facts once, preserving all admission boundaries."""
    bound = _verified(binding, "ascension-execution-binding", journal.public)
    delivered = _verified(delivery, "ascension-delivery-binding", journal.public)
    if delivered["execution_binding_digest"] != binding["digest"]:
        raise ValueError("Delivery belongs to another execution authorization")
    if len(artifact) > MAX_ARTIFACT_BYTES or len(artifact) != delivered["artifact_size"]:
        raise ValueError("Delivered artifact size mismatch")
    if "0x" + legacy.keccak(artifact).hex() != delivered["artifact_keccak256"]:
        raise ValueError("Fetched artifact digest mismatch; URI is not evidence")
    if canonical(reader.context.model_dump()) != canonical(bound["market_context"]):
        raise ValueError("Wrong settlement chain/market/MARK/seed")
    receipt, block = reader.receipt(settlement_tx)
    job_id = bound["market_job_id"]
    job = reader.job(job_id, block["number"])
    if job["worker"] != bound["selected_worker"] or job["spec_hash"] != bound["market_spec_hash"]:
        raise ValueError("Settlement job/worker/spec mismatch")
    if job["result_hash"] != delivered["artifact_keccak256"]:
        raise ValueError("Settlement result does not bind the exact artifact")
    if block["number"] < bound["assignment_block"]["number"]:
        raise ValueError("Settlement predates assignment")
    closed = _events(receipt, reader.context.market, "Closed(uint256,uint8,uint256)", job_id)
    if len(closed) != 1:
        raise ValueError("Exactly one matching closure event required")
    close_words = _words(closed[0]["data"], 2)
    if [int.from_bytes(word, "big") for word in close_words] != [job["state"], job["refund"]]:
        raise ValueError("Closure event differs from contract state")
    payouts = _events(receipt, reader.context.market, "Payout(uint256,address,uint256,uint256)", job_id)
    actual_payouts = []
    for event in payouts:
        if len(event["topics"]) != 3:
            raise ValueError("Malformed payout event")
        gross, burned = (int.from_bytes(word, "big") for word in _words(event["data"], 2))
        actual_payouts.append(
            {"recipient": _abi_address(_words(event["topics"][2], 1)[0]), "gross": str(gross), "burned": str(burned)}
        )
        if burned != gross // 100:
            raise ValueError("Per-payout burn rounding mismatch")
    review_logs = reader.rpc(
        "eth_getLogs",
        [
            {
                "address": address(reader.context.market),
                "fromBlock": hex(bound["assignment_block"]["number"]),
                "toBlock": hex(block["number"]),
                "topics": [
                    _topic("Validated(uint256,address,bool,bytes32,bytes32)"),
                    "0x" + int(job_id).to_bytes(32, "big").hex(),
                ],
            }
        ],
    )
    if not isinstance(review_logs, list) or len(review_logs) > 3:
        raise ValueError("Unexpected review history")
    reviews: list[dict[str, Any]] = []
    for event in review_logs:
        review_receipt, review_block = reader.receipt(hash32(event["transactionHash"]))
        if (
            event not in review_receipt["logs"]
            or not bound["assignment_block"]["number"] <= review_block["number"] <= block["number"]
        ):
            raise ValueError("Review event is outside the exact authorized history")
        if (
            len(event["topics"]) != 3
            or address(event["address"]) != address(reader.context.market)
            or event["topics"][:2]
            != [_topic("Validated(uint256,address,bool,bytes32,bytes32)"), "0x" + int(job_id).to_bytes(32, "big").hex()]
        ):
            raise ValueError("Review event provenance mismatch")
        reviewer = _abi_address(_words(event["topics"][2], 1)[0])
        approved_word, result_hash, evidence_hash = _words(event["data"], 3)
        vote = int.from_bytes(approved_word, "big")
        if (
            vote not in (0, 1)
            or "0x" + result_hash.hex() != delivered["artifact_keccak256"]
            or evidence_hash == bytes(32)
        ):
            raise ValueError("Review does not bind the exact artifact and evidence")
        if reviewer in {item["reviewer"] for item in reviews}:
            raise ValueError("Duplicate review attribution")
        reviews.append(
            {
                "reviewer": reviewer,
                "approved": vote == 1,
                "artifact_keccak256": "0x" + result_hash.hex(),
                "evidence_keccak256": "0x" + evidence_hash.hex(),
                "transaction_hash": event["transactionHash"],
            }
        )
    if (
        sum(item["approved"] for item in reviews) != job["yes"]
        or sum(not item["approved"] for item in reviews) != job["no"]
    ):
        raise ValueError("Review evidence does not reconstruct the settlement quorum")
    if job["state"] == 4:
        if job["yes"] != 2 or job["no"] >= 2:
            raise ValueError("Paid work lacks approval quorum")
        expected = payout_breakdown(job["price"], job["bounty"])
        if len(actual_payouts) != 3 or job["refund"] != expected["refund"]:
            raise ValueError("Paid work payout/refund count mismatch")
        if actual_payouts[0]["recipient"] != job["worker"] or int(actual_payouts[0]["gross"]) != expected["gross"][0]:
            raise ValueError("Worker payout mismatch")
        approved: list[str] = []
        for index in range(3):
            validator = _abi_address(
                reader.call(
                    reader.context.market, "committees(uint256,uint256)", (int(job_id), index), block["number"], 1
                )[0]
            )
            vote = int.from_bytes(
                reader.call(
                    reader.context.market,
                    "votes(uint256,address)",
                    (int(job_id), int(validator, 16)),
                    block["number"],
                    1,
                )[0],
                "big",
            )
            if vote == 1:
                approved.append(validator)
        if [item["recipient"] for item in actual_payouts[1:]] != approved or [
            int(item["gross"]) for item in actual_payouts[1:]
        ] != expected["gross"][1:]:
            raise ValueError("Validator payouts do not match the approving committee")
        acceptance, status = "accepted", "paid"
    elif job["state"] == 6:
        if job["yes"] >= 2 or job["no"] >= 2 or payouts or job["refund"] != job["bounty"]:
            raise ValueError("No-quorum refund must preserve the bounty without slashing")
        acceptance, status = "unresolved_no_quorum", "refunded"
    elif job["state"] == 5:
        if job["no"] != 2 or len(actual_payouts) != 1:
            raise ValueError("Delivered-work failure requires negative quorum and bond accounting")
        slash = actual_payouts[0]
        if (
            slash["recipient"] != job["client"]
            or int(slash["gross"]) != job["bond"]
            or job["refund"] != job["bounty"] + job["bond"] - job["bond"] // 100
        ):
            raise ValueError("Failure/slashing refund mismatch")
        acceptance, status = "rejected", "failed"
    else:
        raise ValueError("Settlement is not terminal")
    context = reader.context
    attribution = {"chain": context.chain_id, "market": context.market.lower(), "job": job_id}
    key = "@successor:ascension:settlement:" + digest("settlement-job", attribution)
    record = {
        "schema_version": 1,
        "institution_id": bound["institution_id"],
        "mission_id": bound["mission_id"],
        "logical_job_id": bound["logical_job_id"],
        "execution_binding_digest": binding["digest"],
        "delivery_digest": delivery["digest"],
        "chain": attribution,
        "transaction_hash": settlement_tx,
        "block": block,
        "job_acceptance": acceptance,
        "candidate_verdict": delivered["candidate_verdict"],
        "settlement_status": status,
        "memory_admission": "not_granted",
        "institutional_admission": "not_granted",
        "authority_status": "not_granted",
        "payouts": actual_payouts,
        "reviews": reviews,
        "refund_base_units": str(job["refund"]),
        "token": TOKEN,
        "symbol": "AGIALPHA",
        "decimals": 18,
        "evidence_scope": context.scope,
        "customer_realized_value": None,
    }
    with journal.transaction() as cx:
        try:
            previous = journal.latest(key, cx)
        except KeyError:
            journal.append(cx, key, {"state": "imported", "settlement": record})
            return record
        if canonical(previous["settlement"]) != canonical(record):
            raise ValueError("Settlement already attributed; duplicate payment/admission is forbidden")
        return dict(previous["settlement"])


def list_settlements(
    journal: Journal, institution_id: str, cx: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    """Export signed attributable settlements without altering historical signed bytes.

    Pass the caller's snapshot connection to make institution and economic exports
    one consistent snapshot. Private keys and credentials are never included.
    """
    if cx is None:
        with closing(sqlite3.connect(journal.path)) as connection:
            connection.execute("BEGIN")
            return list_settlements(journal, institution_id, connection)
    records = []
    for body_text, hashed, signature in cx.execute(
        "SELECT body,hash,signature FROM events WHERE mission LIKE '@successor:ascension:settlement:%' ORDER BY seq"
    ):
        body = json.loads(body_text)
        settlement = body["document"]["settlement"]
        if settlement["institution_id"] != institution_id:
            continue
        if hashlib.sha256(body_text.encode()).hexdigest() != hashed:
            raise ValueError("Settlement journal bytes are corrupt")
        try:
            journal.key.public_key().verify(base64.b64decode(signature, validate=True), bytes.fromhex(hashed))
        except (InvalidSignature, ValueError) as exc:
            raise ValueError("Settlement journal signature is invalid") from exc
        records.append(
            {
                "schema": "agialpha.ascension.journal-settlement.v1",
                "public_key": journal.public,
                "canonical_body": body_text,
                "hash": hashed,
                "signature": signature,
                "settlement": settlement,
            }
        )
    return records


def validate_historical_settlement(record: dict[str, Any]) -> dict[str, Any]:
    """Authenticate bounded historical bytes; this does not establish a trusted signer.

    The independently trusted institution export carries custody. An embedded key
    authenticates only this old record's provenance; no chain revalidation, new
    payment attribution, admission or operational authority follows from it.
    """
    from ..store import canonical as historical_canonical

    if (
        not isinstance(record, dict)
        or set(record) != {"schema", "public_key", "canonical_body", "hash", "signature", "settlement"}
        or record["schema"] != "agialpha.ascension.journal-settlement.v1"
        or not isinstance(record["canonical_body"], str)
        or not isinstance(record["public_key"], str)
        or not isinstance(record["hash"], str)
        or not isinstance(record["signature"], str)
        or len(record["public_key"]) != 64
        or len(record["hash"]) != 64
        or len(record["signature"]) != 88
    ):
        raise ValueError("Invalid historical settlement wrapper")
    raw = record["canonical_body"].encode("utf-8")
    if not raw or len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("Historical settlement exceeds its byte limit")
    depth, quoted, escaped = 0, False, False
    for char in record["canonical_body"]:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 32:
                raise ValueError("Historical settlement exceeds its depth limit")
        elif char in "]}":
            depth -= 1
            if depth < 0:
                raise ValueError("Malformed historical settlement structure")
    if quoted or depth:
        raise ValueError("Malformed historical settlement structure")
    body = legacy.parse(raw, MAX_ARTIFACT_BYTES)
    if not isinstance(body, dict) or set(body) != {
        "schema",
        "sequence",
        "previous",
        "identity",
        "mission",
        "time_ns",
        "document",
    }:
        raise ValueError("Invalid historical settlement journal body")
    if type(body["schema"]) is not int or body["schema"] != 1:
        raise ValueError("Unsupported historical journal schema")
    if type(body["sequence"]) is not int or type(body["time_ns"]) is not int:
        raise ValueError("Historical journal counters must be exact integers")
    uint(body["sequence"], 53, "journal sequence", positive=True)
    uint(body["time_ns"], 64, "journal timestamp", positive=True)
    if not isinstance(body["previous"], str) or len(body["previous"]) != 64:
        raise ValueError("Invalid historical predecessor hash")
    hash32("0x" + body["previous"])
    if historical_canonical(body) != raw or hashlib.sha256(raw).hexdigest() != record["hash"]:
        raise ValueError("Historical signed bytes or hash changed")
    if body["identity"] != "urn:agialpha:ed25519:" + record["public_key"]:
        raise ValueError("Historical identity differs from its provenance key")
    document = body["document"]
    if not isinstance(document, dict) or set(document) != {"state", "settlement"} or document["state"] != "imported":
        raise ValueError("Invalid historical settlement journal document")
    settlement = document["settlement"]
    if not isinstance(settlement, dict) or canonical(settlement) != canonical(record["settlement"]):
        raise ValueError("Wrapped settlement differs from the exact signed body")
    if type(settlement.get("schema_version")) is not int or settlement["schema_version"] != 1:
        raise ValueError("Unsupported historical settlement schema")
    attribution = settlement.get("chain")
    if not isinstance(attribution, dict) or set(attribution) != {"chain", "market", "job"}:
        raise ValueError("Invalid historical chain attribution")
    uint(attribution["chain"], 256, "chain ID", positive=True)
    uint(attribution["job"], 256, "market job ID", positive=True)
    address(attribution["market"])
    if body["mission"] != "@successor:ascension:settlement:" + digest("settlement-job", attribution):
        raise ValueError("Historical journal attribution differs from the settlement")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(record["public_key"])).verify(
            base64.b64decode(record["signature"], validate=True), bytes.fromhex(record["hash"])
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("Historical settlement signature is invalid") from exc
    return dict(record)
