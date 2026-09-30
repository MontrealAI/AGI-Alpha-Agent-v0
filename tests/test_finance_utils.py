# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import patch
import statistics

from alpha_factory_v1.backend.agents import finance_agent


class TestFinanceUtils(unittest.TestCase):
    def test_pct_basic(self):
        self.assertAlmostEqual(finance_agent._pct(100.0, 110.0), 0.1)
        self.assertEqual(finance_agent._pct(0.0, 5.0), 0.0)

    def test_cf_var_fallback(self):
        returns = [0.01, -0.02, 0.005, 0.015]
        mu = statistics.mean(returns)
        sig = statistics.pstdev(returns) or 1e-9
        expected = max(0.0, -(mu + statistics.NormalDist().inv_cdf(0.01) * sig))
        with (
            patch.object(finance_agent, "np", None, create=True),
            patch.object(finance_agent, "skew", None, create=True),
            patch.object(finance_agent, "kurtosis", None, create=True),
            patch.object(finance_agent, "erfcinv", None, create=True),
        ):
            self.assertAlmostEqual(finance_agent._cf_var(returns), expected)

    def test_cvar(self):
        returns = [-0.1, 0.2, -0.05, 0.03]
        expected = 0.1
        self.assertAlmostEqual(finance_agent._cvar(returns), expected)
        self.assertEqual(finance_agent._cvar([]), 0.0)
        self.assertEqual(finance_agent._cvar([0.01, 0.02]), 0.0)

    def test_constant_risk_and_confidence(self):
        self.assertEqual(finance_agent._cf_var([0.01] * 5), 0.0)
        self.assertEqual(finance_agent._cf_var([-0.02] * 5), 0.02)
        with self.assertRaises(ValueError):
            finance_agent._cf_var([0.1, 0.2], 1)

    def test_simulator_does_not_reset_process_random_state(self):
        import random

        state = random.getstate()
        first = finance_agent._SimExchange()
        second = finance_agent._SimExchange()
        self.assertEqual([first.price("TEST") for _ in range(3)], [second.price("TEST") for _ in range(3)])
        self.assertEqual(random.getstate(), state)

    def test_planner_uses_cash_to_open_initial_positions(self):
        planner = object.__new__(finance_agent._Planner)
        orders = planner.rollout(finance_agent._Portfolio(), {"TEST": 100}, {"TEST": 0.5}, cash=10000)
        self.assertEqual(orders[0]["qty"], 50)

    def test_pnl_is_actual_cash_plus_marked_positions(self):
        from types import SimpleNamespace

        agent = object.__new__(finance_agent.FinanceAgent)
        agent.cfg = SimpleNamespace(start_balance=10000)
        agent.cash, agent.realized_pnl, agent.halted = 4995.0, 0.0, False
        agent.cost_basis = {"TEST": 5005.0}
        agent.portfolio = finance_agent._Portfolio()
        agent.portfolio.update("TEST", 50)
        observed = []
        agent.pnl_g = SimpleNamespace(set=observed.append)
        with patch.object(finance_agent, "_publish") as publish:
            agent._publish_state({"TEST": 110}, {})
        payload = publish.call_args.args[1]
        self.assertEqual(payload["pnl"], 495)
        self.assertEqual(payload["unrealized_pnl"], 495)
        self.assertEqual(observed, [0.0])

    def test_price_error_never_substitutes_a_tradable_quote(self):
        from types import SimpleNamespace

        agent = object.__new__(finance_agent.FinanceAgent)
        with patch.object(finance_agent._SimExchange, "price", side_effect=OSError("unavailable")):
            agent.broker = finance_agent._SimExchange()
            agent.history = {"TEST": [100]}
            with self.assertRaises(OSError):
                agent._safe_price("TEST")
        agent.broker = SimpleNamespace(price=lambda _: float("nan"))
        with self.assertRaises(ValueError):
            agent._safe_price("TEST")

    def test_testnet_cost_uses_fill_receipt_instead_of_later_market_price(self):
        from types import SimpleNamespace

        broker = object.__new__(finance_agent._BinanceBroker)
        receipt = {
            "status": "FILLED",
            "executedQty": "2",
            "cummulativeQuoteQty": "210",
            "fills": [{"commission": "0.21", "commissionAsset": "USDT"}],
        }
        broker.cli = SimpleNamespace(create_order=lambda **kwargs: receipt)
        self.assertAlmostEqual(broker.market("BUY", 2, "BTCUSDT"), 210.21)
        self.assertAlmostEqual(broker.market("SELL", 2, "BTCUSDT"), -209.79)
        receipt["status"] = "PARTIALLY_FILLED"
        with self.assertRaises(RuntimeError):
            broker.market("BUY", 2, "BTCUSDT")
        receipt["status"] = "FILLED"
        receipt["fills"][0]["commissionAsset"] = "BNB"
        with self.assertRaises(RuntimeError):
            broker.market("BUY", 2, "BTCUSDT")

    def test_paper_broker_is_explicit_default_and_real_mode_is_rejected(self):
        self.assertEqual(finance_agent._FinCfg().broker_mode, "paper")
        with self.assertRaises(ValueError):
            finance_agent._FinCfg(broker_mode="live")

    def test_maxdd(self):
        returns = [0.1, -0.2, 0.05, -0.1]
        self.assertAlmostEqual(finance_agent._maxdd(returns), 0.244)

    def test_portfolio(self):
        p = finance_agent._Portfolio()
        p.update("BTC", 1.0)
        self.assertEqual(p.qty("BTC"), 1.0)
        self.assertEqual(p.book(), {"BTC": 1.0})
        self.assertEqual(p.value({"BTC": 100.0}), 100.0)
        p.update("BTC", -1.0)
        self.assertEqual(p.qty("BTC"), 0.0)
        self.assertEqual(p.book(), {})


if __name__ == "__main__":  # pragma: no cover - manual execution
    unittest.main()
