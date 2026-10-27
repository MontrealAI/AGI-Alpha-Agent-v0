# SPDX-License-Identifier: Apache-2.0
"""Bind an executable research artifact to pinned existing lifecycle/trust interfaces."""

from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import re
import stat
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, cast

STUDY = Path(__file__).resolve().parents[1]
V3 = STUDY.parent / "agi-alpha-economic-construction-v3" / "integration" / "inheritance.py"
V3_SHA256 = "383e9f563bb2827c9792e9fc3fdd4a6d946e302962e205293861eef8ef156d05"
BUNDLE_SCHEMA = "inspection-evidence-executable-bundle/v1"
SCOPE = "local-computational-inspection-evidence-audit/v1"
DOMAIN = "opportunity-discovery-mission"
MODE = "LOCAL_EPHEMERAL_RESEARCH_AUTHORITY_NOT_LIVE_ENS"
MAX_BYTES = 2_000_000
HEX = re.compile(r"^[0-9a-f]{64}$")


def canonical(value: Any) -> bytes:
    """Encode finite JSON for all local bindings."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    """Hash a canonical local object."""
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path: Path) -> str:
    """Hash an ordinary file; artifact/source symlinks are excluded."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("expected ordinary file: " + str(path))
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_json(path: Path) -> Any:
    """Read a regular finite JSON object without silently repeated keys."""
    file_sha(path)

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for name, item in pairs:
            if name in value:
                raise ValueError("duplicate JSON key: " + name)
            value[name] = item
        return value

    result = json.loads(path.read_bytes(), object_pairs_hook=unique)
    canonical(result)
    return result


