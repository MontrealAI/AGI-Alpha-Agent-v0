# SPDX-License-Identifier: Apache-2.0
"""Explicit Jobs v0 admission and reviewed bounded-work handoffs; no wallet writes."""
from __future__ import annotations

import base64
import hashlib
import uuid
from pathlib import Path
from typing import Any, Callable, Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator, model_serializer, SerializerFunctionWrapHandler

from .ascension import keccak, parse
from .chain import AGIALPHA, address
from .engine import Engine, verify_export
from .models import Mission, StrictModel
from .store import Conflict, Journal, canonical, digest
from .successor.studio_operator import ReadOnlyRPC

from .work_spec import MAX_BYTES, WorkSpec, read_spec

DELIVERY_SCHEMA = "agialpha.ecosystem-reviewed-delivery.v1"
BACKEND = "agijobsv0-jobregistry-v2"


class ContractPin(StrictModel):
    address: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    runtime_keccak256: str = Field(pattern=r"^0x[0-9a-f]{64}$")


class JobsProfile(StrictModel):
    """Host-installed full-code pins, never supplied as authority by a work file."""

    schema_id: Literal["agialpha.jobs-v0-profile.v1"] = Field(alias="schema")
    backend: Literal["agijobsv0-jobregistry-v2"]
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    rpc_url: str = Field(max_length=2048)
    chain_id: int = Field(ge=1, le=2**53 - 1)
    confirmations: int = Field(ge=1, le=10000)
    scope: Literal["disposable-local-fixture", "operator-configured-chain"]
    contracts: dict[str, ContractPin]

    @model_serializer(mode="wrap")
    def canonical_profile(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        data["schema"] = data.pop("schema_id", data.get("schema", "agialpha.jobs-v0-profile.v1"))
        return data

    @model_validator(mode="after")
    def boundaries(self) -> JobsProfile:
        expected = {"registry", "token", "stake", "validation", "identity", "configuration", "lifecycle", "settlement"}
        if set(self.contracts) != expected:
            raise ValueError("Every registry/delegate/dependency full-code pin is required")
        for pin in self.contracts.values():
            address(pin.address)
            if int(pin.runtime_keccak256, 16) == 0:
                raise ValueError("An empty code pin is not configured")
        url = urlsplit(self.rpc_url)
        local = url.hostname in {"localhost", "127.0.0.1", "::1"}
        if not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("RPC must not embed credentials, query or fragment")
        if url.scheme != "https" and not (url.scheme == "http" and local and self.chain_id != 1):
            raise ValueError("Remote and mainnet RPC require HTTPS")
        if self.scope == "disposable-local-fixture" and (not local or self.chain_id == 1):
            raise ValueError("Disposable qualification requires a non-mainnet loopback RPC")
        if self.chain_id == 1 and address(self.contracts["token"].address) != AGIALPHA:
            raise ValueError("Mainnet Jobs v0 uses the canonical AGIALPHA token")
        return self


def installed_profile(journal: Journal) -> JobsProfile:
    path = journal.root / "jobs-v0-profile.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64_000:
        raise ValueError("Install a bounded, independently verified Jobs v0 profile on this host")
    return JobsProfile.model_validate(parse(path.read_bytes(), 64_000))


def _hex(value: Any, size: int | None = None) -> bytes:
    if not isinstance(value, str) or not value.startswith("0x") or len(value) % 2:
        raise ValueError("Invalid hex bytes")
    result = bytes.fromhex(value[2:])
    if size is not None and len(result) != size:
        raise ValueError("Incorrect byte length")
    return result


def _quantity(value: Any) -> int:
    if not isinstance(value, str) or not value.startswith("0x") or not value[2:]:
        raise ValueError("Invalid RPC quantity")
    result = int(value, 16)
    if result < 0 or result >= 2**256:
        raise ValueError("Out-of-range quantity")
    return result


def observe_assignment(
    profile: JobsProfile,
    job_id: str,
    worker: str,
    spec_hash: str,
    assignment_tx: str,
    *,
    rpc: Callable[[str, list[Any]], Any] | None = None,
    states: tuple[int, ...] = (2,),
) -> dict[str, Any]:
    """Verify exact current assignment, canonical receipt and installed full-code pins."""
    from eth_abi.abi import decode, encode

    if not job_id.isdecimal() or str(int(job_id)) != job_id or not 0 < int(job_id) < 2**256:
        raise ValueError("Job ID must be a positive canonical uint256 string")
    worker = address(worker)
    _hex(spec_hash, 32)
    _hex(assignment_tx, 32)
    read = rpc or ReadOnlyRPC(profile.rpc_url)
    if _quantity(read("eth_chainId", [])) != profile.chain_id:
        raise ValueError("Wrong chain")
    head = _quantity(read("eth_blockNumber", []))
    number = head - profile.confirmations + 1
    if profile.chain_id == 1:
        finalized = read("eth_getBlockByNumber", ["finalized", False])
        number = min(number, _quantity(finalized["number"]))
    if number < 0:
        raise ValueError("Insufficient confirmations")
    block_tag = hex(number)
    block = read("eth_getBlockByNumber", [block_tag, False])
    if _quantity(block["number"]) != number:
        raise ValueError("Wrong checkpoint number")
    block_hash = "0x" + _hex(block["hash"], 32).hex()
    now = _quantity(block["timestamp"])
    contracts = {name: address(pin.address) for name, pin in profile.contracts.items()}
    for name, pin in profile.contracts.items():
        code = _hex(read("eth_getCode", [contracts[name], block_tag]))
        if not code or "0x" + keccak(code).hex() != pin.runtime_keccak256:
            raise ValueError(f"Full runtime bytecode mismatch: {name}")

    def call(
        name: str, signature: str, outputs: list[str], inputs: list[str] | None = None, args: list[Any] | None = None
    ) -> tuple[Any, ...]:
        data = keccak(signature.encode())[:4] + encode(inputs or [], args or [])
        return tuple(
            decode(outputs, _hex(read("eth_call", [{"to": contracts[name], "data": "0x" + data.hex()}, block_tag])))
        )

    if call("registry", "version()", ["uint256"])[0] != 2 or call("registry", "paused()", ["bool"])[0]:
        raise ValueError("Registry version is unsupported or paused")
    modules = call("registry", "implementationModules()", ["address[3]"])[0]
    if [address(value) for value in modules] != [
        contracts[name] for name in ("configuration", "lifecycle", "settlement")
    ]:
        raise ValueError("Immutable registry delegates differ from installed profile")
    for method, name in (
        ("stakeManager()", "stake"),
        ("validationModule()", "validation"),
        ("identityRegistry()", "identity"),
    ):
        if address(call("registry", method, ["address"])[0]) != contracts[name]:
            raise ValueError("Registry dependency changed")
    if (
        address(call("stake", "token()", ["address"])[0]) != contracts["token"]
        or call("token", "decimals()", ["uint8"])[0] != 18
    ):
        raise ValueError("Jobs token dependency or units differ")
    values = call(
        "registry",
        "jobs(uint256)",
        ["address", "address", "uint128", "uint96", "uint128", "bytes32", "bytes32", "bytes32", "uint256"],
        ["uint256"],
        [int(job_id)],
    )
    metadata = values[8]
    state, deadline, assigned_at = metadata & 7, (metadata >> 77) & (2**64 - 1), (metadata >> 141) & (2**64 - 1)
    if state not in states or address(values[1]) != worker or "0x" + values[7].hex() != spec_hash.lower():
        raise ValueError("Job state, assigned worker or exact work commitment differs")
    if not assigned_at or (state == 2 and now >= deadline):
        raise ValueError("Assignment missing or delivery deadline expired")
    receipt = read("eth_getTransactionReceipt", [assignment_tx])
    if (
        not isinstance(receipt, dict)
        or receipt.get("status") != "0x1"
        or receipt.get("transactionHash", "").lower() != assignment_tx.lower()
    ):
        raise ValueError("Assignment receipt missing or reverted")
    if (
        address(receipt["to"]) != contracts["registry"]
        or address(receipt["from"]) != worker
        or _quantity(receipt["blockNumber"]) > number
    ):
        raise ValueError("Assignment is not a confirmed direct worker call to this registry")
    receipt_hash = "0x" + _hex(receipt["blockHash"], 32).hex()
    event_topic = "0x" + keccak(b"AgentAssigned(uint256,address,string)").hex()
    matches = []
    for log in receipt["logs"]:
        if address(log["address"]) != contracts["registry"] or not log.get("topics") or log["topics"][0] != event_topic:
            continue
        if (
            log.get("removed") is not False
            or log.get("transactionHash", "").lower() != assignment_tx.lower()
            or log.get("blockHash", "").lower() != receipt_hash
            or _quantity(log["blockNumber"]) != _quantity(receipt["blockNumber"])
        ):
            raise ValueError("Assignment log is removed or differs from its canonical receipt")
        if (
            len(log["topics"]) != 3
            or int.from_bytes(_hex(log["topics"][1], 32)) != int(job_id)
            or _hex(log["topics"][2], 32) != bytes(12) + bytes.fromhex(worker[2:])
        ):
            raise ValueError("Assignment event scope differs")
        decode(["string"], _hex(log["data"]))
        matches.append(log)
    if len(matches) != 1:
        raise ValueError("Exactly one scoped assignment event is required")
    if (
        read("eth_getBlockByNumber", [receipt["blockNumber"], False])["hash"].lower() != receipt_hash
        or read("eth_getBlockByNumber", [block_tag, False])["hash"].lower() != block_hash
    ):
        raise ValueError("Canonical chain changed during verification")
    return {
        "backend": BACKEND,
        "chain_id": profile.chain_id,
        "registry": contracts["registry"],
        "token": contracts["token"],
        "decimals": 18,
        "job_id": job_id,
        "worker": worker,
        "employer": address(values[0]),
        "spec_hash": spec_hash.lower(),
        "state": state,
        "deadline": str(deadline),
        "reward": str(values[2]),
        "stake": str(values[3]),
        "result_hash": "0x" + values[6].hex(),
        "assignment_transaction": assignment_tx.lower(),
        "assignment_block_hash": receipt_hash,
        "block_number": block_tag,
        "block_hash": block_hash,
        "observed_at": now,
        "profile_digest": digest(profile.model_dump()),
        "authority": "read-only",
    }


def admit(journal: Journal, raw: bytes, job_id: str, worker: str, assignment_tx: str) -> dict[str, Any]:
    """Atomically retain observed market binding and queue one explicit native mission."""
    journal.verify()
    spec, spec_hash = read_spec(raw)
    if spec.executor != "alpha-native-v1":
        raise ValueError("This admission route requires the separately selected native executor")
    profile = installed_profile(journal)
    observation = observe_assignment(profile, job_id, worker, spec_hash, assignment_tx)
    binding = {name: observation[name] for name in ("backend", "chain_id", "registry", "job_id")}
    key = "@ecosystem:" + digest(binding)
    ident = str(uuid.uuid5(uuid.NAMESPACE_URL, key))
    with journal.transaction() as cx:
        control = journal.latest("@control", cx)
        if control["state"] != "ready" or control["config_hash"] != digest(journal.config.model_dump()):
            raise Conflict("Agent is paused or configuration changed")
        try:
            old = journal.latest(key, cx)
        except KeyError:
            old = None
        if old is not None:
            for field in ("spec_hash", "worker", "profile_digest", "assignment_transaction"):
                if old["observation"][field] != observation[field]:
                    raise Conflict("Market job already binds different work or authority")
            return {"binding": old, "mission": journal.latest(ident, cx), "replayed": True}
        try:
            journal.latest(ident, cx)
        except KeyError:
            pass
        else:
            raise Conflict("Native mission identity collision")
        mission = journal.append(
            cx,
            ident,
            {
                "state": "queued",
                "request": spec.mission.model_dump(),
                "request_hash": digest(spec.mission.model_dump()),
            },
        )
        retained = journal.append(
            cx,
            key,
            {
                "state": "admitted",
                "mission_id": ident,
                "spec_base64": base64.b64encode(raw).decode(),
                "observation": observation,
            },
        )
        return {"binding": retained, "mission": mission, "replayed": False}


def _retained(journal: Journal, binding_id: str) -> tuple[dict[str, Any], WorkSpec, JobsProfile]:
    if not binding_id.startswith("@ecosystem:") or len(binding_id) != 75:
        raise ValueError("Invalid ecosystem binding identity")
    record = journal.latest(binding_id)
    spec, spec_hash = read_spec(base64.b64decode(record["spec_base64"], validate=True))
    profile = installed_profile(journal)
    if (
        spec_hash != record["observation"]["spec_hash"]
        or digest(profile.model_dump()) != record["observation"]["profile_digest"]
    ):
        raise Conflict("Retained work or independently installed profile changed")
    return record, spec, profile


def execute(journal: Journal, binding_id: str) -> dict[str, Any]:
    """Recheck admission before explicit execution; never replay interrupted work."""
    record, spec, profile = _retained(journal, binding_id)
    observation = record["observation"]
    observe_assignment(
        profile,
        observation["job_id"],
        observation["worker"],
        observation["spec_hash"],
        observation["assignment_transaction"],
    )
    mission = journal.latest(record["mission_id"])
    if mission["request_hash"] != digest(spec.mission.model_dump()):
        raise Conflict("Native mission no longer matches commissioned work")
    if mission["state"] != "queued":
        return mission
    return Engine(journal).execute(record["mission_id"])


def delivery(journal: Journal, binding_id: str) -> dict[str, Any]:
    """Export reviewed native work bound to the market; no submit/payment occurs."""
    record, spec, profile = _retained(journal, binding_id)
    old = record["observation"]
    current = observe_assignment(
        profile, old["job_id"], old["worker"], old["spec_hash"], old["assignment_transaction"], states=(2, 3, 4, 5, 6)
    )
    artifact = Engine(journal).export(record["mission_id"])
    verify_export(artifact, journal.public)
    if artifact["receipt"]["body"]["document"]["request"] != spec.mission.model_dump():
        raise ValueError("Reviewed artifact differs from exact commissioned mission")
    body = {
        "schema": DELIVERY_SCHEMA,
        "spec_base64": record["spec_base64"],
        "binding": old,
        "native_artifact": artifact,
        "authority": "reviewed-work-only; no wallet or settlement authority",
    }
    # Stable admission observation: repeated export has identical exact bytes.
    hashed = digest(body)
    result = {
        "body": body,
        "public_key": journal.public,
        "sha256": hashed,
        "signature": base64.b64encode(journal.key.sign(bytes.fromhex(hashed))).decode(),
    }
    raw = canonical(result)
    result_hash = "0x" + hashlib.sha256(raw).hexdigest()
    if current["state"] != 2 and current["result_hash"] != result_hash:
        raise Conflict("Submitted market result differs from the retained native artifact")
    return {
        "artifact_base64": base64.b64encode(raw).decode(),
        "result_hash": result_hash,
        "current_observation": current,
        "scope": "local operator reviewed; marketplace acceptance remains separate",
    }


def verify_delivery(raw: bytes, trusted_key: str, expected_binding: dict[str, Any]) -> dict[str, Any]:
    """Verify externally pinned signer, exact binding, work and native approval."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    value = parse(raw, 2_000_000)
    if set(value) != {"body", "public_key", "sha256", "signature"} or value["public_key"] != trusted_key:
        raise ValueError("Delivery identity or shape differs")
    body = value["body"]
    if body["schema"] != DELIVERY_SCHEMA or body["binding"] != expected_binding or digest(body) != value["sha256"]:
        raise ValueError("Delivery scope or exact bytes differ")
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(trusted_key)).verify(
        base64.b64decode(value["signature"], validate=True), bytes.fromhex(value["sha256"])
    )
    spec, spec_hash = read_spec(base64.b64decode(body["spec_base64"], validate=True))
    if spec_hash != expected_binding["spec_hash"] or spec.executor != "alpha-native-v1":
        raise ValueError("Delivery work commitment or executor differs")
    native = body["native_artifact"]
    verify_export(native, trusted_key)
    if native["receipt"]["body"]["document"]["request"] != spec.mission.model_dump():
        raise ValueError("Native result is for another mission")
    return {"valid": True, "result_hash": "0x" + hashlib.sha256(raw).hexdigest(), "authority": "reviewed-work-only"}


def main() -> None:
    """Explicit installed-agent workflow; never initializes credentials or writes chain state."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    admission = sub.add_parser("admit")
    admission.add_argument("--spec", type=Path, required=True)
    admission.add_argument("--job-id", required=True)
    admission.add_argument("--worker", required=True)
    admission.add_argument("--assignment-tx", required=True)
    for name in ("execute", "show", "export"):
        sub.add_parser(name).add_argument("--binding", required=True)
    args = parser.parse_args()
    journal = Journal(args.home)
    if args.action == "admit":
        with args.spec.open("rb") as source:
            raw = source.read(MAX_BYTES + 1)
        result = admit(journal, raw, args.job_id, args.worker, args.assignment_tx)
    elif args.action == "execute":
        result = execute(journal, args.binding)
    elif args.action == "export":
        result = delivery(journal, args.binding)
    else:
        result = journal.latest(args.binding)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
