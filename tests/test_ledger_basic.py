# SPDX-License-Identifier: Apache-2.0
from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.common.utils import messaging


def test_log_and_tail(tmp_path):
    ledger = Ledger(str(tmp_path / "ledger.db"), broadcast=False)
    e1 = messaging.Envelope(sender="a", recipient="b", payload={"v": 1}, ts=0.0)
    e2 = messaging.Envelope(sender="b", recipient="c", payload={"v": 2}, ts=1.0)
    ledger.log(e1)
    ledger.log(e2)
    tail = ledger.tail(2)
    assert tail[0]["payload"]["v"] == 1
    assert tail[1]["payload"]["v"] == 2