def save(path: Path, value: Any) -> None:
    """Create a finite JSON evidence artifact, refusing overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def inherited() -> Any:
    """Reuse v3 helpers and the unchanged, transitively pinned v1 source closure."""
    if file_sha(V3) != V3_SHA256:
        raise ValueError("preserved inheritance helper changed")
    name = "opportunity_v4_preserved_inheritance"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, V3)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load preserved inheritance helper")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    module.upstream().verify_sources()
    return module


def native_trust() -> Any:
    """Return the existing pinned native trust implementation."""
    return inherited().native_trust()


def upstream_runner() -> Any:
    """Load the pinned existing transport and A/B/C accounting conformance runner."""
    helper = inherited()
    name = "opportunity_v4_existing_transport"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, helper.PARENT / "run_integration.py")
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load existing transport replay")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


def safe_member(name: str) -> bool:
    """Admit only the declared instrument application closure, never task data."""
    path = PurePosixPath(name)
    forbidden = {"evaluation", "protected", "data", "inputs", "outputs", "results", "tests", "__pycache__"}
    return bool(
        not path.is_absolute()
        and len(path.parts) >= 2
        and path.parts[0] == "instrument"
        and all(part not in {"", ".", ".."} for part in path.parts)
        and not any(part.lower() in forbidden for part in path.parts)
        and path.suffix in {".py", ".json", ".md", ".txt", ".xsd"}
        and not path.name.lower().startswith(("test_", "oracle", "answer", "."))
        and "\\" not in name
    )


def scan_payload(data: bytes, protected: tuple[bytes, ...] = ()) -> None:
    """Reject registered protected strings and bounded credential patterns, not general DLP."""
    if any(value and value in data for value in protected):
        raise ValueError("registered protected material in retained source")
    patterns = (
        rb"sk-[A-Za-z0-9_-]{20,}",
        rb"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----",
        rb"(?i)\b(?:api_key|password|secret)\s*[:=]\s*[\"'][^\"'\s]{16,}[\"']",
    )
    if any(re.search(pattern, data) for pattern in patterns):
        raise ValueError("credential-pattern material excluded from retained source")


def dependency_inventory(declared: dict[str, str]) -> dict[str, Any]:
    """Hash installed declared distributions, including actual native binaries.

    Resolve mandatory installed transitive requirements and the local trust
    harness dependencies. Hash their actual files except bytecode and installer
    scripts outside the package directory. This is not a whole-OS attestation.
    """
    started = time.perf_counter()
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name

    roots = {canonicalize_name(name): version for name, version in declared.items()}
    for name in ("cryptography", "pydantic", "packaging"):
        roots.setdefault(name, importlib.metadata.version(name))
    pending = [(name, frozenset()) for name in roots]
    resolved: dict[str, str] = {}
    extras_seen: dict[str, frozenset[str]] = {}
    while pending:
        name, extras = pending.pop()
        name = canonicalize_name(name)
        if name in extras_seen and extras <= extras_seen[name]:
            continue
        active = extras_seen.get(name, frozenset()) | extras
        extras_seen[name] = active
        distribution = importlib.metadata.distribution(name)
        if name in roots and distribution.version != roots[name]:
            raise ValueError("runtime dependency version changed: " + name)
        resolved[name] = distribution.version
        for raw in distribution.requires or []:
            requirement = Requirement(raw)
            if requirement.marker is not None and not any(
                requirement.marker.evaluate({"extra": extra}) for extra in {"", *active}
            ):
                continue
            version = importlib.metadata.version(requirement.name)
            if requirement.specifier and version not in requirement.specifier:
                raise ValueError("installed dependency does not satisfy declared requirement: " + str(requirement))
            pending.append((requirement.name, frozenset(requirement.extras)))
    packages: dict[str, Any] = {}
    total_bytes = 0
    for name, expected in sorted(resolved.items()):
        distribution = importlib.metadata.distribution(name)
        if distribution.version != expected:
            raise ValueError("runtime dependency version changed: " + name)
        rows = []
        excluded = []
        if distribution.files is None:
            raise ValueError("dependency has no installed file inventory: " + name)
        for entry in sorted(distribution.files, key=str):
            relative = str(entry)
            if "__pycache__" in entry.parts or entry.suffix == ".pyc" or ".." in entry.parts:
                excluded.append(relative)
                continue
            path = Path(distribution.locate_file(entry))
            if not path.is_file():
                raise ValueError("declared dependency file missing: " + name + ":" + relative)
            resolved = path.resolve()
            size = resolved.stat().st_size
            rows.append({"path": relative, "bytes": size, "sha256": file_sha(resolved)})
            total_bytes += size
        packages[name] = {
            "version": distribution.version,
            "files": len(rows),
            "bytes": sum(row["bytes"] for row in rows),
            "content_sha256": digest(rows),
            "excluded_installer_scripts_or_bytecode": excluded,
        }
    executable = Path(sys.executable).resolve()
    identity = {
        "python": {
            "version": sys.version,
            "implementation": sys.implementation.name,
            "binary_sha256": file_sha(executable),
        },
        "declared_roots": roots,
        "distributions": packages,
        "scope": "installed transitive package closure; separately provisioned, not payload; OS/stdlib not image-attested",
    }
    return {"identity": identity, "seconds": time.perf_counter() - started, "hashed_bytes": total_bytes}


def validate_closure(specification: dict[str, Any]) -> None:
    """Require explicit frozen files, schema, policy and dependency identities."""
    required = {"schema", "files", "dependencies", "schema_identity", "policy_identity", "entrypoint", "provenance"}
    optional = {
        "instrument_version",
        "frozen_at_utc",
        "python",
        "generic_identity_sha256",
        "runtime_files_total_bytes",
        "confirmation_seen",
    }
    if not required <= set(specification) <= required | optional:
        raise ValueError("unsupported or incomplete runtime closure declaration")
    if specification["schema"] != "inspection-evidence-closure/v1":
        raise ValueError("unsupported or incomplete runtime closure declaration")
    files = specification["files"]
    if not isinstance(files, dict) or not files or any(not safe_member(name) for name in files):
        raise ValueError("runtime closure contains undeclared kind or unsafe member")
    if any(not isinstance(value, str) or not HEX.fullmatch(value) for value in files.values()):
        raise ValueError("runtime closure requires exact source hashes")
    if specification["entrypoint"] != "instrument/cli.py" or specification["entrypoint"] not in files:
        raise ValueError("only the fixed audit CLI may execute")
    if not isinstance(specification["dependencies"], dict) or not specification["dependencies"]:
        raise ValueError("runtime dependencies must be explicitly declared")
    if not specification["schema_identity"] or not specification["policy_identity"]:
        raise ValueError("schema and policy identities required")


def pack_bundle(
    source: Path, specification: dict[str, Any], environment: dict[str, Any], output: Path
) -> dict[str, Any]:
    """Pack the complete custom application closure with separately pinned dependencies."""
    validate_closure(specification)
    contents: dict[str, bytes] = {}
    for name, expected in sorted(specification["files"].items()):
        path = source / name
        if file_sha(path) != expected:
            raise ValueError("frozen runtime source changed: " + name)
        contents[name] = path.read_bytes()
        scan_payload(contents[name])
    if sum(map(len, contents.values())) > MAX_BYTES:
        raise ValueError("uncompressed retained code exceeds existing bridge bound")
    manifest = {
        "schema": BUNDLE_SCHEMA,
        "closure": specification,
        "dependency_identity": environment,
        "scope": SCOPE,
        "authority": "none inherited; independently configured current local research grant required",
        "data": "public mission sources remain outside payload and are separately hash-bound",
        "evaluation": "protected tasks and independent oracle excluded",
    }
    contents["MANIFEST.json"] = canonical(manifest)
    scan_payload(contents["MANIFEST.json"])
    if sum(map(len, contents.values())) > MAX_BYTES:
        raise ValueError("complete expanded payload exceeds existing bridge bound")
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(contents.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 27, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    if output.stat().st_size > MAX_BYTES:
        raise ValueError("payload exceeds existing two-megabyte bridge limit")
    return manifest


def unpack_bundle(bundle: Path, destination: Path, expected_sha: str) -> dict[str, Any]:
    """Verify all members before extracting into a new recipient directory."""
    if file_sha(bundle) != expected_sha or bundle.stat().st_size > MAX_BYTES:
        raise ValueError("received bundle size or digest mismatch")
    with zipfile.ZipFile(bundle) as archive:
        infos = archive.infolist()
        names = [row.filename for row in infos]
        if len(names) != len(set(names)) or "MANIFEST.json" not in names:
            raise ValueError("duplicate member or missing bundle manifest")
        if any(name != "MANIFEST.json" and not safe_member(name) for name in names):
            raise ValueError("untrusted or unsafe bundle member")
        if any(stat.S_IFMT(row.external_attr >> 16) != stat.S_IFREG for row in infos):
            raise ValueError("nonregular bundle member")
        if sum(row.file_size for row in infos) > MAX_BYTES:
            raise ValueError("expanded payload exceeds bridge bound")
        contents = {name: archive.read(name) for name in names}
    scan_payload(contents["MANIFEST.json"])
    manifest = json.loads(contents["MANIFEST.json"])
    specification = manifest.get("closure", {})
    validate_closure(specification)
    if manifest.get("schema") != BUNDLE_SCHEMA or manifest.get("scope") != SCOPE:
        raise ValueError("unsupported bundle schema or scope")
    if set(contents) != set(specification["files"]) | {"MANIFEST.json"}:
        raise ValueError("payload does not contain its exact declared closure")
    for name, expected in specification["files"].items():
        if hashlib.sha256(contents[name]).hexdigest() != expected:
            raise ValueError("source identity mismatch inside payload: " + name)
        scan_payload(contents[name])
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in contents.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return cast(dict[str, Any], manifest)


def verify_installed_bundle(root: Path, expected: dict[str, Any]) -> dict[str, Any]:
    """Recheck current code, schemas, policy and installed dependency bytes."""
    manifest = load_json(root / "MANIFEST.json")
    if manifest != expected:
        raise ValueError("recipient bundle manifest changed")
    specification = manifest["closure"]
    validate_closure(specification)
    for name, expected_sha in specification["files"].items():
        if file_sha(root / name) != expected_sha:
            raise ValueError("recipient source changed: " + name)
    actual = {
        str(path.relative_to(root)) for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts
    }
    if actual != set(specification["files"]) | {"MANIFEST.json"}:
        raise ValueError("recipient application contains an undeclared file")
    inventory = dependency_inventory(specification["dependencies"])
    if inventory["identity"] != manifest["dependency_identity"]:
        raise ValueError("recipient installed dependency content changed")
    return inventory


def bind_request(path: Path) -> dict[str, Any]:
    """Bind full current request semantics and externally provided source bytes."""
    request = load_json(path)
    if not isinstance(request, dict) or not isinstance(request.get("mission"), dict):
        raise ValueError("request must declare current mission")
    if not isinstance(request.get("assets"), dict):
        raise ValueError("request must declare source assets")
    assets = {}
    for role, row in sorted(request["assets"].items()):
        if not isinstance(row, dict) or not HEX.fullmatch(str(row.get("sha256", ""))):
            raise ValueError("source requires exact hash")
        source = path.parent / row["path"]
        actual = file_sha(source)
        if actual != row["sha256"]:
            raise ValueError("current mission source changed: " + role)
        assets[role] = {"sha256": actual, "bytes": source.stat().st_size, "path": str(source.resolve())}
    return {
        "request_sha256": digest(request),
        "request_file_sha256": file_sha(path),
        "mission": request["mission"],
        "assets": assets,
        "source_access": "separate filesystem sources; read-only application use checked by pre/post digests",
    }


def grant_payload(identity: dict[str, Any], request_binding: dict[str, Any], nonce: str, now: int) -> dict[str, Any]:
    """Describe a single computation, with no manufacturing or part-release right."""
    return {
        "identity": digest(identity),
        "request_binding": digest(request_binding),
        "recipient": "lyra.agent.agi.eth",
        "nonce": nonce,
        "not_before": now - 1,
        "expires": now + 3600,
        "right": "run-research-evidence-audit",
        "scope": SCOPE,
        "mode": MODE,
    }


def check_grant(
    signed: dict[str, Any], context: dict[str, Any], identity: dict[str, Any], request: dict[str, Any], now: int
) -> dict[str, Any]:
    """Use native Ed25519/roles and recheck current mission separately from qualification."""
    native = native_trust()
    if context.get("mode") != MODE or context.get("recipient") != "lyra.agent.agi.eth":
        raise ValueError("unsupported local authority context")
    registry = native.TrustRegistry(
        {"local-controller": native.TrustAnchor(context["public_controller_key"], frozenset({"controller"}))}
    )
    for principal in context.get("revoked", []):
        registry.revoke(principal)
    payload = registry.verify(native.SignedEnvelope.model_validate(signed), DOMAIN, "controller")
    expected = {"identity", "request_binding", "recipient", "nonce", "not_before", "expires", "right", "scope", "mode"}
    if set(payload) != expected or payload["mode"] != MODE or payload["scope"] != SCOPE:
        raise ValueError("unsupported signed research authority terms")
    if payload["identity"] != digest(identity) or payload["request_binding"] != digest(request):
        raise ValueError("authority does not bind complete current artifact and mission")
    if payload["recipient"] != context["recipient"] or payload["right"] != "run-research-evidence-audit":
        raise ValueError("current recipient or computation right absent")
    if any(type(payload[key]) is not int for key in ("not_before", "expires")) or type(now) is not int:
        raise ValueError("authority times require integers")
    if not payload["not_before"] <= now < payload["expires"]:
        raise ValueError("current mission authority expired or not yet valid")
    if not isinstance(payload["nonce"], str) or not payload["nonce"]:
        raise ValueError("one-use authority nonce required")
    return cast(dict[str, Any], payload)
