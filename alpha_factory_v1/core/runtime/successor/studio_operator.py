# SPDX-License-Identifier: Apache-2.0
"""Local Studio operations with installed trust and retained, immutable requests."""

from __future__ import annotations

import re
import secrets
import hashlib
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import Field, model_validator

from ..store import Conflict, Journal, _private_recovery_bytes, private_write
from .ascension import MarketContext, MarketReader, address, hash32, list_settlements
from .jobs import JobDispatcher, compile_jobs
from .protocol import (
    UTC,
    ExecutionAuthorization,
    Identifier,
    JobContract,
    JobDependency,
    JobGraph,
    Institution,
    MissionConstitution,
    StrictModel,
    canonical,
    digest,
    safe_json_loads,
)
from .state import SuccessorStore
from .trust import SignedEnvelope, sign_record, validate_external_trust_bytes

MAX_INPUT_BYTES = 512 * 1024
PREFIX = "@ascension-studio:"


def approval_slot(principal: str) -> str:
    """Use a dedicated preinstalled private credential slot, never a general file oracle."""
    return "studio-approval/" + hashlib.sha256(principal.encode("utf-8")).hexdigest() + ".token"


class OperatorProfile(StrictModel):
    """One deliberately installed project/cycle context; imports cannot alter it."""

    project_id: Identifier
    cycle_id: Identifier
    plan_index: int = Field(ge=0, le=127)
    institution_id: Identifier
    mission_id: Identifier
    producer: Identifier
    acceptance_owner: Identifier
    valid_until: UTC
    market_context: MarketContext
    rpc_url: str = Field(min_length=1, max_length=2048)
    companion_jobs: list[JobContract] = Field(min_length=6, max_length=255)
    edges: list[JobDependency] = Field(default_factory=list, max_length=1024)

    @model_validator(mode="after")
    def validate_profile(self) -> OperatorProfile:
        """Allow only explicit HTTPS nodes or a loopback disposable development node."""
        url = urlsplit(self.rpc_url)
        local = url.hostname in {"127.0.0.1", "localhost", "::1"}
        if not url.hostname or url.username or url.password or url.fragment:
            raise ValueError("operator RPC URL is invalid")
        if url.scheme != "https" and not (url.scheme == "http" and local and self.market_context.chain_id != "1"):
            raise ValueError("operator RPC requires HTTPS except on a local development chain")
        if {job.family for job in self.companion_jobs} != {
            "constitution",
            "evidence",
            "formation",
            "challenge",
            "admission",
            "renewal",
        }:
            raise ValueError("operator profile must explicitly supply the six companion job families")
        return self


class OperatorTemplate(StrictModel):
    """Installed policy for explicit browser pairing of new bounded work records."""

    template_id: Identifier
    controller: Identifier
    producer: Identifier
    acceptance_owner: Identifier
    valid_until: UTC
    market_context: MarketContext
    rpc_url: str = Field(min_length=1, max_length=2048)
    max_calls: int = Field(ge=1, le=100)

    @model_validator(mode="after")
    def read_only_context(self) -> OperatorTemplate:
        url = urlsplit(self.rpc_url)
        local = url.hostname in {"127.0.0.1", "localhost", "::1"}
        if (
            not url.hostname
            or url.username
            or url.password
            or url.fragment
            or (url.scheme != "https" and not (url.scheme == "http" and local and self.market_context.chain_id != "1"))
        ):
            raise ValueError("template RPC requires a valid HTTPS node or local non-mainnet development node")
        if self.market_context.mark is None:
            raise ValueError("Studio templates require a complete pinned MARK and seed context")
        return self


class OperatorSigner(StrictModel):
    """An administrator-installed role signer, protected by a distinct role token."""

    principal: Identifier
    key_file: str = Field(min_length=1, max_length=200)
    approval_token_file: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def private_slots(self) -> OperatorSigner:
        for name in (self.key_file, self.approval_token_file):
            if (
                Path(name).is_absolute()
                or not re.fullmatch(r"[A-Za-z0-9_./-]+", name)
                or any(part in {".", ".."} for part in name.split("/"))
            ):
                raise ValueError("signer slots must be explicit relative private file paths")
        if self.approval_token_file != approval_slot(self.principal) or self.key_file.startswith("studio-approval/"):
            raise ValueError("role approval requires its dedicated independently preinstalled token slot")
        return self


