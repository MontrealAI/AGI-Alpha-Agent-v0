# SPDX-License-Identifier: Apache-2.0
"""Behavior, evidence integrity and existing-transport integration regressions."""

from __future__ import annotations

import ast
import base64
import copy
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

from contrib.upgrade_decision.core import (
    assess,
    call_shape,
    canonical,
    constraint_accepts,
    declaration,
    load,
    metadata,
    mission_key,
    parse,
    sha,
    signature_accepts,
    validate,
    verify,
)
from contrib.upgrade_decision.delivery import accounting, markdown, render_html

HERE = Path(__file__).resolve().parent


def source(text: str, path: str) -> dict[str, Any]:
    return {
        "repository": "MontrealAI/AGI-Alpha-Agent-v0",
        "commit": "a" * 40,
        "path": path,
        "text": text,
        "sha256": sha(text.encode()),
    }


def request(
    before: str = "def check(x, *, strict=False): pass\n",
    after: str = "def check(x): pass\n",
    consumer: str = "from pkg.api import check\ncheck(1, strict=True)\n",
) -> dict[str, Any]:
    call = next(n for n in ast.walk(ast.parse(consumer)) if isinstance(n, ast.Call))
    return {
        "schema": "alpha-upgrade-call-request/v1",
        "id": "contract-fixture",
        "title": "Fixture contract",
        "purpose": "Test an explicit captured call contract.",
        "sources": {
            "before": source(before, "pkg/api.py"),
            "after": source(after, "pkg/api.py"),
            "consumer": source(consumer, "consumer.py"),
        },
        "calls": [
            {
                "id": "selected-call",
                "consumer": "consumer",
                "line": call.lineno,
                "column": call.col_offset,
                "callee": ast.unparse(call.func),
                "before": {"source": "before", "symbol": "check"},
                "after": {"source": "after", "symbol": "check"},
                "mapping": {"kind": "direct-import", "explanation": "Captured explicit import."},
            }
        ],
        "historicalEvidence": [],
        "recordedChecks": [],
    }


def test_actionable_conflict_has_sources_and_an_independent_binding_check() -> None:
    pack = request()
    result = assess(pack)
    assert result["nextAction"] == "HOLD_UPDATE_AND_TEST"
    assert result["engineeringAcceptance"] is True and result["customerAcceptance"] == "unknown"
    row = result["calls"][0]
    assert row["mappingVerified"] and row["beforeAccepts"] is True and row["afterAccepts"] is False
    assert len(row["evidence"]) == 3 and all("/blob/" in x["url"] for x in row["evidence"])
    assert result["review"]["verifier"]["accepted"] and not result["review"]["critic"]
    assert result["resources"]["networkRequests"]["value"] == 0


def test_no_issue_and_no_blanket_upgrade_authorization() -> None:
    text = "def check(x, *, strict=False): pass\n"
    result = assess(request(text, text))
    assert result["calls"][0]["status"] == "BINDING_PRESERVED"
    assert result["nextAction"] == "RUN_BEHAVIOR_AND_SECURITY_CHECKS"
    assert result["review"]["critic"] == [] and result["review"]["corrections"] == []


def test_nested_super_calls_are_bound_by_callee_as_well_as_location() -> None:
    pack = load((HERE / "examples/historical.json").read_bytes())
    result = assess(pack)
    assert result["calls"][0]["status"] == "BINDING_CONFLICT"
    assert result["calls"][0]["beforeAccepts"] is True and result["calls"][0]["afterAccepts"] is False
    assert result["calls"][0]["mappingVerified"] is False
    assert result["review"]["critic"][0]["kind"] == "dispatch-unproved"
    assert "unproved" in result["calls"][0]["qualification"]


