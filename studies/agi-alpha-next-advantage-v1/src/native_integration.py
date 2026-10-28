# SPDX-License-Identifier: Apache-2.0
"""Execute frozen Alpha accounting, authority fixtures, and explicit scope refusal."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

STUDY = Path(__file__).resolve().parents[1]
SOURCE_SHA = "80b345828f34fd8a6e592977dd17ef37141305f4"
SNAPSHOT = STUDY / "vendor" / "runtime"
MANIFEST = STUDY / "provenance" / "runtime_source_manifest.json"
REPOSITORY = STUDY.parents[1]
SOURCE = SNAPSHOT if SNAPSHOT.is_dir() else REPOSITORY


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def verify_frozen_runtime() -> dict[str, Any]:
    if not MANIFEST.is_file():
        raise ValueError("frozen runtime manifest must exist before execution")
    manifest = json.loads(MANIFEST.read_text())
    if manifest["source_commit"] != SOURCE_SHA:
        raise ValueError("unexpected frozen native source identity")
    for entry in manifest["files"]:
        path = SOURCE / entry["path"]
        data = path.read_bytes()
        if hash_bytes(data) != entry["sha256"] or len(data) != entry["bytes"]:
            raise ValueError("native runtime source changed: " + entry["path"])
    return {"commit": SOURCE_SHA, "files": len(manifest["files"]), "verified": True}


def native() -> dict[str, Any]:
    verify_frozen_runtime()
    sys.path.insert(0, str(SOURCE))
    from alpha_factory_v1.core.runtime.store import Conflict, Journal
    from alpha_factory_v1.core.runtime.successor.flywheel_access import (
        AccessRequest, ENSAuthority, ENSPins, REGISTRAR, REGISTRY, WRAPPER, ResourceAccess, ServiceIdentity, namehash,
    )
    from alpha_factory_v1.core.runtime.successor.flywheel_capsules import CapsuleManifest
    from alpha_factory_v1.core.runtime.successor.flywheel_costs import CATEGORIES, Charge, CostLedger
    from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, sign_record

    for name, module in tuple(sys.modules.items()):
        if name.startswith("alpha_factory_v1") and getattr(module, "__file__", None):
            actual = Path(module.__file__).resolve()
            if not actual.is_relative_to(SOURCE.resolve()):
                raise ValueError("native imports came from a different source: " + name)
    return locals()


def micro_usd(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not money")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("invalid decimal amount") from error
    scaled = amount * 1_000_000
    if not amount.is_finite() or amount < 0 or scaled != scaled.to_integral_value() or scaled > 10**15:
        raise ValueError("amount must be finite nonnegative USD with at most six decimal places")
    return int(scaled)


def normalize(payload: dict[str, Any]) -> list[dict[str, Any]]:
    required = {"event_id", "bucket", "amount_usd", "activity"}
    allowed = required | {"job_id", "category", "day"}
    events, seen = [], set()
    for raw in payload["events"]:
        if not isinstance(raw, dict) or not required <= set(raw) or set(raw) - allowed:
            raise ValueError("expense record schema mismatch")
        if not isinstance(raw["event_id"], str) or not raw["event_id"] or raw["event_id"] in seen:
            raise ValueError("every expense must have a unique activity event identity")
        if raw["bucket"] not in {"A", "B", "C"}:
            raise ValueError("expense must belong to exactly one A/B/C bucket")
        if not isinstance(raw["activity"], str) or not raw["activity"]:
            raise ValueError("expense requires a described activity")
        seen.add(raw["event_id"])
        events.append({**raw, "amount_micro_usd": micro_usd(raw["amount_usd"]),
                       "amount_usd": str(raw["amount_usd"]), "category": raw.get("category", "overhead")})
    if not events:
        raise ValueError("accounting replay requires at least one expense")
    return events


def accounting_fixture(root: Path, api: dict[str, Any]) -> dict[str, Any]:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    trust = api["TrustRegistry"]({"study-accountant": api["TrustAnchor"](public, frozenset({"accounting"}))})
    journal = api["Journal"].initialize(root)
    return {"key": key, "trust": trust, "journal": journal, "ledger": api["CostLedger"](journal, trust),
            "public": public, "commands": []}


def apply(fixture: dict[str, Any], api: dict[str, Any], operation: str, action: str, record: Any) -> Any:
    signed = api["sign_record"](fixture["key"], "study-accountant", "flywheel-cost-command", {
        "journal_identity": fixture["journal"].identity, "operation_id": operation,
        "action": action, "record": record,
    })
    value = fixture["ledger"].apply(signed)
    fixture["commands"].append(signed.model_dump())
    return value


def export_journal(journal: Any) -> dict[str, Any]:
    with sqlite3.connect(journal.path) as connection:
        events = [{"sequence": row[0], "mission": row[1], "body": json.loads(row[2]),
                   "hash": row[3], "signature": row[4]}
                  for row in connection.execute("SELECT * FROM events ORDER BY seq")]
    return {"identity": journal.identity, "public_key": journal.public, "events": events}


def independently_verify_export(public: dict[str, Any]) -> int:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public["public_key"]))
    previous = "0" * 64
    for index, event in enumerate(public["events"], 1):
        body = event["body"]
        if body["sequence"] != index or event["sequence"] != index or body["previous"] != previous:
            raise ValueError("public journal chain mismatch")
        if body["identity"] != public["identity"] or body["mission"] != event["mission"]:
            raise ValueError("public journal identity mismatch")
        if hash_bytes(json_bytes(body)) != event["hash"]:
            raise ValueError("public journal digest mismatch")
        key.verify(base64.b64decode(event["signature"], validate=True), bytes.fromhex(event["hash"]))
        previous = event["hash"]
    return len(public["events"])


def replay_account(payload: dict[str, Any], output: Path) -> dict[str, Any]:
    api, events = native(), normalize(payload)
    output.mkdir(parents=True, exist_ok=True)
    categories = sorted(api["CATEGORIES"])
    if any(event["category"] not in categories for event in events):
        raise ValueError("unsupported native resource category")
    inputs = {"collections": micro_usd(payload.get("collections_usd", 0)),
              "capital": micro_usd(payload.get("capital_usd", 0)), "reserve": micro_usd(payload.get("reserve_usd", 0))}
    expense_totals = {bucket: sum(event["amount_micro_usd"] for event in events if event["bucket"] == bucket)
                      for bucket in "ABC"}
    input_digest = hash_bytes(json_bytes(payload))
    with tempfile.TemporaryDirectory(prefix="alpha-study-native-") as temporary:
        fixture = accounting_fixture(Path(temporary) / "journal", api)
        for bucket in "ABC":
            selected = [event for event in events if event["bucket"] == bucket]
            if not selected:
                continue
            for category in categories:
                subset = [event for event in selected if event["category"] == category]
                amount = sum(event["amount_micro_usd"] for event in subset)
                charge = api["Charge"](activity_id=f"projection/{bucket}/{category}", mission_id="study-enterprise",
                    bucket=bucket, category=category, accrued_micro_usd=amount, paid_micro_usd=amount,
                    basis="attested", evidence_digest=hash_bytes(json_bytes(subset)),
                    note="Synthetic accounting signer; simulated USD. Aggregate binds unique source events. Empty category is explicitly zero within this model.")
                apply(fixture, api, f"charge/{bucket}/{category}", "charge", charge.model_dump())
            action = {"A": "seal", "B": "seal-retention", "C": "seal-investment"}[bucket]
            apply(fixture, api, "seal/" + bucket, action,
                  {"mission_id": "study-enterprise", "evidence_digest": input_digest, "categories": categories})
        for action, key in (("capital", "capital"), ("collection", "collections")):
            if inputs[key]:
                record = {"record_id": "study-" + key, "mission_id": "study-enterprise",
                          "amount_micro_usd": inputs[key], "evidence_digest": hash_bytes(json_bytes([key, input_digest]))}
                apply(fixture, api, action, action, record)
        apply(fixture, api, "reserve", "reserve", inputs["reserve"])
        report = fixture["ledger"].report()
        expected_profit = inputs["collections"] - sum(expense_totals.values())
        expected_cash = inputs["capital"] + expected_profit
        expected = {"costs": expense_totals, "collected_revenue": inputs["collections"],
                    "complete_cost_profit": expected_profit, "cash": expected_cash, "obligations": 0,
                    "reserve": inputs["reserve"], "available_funds": expected_cash - inputs["reserve"]}
        if any(report[key] != value for key, value in expected.items()):
            raise AssertionError("native ledger differs from independent event reconstruction")
        receipt = fixture["journal"].verify()
        public = export_journal(fixture["journal"])
        verified = independently_verify_export(public)
        result = {"schema": "next-advantage-native-accounting/v1", "label": payload.get("label", "study-account"),
            "input_sha256": input_digest, "artifact_digest": payload.get("artifact_digest"),
            "source": verify_frozen_runtime(), "source_event_count": len(events), "report": report,
            "independent_expected": expected, "journal_verification": receipt,
            "public_signatures_verified": verified, "accounting_public_key": fixture["public"],
            "economic_values": "SIMULATED", "identity": "LOCAL_SYNTHETIC_ACCOUNTANT",
            "live_sales": False, "live_ens": False, "native_scheduling_admission": False,
            "projection": "Distinct source events aggregate into bounded native A/B/C category charges. No source activity is charged twice. Missing category maps to overhead. Explicit zero categories mean zero in the supplied model, not observed zero costs.",
            "replay_variability": "Economic totals and source hashes are deterministic; fresh local keys, journal identity, timestamps and signatures vary."}
        (output / "accounting-report.json").write_text(json.dumps(result, indent=2) + "\n")
        (output / "journal-public.json").write_text(json.dumps(public, indent=2) + "\n")
        (output / "accounting-commands.json").write_text(json.dumps(fixture["commands"], indent=2) + "\n")
        (output / "input.json").write_text(json.dumps(payload, indent=2) + "\n")
    return result


def refuse(call: Any) -> str:
    try:
        call()
    except (ValueError, KeyError, RuntimeError) as error:
        return str(error)
    raise AssertionError("negative control unexpectedly accepted")


class SyntheticRPC:
    """Fictional read-only chain responses; never a live identity claim."""

    def __init__(self, api: dict[str, Any], wallets: dict[str, str], now: int):
        self.api, self.wallets, self.now = api, wallets.copy(), now
        self.calls: list[str] = []

    def call(self, method: str, params: list[Any]) -> Any:
        from eth_utils import keccak

        self.calls.append(method)
        if method == "eth_chainId":
            return "0x1"
        if method == "eth_getBlockByNumber":
            return {"number": "0x64", "hash": "0x" + "ab" * 32, "timestamp": hex(self.now)}
        if method == "eth_getCode":
            return "0x60006000" if params[0] in {self.api[name] for name in ("REGISTRY", "WRAPPER", "REGISTRAR")} else "0x"
        if method == "eth_call":
            selector, argument = params[0]["data"][2:10], params[0]["data"][10:]
            if selector == keccak(text="nameExpires(uint256)")[:4].hex():
                return "0x" + format(self.now + 86400, "064x")
            if selector == keccak(text="owner(bytes32)")[:4].hex():
                owner = self.wallets.get(argument, "0x" + "00" * 20)
                return "0x" + owner[2:].rjust(64, "0")
        raise ValueError("unsupported fictional RPC method")


def access_controls(api: dict[str, Any], root: Path) -> dict[str, Any]:
    from eth_account import Account
    from eth_account.messages import encode_defunct

    a, b, outsider = Account.create(), Account.create(), Account.create()
    names = {"agi.eth": a.address.lower(), "agent.agi.eth": a.address.lower(),
             "producer.agent.agi.eth": a.address.lower(), "recipient.agent.agi.eth": b.address.lower()}
    owners = {api["namehash"](name).hex(): wallet for name, wallet in names.items()}
    readers = (SyntheticRPC(api, owners, int(time.time())), SyntheticRPC(api, owners, int(time.time())))
    readers[1].now = readers[0].now
    pin = hash_bytes(bytes.fromhex("60006000"))
    pins = api["ENSPins"](registry_sha256=pin, wrapper_sha256=pin, registrar_sha256=pin)
    authority = api["ENSAuthority"](readers, pins)
    journal = api["Journal"].initialize(root)
    access = api["ResourceAccess"](journal, api["ServiceIdentity"](origin="https://study-fixture.example"), authority)
    resource, request = hash_bytes(b"scheduling-artifact-fixture"), hash_bytes(b"fresh-invocation-fixture")

    def proof(name: str, wallet: Any) -> Any:
        challenge = access.challenge(name, wallet.address, resource, "invoke", request)
        signature = Account.sign_message(encode_defunct(text=challenge["message"]), wallet.key).signature.hex()
        return api["AccessRequest"](challenge_id=challenge["challenge_id"], signature=signature)

    allowed = []
    for name, wallet in (("producer.agent.agi.eth", a), ("recipient.agent.agi.eth", b)):
        grant = proof(name, wallet)
        prepared = access.prepare(grant, resource, "invoke", request)
        with journal.transaction() as connection:
            allowed.append(access.consume(prepared, connection))
        refuse(lambda: access.prepare(grant, resource, "invoke", request))
    denied = proof("recipient.agent.agi.eth", outsider)
    unauthorized = refuse(lambda: access.prepare(denied, resource, "invoke", request))
    revoked = proof("recipient.agent.agi.eth", b)
    for reader in readers:
        reader.wallets[api["namehash"]("recipient.agent.agi.eth").hex()] = outsider.address.lower()
    revocation = refuse(lambda: access.prepare(revoked, resource, "invoke", request))
    return {"mode": "SYNTHETIC_ENSV1_RESPONSES_REAL_EIP191_CHECKS", "authorized_names": [row["name"] for row in allowed],
            "different_wallets": allowed[0]["wallet"] != allowed[1]["wallet"], "unauthorized_refusal": unauthorized,
            "revoked_authority_refusal": revocation, "replay_refusals": 2,
            "rpc_calls": sum(len(reader.calls) for reader in readers), "network_requests": 0,
            "journal": journal.verify(), "live_ens_qualified": False, "scheduling_execution_authorized": False}


def run_controls(output: Path) -> dict[str, Any]:
    api = native()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="alpha-native-controls-") as temporary:
        fixture = accounting_fixture(Path(temporary) / "account", api)
        charge = {"activity_id": "unique-activity", "mission_id": "test", "bucket": "A", "category": "compute",
                  "accrued_micro_usd": 12, "paid_micro_usd": 0, "basis": "attested",
                  "evidence_digest": "1" * 64, "note": "Synthetic control"}
        apply(fixture, api, "charge", "charge", charge)
        duplicate = refuse(lambda: apply(fixture, api, "double", "charge", {**charge, "bucket": "B"}))
        apply(fixture, api, "invoice", "invoice", {"record_id": "invoice", "mission_id": "test",
              "amount_micro_usd": 1000, "evidence_digest": "2" * 64})
        if fixture["ledger"].report()["collected_revenue"] != 0:
            raise AssertionError("invoice became revenue")
        unknown = {**charge, "activity_id": "unknown", "accrued_micro_usd": None, "basis": "unknown"}
        apply(fixture, api, "unknown", "charge", unknown)
        report = fixture["ledger"].report()
        if report["complete_cost_profit"] is not None or report["available_funds"] is not None:
            raise AssertionError("unknown liability became a known profit")
        seal = refuse(lambda: apply(fixture, api, "incomplete-seal", "seal", {
            "mission_id": "test", "evidence_digest": "3" * 64, "categories": sorted(api["CATEGORIES"])}))
        fixture["trust"].revoke("study-accountant")
        revoked = refuse(lambda: apply(fixture, api, "revoked", "reserve", 0))
        scope = refuse(lambda: api["CapsuleManifest"](
            skill_id="scheduling-policy", version=1, origin_mission="study-enterprise", origin_record_digest="1" * 64,
            origin_agent="producer.agent.agi.eth", origin_wallet="0x" + "11" * 20, content_digest="2" * 64,
            supported_scope="manufacturing-scheduling/v1", prerequisites=[], limitations="Research policy only",
            rights="cleared-for-authenticated-network", rights_evidence="3" * 64, dependency_digests=[]))
        access = access_controls(api, Path(temporary) / "access")
        result = {"schema": "next-advantage-native-controls/v1", "source": verify_frozen_runtime(),
                  "duplicate_across_buckets_refused": duplicate, "invoice_not_revenue": True,
                  "unknown_cost_not_zero": True, "incomplete_seal_refused": seal,
                  "revoked_accounting_signer_refused": revoked, "unsupported_scheduling_scope_refused": scope,
                  "access": access, "journal": fixture["journal"].verify(),
                  "boundary": "Native accounting and access controls execute; scheduling artifacts cannot enter the protected main capsule scope. No live model, sales, ENS, settlement, or production admission."}
    (output / "controls.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    result = {}
    if args.input:
        result["account"] = replay_account(json.loads(args.input.read_text()), args.output / "account")
    if args.self_test:
        result["controls"] = run_controls(args.output / "controls")
        engine = SOURCE / "examples" / "alpha-flywheel" / "engine.mjs"
        process = subprocess.run(["node", str(STUDY / "src" / "native_lifecycle.mjs"), str(engine),
                                  str(args.output / "lifecycle.json")], capture_output=True, text=True, check=True)
        result["lifecycle"] = json.loads(process.stdout)
    print(json.dumps({"status": "PASS", "executed": list(result), "source": SOURCE_SHA}))


if __name__ == "__main__":
    main()