class OperatorConfig(StrictModel):
    """Versioned local installation configuration, never an incoming work format."""

    schema_name: Literal["agialpha.ascension.studio-operator.v1"] = Field(alias="schema")
    profiles: list[OperatorProfile] = Field(default_factory=list, max_length=64)
    templates: list[OperatorTemplate] = Field(default_factory=list, max_length=32)
    signers: list[OperatorSigner] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def unique_profiles(self) -> OperatorConfig:
        pairs = [(profile.project_id, profile.cycle_id, profile.plan_index) for profile in self.profiles]
        if len(set(pairs)) != len(pairs):
            raise ValueError("each project, cycle and plan index must have one installed profile")
        if not self.profiles and not self.templates:
            raise ValueError("install an explicit profile or pairing template")
        if len({item.template_id for item in self.templates}) != len(self.templates):
            raise ValueError("installed template IDs must be unique")
        if len({item.principal for item in self.signers}) != len(self.signers):
            raise ValueError("each principal must have one installed signer")
        return self


class ReadOnlyRPC:
    """Bounded RPC transport with no transaction, wallet or arbitrary method access."""

    def __init__(self, url: str) -> None:
        self.url = url

    def __call__(self, method: str, params: list[Any]) -> Any:
        if method not in {
            "eth_chainId",
            "eth_getCode",
            "eth_call",
            "eth_getTransactionReceipt",
            "eth_getBlockByNumber",
            "eth_getLogs",
            "eth_blockNumber",
        }:
            raise ValueError("only supported read-only RPC methods are available")
        with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
            with client.stream(
                "POST", self.url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            ) as response:
                response.raise_for_status()
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 2_000_000:
                        raise ValueError("RPC response exceeds its bounded limit")
        body = safe_json_loads(bytes(raw))
        if not isinstance(body, dict) or body.get("id") != 1 or body.get("jsonrpc") != "2.0":
            raise ValueError("invalid RPC response")
        if "error" in body or "result" not in body:
            raise ValueError("RPC did not return a successful read")
        return body["result"]


def _read(path: Path, limit: int = MAX_INPUT_BYTES) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("required operator configuration is absent, linked or oversized")
    return path.read_bytes()


def _installed(journal: Journal) -> tuple[OperatorConfig, SuccessorStore, str]:
    config = OperatorConfig.model_validate(safe_json_loads(_read(journal.root / "studio-operator.json")))
    trust_bytes = _read(journal.root / "successor-trust.json", 131_072)
    trust = validate_external_trust_bytes(trust_bytes)
    configuration_digest = digest("studio-operator-trust", safe_json_loads(trust_bytes))
    return config, SuccessorStore(journal, trust), configuration_digest


