# SPDX-License-Identifier: Apache-2.0
"""Out-of-band principal trust and independently retained journal checkpoints."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import BaseModel, ConfigDict, Field

from .protocol import canonical, digest


class SignedEnvelope(BaseModel):
    """Authenticate one typed protocol record; never carry a trust root."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    domain: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    principal: str = Field(min_length=1, max_length=160)
    payload: dict[str, Any]
    signature: str = Field(min_length=88, max_length=88)


@dataclass(frozen=True)
class TrustAnchor:
    """Operator-installed identity and roles, outside incoming evidence."""

    public_key: str
    roles: frozenset[str]
    provenance: Literal["local", "independent"] = "local"
    independence_attestation: str = ""

    def __post_init__(self) -> None:
        if len(bytes.fromhex(self.public_key)) != 32:
            raise ValueError("trust key must be a raw Ed25519 public key")
        if self.provenance == "independent" and not self.independence_attestation:
            raise ValueError("independent trust requires an out-of-band attestation")


class TrustRegistry:
    """Trust supplied by the operator; imported objects cannot extend it."""

    def __init__(self, anchors: dict[str, TrustAnchor]) -> None:
        self._anchors = dict(anchors)
        self._revoked: set[str] = set()

    def revoke(self, principal: str) -> None:
        """Immediately remove a principal's eligibility for future actions."""
        self._revoked.add(principal)

    def anchor(self, principal: str, role: str) -> TrustAnchor:
        """Require a currently trusted principal with this exact role."""
        anchor = self._anchors.get(principal)
        if anchor is None or principal in self._revoked or role not in anchor.roles:
            raise ValueError("principal is not currently trusted for the required role")
        return anchor

    def verify(self, envelope: SignedEnvelope, domain: str, role: str) -> dict[str, Any]:
        """Verify a signature using only the independently configured registry."""
        if envelope.domain != domain:
            raise ValueError("signed record domain mismatch")
        anchor = self.anchor(envelope.principal, role)
        commitment = digest(domain, {"principal": envelope.principal, "payload": envelope.payload})
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(anchor.public_key)).verify(
                base64.b64decode(envelope.signature, validate=True), bytes.fromhex(commitment)
            )
        except (InvalidSignature, ValueError) as exc:
            raise ValueError("record signature is invalid") from exc
        return envelope.payload


def sign_record(
    key: Ed25519PrivateKey, principal: str, domain: str, record: BaseModel | dict[str, Any]
) -> SignedEnvelope:
    """Sign a typed record without conferring trust on its signer."""
    payload = record.model_dump(mode="json") if isinstance(record, BaseModel) else record
    canonical(payload)
    commitment = digest(domain, {"principal": principal, "payload": payload})
    return SignedEnvelope(
        domain=domain,
        principal=principal,
        payload=payload,
        signature=base64.b64encode(key.sign(bytes.fromhex(commitment))).decode("ascii"),
    )


def local_principals() -> tuple[TrustRegistry, dict[str, Ed25519PrivateKey]]:
    """Create explicitly local rehearsal roles; these are never independent proof."""
    roles = {
        "local-controller": {"controller", "admission", "authority", "acceptance", "control", "worker"},
        "local-producer": {"producer", "worker"},
        "local-verifier": {"verifier", "acceptance", "worker"},
    }
    keys = {principal: Ed25519PrivateKey.generate() for principal in roles}
    registry = TrustRegistry(
        {
            principal: TrustAnchor(
                key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset(roles[principal])
            )
            for principal, key in keys.items()
        }
    )
    return registry, keys


@dataclass(frozen=True)
class JournalCheckpoint:
    """A checkpoint supplied separately from a portable package or local history."""

    identity: str
    sequence: int
    head: str

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or not 1 <= self.sequence <= 2**53 - 1:
            raise ValueError("checkpoint sequence must be a bounded positive integer")
        if (
            not isinstance(self.head, str)
            or len(self.head) != 64
            or any(char not in "0123456789abcdef" for char in self.head)
        ):
            raise ValueError("checkpoint head must be a lowercase SHA-256 digest")
        if not isinstance(self.identity, str) or not self.identity.startswith("urn:agialpha:ed25519:"):
            raise ValueError("checkpoint identity must be an explicitly pinned journal key")

    def verify(self, journal: Any) -> None:
        """Detect truncation to an otherwise correctly signed historical state."""
        checked = journal.verify()
        if checked["identity"] != self.identity or checked["events"] < self.sequence:
            raise ValueError("journal is older than or unrelated to the retained checkpoint")
        with journal.transaction() as cx:
            row = cx.execute("SELECT hash FROM events WHERE seq=?", (self.sequence,)).fetchone()
            if row is None or row[0] != self.head:
                raise ValueError("journal diverges from independently retained checkpoint")

    @classmethod
    def capture(cls, journal: Any) -> JournalCheckpoint:
        """Return an anchor for independent retention; local retention adds no assurance."""
        checked = journal.verify()
        return cls(checked["identity"], checked["events"], checked["head"])


