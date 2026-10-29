# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from alpha_factory_v1.core.runtime.structural_transfer import extract, inspect_capture, reserve_source
from contrib.compounding_discovery import project_public_ledger as projector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PUBLIC = HERE / "source-evidence/exchange-public-ledger.sqlite"


def test_public_ledger_has_only_minimal_nonsecret_fields() -> None:
    manifest = json.loads((HERE / "source-evidence/public-ledger-provenance.json").read_text())
    assert hashlib.sha256(PUBLIC.read_bytes()).hexdigest() == manifest["derived_sha256"]
    with sqlite3.connect(PUBLIC.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert db.execute("PRAGMA freelist_count").fetchone()[0] == 0
        objects = db.execute("SELECT type,name FROM sqlite_master ORDER BY name").fetchall()
        assert objects == [("table", name) for name in sorted(projector.PUBLIC_COLUMNS)]
        for table, columns in projector.PUBLIC_COLUMNS.items():
            assert [row[1] for row in db.execute("PRAGMA table_info(" + table + ")")] == columns
            assert db.execute("SELECT count(*) FROM " + table).fetchone()[0] == manifest["rows"][table]
            for row in db.execute("SELECT * FROM " + table):
                assert all(isinstance(value, (int, str)) for value in row)
        config = json.loads(db.execute("SELECT value FROM config WHERE id=1").fetchone()[0])
        assert config == {"opening": 100000000, "working": 1000000}
        assert {row[0] for row in db.execute("SELECT kind FROM journal")} <= {
            "expense",
            "expense_paid",
            "buyer_provision",
            "revenue",
            "collections",
        }
        assert {row[0] for row in db.execute("SELECT state FROM trades")} == {"released"}
        assert {row[0] for row in db.execute("SELECT state FROM investments")} == {"complete"}
        queries = ("SELECT amount FROM journal", "SELECT price,refund_due FROM trades", "SELECT cap FROM investments")
        for query in queries:
            assert all(str(value).isdigit() for row in db.execute(query) for value in row)


def test_public_capture_replays_same_arithmetic_and_rejects_wrong_amount(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    source = json.loads((HERE / "source.json").read_text())
    capture = json.loads((HERE / "capture.json").read_text())
    assert extract(source) == capture
    assert inspect_capture(capture)["valid"] is True
    result = capture["observation"]["result"]
    assert (result["cash"], result["obligations"], result["free"]) == ("128994728", "92200000", "36794728")
    target = source["task"]["target"]
    assert reserve_source.verify(target, result)["accepted"] is True
    changed = {**result, "free": str(int(result["free"]) + 1)}
    assert reserve_source.verify(target, changed)["accepted"] is False


def test_projection_omits_private_bytes_and_preserves_independent_arithmetic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original, derived = tmp_path / "private.sqlite", tmp_path / "public.sqlite"
    private_marker = "PRIVATE_PROJECTION_TEST_MARKER_NEVER_PUBLISH"
    with sqlite3.connect(original) as db:
        db.executescript(
            "CREATE TABLE config(id INTEGER,value TEXT);"
            "CREATE TABLE journal(seq INTEGER,kind TEXT,amount TEXT);"
            "CREATE TABLE trades(price TEXT,state TEXT,custody INTEGER,refund_due TEXT,"
            "cipher BLOB,key BLOB,nonce BLOB);"
            "CREATE TABLE investments(cap TEXT,state TEXT);"
            "CREATE TABLE private_artifacts(cipher BLOB,key BLOB,nonce BLOB);"
        )
        config = json.dumps({"opening": 1000, "working": 10, "private": private_marker})
        db.execute("INSERT INTO config VALUES(1,?)", (config,))
        rows = [(1, "collections", "100"), (2, "expense", "20"), (3, "expense_paid", "5")]
        db.executemany("INSERT INTO journal VALUES(?,?,?)", rows)
        db.execute("INSERT INTO trades VALUES('50','funded',1,'3',?,?,?)", (private_marker.encode(),) * 3)
        db.execute("INSERT INTO investments VALUES('7','reserved')")
        db.execute("INSERT INTO private_artifacts VALUES(?,?,?)", (private_marker.encode(),) * 3)
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    monkeypatch.setattr(projector, "ORIGINAL_SHA256", original_hash)
    manifest = projector.project(original, derived)
    assert private_marker.encode() not in derived.read_bytes()
    assert original_hash == hashlib.sha256(original.read_bytes()).hexdigest()
    useful = tmp_path / "useful.json"
    useful.write_text("{}\n")
    target = {
        "id": "public-projection-regression",
        "database": str(original),
        "database_sha256": original_hash,
        "useful_artifact": str(useful),
        "useful_artifact_sha256": hashlib.sha256(useful.read_bytes()).hexdigest(),
    }
    original_result = reserve_source.snapshot(target)
    assert reserve_source.verify(target, original_result)["accepted"] is True
    public_target = {**target, "database": str(derived), "database_sha256": manifest["derived_sha256"]}
    public_result = reserve_source.snapshot(public_target)
    assert reserve_source.verify(public_target, public_result)["accepted"] is True
    for field in ("cash", "obligations", "free", "decomposition"):
        assert original_result[field] == public_result[field]
    assert (public_result["cash"], public_result["obligations"], public_result["free"]) == ("1095", "85", "1010")
    with pytest.raises(ValueError, match="destination must be absent"):
        projector.project(original, derived)


def test_every_public_example_binds_the_new_capture() -> None:
    capture = json.loads((HERE / "capture.json").read_text())
    request = json.loads((HERE / "example-request.json").read_text())
    mission = json.loads((HERE / "example-mission.json").read_text())
    assert request["captures"] == [capture]
    assert mission["work"]["request"]["captures"] == [capture]
    assert capture["source"]["task"]["target"]["database"].endswith("exchange-public-ledger.sqlite")
    assert "Historical sanitized derived replay" in capture["source"]["context"]
    assert "exchange.sqlite" not in json.dumps([capture, request, mission])