def _key(request_digest: str) -> str:
    if not isinstance(request_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", request_digest):
        raise ValueError("request digest is invalid")
    return PREFIX + request_digest


def status(journal: Journal) -> dict[str, Any]:
    """Describe prerequisites without contacting a network or exposing RPC credentials."""
    result: dict[str, Any] = {
        "configured": False,
        "identity": journal.identity,
        "public_key": journal.public,
        "control": journal.latest("@control")["state"],
        "transport": "same-origin local API; portable files for hosted Studio",
        "profiles": [],
        "templates": [],
        "local_signers": [],
        "setup_roles": [],
        "scope": "Bounded native computation; no wallet signing, transaction broadcast or automatic adoption.",
    }
    try:
        trust_bytes = _read(journal.root / "successor-trust.json", 131_072)
        validate_external_trust_bytes(trust_bytes)
        result["setup_roles"] = [
            {
                "principal": principal,
                "roles": item["roles"],
                "public_key": item["public_key"],
                "approval_token_file": approval_slot(principal),
            }
            for principal, item in safe_json_loads(trust_bytes)["principals"].items()
        ]
    except (OSError, ValueError):
        pass
    try:
        config, store, _ = _installed(journal)
        for template in config.templates:
            store.trust.anchor(template.controller, "controller")
            store.trust.anchor(template.producer, "producer")
            store.trust.anchor(template.acceptance_owner, "acceptance")
            result["templates"].append(
                {key: value for key, value in template.model_dump(mode="json").items() if key != "rpc_url"}
            )
        result["local_signers"] = [signer.principal for signer in config.signers]
        for profile in config.profiles:
            institution = store.read(profile.institution_id)
            controller = institution["institution"]["controller"]
            store.trust.anchor(controller, "controller")
            store.trust.anchor(profile.producer, "producer")
            store.trust.anchor(profile.acceptance_owner, "acceptance")
            if institution["institution"]["constitution"]["mission_id"] != profile.mission_id:
                raise ValueError("operator profile mission differs from its institution")
            result["profiles"].append(
                {
                    "project_id": profile.project_id,
                    "cycle_id": profile.cycle_id,
                    "plan_index": profile.plan_index,
                    "institution_id": profile.institution_id,
                    "controller": controller,
                    "acceptance_owner": profile.acceptance_owner,
                    "stopped": institution["stopped"],
                    "market_context": profile.market_context.model_dump(mode="json"),
                }
            )
        result["configured"] = True
        result["prerequisite"] = "Installed profiles are ready. Review the work, then approve a separate grant."
    except (OSError, ValueError, KeyError):
        result["profiles"] = []
        result["templates"] = []
        result["local_signers"] = []
        result["prerequisite"] = (
            "An operator must install studio-operator.json and successor-trust.json in the initialized agent home, "
            "with a retained institution, explicit companion jobs, controller, worker and acceptance roles. "
            "Work files cannot install this configuration. Open the setup guide below."
        )
    return result


def records(journal: Journal) -> list[dict[str, Any]]:
    """List project history without returning private work or grants in the archive."""
    with journal.transaction() as cx:
        identifiers = [
            row[0]
            for row in cx.execute(
                "SELECT DISTINCT mission FROM events WHERE mission LIKE ? ORDER BY mission", (PREFIX + "%",)
            )
        ]
        current = [journal.latest(ident, cx) for ident in identifiers]
    return [
        {
            **{key: record[key] for key in ("request_digest", "project_id", "cycle_id", "state", "revision")},
            "plan_index": record["request"]["plan_index"],
            "family": record["request"]["work_spec"]["family"],
        }
        for record in current
    ]


def show(journal: Journal, request_digest: str) -> dict[str, Any]:
    """Return the exact retained state; retrieval never dispatches a run."""
    return journal.latest(_key(request_digest))


def export(journal: Journal, request_digest: str) -> dict[str, Any]:
    """Export the retained signed result without rerunning or reserializing its artifact."""
    record = show(journal, request_digest)
    return _retained_result(journal, record)


def _retained_result(journal: Journal, record: dict[str, Any]) -> dict[str, Any]:
    from .studio import retained_work, verify_work_result

    result = record.get("result")
    if result is None:
        if "binding" not in record:
            raise Conflict("no delivered result yet; export the prepared terms or grant request instead")
        try:
            result = retained_work(journal, record["request"], record["binding"]["digest"])
        except KeyError as exc:
            raise Conflict(
                "no completed native result was retained; the controller must resolve interrupted work"
            ) from exc
    verify_work_result(record["request"], result, public_key=journal.public)
    return result


def _review_requests(journal: Journal, record: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    from .studio import acceptance_request

    return {
        decision: {
            "schema": "agialpha.ascension.studio-review-request.v1",
            "domain": "job-acceptance",
            "principal": record["prepared"]["job_contract"]["acceptance_owner"],
            "request_digest": record["request_digest"],
            "payload": acceptance_request(record["request"], result, public_key=journal.public, accepted=accepted),
            "instruction": "The installed acceptance owner must review and separately sign this exact local decision.",
        }
        for decision, accepted in (("accept", True), ("reject", False))
    }


def export_settlement(journal: Journal, request_digest: str) -> dict[str, Any]:
    """Return the preserved signed journal bytes for this exact settlement."""
    record = show(journal, request_digest)
    if "settlement" not in record:
        raise Conflict("there is no verified settlement to export")
    institution_id = record["prepared"]["job_contract"]["institution_id"]
    matches = [
        entry for entry in list_settlements(journal, institution_id) if entry["settlement"] == record["settlement"]
    ]
    if len(matches) != 1:
        raise ValueError("exact signed settlement is unavailable")
    return matches[0]


def _profile(config: OperatorConfig, request: dict[str, Any], journal: Journal) -> OperatorProfile:
    matches = [
        profile
        for profile in config.profiles
        if profile.project_id == request.get("project_id")
        and profile.cycle_id == request.get("cycle_id")
        and profile.plan_index == request.get("plan_index")
    ]
    if matches:
        return matches[0]
    try:
        paired = journal.latest(_pair_key(request))
    except KeyError as exc:
        raise ValueError("pair this work using an installed template or install its exact operator profile") from exc
    templates = [template for template in config.templates if template.template_id == paired["template_id"]]
    if len(templates) != 1 or digest("studio-operator-template", templates[0]) != paired["template_digest"]:
        raise Conflict("the installed pairing template changed or was removed")
    if paired["request_digest"] != digest("ascension-studio-request", request):
        raise Conflict("this paired plan index already belongs to different exact work")
    validated_profile: OperatorProfile = OperatorProfile.model_validate(paired["profile"])
    return validated_profile


def _pair_key(request: dict[str, Any]) -> str:
    return "@ascension-studio-profile:" + digest(
        "studio-profile", {key: request[key] for key in ("project_id", "cycle_id", "plan_index")}
    )


def _pair(journal: Journal, config: OperatorConfig, store: SuccessorStore, payload: dict[str, Any]) -> dict[str, Any]:
    from . import studio

    _fields(payload, {"request_json", "template_id", "seed_id", "confirm"})
    if payload["confirm"] is not True:
        raise ValueError("explicit pairing confirmation is required")
    request = studio.validate_request(safe_json_loads(payload["request_json"], max_bytes=MAX_INPUT_BYTES))
    templates = [template for template in config.templates if template.template_id == payload["template_id"]]
    if len(templates) != 1:
        raise ValueError("choose an installed operator pairing template")
    template = templates[0]
    for principal, role in (
        (template.controller, "controller"),
        (template.producer, "producer"),
        (template.acceptance_owner, "acceptance"),
    ):
        store.trust.anchor(principal, role)
    request_hash = digest("ascension-studio-request", request)
    institution_id, mission_id = "studio-" + request_hash[:32], "mission-" + request_hash[:32]
    prepared = studio.prepare_work(
        request,
        institution_id=institution_id,
        mission_id=mission_id,
        producer=template.producer,
        acceptance_owner=template.acceptance_owner,
        valid_until=template.valid_until,
    )
    terms = JobContract.model_validate(prepared["job_contract"])
    companions = [
        terms.model_copy(
            update={
                "job_id": "companion-" + family + "-" + request_hash[:16],
                "family": family,
                "goal": "Pending "
                + family
                + " obligation for this exact bounded work; requires separate attributable completion",
                "outputs": {"record": family + "-record-v1"},
                "allowed_tools": [],
                "acceptance_conditions": [
                    "Separately review this lifecycle obligation; preparation is not completion."
                ],
            }
        )
        for family in ("constitution", "evidence", "formation", "challenge", "admission", "renewal")
    ]
    context = MarketContext.model_validate(
        {**template.market_context.model_dump(mode="json"), "seed_id": payload["seed_id"]}
    )
    profile = OperatorProfile(
        project_id=request["project_id"],
        cycle_id=request["cycle_id"],
        plan_index=request["plan_index"],
        institution_id=institution_id,
        mission_id=mission_id,
        producer=template.producer,
        acceptance_owner=template.acceptance_owner,
        valid_until=template.valid_until,
        market_context=context,
        rpc_url=template.rpc_url,
        companion_jobs=companions,
    )
    document = {
        "profile": profile.model_dump(mode="json"),
        "template_id": template.template_id,
        "template_digest": digest("studio-operator-template", template),
        "request_digest": request_hash,
    }
    with journal.transaction() as cx:
        try:
            existing = journal.latest(_pair_key(request), cx)
        except KeyError:
            journal.append(cx, _pair_key(request), document)
        else:
            if Journal.document(existing) != document:
                raise Conflict("this work is already paired with a different explicit profile")
    store.create_institution(
        Institution(
            id=institution_id,
            controller=template.controller,
            constitution=MissionConstitution(
                mission_id=mission_id,
                owner=template.controller,
                objective=terms.goal,
                scope="explicitly authorized fixed local computation; all companion obligations remain pending",
                authority_ceiling="sandbox",
                prohibited_actions=["wallet-signing", "automatic-admission", "host-code", "network"],
            ),
        ),
        {"calls": template.max_calls},
    )
    return operate(journal, "prepare", {"request": request})


def _sign(
    journal: Journal,
    config: OperatorConfig,
    store: SuccessorStore,
    *,
    principal: str,
    role: str,
    domain: str,
    payload: dict[str, Any],
    approval_token: str,
) -> dict[str, Any]:
    if not isinstance(approval_token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", approval_token):
        raise ValueError("the separately installed role approval token is required")
    signers = [signer for signer in config.signers if signer.principal == principal]
    if len(signers) != 1:
        raise ValueError("this principal has no installed local signer; use its external signed file handoff")
    signer = signers[0]
    for name in (signer.key_file, signer.approval_token_file):
        current = journal.root
        for part in Path(name).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("installed signer path must not contain links")
    expected = _private_recovery_bytes(journal.root / signer.approval_token_file, limit=256).strip()
    if secrets.compare_digest(expected, (journal.root / "api.token").read_bytes().strip()):
        raise ValueError("the API token cannot authorize a separate role signature")
    for other in config.signers:
        if other.principal != principal and secrets.compare_digest(
            expected, _private_recovery_bytes(journal.root / other.approval_token_file, limit=256).strip()
        ):
            raise ValueError("different installed role signers require distinct approval credentials")
    if not re.fullmatch(rb"[A-Za-z0-9_-]{43,128}", expected) or not secrets.compare_digest(
        approval_token.encode("utf-8"), expected
    ):
        raise ValueError("role approval token is invalid")
    key = Ed25519PrivateKey.from_private_bytes(_private_recovery_bytes(journal.root / signer.key_file, limit=32))
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    if public != store.trust.anchor(principal, role).public_key:
        raise ValueError("installed signer key differs from its separately trusted public identity")
    signed_document: dict[str, Any] = sign_record(key, principal, domain, payload).model_dump(mode="json")
    return signed_document


def _fields(payload: dict[str, Any], expected: set[str]) -> None:
    if not isinstance(payload, dict) or set(payload) != expected:
        raise ValueError("operation has unknown or missing fields")


def _install(journal: Journal, payload: dict[str, Any]) -> dict[str, Any]:
    _fields(payload, {"template", "signers", "confirm"})
    if payload["confirm"] is not True:
        raise ValueError("explicit operator installation confirmation is required")
    if (journal.root / "studio-operator.json").exists() or (journal.root / "studio-operator.json").is_symlink():
        raise Conflict("operator settings already exist; first installation cannot overwrite them")
    config = OperatorConfig.model_validate(
        {
            "schema": "agialpha.ascension.studio-operator.v1",
            "templates": [payload["template"]],
            "signers": payload["signers"],
        }
    )
    trust = validate_external_trust_bytes(_read(journal.root / "successor-trust.json", 131_072))
    template = config.templates[0]
    for principal, role in (
        (template.controller, "controller"),
        (template.producer, "producer"),
        (template.acceptance_owner, "acceptance"),
    ):
        trust.anchor(principal, role)
    installed_tokens: set[bytes] = set()
    for signer in config.signers:
        if signer.principal not in {template.controller, template.acceptance_owner}:
            raise ValueError("first installation accepts only the selected controller and acceptance signer slots")
        for name in (signer.key_file, signer.approval_token_file):
            current = journal.root
            for part in Path(name).parts:
                current = current / part
                if current.is_symlink():
                    raise ValueError("installed signer paths cannot contain links")
        key = Ed25519PrivateKey.from_private_bytes(_private_recovery_bytes(journal.root / signer.key_file, limit=32))
        role = "controller" if signer.principal == template.controller else "acceptance"
        if (
            key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
            != trust.anchor(signer.principal, role).public_key
        ):
            raise ValueError("installed role key differs from its independently configured public trust")
        approval = _private_recovery_bytes(journal.root / signer.approval_token_file, limit=256).strip()
        if (
            not re.fullmatch(rb"[A-Za-z0-9_-]{43,128}", approval)
            or secrets.compare_digest(approval, (journal.root / "api.token").read_bytes().strip())
            or approval in installed_tokens
        ):
            raise ValueError("role approval requires a distinct preinstalled token_urlsafe(32) credential")
        installed_tokens.add(approval)
    private_write(journal.root / "studio-operator.json", canonical(config.model_dump(mode="json", by_alias=True)))
    return status(journal)


def operate(journal: Journal, action: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Run one explicit phase against trusted installation and authoritative local records."""
    from . import studio

    canonical(payload)
    if len(canonical(payload)) > MAX_INPUT_BYTES:
        raise ValueError("operation exceeds 512 KiB")
    if action == "install":
        return _install(journal, payload)
    if action == "import":
        _fields(payload, {"request_json"})
        if not isinstance(payload["request_json"], str):
            raise ValueError("work file must contain JSON text")
        return operate(
            journal, "prepare", {"request": safe_json_loads(payload["request_json"], max_bytes=MAX_INPUT_BYTES)}
        )
    if action in {"run-import", "accept-import"}:
        field = "authorization" if action == "run-import" else "acceptance"
        _fields(payload, {"request_digest", "revision", "confirm", field + "_json"})
        if not isinstance(payload[field + "_json"], str):
            raise ValueError("signed envelope must contain JSON text")
        signed = safe_json_loads(payload[field + "_json"], max_bytes=131_072)
        return operate(
            journal,
            "run" if action == "run-import" else "accept",
            {
                "request_digest": payload["request_digest"],
                "revision": payload["revision"],
                "confirm": payload["confirm"],
                field: signed,
            },
        )
    if action == "recover":
        _fields(payload, {"request_digest", "revision"})
        prior = show(journal, payload["request_digest"])
        if type(payload["revision"]) is not int or payload["revision"] != prior["revision"]:  # noqa: E721
            raise Conflict("project state changed; refresh and inspect the current revision")
        result = _retained_result(journal, prior)
        return journal.transition(
            prior["id"],
            prior["revision"],
            {"running", "interrupted"},
            "delivered",
            fields={"result": result, "review_requests": _review_requests(journal, prior, result)},
            require_ready=False,
        )
    if action in {"freeze-evaluation", "evaluate"}:
        expected = {"request_digest", "revision"}
        if action == "freeze-evaluation":
            expected |= {"baseline_request_digest", "evaluation_id"}
        _fields(payload, expected)
        current = show(journal, payload["request_digest"])
        if type(payload["revision"]) is not int or payload["revision"] != current["revision"]:  # noqa: E721
            raise Conflict("project state changed; refresh before evaluating")
        if action == "freeze-evaluation":
            if current["state"] not in {"prepared", "sealed", "bound"}:
                raise Conflict("freeze the evaluation before any candidate execution")
            baseline = show(journal, payload["baseline_request_digest"])
            frozen = studio.freeze_evaluation(
                journal,
                baseline["request"],
                _retained_result(journal, baseline),
                current["request"],
                evaluation_id=payload["evaluation_id"],
            )
            fields = {"evaluation_freeze": frozen, "baseline_request_digest": baseline["request_digest"]}
        else:
            if "evaluation_freeze" not in current:
                raise Conflict("this work has no evaluation frozen before execution")
            baseline = show(journal, current["baseline_request_digest"])
            report = studio.evaluate_work(
                journal,
                current["evaluation_freeze"],
                baseline["request"],
                _retained_result(journal, baseline),
                current["request"],
                _retained_result(journal, current),
            )
            fields = {"evaluation": report}
        return journal.transition(
            current["id"], current["revision"], {current["state"]}, current["state"], fields=fields, require_ready=False
        )
    config, store, trust_digest = _installed(journal)
    if action == "pair":
        return _pair(journal, config, store, payload)
    if action == "run-signed":
        _fields(payload, {"request_digest", "revision", "confirm"})
        current = show(journal, payload["request_digest"])
        if "signed_authorization" not in current:
            raise Conflict("the controller must explicitly sign this retained grant first")
        return operate(journal, "run", {**payload, "authorization": current["signed_authorization"]})
    if action == "prepare":
        _fields(payload, {"request"})
        request = payload["request"]
        if not isinstance(request, dict):
            raise ValueError("work request must be an object")
        profile = _profile(config, request, journal)
        configuration_digest = digest(
            "studio-operator-config",
            {
                "profile": profile.model_dump(mode="json"),
                "trust_digest": trust_digest,
            },
        )
        prepared = studio.prepare_work(
            request,
            institution_id=profile.institution_id,
            mission_id=profile.mission_id,
            producer=profile.producer,
            acceptance_owner=profile.acceptance_owner,
            valid_until=profile.valid_until,
        )
        request_digest = prepared["request_digest"]
        graph = JobGraph(
            jobs=[*profile.companion_jobs, JobContract.model_validate(prepared["job_contract"])], edges=profile.edges
        )
        compile_jobs(graph)
        institution = store.read(profile.institution_id)
        if institution["institution"]["constitution"]["mission_id"] != profile.mission_id:
            raise ValueError("installed institution and mission differ")
        store.trust.anchor(profile.producer, "producer")
        store.trust.anchor(profile.acceptance_owner, "acceptance")
        with journal.transaction() as cx:
            try:
                prior = journal.latest(_key(request_digest), cx)
            except KeyError:
                return journal.append(
                    cx,
                    _key(request_digest),
                    {
                        "state": "prepared",
                        "request_digest": request_digest,
                        "project_id": profile.project_id,
                        "cycle_id": profile.cycle_id,
                        "request": request,
                        "prepared": prepared,
                        "graph": graph.model_dump(mode="json"),
                        "configuration_digest": configuration_digest,
                        "market_context": profile.market_context.model_dump(mode="json"),
                        "controller": institution["institution"]["controller"],
                    },
                )
            if (
                canonical(prior["request"]) != canonical(request)
                or prior["configuration_digest"] != configuration_digest
            ):
                raise Conflict("request or installed configuration changed; retain the original record")
            return prior

    common = {"request_digest", "revision"}
    fields = {
        "seal": {"confirm"},
        "bind": {"market_job_id", "posting_tx", "assignment_tx", "acting_identity", "expires_at"},
        "run": {"authorization", "confirm"},
        "settle": {"settlement_tx"},
        "accept": {"acceptance", "confirm"},
        "sign-grant": {"approval_token", "confirm"},
        "sign-review": {"approval_token", "decision", "confirm"},
    }
    if action not in fields:
        raise ValueError("unsupported Studio phase")
    _fields(payload, common | fields[action])
    if action in {"seal", "run", "accept", "sign-grant", "sign-review"} and payload["confirm"] is not True:
        raise ValueError("explicit phase confirmation is required")
    current = show(journal, payload["request_digest"])
    if type(payload["revision"]) is not int or payload["revision"] != current["revision"]:  # noqa: E721
        raise Conflict("project state changed; refresh and inspect the current revision")
    request = current["request"]
    profile = _profile(config, request, journal)
    configuration_digest = digest(
        "studio-operator-config",
        {
            "profile": profile.model_dump(mode="json"),
            "trust_digest": trust_digest,
        },
    )
    if current["configuration_digest"] != configuration_digest:
        raise Conflict("installed configuration changed; the retained work cannot silently inherit new authority")
    reader = MarketReader(profile.market_context, ReadOnlyRPC(profile.rpc_url))
    required = {
        "seal": {"prepared"},
        "bind": {"sealed"},
        "run": {"bound"},
        "settle": {"delivered", "settled"},
        "accept": {"delivered", "settled"},
        "sign-grant": {"bound"},
        "sign-review": {"delivered", "settled"},
    }
    if current["state"] not in required[action]:
        raise Conflict("this phase is unavailable in the current state; inspect or export existing evidence")
    if action == "sign-grant":
        signed = _sign(
            journal,
            config,
            store,
            principal=current["controller"],
            role="controller",
            domain="execution",
            payload=current["grant_request"]["payload"],
            approval_token=payload["approval_token"],
        )
        return journal.transition(
            current["id"], current["revision"], {"bound"}, "bound", fields={"signed_authorization": signed}
        )
    if action == "sign-review":
        if payload["decision"] not in {"accept", "reject"}:
            raise ValueError("choose an explicit accept or reject decision for the delivered work")
        proposal = current["review_requests"][payload["decision"]]
        signed = _sign(
            journal,
            config,
            store,
            principal=proposal["principal"],
            role="acceptance",
            domain="job-acceptance",
            payload=proposal["payload"],
            approval_token=payload["approval_token"],
        )
        return operate(
            journal,
            "accept",
            {
                "request_digest": payload["request_digest"],
                "revision": current["revision"],
                "acceptance": signed,
                "confirm": True,
            },
        )
    if action == "seal":
        seal = studio.seal_work(store, request, reader, current["prepared"], JobGraph.model_validate(current["graph"]))
        return journal.transition(current["id"], current["revision"], {"prepared"}, "sealed", fields={"seal": seal})
    if action == "bind":
        worker = address(payload["acting_identity"])
        store.trust.anchor(worker, "worker")
        terms = JobContract.model_validate(current["prepared"]["job_contract"])
        authorization = ExecutionAuthorization(
            authorization_id="studio-" + current["request_digest"],
            acting_identity=worker,
            job_terms_digest=digest("job-terms", terms),
            release_digest=terms.release_digest,
            environment_digest=terms.environment_digest,
            capabilities=terms.allowed_tools,
            reservation_id="studio-reservation-" + current["request_digest"],
            expires_at=payload["expires_at"],
        )
        binding = studio.bind_work(
            journal,
            request,
            current["seal"],
            reader,
            market_job_id=payload["market_job_id"],
            posting_tx=hash32(payload["posting_tx"]),
            assignment_tx=hash32(payload["assignment_tx"]),
            execution_authorization=authorization.model_dump(mode="json"),
        )
        grant = {**authorization.model_dump(mode="json"), "market_binding_digest": binding["digest"]}
        handoff = {
            "schema": "agialpha.ascension.studio-grant-request.v1",
            "request_digest": current["request_digest"],
            "project_id": profile.project_id,
            "cycle_id": profile.cycle_id,
            "domain": "execution",
            "principal": current["controller"],
            "payload": grant,
            "binding": binding,
            "instruction": (
                "Review exact scope and sign separately using the installed controller. This is not a grant."
            ),
        }
        return journal.transition(
            current["id"],
            current["revision"],
            {"sealed"},
            "bound",
            fields={"binding": binding, "grant_request": handoff},
        )
    if action == "run":
        signed_authorization = SignedEnvelope.model_validate(payload["authorization"])
        verified = store.trust.verify(signed_authorization, "execution", "controller")
        if signed_authorization.principal != current["controller"] or canonical(verified) != canonical(
            current["grant_request"]["payload"]
        ):
            raise ValueError("controller grant does not authorize this exact retained request and assignment")
        running = journal.transition(current["id"], current["revision"], {"bound"}, "running")

        def operator_checkpoint() -> None:
            installed, _, installed_trust = _installed(journal)
            installed_profile = _profile(installed, request, journal)
            if (
                digest(
                    "studio-operator-config",
                    {
                        "profile": installed_profile.model_dump(mode="json"),
                        "trust_digest": installed_trust,
                    },
                )
                != configuration_digest
            ):
                raise Conflict("installed operator profile or trust changed during execution")

        try:
            result = studio.execute_work(
                JobDispatcher(store, profile.institution_id),
                request,
                current["seal"],
                current["binding"],
                signed_authorization,
                operator_checkpoint=operator_checkpoint,
            )
        except Exception:
            journal.transition(current["id"], running["revision"], {"running"}, "interrupted", require_ready=False)
            raise
        return journal.transition(
            current["id"],
            running["revision"],
            {"running"},
            "delivered",
            fields={"result": result, "review_requests": _review_requests(journal, current, result)},
            require_ready=False,
        )
    if action == "accept":
        acceptance = SignedEnvelope.model_validate(payload["acceptance"])
        studio.accept_work(JobDispatcher(store, profile.institution_id), request, current["result"], acceptance)
        return journal.transition(
            current["id"],
            current["revision"],
            required[action],
            current["state"],
            fields={"local_acceptance": acceptance.model_dump(mode="json")},
            require_ready=False,
        )
    settlement = studio.settle_work(
        journal, request, current["result"], reader, settlement_tx=hash32(payload["settlement_tx"])
    )
    return journal.transition(
        current["id"],
        current["revision"],
        required[action],
        "settled",
        fields={"settlement": settlement},
        require_ready=False,
    )
