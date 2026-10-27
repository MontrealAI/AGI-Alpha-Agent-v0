# SPDX-License-Identifier: Apache-2.0
"""Record local protocol conformance with explicit fictional authority and costs.

Requires a source checkout and its test dependencies. This is a test harness,
never a production provisioner or a frontier-model qualification command.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any


def record() -> dict[str, Any]:
    """Execute the current fixture afresh and export public, non-secret receipts."""
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    fixture = root / "tests/runtime/test_flywheel_protected.py"
    spec = importlib.util.spec_from_file_location("protected_flywheel_fixture", fixture)
    if spec is None or spec.loader is None:
        raise RuntimeError("source-checkout conformance fixture required")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="protected-flywheel-conformance-") as temporary:
        state = module.setup.__wrapped__(Path(temporary))
        module.test_reconciled_acceptance_required_for_successful_reuse(state, False, False, None)
        before_payment = state["costs"].report()
        module.account(
            state,
            "payment",
            {
                "payment_id": "fictional-later-payment",
                "activity_id": "origin/compute",
                "amount_micro_usd": 1,
                "evidence_digest": "d" * 64,
            },
            "fictional-later-payment",
        )
        after_payment = state["costs"].report()
        assert after_payment["costs"] == before_payment["costs"]
        assert after_payment["available_funds"] == before_payment["available_funds"]
        assert after_payment["cash"] == before_payment["cash"] - 1
        assert after_payment["obligations"] == before_payment["obligations"] - 1
        try:
            module.account(
                state,
                "capital",
                {
                    "record_id": "duplicate-fictional-funding",
                    "mission_id": module.ORIGIN,
                    "amount_micro_usd": 10_000,
                    "evidence_digest": module.ZERO,
                },
                "duplicate-fictional-funding",
            )
        except module.Conflict:
            duplicate_funding_refused = True
        else:
            raise AssertionError("duplicate capital evidence unexpectedly credited")
        assert state["costs"].report() == after_payment
        network = state["library"].snapshot()[module.BRANCH]
        ident = next(iter(network["entries"]))
        candidate = network["entries"][ident]
        service = state["service"]
        catalog_resource = service.catalog_resource()
        catalog = service.catalog(
            module.proof(
                state,
                catalog_resource,
                "discover",
                module.digest("flywheel-catalog-request", {"resource": catalog_resource}),
            )
        )
        stale = module.proof(state, ident, "discover", module.digest("flywheel-discover", {"candidate_digest": ident}))
        module.control(state, ident, "revoke")
        try:
            service.manifest(ident, stale)
        except module.Conflict:
            refused = True
        else:
            raise AssertionError("revoked stale access unexpectedly succeeded")
        source_paths = {
            fixture,
            Path(__file__).resolve(),
            *root.joinpath("alpha_factory_v1/core/runtime/successor").glob("flywheel_*.py"),
            *[
                root / "alpha_factory_v1/core/runtime" / name
                for name in (
                    "api.py",
                    "cli.py",
                    "chain.py",
                    "engine.py",
                    "models.py",
                    "provider.py",
                    "store.py",
                    "work.py",
                )
            ],
            *[
                root / "alpha_factory_v1/core/runtime/successor" / name
                for name in (
                    "transformation.py",
                    "transformation_library.py",
                    "trust.py",
                    "protocol.py",
                    "signatures.py",
                )
            ],
        }
        return {
            "schema": "protected-flywheel-conformance/v2",
            "scope": "LOCAL NATIVE WORK AND SYNTHETIC PROTOCOL CONFORMANCE ONLY",
            "actual_frontier_model_execution": False,
            "live_ens_qualification": False,
            "production_service_provisioned": False,
            "real_peer_reuse_qualified": False,
            "actual_customer_collections": 0,
            "prices_costs_and_funding": "fictional fixture attestations; not observed real amounts",
            "signers_and_chain": "ephemeral fictional role keys and RPC responses; no network requests or actual ENS identities",
            "origin_execution": "actual native Research submit, execute, quote verification and automated review; no frontier model or independent organizational acceptance",
            "historical_records": [
                {
                    "file": "protected-flywheel-conformance-historical.json",
                    "sha256": "9d2202568c78b147d38c3a0bbf55611696aa3fd111000bb35a7742ed15ae365a",
                    "scope": "original synthetic fixture with constructed origin acceptance; never qualifies native delivery or this source",
                },
                {
                    "commit": "93e8422f6417d751ff9de53553b31faf97f60c27",
                    "file": "docs/agent/release-evidence/protected-flywheel-conformance.json",
                    "sha256": "690a0d6c36b548c670ec58c23c360070d116a3c1105795be28cadeb4fdbe1a90",
                    "scope": "superseded synthetic fixture with constructed origin; original bytes remain in Git history",
                },
            ],
            "execution_digest": service.execution_digest,
            "source_sha256": {
                path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(source_paths)
            },
            "example": {
                "origin_delivery": state["journal"].latest(module.ORIGIN),
                "manifest": candidate["manifest"],
                "plan": candidate["plan"],
                "assessment": candidate["decision"],
                "invocation": network["invocations"]["fresh-peer"],
                "costs": state["costs"].report(),
                "fictional_payment_reconciliation": {
                    "before": before_payment,
                    "after": after_payment,
                    "attestations": state["costs"].snapshot()["payments"],
                    "funds_transferred": False,
                },
            },
            "catalog": catalog,
            "current_state": module.entry(state, ident)["state"],
            "revoked_stale_access_refused": refused,
            "duplicate_funding_refused": duplicate_funding_refused,
            "journal_integrity": state["journal"].verify(),
            "required_live_resources": [
                "approved frontier model/executor, exact configuration, quota, billing and finite allowance",
                "approved service host, durable encrypted storage and separately retained key/checkpoint custody",
                "two approved RPC readers and real code pins",
                "two owner-controlled eligible agent wallets signing fresh challenges",
            ],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="new synthetic conformance JSON file")
    args = parser.parse_args()
    payload = record()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")
    print("Recorded local conformance; no live ENS/model qualification, customer revenue or real peer advantage.")


if __name__ == "__main__":
    main()
