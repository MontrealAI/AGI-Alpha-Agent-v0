# SPDX-License-Identifier: Apache-2.0
"""Service-bound EOA proofs and fresh pinned ENSv1 authority reads.

Only direct registry managers or wrapped owners of an exact ASCII label below
agent.agi.eth are supported. Delegation, contract wallets, ENSv2 and CCIP names
are deliberately unsupported. RPC responses remain an operator trust dependency.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import time
from typing import Any, Protocol
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from ..chain import address
from ..store import Conflict, Journal
from .protocol import Digest, StrictModel, canonical, digest

REGISTRY = "0x00000000000c2e074ec69a0dfb2997ba6c7d2e1e"
WRAPPER = "0xd4416b13d2b3a9abae7acd5d6c2bbdbe25686401"
REGISTRAR = "0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85"


class ReadRPC(Protocol):
    """Reuse the runtime's allowlisted read-only JSON-RPC transport."""

    def call(self, method: str, params: list[Any]) -> Any: ...


def direct_name(name: str) -> str:
    """Accept one normalized ASCII direct label, never a suffix-only claim."""
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.agent\.agi\.eth", name):
        raise ValueError("one normalized direct ASCII label below agent.agi.eth is required")
    if name.startswith("xn--"):
        raise ValueError("internationalized labels require a separately reviewed normalization policy")
    return name


def namehash(name: str) -> bytes:
    """ENSIP-1 namehash using the established Ethereum Keccak implementation."""
    from eth_utils.crypto import keccak

    node = bytes(32)
    for label in reversed(name.split(".")):
        node = keccak(node + keccak(text=label))
    return bytes(node)


class ENSPins(StrictModel):
    """Separately approved mainnet implementation identities; no guessed pins."""

    registry_sha256: Digest
    wrapper_sha256: Digest
    registrar_sha256: Digest
    max_block_age_seconds: int = Field(default=60, ge=1, le=120)


class ENSAuthority:
    """Check a canonical recent block with two configured independent readers."""

    def __init__(self, readers: tuple[ReadRPC, ReadRPC], pins: ENSPins) -> None:
        if readers[0] is readers[1]:
            raise ValueError("two separately configured RPC readers are required")
        self.readers, self.pins = readers, ENSPins.model_validate(pins.model_dump())

    @staticmethod
    def _words(rpc: ReadRPC, target: str, signature: str, argument: bytes, block: dict[str, Any]) -> list[int]:
        from eth_utils.crypto import keccak

        result = rpc.call(
            "eth_call", [{"to": target, "data": "0x" + (keccak(text=signature)[:4] + argument).hex()}, block]
        )
        if not isinstance(result, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{64}){1,3}", result):
            raise ValueError("invalid fixed-width ENS ABI result")
        return [int(result[i : i + 64], 16) for i in range(2, len(result), 64)]

    def verify(self, name: str, wallet: str, *, now: int | None = None) -> dict[str, Any]:
        name, wallet = direct_name(name), address(wallet)
        now = int(time.time()) if now is None else now
        first = self.readers[0].call("eth_getBlockByNumber", ["latest", False])
        if not isinstance(first, dict) or not re.fullmatch(r"0x[0-9a-fA-F]{64}", first.get("hash", "")):
            raise ValueError("current canonical block unavailable")
        number = int(first["number"], 16)
        timestamp = int(first["timestamp"], 16)
        if not 0 <= now - timestamp <= self.pins.max_block_age_seconds:
            raise ValueError("ENS chain evidence is stale or future dated")
        block = {"blockHash": first["hash"], "requireCanonical": True}
        snapshots = []
        for rpc in self.readers:
            if rpc.call("eth_chainId", []) != "0x1":
                raise ValueError("ENSv1 access requires Ethereum mainnet")
            latest = rpc.call("eth_getBlockByNumber", ["latest", False])
            if not latest or not number <= int(latest["number"], 16) <= number + 3:
                raise ValueError("RPC readers disagree on current chain position")
            if not 0 <= now - int(latest["timestamp"], 16) <= self.pins.max_block_age_seconds:
                raise ValueError("ENS reader is stale")
            selected = rpc.call("eth_getBlockByNumber", [hex(number), False])
            if not selected or selected != first:
                raise ValueError("RPC readers disagree on the complete canonical block")
            for target, pin in (
                (REGISTRY, self.pins.registry_sha256),
                (WRAPPER, self.pins.wrapper_sha256),
                (REGISTRAR, self.pins.registrar_sha256),
            ):
                code = rpc.call("eth_getCode", [target, block])
                if not isinstance(code, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})+", code):
                    raise ValueError("pinned ENS implementation unavailable")
                if hashlib.sha256(bytes.fromhex(code[2:])).hexdigest() != pin:
                    raise ValueError("ENS implementation changed; requalification is required")
            if rpc.call("eth_getCode", [wallet, block]) != "0x":
                raise ValueError("only EOA wallet proofs are supported")
            from eth_utils.crypto import keccak

            expiry = self._words(rpc, REGISTRAR, "nameExpires(uint256)", bytes(keccak(text="agi")), block)
            if len(expiry) != 1 or expiry[0] <= now:
                raise ValueError("agi.eth registration has expired")
            owners = []
            for ancestor in ("agi.eth", "agent.agi.eth", name):
                words = self._words(rpc, REGISTRY, "owner(bytes32)", namehash(ancestor), block)
                if len(words) != 1 or not 0 < words[0] < 2**160:
                    raise ValueError("ENS authority is missing or malformed")
                owner = "0x" + format(words[0], "040x")
                wrapped_expiry = None
                if owner == WRAPPER:
                    data = self._words(rpc, WRAPPER, "getData(uint256)", namehash(ancestor), block)
                    if (
                        len(data) != 3
                        or not 0 < data[0] < 2**160
                        or not 0 <= data[1] < 2**32
                        or not now < data[2] < 2**64
                    ):
                        raise ValueError("wrapped authority is absent, expired or malformed")
                    owner, wrapped_expiry = "0x" + format(data[0], "040x"), data[2]
                owners.append({"name": ancestor, "owner": owner, "wrapped_expiry": wrapped_expiry})
            if owners[-1]["owner"] != wallet:
                raise ValueError("requesting wallet has no current direct-label authority")
            if rpc.call("eth_getBlockByNumber", [hex(number), False]) != first:
                raise ValueError("chain changed during ENS authorization")
            snapshots.append({"name": name, "wallet": wallet, "owners": owners, "registrar_expiry": expiry[0]})
        if snapshots[0] != snapshots[1]:
            raise ValueError("ENS authority readers disagree")
        return {
            **snapshots[0],
            "chain_id": 1,
            "block_number": number,
            "block_hash": first["hash"],
            "checked_at": now,
            "pins": self.pins.model_dump(),
            "rules": "ensv1-direct-registry-or-wrapped-owner/v1",
        }


