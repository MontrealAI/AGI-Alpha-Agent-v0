# SPDX-License-Identifier: Apache-2.0
"""Backend-specific ledger tests.

Requires a running Postgres instance configured via the standard environment
variables ``PGHOST``, ``PGPORT``, ``PGUSER``, ``PGPASSWORD`` and ``PGDATABASE``.
The Postgres test is skipped when the server is unreachable or ``psycopg2`` is
not installed.
"""

from __future__ import annotations

import json
import os
from typing import Iterable

import pytest
from google.protobuf import json_format
import google.protobuf.struct_pb2  # noqa: F401 - register descriptors

from alpha_factory_v1.common.utils import logging as insight_logging
from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.common.utils import messaging

try:  # optional dependency
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover - optional
    psycopg2 = None  # type: ignore


def _expected_root(envs: Iterable[messaging.Envelope]) -> str:
    hashes: list[str] = []
    for env in envs:
        if hasattr(env, "DESCRIPTOR"):
            record = json_format.MessageToDict(env, preserving_proto_field_name=True)
        else:
            record = env.__dict__
        data = json.dumps(record, sort_keys=True).encode()
        hashes.append(insight_logging.blake3(data).hexdigest())  # type: ignore[attr-defined]
    return insight_logging._merkle_root(hashes)


def test_duckdb_merkle_root(tmp_path) -> None:
    ledger = Ledger(tmp_path / "log.duckdb", db="duckdb", broadcast=False)
    env = messaging.Envelope(sender="a", recipient="b", payload={"v": 1}, ts=0.0)
    ledger.log(env)
    assert ledger.compute_merkle_root() == _expected_root([env])


@pytest.mark.skipif(psycopg2 is None, reason="psycopg2 missing")
def test_postgres_merkle_root(tmp_path) -> None:
    params = {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", ""),
        "dbname": os.getenv("PGDATABASE", "postgres"),
    }
    try:
        conn = psycopg2.connect(**params)
    except Exception:
        pytest.skip("postgres unavailable")
    with conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS messages")
    conn.close()

    ledger = Ledger(tmp_path / "ignore.db", db="postgres", broadcast=False)
    env = messaging.Envelope(sender="a", recipient="b", payload={"v": 1}, ts=0.0)
    ledger.log(env)
    assert ledger.compute_merkle_root() == _expected_root([env])
    ledger.close()
