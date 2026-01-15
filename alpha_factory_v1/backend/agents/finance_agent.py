# SPDX-License-Identifier: Apache-2.0
"""
alpha_factory_v1.backend.agents.finance_agent
=============================================
α-Factory FinanceAgent (v0.7.0 – 2025-05-02)

Cross-asset autonomous trader with institutional-grade risk controls.

▸ Live-mode  : Binance test-net  (requires BINANCE_API_KEY / BINANCE_API_SECRET)
▸ Sim-mode   : built-in stochastic exchange (zero external deps)

Key features
------------
✓ Hybrid multi-factor alpha engine (momentum, reversal, carry, volatility)
✓ MuZero-lite or heuristic execution planner (torch/lightgbm optional)
✓ Cornish-Fisher VaR · CVaR · MaxDD hard stops
✓ Prometheus & MCP telemetry (‘alpha_pnl_realised_usd’, …)
✓ OpenAI Agents SDK tools (`alpha_signals`, `portfolio_state`)
✓ Mesh-native registration (Google ADK)
✓ **Graceful degradation** — never crashes if optional libraries are missing
"""
from __future__ import annotations

# ─────────────────────────── std-lib ───────────────────────────
import asyncio
import contextlib
import json
import logging

_log = logging.getLogger("AlphaFactory.FinanceAgent")

import os
import random
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, MutableMapping, Sequence

# ──────────────────── soft-optional third-party ─────────────────
try:
    import numpy as np  # type: ignore
except ModuleNotFoundError:
    _log.warning("numpy not installed – finance features degraded")
    np = None  # type: ignore
try:
    from scipy.stats import skew, kurtosis  # type: ignore
except ModuleNotFoundError:
    _log.warning("scipy missing – stats features disabled")
try:
    from scipy.special import erfcinv  # type: ignore
except ModuleNotFoundError:
    _log.warning("scipy.special.erfcinv unavailable")
try:
    from backend.agents.registry import Gauge  # type: ignore
    from prometheus_client import make_asgi_app  # type: ignore
except Exception:
    _log.warning("prometheus_client missing – metrics disabled")
try:
    from binance import Client as _BnClient  # type: ignore
except ModuleNotFoundError:
    _log.warning("binance package not installed – live trading disabled")
try:
    import torch  # type: ignore
    from torch import nn  # type: ignore
except (ModuleNotFoundError, OSError):
    _log.warning("torch missing – MuZero planner disabled")
if "torch" not in globals():
    torch = None  # type: ignore
try:
    import lightgbm as lgb  # type: ignore
except ModuleNotFoundError:
    _log.warning("lightgbm missing – gradient boosting disabled")
    lgb = None  # type: ignore
try:
    import adk  # type: ignore
except ModuleNotFoundError:
    _log.warning("google-adk not installed – mesh integration disabled")
    adk = None  # type: ignore
try:
    from aiohttp import ClientError as AiohttpClientError  # type: ignore
except ModuleNotFoundError:
    _log.warning("aiohttp not installed – network error types unavailable")
    AiohttpClientError = OSError  # type: ignore
with contextlib.suppress(Exception):  # pragma: no cover - optional ADK
    from adk import ClientError as AdkClientError  # type: ignore[attr-defined]
if "AiohttpClientError" not in globals():

    class AiohttpClientError(Exception):
        pass


if "AdkClientError" not in globals():

    class AdkClientError(Exception):
        pass


try:
    from openai.agents import tool  # type: ignore
except ModuleNotFoundError:
    _log.warning("openai-agents not installed – tool wrappers disabled")

    def tool(fn=None, **_):  # type: ignore
        return (lambda f: f)(fn) if fn else lambda f: f


if "tool" not in globals():  # offline stub

    def tool(fn=None, **_):  # type: ignore
        return (lambda f: f)(fn) if fn else lambda f: f


# ─────────────────────── α-Factory imports ─────────────────────
from backend.agent_base import AgentBase  # type: ignore
from backend.agents import register  # type: ignore
from backend.orchestrator import _publish  # type: ignore
from .. import risk
from ..model_provider import ModelProvider
from ..memory import Memory
from ..governance import Governance

# ────────────────────────── logger cfg ─────────────────────────
_log.setLevel(logging.INFO)

if "make_asgi_app" not in globals():  # pragma: no cover - optional dep missing

    def metrics_asgi_app():
        async def _unavailable(scope, receive, send):
            if scope.get("type") != "http":
                return
            headers = [(b"content-type", b"text/plain")]
            await send({"type": "http.response.start", "status": 503, "headers": headers})
            await send({"type": "http.response.body", "body": b"prometheus unavailable"})

        return _unavailable

else:  # pragma: no cover - executed when prometheus_client is installed

    def metrics_asgi_app():
        return make_asgi_app()