class AccessRequest(StrictModel):
    """One proof authorizes one resource and request commitment, never a session."""

    challenge_id: Digest
    signature: str = Field(pattern=r"^(?:0x)?[0-9a-fA-F]{130}$")


class ServiceIdentity(StrictModel):
    origin: str = Field(max_length=300)
    purpose: str = Field(default="protected-alpha-capsules/v1", max_length=80)

    @model_validator(mode="after")
    def exact_origin(self) -> ServiceIdentity:
        url = urlsplit(self.origin)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.path
            or url.query
            or url.fragment
        ):
            raise ValueError("service identity must be a credential-free exact HTTPS origin")
        return self


class ResourceAccess:
    """Keep challenge consumption and protected operation in the same journal transaction."""

    def __init__(self, journal: Journal, service: ServiceIdentity, authority: ENSAuthority) -> None:
        self.journal, self.service, self.authority = journal, service.model_copy(deep=True), authority

    def challenge(self, name: str, wallet: str, resource: str, action: str, request_digest: str) -> dict[str, Any]:
        name, wallet = direct_name(name), address(wallet)
        if (
            action not in {"discover", "retrieve", "invoke"}
            or not re.fullmatch(r"[0-9a-f]{64}", resource)
            or not re.fullmatch(r"[0-9a-f]{64}", request_digest)
        ):
            raise ValueError("unsupported resource authorization request")
        now = int(time.time())
        payload = {
            "service": self.service.model_dump(),
            "journal_identity": self.journal.identity,
            "name": name,
            "wallet": wallet,
            "resource": resource,
            "action": action,
            "request_digest": request_digest,
            "issued_at": now,
            "expires_at": now + 120,
            "nonce": secrets.token_hex(32),
        }
        ident = digest("flywheel-challenge", payload)
        message = (
            "AGI Alpha resource authorization v1\n"
            + canonical(payload).decode()
            + "\nNo spending, settlement, deployment or external-system authority."
        )
        with self.journal.transaction() as cx:
            try:
                issued = self.journal.latest("@flywheel-challenge-rate", cx)["issued"]
            except KeyError:
                issued = []
            issued = [item for item in issued if now - item["at"] < 60]
            if len(issued) >= 100 or sum(item["wallet"] == wallet for item in issued) >= 5:
                raise Conflict("challenge issuance rate reached; retry after expiry")
            self.journal.append(cx, "@flywheel-challenge-rate", {"issued": [*issued, {"at": now, "wallet": wallet}]})
            self.journal.append(
                cx, "@flywheel-challenge:" + ident, {"payload": payload, "message": message, "used": False}
            )
        return {"challenge_id": ident, "message": message, "expires_at": now + 120}

    def verify(self, proof: AccessRequest, resource: str, action: str, request_digest: str, cx: Any) -> dict[str, Any]:
        from eth_account import Account
        from eth_account.messages import encode_defunct

        proof = AccessRequest.model_validate(proof.model_dump())
        key = "@flywheel-challenge:" + proof.challenge_id
        record = self.journal.latest(key, cx)
        payload, now = record["payload"], int(time.time())
        expected_message = (
            "AGI Alpha resource authorization v1\n"
            + canonical(payload).decode()
            + "\nNo spending, settlement, deployment or external-system authority."
        )
        if digest("flywheel-challenge", payload) != proof.challenge_id or record["message"] != expected_message:
            raise ValueError("resource challenge commitment changed")
        if record["used"] or not payload["issued_at"] <= now < payload["expires_at"]:
            raise Conflict("resource challenge expired or already consumed")
        if (
            payload["service"] != self.service.model_dump()
            or payload["journal_identity"] != self.journal.identity
            or payload["resource"] != resource
            or payload["action"] != action
            or payload["request_digest"] != request_digest
        ):
            raise ValueError("proof is bound to another service, resource, purpose or request")
        if (
            address(Account.recover_message(encode_defunct(text=record["message"]), signature=proof.signature))
            != payload["wallet"]
        ):
            raise ValueError("wallet signature does not match this resource challenge")
        authority = self.authority.verify(payload["name"], payload["wallet"])
        if int(time.time()) >= payload["expires_at"]:
            raise Conflict("resource challenge expired during authority verification")
        self.journal.append(
            cx,
            key,
            {**self.journal.document(record), "used": True, "authorization": authority, "signature": proof.signature},
        )
        return authority
