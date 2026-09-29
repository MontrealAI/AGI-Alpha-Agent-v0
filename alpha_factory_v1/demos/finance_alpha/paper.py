# SPDX-License-Identifier: Apache-2.0
"""Deterministic, long-only paper research with next-open execution and a cash ledger.

No network, exchange credentials, model calls or order submission belong here.
Prices are user-supplied USD bars or explicitly synthetic fixtures, never live quotes.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import date, timedelta
import hashlib
import io
import json
import math
from pathlib import Path
import random
import re
from typing import Any

MAX_BYTES = 2_000_000
MAX_DATES = 2000
MAX_SYMBOLS = 8
CASES = {"trend": "Persistent trends", "reversal": "Trend reversal", "crash": "Gap and recovery"}
STRATEGIES = ("momentum", "reversion", "equal_weight", "cash")


def finite(name: str, value: Any, low: float, high: float) -> float:
    """Reject booleans, non-numbers and non-finite or out-of-range values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise ValueError(f"{name} must be a finite number in [{low:g}, {high:g}]")
    return float(value)


@dataclass(frozen=True)
class Config:
    strategy: str = "momentum"
    initial_cash: float = 10000.0
    lookback: int = 20
    rebalance_every: int = 5
    fee_bps: float = 10.0
    slippage_bps: float = 5.0
    max_exposure: float = 0.9
    max_position: float = 0.6
    max_drawdown: float = 0.15
    max_cvar: float = 0.04

    def __post_init__(self) -> None:
        if self.strategy not in STRATEGIES:
            raise ValueError(f"strategy must be one of {STRATEGIES}")
        for name, low, high in (("lookback", 5, 120), ("rebalance_every", 1, 60)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer in [{low}, {high}]")
        for name, minimum, maximum in (
            ("initial_cash", 100, 100000000),
            ("fee_bps", 0, 200),
            ("slippage_bps", 0, 200),
            ("max_exposure", 0, 1),
            ("max_position", 0, 1),
            ("max_drawdown", 0.001, 1),
            ("max_cvar", 0.001, 1),
        ):
            finite(name, getattr(self, name), minimum, maximum)


@dataclass(frozen=True)
class Bar:
    date: str
    symbol: str
    open: float
    close: float


def parse_csv(text: str) -> list[Bar]:
    """Require a complete, strictly chronological panel; never fill missing prices."""
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("CSV must be UTF-8 text no larger than 2 MB")
    try:
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), strict=True)
        if reader.fieldnames != ["date", "symbol", "open", "close"]:
            raise ValueError("CSV header must be exactly: date,symbol,open,close")
        # The input is already bounded to 2 MB; reject malformed quoting and field overflow.
        rows = list(reader)
    except csv.Error as exc:
        raise ValueError(f"Malformed CSV: {exc}") from exc
    bars: list[Bar] = []
    seen: set[tuple[str, str]] = set()
    panels: dict[str, set[str]] = {}
    previous = ""
    for number, row in enumerate(rows, 2):
        if number > MAX_DATES * MAX_SYMBOLS + 1 or set(row) != {"date", "symbol", "open", "close"}:
            raise ValueError("CSV has too many rows or malformed columns")
        stamp, symbol = row["date"], row["symbol"]
        try:
            if date.fromisoformat(stamp).isoformat() != stamp or stamp < previous:
                raise ValueError("Dates must use YYYY-MM-DD and be chronological")
            if not re.fullmatch(r"[A-Z][A-Z0-9_.-]{0,23}", symbol):
                raise ValueError("Symbols must be 1–24 uppercase letters, numbers, underscores, dots or hyphens")
            opening = finite("open", float(row["open"]), 0.000001, 100000000)
            closing = finite("close", float(row["close"]), 0.000001, 100000000)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"CSV row {number}: {exc}") from exc
        if (stamp, symbol) in seen:
            raise ValueError(f"CSV row {number}: duplicate date/symbol")
        seen.add((stamp, symbol))
        panels.setdefault(stamp, set()).add(symbol)
        if len(panels) > MAX_DATES or len(panels[stamp]) > MAX_SYMBOLS:
            raise ValueError("CSV allows at most 2,000 dates and 8 symbols")
        bars.append(Bar(stamp, symbol, opening, closing))
        previous = stamp
    if len(panels) < 7:
        raise ValueError("CSV requires at least 7 complete dates")
    universe = next(iter(panels.values()))
    if any(symbols != universe for symbols in panels.values()):
        raise ValueError("Every date must contain the same symbols; missing bars are not filled")
    return sorted(bars, key=lambda bar: (bar.date, bar.symbol))