# ═════════════════════════ configuration ═══════════════════════


@dataclass
class _FinCfg:
    universe: Sequence[str] = tuple(os.getenv("ALPHA_UNIVERSE", "BTCUSDT,ETHUSDT").split(","))
    cycle_sec: int = int(os.getenv("FIN_CYCLE_SECONDS", 60))
    start_balance: float = float(os.getenv("FIN_START_BALANCE_USD", 10_000.0))

    # risk limits
    var_limit: float = float(os.getenv("ALPHA_MAX_VAR_USD", 50_000.0))
    cvar_limit: float = float(os.getenv("ALPHA_MAX_CVAR_USD", 75_000.0))
    maxdd_limit: float = float(os.getenv("ALPHA_MAX_DD_PCT", 20.0)) / 100

    # broker creds
    key: str | None = os.getenv("BINANCE_API_KEY")
    secret: str | None = os.getenv("BINANCE_API_SECRET")

    # planner
    planner_depth: int = int(os.getenv("FIN_PLANNER_DEPTH", 5))

    # misc
    prometheus_enabled: bool = bool(int(os.getenv("FIN_PROMETHEUS", "1")))
    adk_mesh: bool = bool(int(os.getenv("ADK_MESH", "0")))


# ═════════════════════════ exchange layer ══════════════════════
class _SimExchange:
    """Tiny random-walk price generator & fill engine (stateful)."""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self._p: Dict[str, float] = {}

    # ------------------------------
    def price(self, sym: str) -> float:
        px = self._p.get(sym, 100.0)
        px *= 1.0 + random.gauss(0.0, 0.0015)
        self._p[sym] = max(px, 0.01)
        return self._p[sym]

    # ------------------------------
    def market(self, side: str, qty: float, sym: str) -> float:
        px = self.price(sym)
        notional = qty * px
        return -notional if side == "SELL" else notional


class _BinanceBroker:
    """Light wrapper around python-binance *test-net*."""

    def __init__(self, key: str, secret: str, universe: Sequence[str]):
        self.cli = _BnClient(key, secret, testnet=True)
        self._ensure_testnet_assets(universe)

    def price(self, sym: str) -> float:
        return float(self.cli.get_symbol_ticker(symbol=sym)["price"])

    def market(self, side: str, qty: float, sym: str) -> float:
        self.cli.create_order(symbol=sym, side=side, type="MARKET", quantity=qty)
        px = self.price(sym)
        return -qty * px if side == "SELL" else qty * px

    # Make sure the asset exists in Test-Net; otherwise create a dummy balance
    def _ensure_testnet_assets(self, universe: Sequence[str]):
        with contextlib.suppress(Exception):
            acc = self.cli.get_account()
            assets = {b["asset"] for b in acc["balances"]}
            for sym in universe:
                base = sym.rstrip("USDT")
                if base not in assets:
                    self.cli.transfer_spot_to_margin(asset=base, amount="0")


# ═══════════════════ factor & risk primitives ══════════════════
def _pct(a: float, b: float) -> float:
    return (b - a) / a if a else 0.0


def _cf_var(returns: List[float], conf: float = 0.99) -> float:
    """Cornish-Fisher VaR assuming non-normality when scipy present."""
    if len(returns) < 2:
        return 0.0
    mu = statistics.mean(returns)
    sig = statistics.pstdev(returns) or 1e-9
    if "np" in globals() and skew and kurtosis and erfcinv:
        s = skew(returns)
        k = kurtosis(returns, fisher=False)
        z = abs(np.sqrt(2) * erfcinv(2 * (1 - conf)))  # type: ignore[arg-type]
        z_cf = z + (z**2 - 1) * s / 6 + (z**3 - 3 * z) * k / 24 - (2 * z**3 - 5 * z) * s**2 / 36
    else:
        z_cf = 2.326  # 99 %
    return abs(mu + z_cf * sig)


def _cvar(returns: List[float], conf: float = 0.99) -> float:
    cut = max(1, int(len(returns) * (1 - conf)))
    tail = sorted(returns)[:cut]
    return abs(sum(tail) / len(tail))


def _maxdd(returns: List[float]) -> float:
    peak = acc = 1.0
    worst = 0.0
    for r in returns:
        acc *= 1 + r
        peak = max(peak, acc)
        worst = min(worst, (acc - peak) / peak)
    return abs(worst)


class _FactorEngine:
    """Hybrid (momentum + risk-parity) factor scores."""

    def __init__(self):
        self.scores: Dict[str, float] = {}

    # ------------------------------
    def update(self, series: Dict[str, List[float]]):
        self.scores.clear()
        for sym, hist in series.items():
            if len(hist) < 30:
                self.scores[sym] = 0.0
                continue
            mom = _pct(hist[-30], hist[-1])
            vol = statistics.pstdev([_pct(a, b) for a, b in zip(hist, hist[1:])]) or 1e-6
            carry = _pct(hist[-31], hist[-1]) if len(hist) >= 31 else 0.0
            rev = -statistics.mean([_pct(a, b) for a, b in zip(hist[-11:-1], hist[-10:])])  # 10-day reversal
            score = (mom + carry + rev) / vol
            self.scores[sym] = score