@pytest.mark.parametrize("callee", ["Client(1)", "Client.__init__(object(), 1)"])
def test_constructor_receiver_cannot_be_guessed_by_two_binders(callee: str) -> None:
    pack = request(
        "class Client:\n def __init__(self, x=0): pass\n",
        "class Client:\n def __init__(self): pass\n",
        "from pkg.api import Client\n" + callee + "\n",
    )
    for side in ("before", "after"):
        pack["calls"][0][side]["symbol"] = "Client.__init__"
    result = assess(pack)
    row = result["calls"][0]
    assert row["status"] == "UNRESOLVED" and "receiver dispatch" in row["reason"]
    assert row["beforeAccepts"] is None and row["afterAccepts"] is None
    assert result["nextAction"] == "REVIEW_UNRESOLVED_SCOPE"
    row.update(status="BINDING_PRESERVED", beforeAccepts=True, afterAccepts=True, mappingVerified=True)
    assert verify(pack, result)["accepted"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r["calls"][0].update(beforeAccepts=False),
        lambda r: r["calls"][0].update(snippet="another call"),
        lambda r: r["calls"][0]["evidence"][0].update(sha256="0" * 64),
        lambda r: r.update(nextAction="RUN_BEHAVIOR_AND_SECURITY_CHECKS"),
        lambda r: r.update(title="a forged outcome"),
        lambda r: r["sourceInventory"][0].update(commit="0" * 40),
        lambda r: r["calls"].append(copy.deepcopy(r["calls"][0])),
    ],
)
def test_substantiated_forgery_is_rejected(mutation: Any) -> None:
    pack = request()
    record = assess(pack)
    mutation(record)
    assert verify(pack, record)["accepted"] is False


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["sources"]["before"].update(text="def changed(): pass"),
        lambda p: p["sources"]["before"].update(path="../secret.py"),
        lambda p: p["sources"]["before"].update(commit="main"),
        lambda p: p["sources"]["before"].update(repository="private endpoint"),
        lambda p: p.update(command="execute arbitrary code"),
        lambda p: p["calls"].append(copy.deepcopy(p["calls"][0])),
        lambda p: p["calls"][0].update(line=True),
    ],
)
def test_corrupt_or_unsupported_input_refuses(change: Any) -> None:
    pack = request()
    change(pack)
    with pytest.raises((ValueError, TypeError)):
        assess(pack)


@pytest.mark.parametrize(
    "consumer",
    [
        "from pkg.api import check\ncheck(*values)\n",
        "from pkg.api import check\ncheck(1, **values)\n",
    ],
)
def test_dynamic_arguments_remain_unresolved(consumer: str) -> None:
    result = assess(request(consumer=consumer))
    assert result["calls"][0]["status"] == "UNRESOLVED"
    assert result["nextAction"] == "REVIEW_UNRESOLVED_SCOPE"


def test_shadowed_direct_import_is_not_an_affected_runtime_call() -> None:
    result = assess(request(consumer="from pkg.api import check\ncheck = other\ncheck(1, strict=True)\n"))
    assert result["calls"][0]["mappingVerified"] is False
    assert result["calls"][0]["status"] == "BINDING_CONFLICT"
    assert "unproved" in result["calls"][0]["qualification"]


def test_explicit_module_rebinding_does_not_become_a_verified_import() -> None:
    pack = request(before="def check(x, *, strict=False): pass\ncheck = replacement\n")
    result = assess(pack)
    assert result["calls"][0]["mappingVerified"] is False


def test_mutated_module_attribute_does_not_become_a_verified_import() -> None:
    pack = request(consumer="import pkg.api as api\napi.check = replacement\napi.check(1, strict=True)\n")
    call = next(n for n in ast.walk(ast.parse(pack["sources"]["consumer"]["text"])) if isinstance(n, ast.Call))
    pack["calls"][0].update(line=call.lineno, column=call.col_offset, callee=ast.unparse(call.func))
    assert assess(pack)["calls"][0]["mappingVerified"] is False


def test_decorated_declaration_remains_unresolved() -> None:
    result = assess(request(before="@decorator\ndef check(x, *, strict=False): pass\n"))
    assert result["calls"][0]["status"] == "UNRESOLVED"


def test_standard_python_bind_oracle_covers_shapes_not_an_implementation_mirror() -> None:
    declarations = [
        "def check(a, /, b=1, *, c): pass",
        "def check(a, /, **kw): pass",
        "def check(*a, b=1, **kw): pass",
        "def check(a=1, *b, c=1): pass",
        "def check(): pass",
        "def check(a, b): pass",
    ]
    for text in declarations:
        fn = declaration(parse(text), "check")
        for count in range(5):
            for mask in range(16):
                shape = {
                    "positionalCount": count,
                    "keywordNames": [name for i, name in enumerate(("a", "b", "c", "extra")) if mask & (1 << i)],
                }
                assert constraint_accepts(metadata(fn), shape) == signature_accepts(fn, shape)


