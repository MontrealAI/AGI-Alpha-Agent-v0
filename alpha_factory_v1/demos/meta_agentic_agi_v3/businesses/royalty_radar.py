#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""RoyaltyRadar: offline reconciliation evidence and a reviewable letter draft.

Mock public stream counts and an explicit EUR-per-stream assumption are not
proof of money owed. No claim is sent and no payment is broadcast. The original
research narrative remains in royalty_radar.md and the demo research archive.
"""
from __future__ import annotations

import asyncio
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import logging
from pathlib import Path
import random
from statistics import mean
from typing import Any, Sequence


@dataclass
class RoyaltyRadarConfig:
    artist_name: str
    isrc_codes: Sequence[str]
    statement_csv: Path
    payout_wallet: str
    dsp_adapters: Sequence[str] = ("mock",)
    llm_model: str = "offline-template"
    gap_eur_floor: float = 50.0
    false_pos_rate: float = 0.05  # legacy metadata; not a calibrated statistical guarantee
    demo_mode: bool = True
    eur_per_stream: str = "0.0032"
    lineage_path: Path = Path("stepstones.jsonl")

    @staticmethod
    def from_yaml(path: str | Path) -> RoyaltyRadarConfig:
        import yaml

        source = Path(path).resolve()
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Royalty configuration must be an object")
        statement = Path(raw["statement_csv"]).expanduser()
        lineage = Path(raw.get("lineage_path", "stepstones.jsonl")).expanduser()
        return RoyaltyRadarConfig(
            artist_name=raw["artist_name"],
            isrc_codes=raw["isrc_codes"],
            statement_csv=statement if statement.is_absolute() else source.parent / statement,
            payout_wallet=raw["payout_wallet"],
            dsp_adapters=raw.get("dsp_adapters", ["mock"]),
            llm_model=raw.get("llm_model", "offline-template"),
            gap_eur_floor=raw.get("gap_eur_floor", 50),
            false_pos_rate=raw.get("false_pos_rate", 0.05),
            demo_mode=raw.get("demo_mode", True),
            eur_per_stream=str(raw.get("eur_per_stream", "0.0032")),
            lineage_path=lineage if lineage.is_absolute() else Path.cwd() / lineage,
        )


async def dsp_mock(isrc: str) -> int:
    return 1_000_000 + random.Random(isrc).randint(0, 500_000)


ADAPTERS = {"mock": dsp_mock}


def _amount(value: Any, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"{name} must be nonnegative and finite")
    return result


class RoyaltyRadarBusiness:
    LABEL = "RoyaltyRadar.alpha.agi.eth"

    def __init__(self, cfg: RoyaltyRadarConfig):
        if cfg.demo_mode is not True:
            raise ValueError("Live settlement is not implemented. Use demo_mode: true to prepare evidence for review.")
        if (
            not cfg.isrc_codes
            or isinstance(cfg.isrc_codes, str)
            or len(cfg.isrc_codes) > 100
            or len(set(cfg.isrc_codes)) != len(cfg.isrc_codes)
        ):
            raise ValueError("Provide 1–100 unique ISRC codes")
        if not cfg.dsp_adapters or any(a not in ADAPTERS for a in cfg.dsp_adapters):
            raise ValueError("Unknown or empty DSP adapters")
        _amount(cfg.eur_per_stream, "eur_per_stream")
        _amount(cfg.gap_eur_floor, "gap_eur_floor")
        self.cfg = cfg
        self.logger = logging.getLogger("RoyaltyRadar")

    def plan(self) -> str:
        return f"Compare assumed streams for {self.cfg.artist_name}; draft evidence for independent review."

    async def run_async(self) -> dict[str, Any]:
        cfg = self.cfg
        width = len(cfg.dsp_adapters)
        values = await asyncio.gather(*(ADAPTERS[a](isrc) for isrc in cfg.isrc_codes for a in cfg.dsp_adapters))
        if any(type(v) is not int or v < 0 for v in values):
            raise ValueError("Adapters must return nonnegative integer stream counts")
        public = {isrc: int(mean(values[i * width : (i + 1) * width])) for i, isrc in enumerate(cfg.isrc_codes)}
        paid_counts, paid_eur = _parse_statement(cfg.statement_csv, cfg.isrc_codes)
        rate, floor = _amount(cfg.eur_per_stream, "eur_per_stream"), _amount(cfg.gap_eur_floor, "gap_eur_floor")
        gaps = {}
        for isrc in cfg.isrc_codes:
            estimate = max(Decimal(0), Decimal(public[isrc]) * rate - paid_eur.get(isrc, Decimal(0)))
            if estimate >= floor and estimate > 0:
                gaps[isrc] = str(estimate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        total = sum((Decimal(v) for v in gaps.values()), Decimal(0))
        artefact = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "artist": cfg.artist_name,
            "gap_eur": str(total.quantize(Decimal("0.01"))),
            "status": "REVIEW_REQUIRED",
            "claim_letter": _letter_prompt(cfg.artist_name, gaps, cfg.payout_wallet),
            "evidence": {
                "public_streams": public,
                "paid_streams": paid_counts,
                "paid_eur": {k: str(v) for k, v in paid_eur.items()},
                "eur_per_stream_assumption": str(rate),
                "adapters": list(cfg.dsp_adapters),
            },
            "scope": "Illustrative reconciliation, not a debt finding. No calibrated false-positive bound, claim delivery or settlement.",
        }
        cfg.lineage_path.parent.mkdir(parents=True, exist_ok=True)
        with cfg.lineage_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(artefact, ensure_ascii=False, allow_nan=False) + "\n")
        return artefact

    def run(self) -> dict[str, Any]:
        return asyncio.run(self.run_async())


def _parse_statement(csv_path: Path, isrc_filter: Sequence[str]) -> tuple[dict[str, int], dict[str, Decimal]]:
    counts: dict[str, int] = {}
    euros: dict[str, Decimal] = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not {"isrc", "streams", "eur"}.issubset(reader.fieldnames):
            raise ValueError("Statement requires isrc, streams and eur columns")
        for index, row in enumerate(reader, 2):
            if index > 100002:
                raise ValueError("Statement exceeds 100,000 rows")
            if row["isrc"] not in isrc_filter:
                continue
            n = int(row["streams"])
            if n < 0:
                raise ValueError(f"Negative streams at row {index}")
            counts[row["isrc"]] = counts.get(row["isrc"], 0) + n
            euros[row["isrc"]] = euros.get(row["isrc"], Decimal(0)) + _amount(row["eur"], f"EUR at row {index}")
    return counts, euros


def _letter_prompt(artist: str, gap: dict[str, str], wallet: str) -> str:
    bullets = "\n".join(f"- {key}: EUR {value} illustrative discrepancy" for key, value in gap.items())
    return (
        f"DRAFT — independent review required\nRe: {artist}\n{bullets or 'No material discrepancy.'}\n"
        "Please reconcile these supplied counts and rate assumptions against the applicable agreements. "
        f"The supplied settlement reference is {wallet}; it has not been verified. No payment is requested by this software."
    )


def _dispatch_payout(eur_amount: float, wallet: str) -> None:
    raise RuntimeError(
        "No payout adapter is implemented: a native-currency transfer is not an AGIALPHA ERC-20 payment."
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cfg", type=Path, default=Path(__file__).parents[1] / "configs/royalty_radar.yml")
    parser.add_argument("--demo", action="store_true", help="Require offline reconciliation")
    args = parser.parse_args()
    try:
        cfg = RoyaltyRadarConfig.from_yaml(args.cfg)
        if args.demo:
            cfg.demo_mode = True
        print(json.dumps(RoyaltyRadarBusiness(cfg).run(), indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"RoyaltyRadar: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
