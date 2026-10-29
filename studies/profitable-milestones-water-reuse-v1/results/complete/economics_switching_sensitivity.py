# SPDX-License-Identifier: Apache-2.0
import csv
import json
from decimal import Decimal as D
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parents[1]
c = json.loads((root / "inputs/economics_complete.json").read_text())
price, fee, dep = D(3500), D(str(c["payment_fee_fraction"])), D(str(c["deposit_fraction"]))
rows = []
for s in c["scenarios"]:
    for shock in (False, True):
        mult = D(str(c["common_shock"]["cost_multiplier"])) if shock else D(1)
        d = D(str(s["first_pass_delivery_probability"]))
        a = D(str(s["acceptance_given_delivery_probability"]))
        k = D(str(s["collection_given_acceptance_probability"]))
        trust = D(str(s["trust_booking_probability"]))
        if shock:
            d *= D(str(c["common_shock"]["first_pass_multiplier"]))
            a *= D(str(c["common_shock"]["acceptance_multiplier"]))
            k *= D(str(c["common_shock"]["collection_multiplier"]))
            trust *= D(str(c["common_shock"]["booking_multiplier"]))
        delivered = d + (1 - d) * D(str(s["correction_rescue_probability"]))
        accepted = delivered * a
        base = mult * D(
            str(
                s["labor_hours"] * s["labor_rate_usd"]
                + s["model_allowance_usd"]
                + s["infrastructure_usd"]
                + s["packaging_usd"]
            )
        )
        correction = (1 - d) * mult * D(str(s["correction_usd"]))
        support = mult * D(str(s["support_usd"]))
        collection_factor = dep + (1 - dep) * k * (1 - fee)
        job_margin = accepted * price * collection_factor - base - correction - support - fee * price * dep
        leads = D(c["horizon_weeks"] * s["leads_per_week"])
        campaign_cost = (
            leads * D(s["lead_cost_usd"])
            + D(sum(c["startup_costs_usd"].values()))
            + D((c["horizon_weeks"] + c["runoff_weeks"]) * c["weekly_overhead_usd"])
        )
        capacity = D(c["slots"] * c["horizon_weeks"]) / (2 - d)
        for label in ("net_fee_cap_after_switching", "gross_value_before_switching"):
            threshold = price if label.startswith("net") else price + D(s["switching_cost_usd"])
            tail = min(
                D(1),
                max(
                    D(0),
                    (D(s["buyer_reservation_max_usd"]) - threshold)
                    / D(s["buyer_reservation_max_usd"] - s["buyer_reservation_min_usd"]),
                ),
            )
            booking = tail * trust
            attempts = min(leads * booking, capacity)
            expected = attempts * job_margin - campaign_cost
            requirement = (
                (
                    (base + correction + support + fee * price * dep + campaign_cost / attempts)
                    / (delivered * price * collection_factor)
                )
                if attempts
                else None
            )
            rows.append(
                {
                    "scenario": s["id"],
                    "common_shock": shock,
                    "reservation_interpretation": label,
                    "price_usd": str(price),
                    "switching_cost_usd": str(s["switching_cost_usd"]),
                    "booking_probability": str(booking),
                    "expected_attempts": str(attempts),
                    "expected_job_margin_before_acquisition_usd": str(job_margin),
                    "break_even_booking_probability": str(campaign_cost / (leads * job_margin))
                    if job_margin > 0
                    else None,
                    "full_33_week_expected_profit_usd": str(expected),
                    "break_even_acceptance_given_delivery": str(requirement) if requirement is not None else None,
                    "scope": "Analytical post-confirmation ambiguity sensitivity; price/seeds/main replay unchanged; no new buyer evidence.",
                }
            )
with (here / "economics_switching_sensitivity.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
print(json.dumps(rows, indent=2))
