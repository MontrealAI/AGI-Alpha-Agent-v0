# SPDX-License-Identifier: Apache-2.0
import asyncio
import json
import logging
from google.protobuf import json_format
from pathlib import Path
from unittest import mock
import pytest

from alpha_factory_v1.common.utils import logging as insight_logging
from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.common.utils import messaging


def test_compute_merkle_root(tmp_path: Path) -> None:
    ledger = Ledger(str(tmp_path / "l.db"), broadcast=False)
    envs = [
        messaging.Envelope(sender="a", recipient="b", payload={"v": 1}, ts=0.0),
        messaging.Envelope(sender="b", recipient="c", payload={"v": 2}, ts=1.0),
        messaging.Envelope(sender="c", recipient="d", payload={"v": 3}, ts=2.0),
    ]
    for env in envs:
        ledger.log(env)
    computed = ledger.compute_merkle_root()
    hashes = []
    for env in envs:
        if hasattr(env, "DESCRIPTOR"):
            record = json_format.MessageToDict(env, preserving_proto_field_name=True)
        else:
            record = env.__dict__
        data = json.dumps(record, sort_keys=True).encode()
        hashes.append(insight_logging.blake3(data).hexdigest())  # type: ignore[attr-defined]
    manual = insight_logging._merkle_root(hashes)
    assert computed == manual


def test_broadcast_merkle_root_logs_root_when_disabled(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    ledger = Ledger(str(tmp_path / "l.db"), broadcast=False)
    env = messaging.Envelope(sender="a", recipient="b", payload={"v": 1}, ts=0.0)
    ledger.log(env)
    root = ledger.compute_merkle_root()

    caplog.set_level(logging.INFO)

    dummy = mock.Mock(side_effect=AssertionError("AsyncClient should not be used"))
    with mock.patch.object(insight_logging, "AsyncClient", dummy):
        asyncio.run(ledger.broadcast_merkle_root())

    assert not dummy.called
    assert any(f"Merkle root {root}" in r.getMessage() for r in caplog.records)


def test_json_console_formatting(capsys: pytest.CaptureFixture[str]) -> None:
    logging.getLogger().handlers.clear()
    insight_logging.setup(json_logs=True)
    log = logging.getLogger("jtest")
    log.info("hello")
    captured = capsys.readouterr()
    out = (captured.err or captured.out).strip()
    data = json.loads(out)
    assert data["msg"] == "hello"
    assert data["lvl"] == "INFO"
