# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

ORIGINAL_SHA256 = "c4a8137f198e536dd6c680a8fe1c0000fe6cdb1500f13af681054f5d67d8754a"
PUBLIC_COLUMNS = {
    "config": ["id", "value"],
    "journal": ["seq", "kind", "amount"],
    "trades": ["price", "state", "custody", "refund_due"],
    "investments": ["cap", "state"],
}


def project(original: Path, destination: Path) -> dict[str, object]:
    if original.is_symlink() or not original.is_file() or original.stat().st_size > 1_048_576:
        raise ValueError("bounded regular source required")
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    if original_hash != ORIGINAL_SHA256:
        raise ValueError("this projection only accepts the frozen historical source")
    if destination.exists() or destination.is_symlink():
        raise ValueError("destination must be absent; original evidence is never overwritten")
    with sqlite3.connect(original.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as source:
        config = json.loads(source.execute("SELECT value FROM config WHERE id=1").fetchone()[0])
        public_config = {name: int(config[name]) for name in ("opening", "working")}
        journal = source.execute("SELECT seq,kind,amount FROM journal ORDER BY seq").fetchall()
        trades = source.execute("SELECT price,state,custody,refund_due FROM trades ORDER BY rowid").fetchall()
        investments = source.execute("SELECT cap,state FROM investments ORDER BY rowid").fetchall()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(destination) as output:
        output.executescript(
            "CREATE TABLE config(id INTEGER PRIMARY KEY,value TEXT NOT NULL);"
            "CREATE TABLE journal(seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,amount TEXT NOT NULL);"
            "CREATE TABLE trades(price TEXT NOT NULL,state TEXT NOT NULL,custody INTEGER NOT NULL,"
            "refund_due TEXT NOT NULL);"
            "CREATE TABLE investments(cap TEXT NOT NULL,state TEXT NOT NULL);"
        )
        output.execute("INSERT INTO config VALUES(1,?)", (json.dumps(public_config, sort_keys=True),))
        output.executemany("INSERT INTO journal VALUES(?,?,?)", journal)
        output.executemany("INSERT INTO trades VALUES(?,?,?,?)", trades)
        output.executemany("INSERT INTO investments VALUES(?,?)", investments)
    if hashlib.sha256(original.read_bytes()).hexdigest() != original_hash:
        raise ValueError("original source changed during projection")
    return {
        "schema": "agialpha/public-ledger-projection/v1",
        "classification": "historical-sanitized-derived-replay",
        "original_sha256": original_hash,
        "original_bytes": original.stat().st_size,
        "derived_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "derived_bytes": destination.stat().st_size,
        "retained_columns": PUBLIC_COLUMNS,
        "rows": {"config": 1, "journal": len(journal), "trades": len(trades), "investments": len(investments)},
        "omitted": [
            "all unlisted tables and columns",
            "private artifacts",
            "encryption material",
            "task and buyer data",
        ],
        "scope": (
            "Derived arithmetic fixture, not original exchange evidence, fresh confirmation or external profit proof"
        ),
        "original_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(project(args.original, args.destination), indent=2))


if __name__ == "__main__":
    main()
