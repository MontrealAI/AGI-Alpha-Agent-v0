# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import subprocess
import time

try:
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover - optional
    psycopg2 = None

import pytest

from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.common.utils import messaging

if not shutil.which("docker") or psycopg2 is None:
    pytest.skip("docker or psycopg2 missing", allow_module_level=True)


@pytest.fixture(scope="module")
def pg_container():
    cid = (
        subprocess.check_output(
            [
                "docker",
                "run",
                "-d",
                "-e",
                "POSTGRES_USER=insight",
                "-e",
                "POSTGRES_PASSWORD=insight",
                "-e",
                "POSTGRES_DB=insight",
                "-p",
                "55432:5432",
                "postgres:16-alpine",
            ]
        )
        .decode()
        .strip()
    )
    try:
        for _ in range(30):
            res = subprocess.run(
                ["docker", "exec", cid, "pg_isready", "-U", "insight"],
                capture_output=True,
            )
            if res.returncode == 0:
                break
            time.sleep(1)
        else:
            subprocess.run(["docker", "logs", cid], check=False)
            raise RuntimeError("postgres not ready")
        yield cid
    finally:
        subprocess.run(["docker", "rm", "-f", cid], check=False)


def test_ledger_postgres_persistence(pg_container):
    os.environ.update(
        {
            "PGHOST": "localhost",
            "PGPORT": "55432",
            "PGUSER": "insight",
            "PGPASSWORD": "insight",
            "PGDATABASE": "insight",
        }
    )
    ledger = Ledger("/tmp/ignore.db", db="postgres", broadcast=False)
    env = messaging.Envelope(sender="a", recipient="b", payload={"v": 1}, ts=0.0)
    ledger.log(env)
    ledger.close()

    conn = psycopg2.connect(host="localhost", port=55432, user="insight", password="insight", dbname="insight")
    with conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM messages")
        count = cur.fetchone()[0]
    conn.close()
    assert count == 1