def csv_text(rows: list[dict[str, Any]], fields: list[str]) -> str:
    """Write stable CSV with controlled field names and LF endings."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def synthetic(case: str = "trend") -> str:
    """Fixed, labeled scenarios, not a historical market feed or expected return."""
    if case not in CASES:
        raise ValueError(f"case must be one of {tuple(CASES)}")
    rng = random.Random(714)
    prices = {"SYNTH_GROWTH": 100.0, "SYNTH_DEFENSIVE": 100.0, "SYNTH_CYCLICAL": 100.0}
    rows = []
    day = date(2025, 1, 2)
    for index in range(160):
        while day.weekday() >= 5:
            day += timedelta(days=1)
        market = rng.gauss(0, 0.003)
        for number, (symbol, previous) in enumerate(prices.items()):
            drift = (0.0025, 0.0003, -0.0004)[number]
            if case == "reversal" and index >= 80:
                drift = (-0.004, 0.001, 0.003)[number]
            gap = (-0.27, -0.04, -0.18)[number] if case == "crash" and index == 90 else rng.gauss(0, 0.002)
            opening = round(previous * (1 + gap), 6)
            closing = round(opening * (1 + drift + market + rng.gauss(0, 0.003)), 6)
            prices[symbol] = closing
            rows.append({"date": day.isoformat(), "symbol": symbol, "open": opening, "close": closing})
        day += timedelta(days=1)
    return csv_text(rows, ["date", "symbol", "open", "close"])


def tail_risk(returns: list[float]) -> dict[str, float | int]:
    """95% historical loss VaR and mean of the worst ceil(5% * n) observations."""
    if not returns or any(not math.isfinite(value) for value in returns):
        raise ValueError("Risk requires finite observed returns")
    losses = sorted(-value for value in returns)
    count = max(1, math.ceil(0.05 * len(losses)))
    return {
        "var95": max(0.0, losses[math.ceil(0.95 * len(losses)) - 1]),
        "cvar95": max(0.0, sum(losses[-count:]) / count),
        "observations": len(losses),
    }


def simulate(bars: list[Bar], config: Config, *, benchmark: bool = False) -> dict[str, Any]:
    """Use closes through t-1 for decisions, fill at t open, and mark at t close."""
    panel: dict[str, dict[str, Bar]] = {}
    for bar in bars:
        panel.setdefault(bar.date, {})[bar.symbol] = bar
    dates = list(panel)
    symbols = sorted(panel[dates[0]])
    start = config.lookback + 1  # lookback close-to-close returns, all before the first execution
    if len(dates) <= start:
        raise ValueError(f"Need at least {start + 1} dates for lookback {config.lookback}")
    cash = float(config.initial_cash)
    units = dict.fromkeys(symbols, 0.0)
    basis = dict.fromkeys(symbols, 0.0)
    realized = fees = slippage = 0.0
    peak = cash
    halted = False
    history: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for index in range(start, len(dates)):
        stamp = dates[index]
        current = panel[stamp]
        prior = panel[dates[index - 1]]
        scheduled = index == start or (not benchmark and (index - start) % config.rebalance_every == 0)
        liquidation = halted and any(units.values())
        if scheduled or liquidation:
            scores = {
                symbol: prior[symbol].close / panel[dates[index - 1 - config.lookback]][symbol].close - 1
                for symbol in symbols
            }
            if benchmark or config.strategy == "equal_weight":
                selected = symbols
            elif config.strategy == "cash" or halted:
                selected = []
            else:
                sign = 1 if config.strategy == "momentum" else -1
                selected = sorted((s for s in symbols if sign * scores[s] > 0), key=lambda s: (-sign * scores[s], s))[
                    :2
                ]
            weight = min(config.max_position, config.max_exposure / len(selected)) if selected else 0.0
            targets = {s: weight if s in selected else 0.0 for s in symbols}
            returns = [
                sum(targets[s] * (panel[dates[t]][s].close / panel[dates[t - 1]][s].close - 1) for s in symbols)
                for t in range(index - config.lookback, index)
            ]
            risk = tail_risk(returns)
            reason = "scheduled_rebalance"
            if benchmark:
                reason = "buy_and_hold_reference"
            elif halted:
                targets = dict.fromkeys(symbols, 0.0)
                reason = "drawdown_halt"
            elif risk["cvar95"] > config.max_cvar:
                targets = dict.fromkeys(symbols, 0.0)
                reason = "tail_risk_to_cash"
            equity_open = cash + sum(units[s] * current[s].open for s in symbols)
            desired = {s: equity_open * targets[s] / current[s].open for s in symbols}
            decisions.append(
                {
                    "signal_date": dates[index - 1],
                    "execution_date": stamp,
                    "reason": reason,
                    "scores": scores,
                    "targets": targets,
                    "estimated_risk": risk,
                }
            )
            # Sell first, then use only available cash. No borrowing or shorting.
            for side in ("SELL", "BUY"):
                for symbol in symbols:
                    delta = desired[symbol] - units[symbol]
                    if (side == "SELL" and delta >= -1e-10) or (side == "BUY" and delta <= 1e-10):
                        continue
                    reference = current[symbol].open
                    price = reference * (1 + config.slippage_bps / 10000 * (1 if side == "BUY" else -1))
                    quantity = abs(delta)
                    if side == "BUY":
                        quantity = min(quantity, cash / (price * (1 + config.fee_bps / 10000)))
                    if quantity * price < 1e-8:
                        continue
                    notional = quantity * price
                    fee = notional * config.fee_bps / 10000
                    if side == "BUY":
                        cash -= notional + fee
                        units[symbol] += quantity
                        basis[symbol] += notional + fee
                    else:
                        allocated_basis = basis[symbol] * quantity / units[symbol]
                        cash += notional - fee
                        realized += notional - fee - allocated_basis
                        units[symbol] -= quantity
                        basis[symbol] -= allocated_basis
                    fees += fee
                    impact = quantity * abs(price - reference)
                    slippage += impact
                    trades.append(
                        {
                            "date": stamp,
                            "signal_date": dates[index - 1],
                            "symbol": symbol,
                            "side": side,
                            "quantity": quantity,
                            "reference_open": reference,
                            "fill_price": price,
                            "fee": fee,
                            "slippage_cost": impact,
                            "cash_after": cash,
                            "units_after": units[symbol],
                        }
                    )
            if cash < -1e-7 or any(q < -1e-7 for q in units.values()):
                raise RuntimeError("Paper ledger violated its no-borrowing/no-shorting invariant")
        market_value = sum(units[s] * current[s].close for s in symbols)
        equity = cash + market_value
        if not math.isfinite(equity) or equity <= 0:
            raise ValueError("Price path exceeds the supported positive-equity numeric range")
        peak = max(peak, equity)
        drawdown = 1 - equity / peak
        newly_halted = not benchmark and not halted and drawdown >= config.max_drawdown
        if newly_halted:
            halted = True
        unrealized = market_value - sum(basis.values())
        if not math.isclose(equity - config.initial_cash, realized + unrealized, abs_tol=1e-6, rel_tol=1e-9):
            raise RuntimeError("Paper P&L did not reconcile")
        history.append(
            {
                "date": stamp,
                "cash": cash,
                "market_value": market_value,
                "equity": equity,
                "pnl": equity - config.initial_cash,
                "realized_pnl": realized,
                "unrealized_pnl": unrealized,
                "drawdown": drawdown,
                "exposure": market_value / equity,
                "fees": fees,
                "slippage_cost": slippage,
                "halted": halted,
                "halt_triggered": newly_halted,
            }
        )
    last = history[-1]
    equity_series = [config.initial_cash] + [row["equity"] for row in history]
    observed = tail_risk([b / a - 1 for a, b in zip(equity_series, equity_series[1:])])
    return {
        "summary": {
            "initial_cash": config.initial_cash,
            "final_equity": last["equity"],
            "net_pnl": last["pnl"],
            "net_return": last["equity"] / config.initial_cash - 1,
            "max_drawdown": max(row["drawdown"] for row in history),
            "fees": fees,
            "slippage_cost": slippage,
            "trades": len(trades),
            "risk_blocks": sum(d["reason"] == "tail_risk_to_cash" for d in decisions),
            "halted": halted,
            "pending_liquidation": halted and any(q > 1e-8 for q in units.values()),
            "realized_pnl": realized,
            "unrealized_pnl": last["unrealized_pnl"],
            "observed_risk": observed,
        },
        "positions": [
            {"symbol": s, "quantity": units[s], "cost_basis": basis[s], "last_close": panel[dates[-1]][s].close}
            for s in symbols
        ],
        "equity": history,
        "trades": trades,
        "decisions": decisions,
    }


def run(csv_input: str | None = None, config: Config | None = None, *, case: str = "trend") -> dict[str, Any]:
    """Return an independently replayable report with strategy, benchmark and cash."""
    config = config or Config()
    source = synthetic(case) if csv_input is None else csv_input
    bars = parse_csv(source)
    canonical = csv_text([asdict(bar) for bar in bars], ["date", "symbol", "open", "close"])
    result = simulate(bars, config)
    reference = simulate(bars, config, benchmark=True)
    report = {
        "schema": "finance-alpha-paper-v1",
        "status": "complete",
        "execution": "paper_only",
        "decision": "review_required",
        "config": asdict(config),
        "data": {
            "kind": "synthetic" if csv_input is None else "user_supplied_unverified",
            "case": case if csv_input is None else None,
            "sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "csv": canonical,
            "bars": len(bars),
            "dates": len({bar.date for bar in bars}),
            "symbols": sorted({bar.symbol for bar in bars}),
        },
        "provenance": {"engine_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "result": result,
        "benchmark": reference,
        "comparison": {
            "strategy": result["summary"]["net_return"],
            "equal_weight_buy_hold": reference["summary"]["net_return"],
            "cash": 0.0,
        },
        "method": {
            "timing": "Signals and tail-risk estimates use prior closes only; fills use the following supplied bar's open.",
            "benchmark": "Same warm-up, capital, exposure/position caps and costs; buy once, hold without risk exits.",
            "risk": "Historical VaR95 uses nearest-rank loss quantile; CVaR95 is the mean worst ceil(5%*n) observations, floored at zero.",
            "halt": "A close-equity drawdown breach schedules next-open liquidation and blocks re-entry. Gaps can exceed the threshold; a final-bar breach remains pending.",
            "accounting": "Cash plus marked positions; average-cost realized P&L includes fees. Slippage is already in fill prices. Open positions are not force-sold at the end.",
        },
        "limitations": [
            "Synthetic scenarios are demonstrations, not forecasts or evidence of profitable alpha.",
            "User CSV provenance, licensing, survivorship, splits and dividends require independent review. Use aligned USD prices; no silent adjustment or gap filling.",
            "No parameter fitting is performed. Repeated strategy selection on the same sample is not an out-of-sample evaluation.",
            "Fractional shares, deterministic full fills and fixed costs omit liquidity, market impact, taxes, financing and corporate actions.",
            "Risk estimates use small historical samples and do not bound future loss. The benchmark has different risk-exit behavior.",
            "No exchange connection, wallet, real order, AGI claim or investment recommendation.",
        ],
    }
    json.dumps(report, allow_nan=False)
    return report
