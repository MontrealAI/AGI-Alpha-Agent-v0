# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from click.testing import CliRunner
import httpx
import pytest

from alpha_factory_v1.core.archive import Agent, Archive
from alpha_factory_v1.core.tools import transfer_test as tt

import sys
import types

# Provide a minimal 'rocketry' module so the CLI imports without optional deps
rocketry_stub = types.ModuleType("rocketry")
rocketry_stub.Rocketry = type("Rocketry", (), {})
conds_mod = types.ModuleType("rocketry.conds")
conds_mod.every = lambda *_: None
rocketry_stub.conds = conds_mod
sys.modules.setdefault("rocketry", rocketry_stub)
sys.modules.setdefault("rocketry.conds", conds_mod)

from alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface import cli  # noqa: E402


@pytest.mark.parametrize("kind", ["valid", "oversized", "compressed"])
def test_transfer_stream_is_bounded(monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    monkeypatch.setenv("ALPHA_TRANSFER_BASE_URL", "http://127.0.0.1:12345/v1")
    agent = Agent(1, {"transfer_cases": [{"prompt": "2+2", "expected": "4"}]}, 0)

    class Body(httpx.SyncByteStream):
        chunks = 0
        closed = False

        def __iter__(self):  # type: ignore[no-untyped-def]
            if kind == "oversized":
                for _ in range(256):
                    self.chunks += 1
                    yield b"x" * 65536
            else:
                self.chunks += 1
                yield b'{"choices":[{"finish_reason":"stop","message":{"content":"4"}}]}'

        def close(self) -> None:
            self.closed = True

    body = Body()

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["Accept-Encoding"] == "identity"
        headers = {"Content-Encoding": "gzip"} if kind == "compressed" else {}
        return httpx.Response(200, headers=headers, stream=body)

    client_type = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client_type(transport=httpx.MockTransport(respond), **kwargs))
    if kind == "valid":
        assert tt.evaluate_agent(agent, "test-model") == 1.0
    else:
        with pytest.raises(ValueError, match="1 MiB" if kind == "oversized" else "identity encoding"):
            tt.evaluate_agent(agent, "test-model")
    assert body.closed
    assert body.chunks <= 17


def test_run_transfer_test_writes_matrix(tmp_path, monkeypatch) -> None:
    db = tmp_path / "arch.db"
    arch = Archive(db)
    arch.add({"name": "a"}, 0.1)
    arch.add({"name": "b"}, 0.9)
    out = tmp_path / "results" / "transfer_matrix.csv"

    def fake_eval(agent, model):
        return agent.score + {"x": 1.0, "y": 2.0}[model]

    monkeypatch.setattr(tt, "evaluate_agent", fake_eval)

    tt.run_transfer_test(["x", "y"], 2, archive_path=db, out_file=out)
    lines = out.read_text().splitlines()
    assert lines[0] == "id,x,y"
    assert lines[1] == "2,1.900,2.900"
    assert lines[2] == "1,1.100,2.100"


def test_cli_transfer_test_invokes(monkeypatch) -> None:
    called = {}

    def fake_run(models, top_n):
        called["models"] = models
        called["top_n"] = top_n

    monkeypatch.setattr(tt, "run_transfer_test", fake_run)

    res = CliRunner().invoke(cli.main, ["transfer-test", "--models", "x,y", "--top-n", "2"])
    assert res.exit_code == 0
    assert called == {"models": ["x", "y"], "top_n": 2}


def test_run_transfer_test_overwrites(tmp_path, monkeypatch) -> None:
    db = tmp_path / "arch.db"
    arch = Archive(db)
    arch.add({"name": "a"}, 0.5)
    out = tmp_path / "results" / "transfer_matrix.csv"
    out.parent.mkdir(parents=True)
    out.write_text("old\n")

    def fake_eval(agent, model):
        return agent.score + 0.1

    monkeypatch.setattr(tt, "evaluate_agent", fake_eval)
    tt.run_transfer_test(["m"], 1, archive_path=db, out_file=out)
    lines = out.read_text().splitlines()
    assert lines == ["id,m", "1,0.600"]