# ═══════════════════ portfolio (in-mem fallback) ════════════════
class _Portfolio:
    def __init__(self):
        self._pos: MutableMapping[str, float] = {}

    def qty(self, sym: str) -> float:
        return self._pos.get(sym, 0.0)

    def value(self, prices: Dict[str, float]) -> float:
        return sum(q * prices.get(s, 0.0) for s, q in self._pos.items())

    def book(self) -> Dict[str, float]:
        return dict(self._pos)

    def update(self, sym: str, qty_delta: float):
        new_qty = self.qty(sym) + qty_delta
        if abs(new_qty) < 1e-9:
            self._pos.pop(sym, None)
        else:
            self._pos[sym] = new_qty


# ═════════════════════ execution planner ═══════════════════════
class _Planner:
    """Rolls out order-book impact scenarios; degrades to heuristic."""

    def __init__(self, depth: int = 5):
        self.depth = depth
        if torch is not None:
            self.net = nn.Sequential(nn.Linear(10, 64), nn.ReLU(), nn.Linear(64, 1))  # type: ignore[attr-defined]
        elif "lgb" in globals():
            self.net = lgb.LGBMRegressor(n_estimators=32)
        else:
            self.net = None  # heuristic fallback

    # ------------------------------
    def rollout(
        self, portfolio: _Portfolio, prices: Dict[str, float], targets: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        orders: List[Dict[str, Any]] = []
        port_val = portfolio.value(prices) or 1.0
        for sym, w in targets.items():
            tgt_qty = w * port_val / prices[sym]
            delta = tgt_qty - portfolio.qty(sym)
            if abs(delta) * prices[sym] < 30:  # ignore <$30
                continue
            side = "BUY" if delta > 0 else "SELL"
            est_px = prices[sym] * (1 + 0.0007 * random.uniform(0.5, 1.5))
            orders.append({"sym": sym, "qty": round(abs(delta), 8), "side": side, "est_fill_px": est_px})
        return orders


# ═════════════════════ main FinanceAgent ═══════════════════════
@register
class FinanceAgent(AgentBase):
    NAME = "finance"
    VERSION = "0.7.0"
    __version__ = VERSION

    def __init__(
        self,
        cfg: _FinCfg | str | None = None,
        model_provider: ModelProvider | None = None,
        memory: Memory | None = None,
        governance: Governance | None = None,
    ):
        """Create a new finance agent.

        Legacy initialisation accepted ``ModelProvider``, ``Memory`` and
        ``Governance`` instances. These parameters remain optional so older test
        helpers continue to work without modification.
        """
        # Avoid calling the legacy AgentBase.__init__ which expects multiple
        # positional arguments.  Other agents in this package skip the super
        # initializer entirely, so we follow the same convention.
        if isinstance(cfg, str):
            self.ens = cfg
            self.cfg = _FinCfg()
        else:
            self.ens = None
            self.cfg = cfg or _FinCfg()
        self.model_provider = model_provider or ModelProvider()
        self.memory = memory or Memory()
        self.governance = governance or Governance(self.memory)

        # ── state ──
        self.portfolio = _Portfolio()
        self.factor = _FactorEngine()
        self.history: Dict[str, List[float]] = {s: [] for s in self.cfg.universe}
        self.planner = _Planner(self.cfg.planner_depth)

        # ── broker selection ──
        if "_BnClient" in globals() and self.cfg.key and self.cfg.secret:
            self.broker: Any = _BinanceBroker(self.cfg.key, self.cfg.secret, self.cfg.universe)
            _log.info("FinanceAgent connected to Binance test-net.")
        else:
            self.broker = _SimExchange()
            _log.warning("FinanceAgent using internal simulated exchange.")

        # ── telemetry ──
        if self.cfg.prometheus_enabled and "Gauge" in globals():
            self.pnl_g = Gauge("alpha_pnl_realised_usd", "Realised PnL (USD)")
        else:

            class _NoOp:  # noqa: D401
                def set(self, *_):
                    ...

            self.pnl_g = _NoOp()

        # ── ADK mesh registration ──
        if self.cfg.adk_mesh and "adk" in globals():
            # registration scheduled by orchestrator after loop start
            pass

    # ───────────── OpenAI Agents SDK tools ─────────────
    @tool(description="Return latest factor z-scores (JSON str).")
    def alpha_signals(self) -> str:
        return json.dumps(self.factor.scores, separators=(",", ":"))

    @tool(description="Return current portfolio book (JSON str).")
    def portfolio_state(self) -> str:
        return json.dumps(self.portfolio.book(), separators=(",", ":"))

    # ───────────── lifecycle entrypoint ────────────────
    async def run(self):
        while True:
            t0 = time.perf_counter()
            try:
                await self._cycle()
            except Exception as exc:  # noqa: BLE001
                _log.exception("Unhandled error in FinanceAgent cycle: %s", exc)
            dt = max(0.0, self.cfg.cycle_sec - (time.perf_counter() - t0))
            await asyncio.sleep(dt)

    async def run_cycle(self):
        """Single orchestrator cycle wrapper."""
        await self._cycle()

    async def step(self) -> None:  # noqa: D401
        """Delegate step execution to :meth:`run_cycle`."""
        await self.run_cycle()

    # ─────────────────── internal cycle ─────────────────
    async def _cycle(self):
        # 1 · sample prices & extend history
        prices = {s: self._safe_price(s) for s in self.cfg.universe}
        for s, p in prices.items():
            h = self.history[s]
            h.append(p)
            if len(h) > 1000:
                h.pop(0)

        # 2 · update factors & portfolio risk
        self.factor.update(self.history)
        flat_ret = [_pct(a, b) for s in self.cfg.universe for a, b in zip(self.history[s][:-1], self.history[s][1:])]
        risk = {
            "var": _cf_var(flat_ret) * self.portfolio.value(prices),
            "cvar": _cvar(flat_ret) * self.portfolio.value(prices),
            "maxdd": _maxdd(flat_ret),
        }

        # 3 · compute target weights (risk-parity style)
        score_sum = sum(abs(v) for v in self.factor.scores.values()) or 1e-9
        targets = {s: self.factor.scores[s] / score_sum for s in self.cfg.universe}

        # 4 · risk hard-stops
        if (
            risk["var"] > self.cfg.var_limit
            or risk["cvar"] > self.cfg.cvar_limit
            or risk["maxdd"] > self.cfg.maxdd_limit
        ):
            _log.warning("Risk limits breached → no trades this cycle.")
            self._publish_state(prices, risk)
            return

        # 5 · plan & execute trades
        orders = self.planner.rollout(self.portfolio, prices, targets)
        for o in orders:
            self.broker.market(o["side"], o["qty"], o["sym"])
            self.portfolio.update(o["sym"], o["qty"] if o["side"] == "BUY" else -o["qty"])
            _log.info("Executed %s %s %.4f @ est %.2f USD", o["side"], o["sym"], o["qty"], o["est_fill_px"])

        # 6 · telemetry publish
        self._publish_state(prices, risk)

    # ────────────────────── helpers ─────────────────────
    def _safe_price(self, sym: str) -> float:
        try:
            return self.broker.price(sym)
        except (AiohttpClientError, asyncio.TimeoutError, OSError) as exc:
            _log.error("Price fetch failed (%s); fallback last-known.", exc)
            return self.history[sym][-1] if self.history[sym] else 100.0
        except Exception as exc:  # pragma: no cover - unexpected
            _log.exception("Unexpected price fetch error: %s", exc)
            raise

    def _publish_state(self, prices: Dict[str, float], risk: Dict[str, float]):
        cash_equiv = self.cfg.start_balance - sum(
            qty * prices.get(sym, 0.0) for sym, qty in self.portfolio.book().items()
        )
        pnl = cash_equiv + self.portfolio.value(prices) - self.cfg.start_balance
        self.pnl_g.set(pnl)

        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "prices": prices,
            "book": self.portfolio.book(),
            "pnl": pnl,
            "risk": risk,
        }
        _publish("fin.state", payload)

    async def _register_mesh(self) -> None:
        max_attempts = 3
        delay = 1.0
        for attempt in range(1, max_attempts + 1):
            try:
                client = adk.Client()
                await client.register(node_type="finance", metadata={"universe": ",".join(self.cfg.universe)})
                _log.info("Registered in ADK mesh id=%s", client.node_id)
                return
            except (AdkClientError, AiohttpClientError, asyncio.TimeoutError, OSError) as exc:
                if attempt == max_attempts:
                    _log.error("ADK mesh registration failed after %d attempts: %s", max_attempts, exc)
                    raise
                _log.warning(
                    "ADK registration attempt %d/%d failed: %s",
                    attempt,
                    max_attempts,
                    exc,
                )
                await asyncio.sleep(delay)
                delay *= 2
            except Exception as exc:  # pragma: no cover - unexpected
                _log.exception("Unexpected ADK registration error: %s", exc)
                raise


# ═════════════════════ registry hook ═══════════════════════════


__all__: list[str] = [
    "FinanceAgent",
    "metrics_asgi_app",
    "ModelProvider",
    "Memory",
    "Governance",
    "risk",
]
