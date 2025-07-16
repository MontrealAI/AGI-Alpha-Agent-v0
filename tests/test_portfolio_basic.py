import os
import json
import tempfile
import asyncio
from unittest import mock
from alpha_factory_v1.backend import portfolio


def test_portfolio_record_and_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "book.jsonl")
        p = portfolio.Portfolio(portfolio.Path(path))
        with mock.patch.object(portfolio.Portfolio, "_broadcast", lambda *a, **k: None):
            p.record_fill("BTC", 1.0, 100.0, "BUY")
            p.record_fill("BTC", 0.5, 110.0, "SELL")
            asyncio.run(p.arecord_fill("BTC", 0.5, 120.0, "BUY"))
        assert p.position("BTC") == 1.0
        assert p.book()["BTC"] == 1.0
        hist = list(p.history())
        assert len(hist) == 3
        assert hist[0].symbol == "BTC"
        assert hist[1].side == "SELL"
        # ensure persisted json
        with open(path) as fh:
            lines = fh.read().splitlines()
        assert len(lines) == 3
        rec = json.loads(lines[0])
        assert rec["symbol"] == "BTC"
        p.clear()
        assert p.book() == {}