def retained_local_principals(directory: str | Any) -> tuple[TrustRegistry, dict[str, Ed25519PrivateKey]]:
    """Keep local rehearsal roles private; refuse partial or changed credential state."""
    import os
    from pathlib import Path

    from cryptography.hazmat.primitives.serialization import NoEncryption, PrivateFormat

    from ..store import private_write, restrict_access
    from .protocol import safe_json_loads

    root = Path(directory)
    if root.is_symlink():
        raise ValueError("principal directory must not be a symbolic link")
    registry, fresh = local_principals()
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=False)
    except FileExistsError:
        if not root.is_dir():
            raise ValueError("principal destination is not a directory")
    else:
        restrict_access(root)
        public_keys = {}
        for principal, generated in fresh.items():
            private_write(
                root / (principal + ".key"),
                generated.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()),
            )
            public_keys[principal] = generated.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        private_write(root / "principals.json", canonical({"scope": "local-rehearsal", "public_keys": public_keys}))
    manifest_path = root / "principals.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("local principal state is incomplete; do not silently replace role keys")
    manifest = safe_json_loads(manifest_path.read_bytes())
    if set(manifest) != {"scope", "public_keys"} or manifest["scope"] != "local-rehearsal":
        raise ValueError("invalid local rehearsal credential manifest")
    if set(manifest["public_keys"]) != set(fresh):
        raise ValueError("local role key inventory changed")
    keys: dict[str, Ed25519PrivateKey] = {}
    anchors: dict[str, TrustAnchor] = {}
    for principal in fresh:
        path = root / (principal + ".key")
        if path.is_symlink() or not path.is_file():
            raise ValueError("local principal state is incomplete; missing role key")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            data = stream.read(33)
        if len(data) != 32:
            raise ValueError("retained principal key is malformed")
        key = Ed25519PrivateKey.from_private_bytes(data)
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        if public != manifest["public_keys"][principal]:
            raise ValueError("retained role key changed outside the local credential inventory")
        keys[principal] = key
        role = (
            "controller"
            if principal == "local-controller"
            else "producer" if principal == "local-producer" else "verifier"
        )
        original = registry.anchor(principal, role)
        anchors[principal] = TrustAnchor(public, original.roles)
    return TrustRegistry(anchors), keys


def validate_local_principal_files(files: dict[str, bytes]) -> None:
    """Validate a complete private recovery key set without generating or installing keys."""
    from .protocol import safe_json_loads

    principals = {"local-controller", "local-producer", "local-verifier"}
    if set(files) != {"principals.json", *(principal + ".key" for principal in principals)}:
        raise ValueError("private recovery requires the complete exact local principal file set")
    manifest = safe_json_loads(files["principals.json"], max_bytes=16_384)
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"scope", "public_keys"}
        or manifest["scope"] != "local-rehearsal"
        or not isinstance(manifest["public_keys"], dict)
        or set(manifest["public_keys"]) != principals
    ):
        raise ValueError("private recovery local principal inventory is invalid")
    public_keys: set[str] = set()
    for principal in principals:
        raw = files[principal + ".key"]
        if len(raw) != 32:
            raise ValueError("private recovery role key must contain exactly 32 raw bytes")
        key = Ed25519PrivateKey.from_private_bytes(raw)
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        if public != manifest["public_keys"][principal] or public in public_keys:
            raise ValueError("private recovery role key does not match its distinct public inventory")
        public_keys.add(public)


def validate_external_trust_bytes(data: bytes) -> TrustRegistry:
    """Validate an explicitly installed public trust registry for private disaster recovery."""
    from .protocol import safe_json_loads

    value = safe_json_loads(data, max_bytes=131_072)
    if not isinstance(value, dict) or set(value) != {"schema_version", "principals"}:
        raise ValueError("destination trust requires schema_version and principals")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or not isinstance(value["principals"], dict)
    ):
        raise ValueError("unsupported destination trust schema")
    if not 1 <= len(value["principals"]) <= 64:
        raise ValueError("destination trust registry must contain 1 to 64 principals")
    roles = {"controller", "admission", "authority", "acceptance", "control", "producer", "worker", "verifier"}
    anchors = {}
    for principal, entry in value["principals"].items():
        if not isinstance(principal, str) or not principal or len(principal) > 128:
            raise ValueError("invalid destination trust principal")
        if not isinstance(entry, dict) or set(entry) != {
            "public_key",
            "roles",
            "provenance",
            "independence_attestation",
        }:
            raise ValueError("destination trust anchor has unknown or missing fields")
        if (
            not isinstance(entry["roles"], list)
            or not entry["roles"]
            or not all(isinstance(role, str) and role in roles for role in entry["roles"])
            or len(set(entry["roles"])) != len(entry["roles"])
        ):
            raise ValueError("destination trust anchor contains unsupported or duplicate roles")
        if entry["provenance"] not in {"local", "independent"} or not isinstance(
            entry["independence_attestation"], str
        ):
            raise ValueError("destination trust provenance is invalid")
        if not isinstance(entry["public_key"], str) or len(entry["public_key"]) != 64:
            raise ValueError("destination public key must be raw hex")
        anchors[principal] = TrustAnchor(
            entry["public_key"], frozenset(entry["roles"]), entry["provenance"], entry["independence_attestation"]
        )
    return TrustRegistry(anchors)
