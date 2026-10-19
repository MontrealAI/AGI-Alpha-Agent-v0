# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.transformation import DiscoveryLoop, pilot_document, pilot_request
from alpha_factory_v1.core.runtime.successor.transformation_library import (
    ReuseConditions,
    ReuseCosts,
    RouterContext,
    TransformationLibrary,
    portable_behavior_digest,
)
from alpha_factory_v1.core.runtime.successor.trust import (
    SignedEnvelope,
    TrustAnchor,
    TrustRegistry,
    local_principals,
    sign_record,
)


@pytest.fixture(scope="module")
def native(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    journal = Journal.initialize(tmp_path_factory.mktemp("native-library") / "state")
    loop = DiscoveryLoop(journal)
    request = pilot_request("00000000-0000-4000-8000-000000000001")
    record = loop.create(request)
    loop.approve(request.campaign_id, record["binding_digest"])
    for number in range(3):
        record = loop.step(request.campaign_id, operation_id=f"library-pilot-{number}")
    loop.confirm(request.campaign_id, [pilot_document(confirmation=True)], record["freeze"]["digest"])
    return loop.envelope(request.campaign_id)


def setup(tmp_path: Path) -> tuple[TransformationLibrary, dict[str, Ed25519PrivateKey], TrustRegistry]:
    trust, keys = local_principals()
    return TransformationLibrary(Journal.initialize(tmp_path / "library"), trust), keys, trust


def conditions(
    native: dict[str, Any], *, method: str = "summary", version: int = 1, setup_cost: int = 20
) -> ReuseConditions:
    return ReuseConditions(
        method_id=method,
        version=version,
        producer="local-producer",
        supported_scope=["public-fixed-summary"],
        prerequisites=["audited-dependencies"],
        failure_conditions=["uncertain-annotations"],
        retirement_triggers=["new instrument, source distribution or checker"],
        costs=ReuseCosts(setup_units=setup_cost, per_use_units=2),
        evidence_digests=[native["freeze"]["digest"], digest("ti-library-result", native["result"])],
    )


def review_payload(library: TransformationLibrary, entry: dict[str, Any], operation: str) -> dict[str, Any]:
    return {
        "journal_identity": library.journal.identity,
        "archive_digest": entry["archive_digest"],
        "supported_scope": entry["conditions"]["supported_scope"],
        "bindings_digest": entry["envelope"]["bindings_digest"],
        "behavior_digest": entry["behavior_digest"],
        "evidence_digests": entry["conditions"]["evidence_digests"],
        "evidence_scope": "local-structural-only",
        "outcome_claim": "structural-coverage-only",
        "operation_id": operation,
        "verdict": "supported",
        "limitations": "Configured local-role test; source truth and human understanding uncalibrated.",
    }


def reviewed(
    library: TransformationLibrary, keys: dict[str, Ed25519PrivateKey], entry: dict[str, Any], operation: str = "review"
) -> dict[str, Any]:
    signed = sign_record(
        keys["local-verifier"], "local-verifier", "ti-library-review", review_payload(library, entry, operation)
    )
    return library.review(entry["archive_digest"], signed, operation_id=operation)


def approval(
    library: TransformationLibrary,
    keys: dict[str, Ed25519PrivateKey],
    entry: dict[str, Any],
    operation: str = "promote",
    action: str = "promote",
) -> SignedEnvelope:
    return sign_record(
        keys["local-controller"],
        "local-controller",
        "ti-library-control",
        {
            "journal_identity": library.journal.identity,
            "archive_digest": entry["archive_digest"],
            "previous_active": library.snapshot()["active"].get(entry["conditions"]["method_id"]),
            "bindings_digest": entry["envelope"]["bindings_digest"],
            "behavior_digest": entry["behavior_digest"],
            "stage": "local-reuse-only",
            "authority_expansion": False,
            "operation_id": operation,
            "action": action,
            "reason": "Explicit local selection; no external or spending authority.",
        },
    )


def activate(
    library: TransformationLibrary,
    keys: dict[str, Ed25519PrivateKey],
    entry: dict[str, Any],
    operation: str = "promote",
) -> dict[str, Any]:
    signed = approval(library, keys, entry, operation)
    return library.control(
        entry["archive_digest"],
        signed,
        expected_behavior_digest=entry["behavior_digest"],
        operation_id=operation,
    )


def context(native: dict[str, Any], **updates: Any) -> RouterContext:
    return RouterContext.model_validate(
        {
            "publicOnly": True,
            "task_scope": "public-fixed-summary",
            "prerequisites": ["audited-dependencies"],
            "observed_failures": [],
            "current_behavior_digest": portable_behavior_digest(native),
            "target_charter_digest": native["charter_digest"],
            "reuse_horizon": 10,
            "max_total_units": 100,
            "incumbent_per_use_units": 5,
            **updates,
        }
    )


def test_archive_preserves_witness_without_promotion_and_replay_does_not_rewrite(
    tmp_path: Path, native: dict[str, Any]
) -> None:
    library, _, _ = setup(tmp_path)
    supplied = copy.deepcopy(native)
    entry = library.archive(supplied, conditions(native), operation_id="archive")
    sequence = library.journal.verify()["events"]
    assert entry["envelope"]["transformation"] == native["transformation"]
    assert entry["state"] == "pending-review" and entry["authority_granted"] is False
    assert library.route(context(native))["decision"] == "retain-incumbent"
    supplied["transformation"]["witness"]["purpose"] = "tampered caller copy"
    assert library.snapshot()["entries"][0]["envelope"]["transformation"] == native["transformation"]
    assert library.archive(native, conditions(native), operation_id="archive") == entry
    assert library.journal.verify()["events"] == sequence
    with pytest.raises(Conflict, match="different library terms"):
        library.archive(native, conditions(native, method="different"), operation_id="archive")
    with pytest.raises(Conflict, match="version"):
        library.archive(native, conditions(native, setup_cost=21), operation_id="replace-version")


def test_only_reviewed_explicitly_promoted_supported_scope_can_route(tmp_path: Path, native: dict[str, Any]) -> None:
    library, keys, _ = setup(tmp_path)
    entry = library.archive(native, conditions(native), operation_id="archive")
    with pytest.raises(Conflict, match="separately supported"):
        activate(library, keys, entry)
    reviewed(library, keys, entry)
    assert library.route(context(native))["decision"] == "retain-incumbent"
    activate(library, keys, entry)
    selected = library.route(context(native))
    assert selected["decision"] == "select-local-method" and selected["declared_total_units"] == 40
    for key in ("authority_granted", "execution_approved", "spending_approved", "independent_organizational_review"):
        assert selected[key] is False
    assert selected["evidence_scope"] == "local-structural-only"


@pytest.mark.parametrize(
    "changes",
    [
        {"task_scope": "unreviewed-population"},
        {"prerequisites": []},
        {"observed_failures": ["uncertain-annotations"]},
        {"current_behavior_digest": "0" * 64},
        {"reuse_horizon": 1},
        {"max_total_units": 39},
        {"incumbent_per_use_units": 4},
    ],
)
def test_router_selectivity_setup_cost_and_ties(
    tmp_path: Path, native: dict[str, Any], changes: dict[str, Any]
) -> None:
    library, keys, _ = setup(tmp_path)
    entry = library.archive(native, conditions(native), operation_id="archive")
    reviewed(library, keys, entry)
    activate(library, keys, entry)
    assert library.route(context(native, **changes))["decision"] == "retain-incumbent"


def test_router_selects_cheaper_supported_method_not_just_component_success(
    tmp_path: Path, native: dict[str, Any]
) -> None:
    library, keys, _ = setup(tmp_path)
    for method, cost in (("expensive", 20), ("cheaper", 5)):
        entry = library.archive(
            native, conditions(native, method=method, setup_cost=cost), operation_id="archive-" + method
        )
        reviewed(library, keys, entry, "review-" + method)
        activate(library, keys, entry, "promote-" + method)
    assert library.route(context(native))["method_id"] == "cheaper"


def test_versions_rollback_retirement_and_restart_preserve_history(tmp_path: Path, native: dict[str, Any]) -> None:
    library, keys, trust = setup(tmp_path)
    one = library.archive(native, conditions(native), operation_id="archive-one")
    reviewed(library, keys, one, "review-one")
    activate(library, keys, one, "promote-one")
    two = library.archive(native, conditions(native, version=2, setup_cost=5), operation_id="archive-two")
    reviewed(library, keys, two, "review-two")
    activate(library, keys, two, "promote-two")
    assert library.route(context(native))["version"] == 2
    rollback = approval(library, keys, one, "rollback-one", "rollback")
    library.control(
        one["archive_digest"],
        rollback,
        expected_behavior_digest=portable_behavior_digest(native),
        operation_id="rollback-one",
    )
    assert library.route(context(native))["version"] == 1
    retire = approval(library, keys, one, "retire-one", "retire")
    library.control(
        one["archive_digest"],
        retire,
        expected_behavior_digest=portable_behavior_digest(native),
        operation_id="retire-one",
    )
    restarted = TransformationLibrary(Journal(library.journal.root), trust)
    assert restarted.route(context(native))["decision"] == "retain-incumbent"
    assert len(restarted.snapshot()["entries"]) == 2
    with pytest.raises(Conflict, match="nonretired"):
        activate(restarted, keys, one, "reactivate-retired")
    assert any(row["action"] == "rollback" for row in restarted.snapshot()["history"])


def test_review_and_controller_require_distinct_principals_and_keys(tmp_path: Path, native: dict[str, Any]) -> None:
    library, keys, trust = setup(tmp_path)
    producer = trust.anchor("local-producer", "producer")
    verifier = trust.anchor("local-verifier", "verifier")
    anchors = {
        name: trust.anchor(name, role)
        for name, role in (
            ("local-producer", "producer"),
            ("local-verifier", "verifier"),
            ("local-controller", "controller"),
        )
    }
    anchors["aliased-verifier"] = TrustAnchor(producer.public_key, frozenset({"verifier"}))
    anchors["aliased-controller"] = TrustAnchor(verifier.public_key, frozenset({"controller"}))
    library.trust = TrustRegistry(anchors)
    entry = library.archive(native, conditions(native), operation_id="archive")
    alias = sign_record(
        keys["local-producer"], "aliased-verifier", "ti-library-review", review_payload(library, entry, "review")
    )
    with pytest.raises(ValueError, match="distinct"):
        library.review(entry["archive_digest"], alias, operation_id="review")
    reviewed(library, keys, entry)
    unsigned = approval(library, keys, entry).payload
    alias_control = sign_record(keys["local-verifier"], "aliased-controller", "ti-library-control", unsigned)
    with pytest.raises(ValueError, match="distinct"):
        library.control(
            entry["archive_digest"],
            alias_control,
            expected_behavior_digest=portable_behavior_digest(native),
            operation_id="promote",
        )


def test_stale_approvals_scope_substitution_and_other_journal_fail_closed(
    tmp_path: Path, native: dict[str, Any]
) -> None:
    library, keys, _ = setup(tmp_path)
    entry = library.archive(native, conditions(native), operation_id="archive")
    payload = review_payload(library, entry, "review")
    for key, value in (
        ("archive_digest", "0" * 64),
        ("bindings_digest", "0" * 64),
        ("evidence_scope", "general-intelligence"),
        ("journal_identity", "another-journal"),
    ):
        wrong = sign_record(keys["local-verifier"], "local-verifier", "ti-library-review", {**payload, key: value})
        with pytest.raises(ValueError):
            library.review(entry["archive_digest"], wrong, operation_id="review")
    reviewed(library, keys, entry)
    control = approval(library, keys, entry)
    with pytest.raises(Conflict, match="frozen behavior"):
        library.control(
            entry["archive_digest"],
            sign_record(
                keys["local-controller"],
                "local-controller",
                "ti-library-control",
                {**control.payload, "behavior_digest": "0" * 64},
            ),
            expected_behavior_digest="0" * 64,
            operation_id="promote",
        )
    assert library.route(context(native))["decision"] == "retain-incumbent"


def test_revocation_and_stop_disable_routing_without_deleting_evidence(tmp_path: Path, native: dict[str, Any]) -> None:
    library, keys, trust = setup(tmp_path)
    entry = library.archive(native, conditions(native), operation_id="archive")
    reviewed(library, keys, entry)
    activate(library, keys, entry)
    trust.revoke("local-controller")
    assert library.route(context(native))["decision"] == "retain-incumbent"
    assert len(library.snapshot()["entries"]) == 1
    with library.journal.transaction() as cx:
        library.journal.append(cx, "@control", {"state": "stopped"})
    assert library.route(context(native))["decision"] == "retain-incumbent"


def test_unfinished_or_missing_confirmation_evidence_cannot_be_supported(
    tmp_path: Path, native: dict[str, Any]
) -> None:
    library, keys, _ = setup(tmp_path)
    incomplete = {**native, "phase": "developed", "freeze": None, "result": None}
    entry = library.archive(incomplete, conditions(native), operation_id="unfinished")
    with pytest.raises(Conflict, match="unfinished"):
        reviewed(library, keys, entry)
    bad = conditions(native, method="missing-evidence").model_copy(update={"evidence_digests": ["0" * 64]})
    entry = library.archive(native, bad, operation_id="missing")
    with pytest.raises(ValueError, match="actual frozen comparison"):
        reviewed(library, keys, entry)


def test_portable_behavior_reuses_across_fresh_campaign_but_changed_behavior_rejects(
    tmp_path: Path, native: dict[str, Any]
) -> None:
    library, keys, _ = setup(tmp_path)
    entry = library.archive(native, conditions(native), operation_id="archive")
    reviewed(library, keys, entry)
    activate(library, keys, entry)
    fresh = DiscoveryLoop(Journal.initialize(tmp_path / "fresh-campaign"))
    request = pilot_request("00000000-0000-4000-8000-000000000002").model_copy(
        update={"development": [pilot_document(confirmation=True)]}
    )
    fresh.create(request)
    target = fresh.envelope(request.campaign_id)
    assert native["bindings_digest"] != target["bindings_digest"]
    assert portable_behavior_digest(native) == portable_behavior_digest(target)
    routed = library.route(context(target))
    assert routed["decision"] == "select-local-method"
    assert routed["target_charter_digest"] == target["charter_digest"]
    assert routed["execution_approved"] is False
    changed = copy.deepcopy(target)
    changed["bindings"]["engine_sha256"] = "e" * 64
    changed["bindings_digest"] = digest("ti-bindings", changed["bindings"])
    assert library.route(context(changed))["decision"] == "retain-incumbent"


def test_native_library_cli_archives_routes_without_signing_or_overwriting(
    tmp_path: Path, native: dict[str, Any]
) -> None:
    import argparse
    import json
    from alpha_factory_v1.core.runtime.successor.protocol import canonical
    from alpha_factory_v1.core.runtime.successor.transformation_library_cli import add_commands, handle

    library, keys, trust = setup(tmp_path)
    registry = {
        "schema_version": 1,
        "principals": {
            name: {
                "public_key": trust.anchor(name, role).public_key,
                "roles": sorted(trust.anchor(name, role).roles),
                "provenance": "local",
                "independence_attestation": "",
            }
            for name, role in (
                ("local-producer", "producer"),
                ("local-verifier", "verifier"),
                ("local-controller", "controller"),
            )
        },
    }
    for name, value in (
        ("trust.json", registry),
        ("campaign.json", native),
        ("conditions.json", conditions(native).model_dump()),
        ("context.json", context(native).model_dump()),
    ):
        (tmp_path / name).write_bytes(canonical(value))
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path)
    actions = parser.add_subparsers(dest="command")
    add_commands(actions)

    def command(action: list[str], output: str) -> argparse.Namespace:
        return parser.parse_args(
            [
                "--home",
                str(library.journal.root),
                "successor-library",
                "--trust",
                str(tmp_path / "trust.json"),
                "--producer",
                "local-producer",
                "--output",
                str(tmp_path / output),
                *action,
            ]
        )

    args = command(
        [
            "archive",
            str(tmp_path / "campaign.json"),
            str(tmp_path / "conditions.json"),
            "--operation-id",
            "cli-archive",
        ],
        "archive.json",
    )
    assert handle(args)["authority_granted"] is False
    assert json.loads((tmp_path / "archive.json").read_bytes())["state"] == "pending-review"
    with pytest.raises(FileExistsError):
        handle(args)
    assert handle(command(["route", str(tmp_path / "context.json")], "route.json"))["execution_approved"] is False
    assert json.loads((tmp_path / "route.json").read_bytes())["decision"] == "retain-incumbent"
    entry = json.loads((tmp_path / "archive.json").read_bytes())
    signed_review = sign_record(
        keys["local-verifier"], "local-verifier", "ti-library-review", review_payload(library, entry, "cli-review")
    )
    (tmp_path / "review-signed.json").write_bytes(canonical(signed_review.model_dump()))
    handle(
        command(
            ["review", entry["archive_digest"], str(tmp_path / "review-signed.json"), "--operation-id", "cli-review"],
            "reviewed.json",
        )
    )
    signed_control = approval(library, keys, entry, "cli-promote")
    (tmp_path / "control-signed.json").write_bytes(canonical(signed_control.model_dump()))
    handle(
        command(
            [
                "control",
                entry["archive_digest"],
                str(tmp_path / "control-signed.json"),
                "--behavior-digest",
                entry["behavior_digest"],
                "--operation-id",
                "cli-promote",
            ],
            "promoted.json",
        )
    )
    handle(command(["route", str(tmp_path / "context.json")], "selected.json"))
    selected = json.loads((tmp_path / "selected.json").read_bytes())
    assert selected["decision"] == "select-local-method"
    assert selected["execution_approved"] is False


@pytest.mark.parametrize("value", [1, 0, "true", False, None])
def test_router_requires_explicit_exact_boolean_public_context(native: dict[str, Any], value: Any) -> None:
    with pytest.raises(ValueError, match="exact-boolean"):
        context(native, publicOnly=value)