def test_rendered_report_is_derived_and_escapes_supplied_text() -> None:
    pack = request()
    pack["title"] = "<script>alert(1)</script>"
    result = assess(pack)
    page = render_html(result)
    assert "<h1><script>" not in page and "&lt;script&gt;" in page
    assert 'lang="fr"' in page and "inconnu" in page and "inconnus" not in markdown(result, "en")
    assert "HOLD_UPDATE_AND_TEST" not in markdown(result, "fr")


def test_unknown_costs_are_not_zero_and_construction_is_not_per_attempt() -> None:
    costs, ledger = accounting(assess(request()))
    assert all(s["humanBaseline"]["minutesPerAccepted"]["value"] is None for s in costs["scenarios"])
    assert all(op["unitCostMicros"]["value"] is None for s in costs["scenarios"] for op in s["operations"])
    assert len([e for e in ledger["events"] if e.get("category") == "capability"]) == 1
    assert next(e for e in ledger["events"] if e["id"] == "collected")["amountMinor"] == 0
    assert all(s["investments"] for s in costs["scenarios"])


def test_duplicate_json_and_bounded_frame_refuse() -> None:
    with pytest.raises(ValueError):
        load(b'{"id":1,"id":2}')
    with pytest.raises(ValueError):
        load(b" " * 750_001)


def test_call_mission_identity_ignores_rendering_and_repeat_receipts() -> None:
    first = request()
    repeated = copy.deepcopy(first)
    repeated.update(id="another-title", title="Another rendering", historicalEvidence=[])
    repeated["calls"][0]["mapping"]["explanation"] = "Reworded explanation"
    repeated["calls"][0]["mapping"]["kind"] = "declared-target"
    assert mission_key(first) == mission_key(repeated)
    changed = request(after="def check(x, *, changed=False): pass\n")
    assert mission_key(first) != mission_key(changed)


@pytest.fixture
def worker(tmp_path: Path) -> Any:
    from contrib.upgrade_decision.worker import UpgradeDecisionWorker

    for name in ("catalog.json", "historical.json", "native-component.json"):
        shutil.copyfile(HERE / "examples" / name, tmp_path / name)
    return UpgradeDecisionWorker(
        tmp_path / "catalog.json",
        python=Path(sys.executable),
        node=Path(str(shutil.which("node"))),
        git=Path(str(shutil.which("git"))),
    )


def limits() -> dict[str, Any]:
    return {
        "service_work": 1,
        "improvement_work": 0,
        "native_calls": 0,
        "native_solve_seconds": 0,
        "wall_seconds": 60,
        "allow_native": False,
        "source_hash": "a" * 64,
    }


def test_complete_fixed_worker_package_and_canonical_ledgers(worker: Any) -> None:
    charges = []
    reply = worker.execute(
        "run-mission", worker.prepare_input("starlette-httpx-historical"), limits(), lambda **kw: charges.append(kw)
    )
    assert reply["verified"] and charges.count({"service_work": 1}) == 1
    item = reply["result"]["download"]
    raw = base64.b64decode(item["base64"], validate=True)
    assert sha(raw) == item["sha256"] and len(raw) == item["bytes"]
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        hashes = json.loads(archive.read("checksums.json"))
        assert set(archive.namelist()) == {*hashes, "checksums.json"}
        assert all(sha(archive.read(name)) == digest for name, digest in hashes.items())
        record = json.loads(archive.read("decision-record.json"))
        assert verify(json.loads(archive.read("source-pack.json")), record)["accepted"]
        assert "Prochaine action" in archive.read("report.fr.md").decode()
    analysis = reply["result"]["costSummary"]
    assert analysis["ledger"]["observed"]["availableSurplus"] is None
    assert all(s["costs"]["fullyLoadedMicrosPerAccepted"] is None for s in analysis["accounting"]["scenarios"])


def test_changed_registry_and_unlisted_input_refuse(worker: Any) -> None:
    with pytest.raises(ValueError):
        worker.prepare_input("unlisted")
    worker.registry.write_bytes(b"{}")
    with pytest.raises(ValueError):
        worker.execute("run-mission", {}, limits(), lambda **kw: None)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda v: v.update(allow_native=True),
        lambda v: v.update(improvement_work=1),
        lambda v: v.update(service_work=999),
        lambda v: v.update(wall_seconds=0),
        lambda v: v.update(service_work=2),
    ],
)
def test_permission_and_budget_expansion_refuses(worker: Any, mutation: Any) -> None:
    caps = limits()
    mutation(caps)
    with pytest.raises(ValueError):
        worker.execute("run-mission", worker.prepare_input("starlette-httpx-historical"), caps, lambda **kw: None)
