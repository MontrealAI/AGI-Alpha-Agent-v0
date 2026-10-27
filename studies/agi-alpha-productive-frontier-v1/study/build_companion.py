# SPDX-License-Identifier: Apache-2.0
"""Build evidence tables and replay one simulated history through native accounting."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from repository_adapter import replay_native_ledger

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "competent_beta": "Competent ordinary Beta",
    "private_work": "Private work (forced)",
    "shared_work": "Shared work (forced)",
    "shared_gym": "Shared Gym (forced)",
    "ordinary_library": "Ordinary library (matched)",
    "selective": "Selective assessment",
}
CATEGORIES = ["model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"]


def read(path: str) -> Any:
    return json.loads((ROOT / path).read_text())


def money(value: float) -> str:
    return f"{value:,.2f}"


def native_replay(example: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    totals: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    mission_id = f"enterprise-seed{example['seed']}"
    horizon = config["days"] - 1
    for row in example["charges"]:
        if row["day"] > horizon:
            continue
        total = totals[(row["bucket"], row["category"])]
        total[0] += row["amount"]
        paid_fraction = (
            1
            if row.get("immediate_paid", False) or horizon - row["day"] >= config["base"]["payment_delay_cost_days"]
            else config["base"]["initial_paid_cost_fraction"]
        )
        total[1] += row["amount"] * paid_fraction
    charges = []
    for bucket in ["A", "B", "C"]:
        for category in CATEGORIES:
            amount, paid = totals[(bucket, category)]
            charges.append(
                {
                    "activity_id": f"simulated-history-{bucket}-{category}",
                    "mission_id": mission_id,
                    "bucket": bucket,
                    "category": category,
                    "accrued_micro_usd": round(amount * 1e6),
                    "paid_micro_usd": round(paid * 1e6),
                    "basis": "attested",
                    "note": "SIMULATED aggregate of unique history activities; explicit model zero where unused; not an actual invoice",
                }
            )
    collections = [
        {
            "record_id": "simulated-history-collections",
            "mission_id": mission_id,
            "amount_micro_usd": round(example["collections"] * 1e6),
        }
    ]
    result = replay_native_ledger(
        charges,
        collections=collections,
        capital_micro_usd=round(example["seed_capital"] * 1e6),
        reserve_micro_usd=round(example["reserves"] * 1e6),
    )
    expected = {
        "complete_cost_profit": example["profit"],
        "cash": example["cash"],
        "obligations": example["obligations"],
        "available_funds": example["available"],
        "collected_revenue": example["collections"],
    }
    differences = {key: result["report"][key] - round(value * 1e6) for key, value in expected.items()}
    if max(abs(x) for x in differences.values()) > 27:
        raise AssertionError(f"Native accounting disagrees beyond aggregate rounding: {differences}")
    result["simulation_reconciliation"] = {
        "seed": example["seed"],
        "policy": example["policy"],
        "micro_usd_differences": differences,
        "rounding_tolerance_micro_usd": 27,
        "aggregation": "27 explicit bucket/category aggregates; original activities remain in exemplar.json",
    }
    (ROOT / "evidence/native_simulation_replay.json").write_text(json.dumps(result, indent=2))
    return result


def build() -> None:
    results = read("results/economics/economic_results.json")
    config = read("protocol/economic_protocol.json")
    example = read("results/economics/exemplar.json")
    native = native_replay(example, config)
    base = results["scenarios"]["base"]
    scenarios = results["scenarios"]
    audit = read("evidence/economic_audit_v3.json")
    if audit["status"] != "PASS" or audit["cohort"]["seeds"] != results["seeds"]:
        raise AssertionError("The final economic audit must pass for this exact confirmation cohort")
    seed_count = results["seeds"][1] - results["seeds"][0] + 1
    comparisons = [
        (scenario, policy, row["incremental_profit_vs_beta"]["mean"])
        for scenario, group in scenarios.items()
        for policy, row in group.items()
        if policy != "competent_beta"
    ]
    positive_means = [(scenario, policy) for scenario, policy, increment in comparisons if increment > 0]
    comparative_result = (
        "No additional-capability or assessment policy has a positive mean paired increment in any declared scenario."
        if not positive_means
        else f"Positive mean paired increments occur in {len(positive_means)} of {len(comparisons)} declared scenario-policy comparisons; their mechanisms require separate inspection."
    )
    lines = [
        r"The frozen confirmation executes 256 paired seeds, 12 scenarios and six policies (18,432 enterprise histories). "
        r"Table~\ref{tab:economics} reports central assumed-market outcomes over 60 operating days. "
        r"These amounts are entirely simulated USD, not earned customer revenue. "
        +
        comparative_result,
        r"\begin{table}[htbp]\centering\small\begin{tabularx}{\linewidth}{Yrrr}\toprule",
        r"Policy & Mean surplus & Paired increment & Available funds\\\midrule",
    ]
    for policy, label in LABELS.items():
        row = base[policy]
        lines.append(
            f"{label} & {money(row['profit']['mean'])} & {money(row['incremental_profit_vs_beta']['mean'])} & {money(row['available']['mean'])}\\\\"
        )
    lines += [
        r"\bottomrule\end{tabularx}\caption{Conditional simulation. Surplus equals simulated collections less all accrued modeled costs. Seed capital is excluded from surplus and included only in funds. Forced treatments isolate capability investment; the library has identical contents and permissions to shared work.}\label{tab:economics}\end{table}"
    ]
    b = base["competent_beta"]
    lines.append(
        f"Ordinary Beta's mean collected-basis surplus is USD {money(b['profit']['mean'])}, with a Monte Carlo 95\\% interval for the mean of [{money(b['profit']['mc95_low'])}, {money(b['profit']['mc95_high'])}]. "
        f"The fifth and ninety-fifth percentiles of individual simulated outcomes are USD {money(b['profit']['p05'])} and USD {money(b['profit']['p95'])}. "
        f"Mean simulated collections are USD {money(b['collections']['mean'])}; mean A/B/C costs are USD {money(b['cost_A']['mean'])}, USD {money(b['cost_B']['mean'])} and USD {money(b['cost_C']['mean'])}. "
        r"The mean interval measures Monte Carlo estimation uncertainty under fixed assumptions, not uncertainty in actual demand or prices."
    )
    counts = {
        policy: sum(
            s[policy]["mode_counts"].get("work", 0) + s[policy]["mode_counts"].get("gym", 0) for s in scenarios.values()
        )
        for policy in ["selective"]
    }
    lines.append(
        f"The selective policy adopts an additional specialist in {counts['selective']} of {seed_count * len(scenarios):,} scenario-seed histories. "
        f"Its central mean paired increment is USD {money(base['selective']['incremental_profit_vs_beta']['mean'])}. "
        f"The shared-work treatment's central mean paired increment is USD {money(base['shared_work']['incremental_profit_vs_beta']['mean'])}. "
        r"This separates the commercial foundation from the additional learning investment."
    )
    lines += [
        r"\fig{06_cumulative_incremental_profit}{Conditional cumulative incremental surplus relative to equally resourced ordinary delivery. The negative lines retain additional assessment, integration and upkeep; no customer premium is assigned to the specialist.}{fig:cumulative}",
        r"\fig{07_portfolio_and_available_funds}{Conditional portfolio and available-funds paths. Left: preparation completion delays offering readiness in the capacity-pressure scenario. Right: selective-policy surplus and available funds in the central scenario. The same candidate offerings are available to ordinary and specialist enterprises; productization is not specialist-created feasibility.}{fig:portfolio}",
        r"\begin{table}[htbp]\centering\footnotesize\begin{tabularx}{\linewidth}{Yrrr}\toprule",
        r"Scenario & Beta surplus & Shared work increment & Selective increment\\\midrule",
    ]
    for name, group in scenarios.items():
        label = name.replace("_", " ").capitalize()
        lines.append(
            f"{label} & {money(group['competent_beta']['profit']['mean'])} & {money(group['shared_work']['incremental_profit_vs_beta']['mean'])} & {money(group['selective']['incremental_profit_vs_beta']['mean'])}\\\\"
        )
    lines += [
        r"\bottomrule\end{tabularx}\caption{Stress outcomes under deliberately changed assumptions; all values are simulated USD. Growth purchases additional capacity from surplus and is separately identified. Larger output from that capacity is not evidence of Alpha compounding.}\end{table}",
        r"\fig{08_economic_stress_frontier}{Paired policy increments across assumption stress tests. The market and operating assumptions, not Monte Carlo replication, determine whether a scenario represents a real opportunity.}{fig:stress}",
    ]
    lines.append(
        r"The corrected low-willingness-to-pay policy stops both lead acquisition and optional prototypes. It still loses USD 874.26 because the fixed 60-day operating commitment and common setup/origin research costs remain. "
        r"The preserved initial policy lost USD 984.26 in that scenario, including USD 110 of avoidable prototypes. The first declared amendment conditioned productization on the marginal contribution of an acquisition-viable portfolio. The final cohort additionally corrects capacity carryover and readiness as disclosed above. These are researcher-corrected policies, not evidence of autonomously learned commercial judgment. "
        r"The growth arm can earn much more under its assumed high demand because every policy may purchase extra capacity. That result concerns scalable ordinary delivery under the assumed market, not a learned expansion of what is technically possible. "
        r"Quality-adjusted units use declared weights 1/3/6 for accepted output. The historical processing-hour ratio excludes preparation and idle capacity; the corrected edition also reports weighted output per total available capacity-hour. Neither weight is measured buyer value."
    )
    pressure = scenarios["capacity_pressure"]
    lines += [
        r"\begin{table}[htbp]\centering\footnotesize\begin{tabularx}{\linewidth}{Yrrrr}\toprule",
        r"Policy & Prep seconds & Job reservations & Unused seconds & Units / hour\\\midrule",
    ]
    for policy, label in LABELS.items():
        row = pressure[policy]
        lines.append(
            f"{label} & {row['preparation_consumed_seconds']['mean']:,.0f} & {row['production_reserved_seconds']['mean']:,.0f} & "
            f"{row['unused_capacity_seconds']['mean']:,.0f} & {row['weighted_units_per_total_capacity_hour']['mean']:,.2f}\\\\"
        )
    lines.append(
        r"\bottomrule\end{tabularx}\caption{Corrected capacity-pressure accounting over 60 days. Every policy receives 108,000 seconds. Preparation plus customer reservations plus unused capacity equals that allowance in each history, before rounding. The final column divides accepted weighted output by the full allowance, including preparation and idle time. Horizon backlog is reported separately in the raw results.}\end{table}"
    )
    growth = scenarios["growth_financed_by_surplus"]
    growth_note = (
        f"Under capacity pressure, shared work's mean increment is USD {money(pressure['shared_work']['incremental_profit_vs_beta']['mean'])} "
        f"and Gym's is USD {money(pressure['shared_gym']['incremental_profit_vs_beta']['mean'])}. "
        "The difference includes delayed readiness, displaced accepted work and the acquisition stop; it is not a second cash charge for opportunity cost. "
        "In the separate surplus-financed growth scenario, only acquired leads inform the unchanged arrival-rate heuristic. "
        f"Mean final additional workers are {growth['competent_beta']['workers']['mean']:.3f} for ordinary Beta, "
        f"{growth['shared_work']['workers']['mean']:.3f} for shared work and {growth['shared_gym']['workers']['mean']:.3f} for Gym. "
        f"Gym's mean accepted output is {growth['shared_gym']['accepted']['mean']:.2f} orders versus "
        f"{growth['competent_beta']['accepted']['mean']:.2f} for Beta; its weighted output per total capacity-hour is "
        f"{growth['shared_gym']['weighted_units_per_total_capacity_hour']['mean']:.3f} versus "
        f"{growth['competent_beta']['weighted_units_per_total_capacity_hour']['mean']:.3f}. "
        "A ratio can improve when the enterprise buys less capacity even while total useful output and surplus fall. "
        "These path-dependent outcomes belong to the declared scheduling and observation heuristic; they do not establish general market growth or a globally optimal investment rule."
    )
    lines.append(growth_note)
    audit_note = (
        f"The read-only audit reconciles all {audit['cohort']['raw_rows']:,} histories, their summaries and exported readiness paths. "
        "Every horizon capacity/backlog identity is exact; the largest cash-accounting residual is less than USD 0.00000002. "
        "No preparation remains unfinished at day 59 in this cohort; separate boundary fixtures demonstrate that unfinished work remains visible when the horizon is shorter. "
        f"Ordinary Beta still loses money in {audit['scenario_policy_descriptives']['low_demand']['competent_beta']['negative_profit_histories']} of 256 low-demand histories, "
        f"and selective assessment in {audit['scenario_policy_descriptives']['low_demand']['selective']['negative_profit_histories']}. "
        "The evidence therefore supports conditional ordinary delivery and selective refusal, not guaranteed enterprise profitability."
    )
    lines.append(audit_note)
    (ROOT / "paper/economic_results.tex").write_text("\n\n".join(lines) + "\n")

    table = [
        "| Policy | Simulated surplus (USD) | Increment vs Beta | Available funds |",
        "| --- | ---: | ---: | ---: |",
    ]
    for policy, label in LABELS.items():
        row = base[policy]
        table.append(
            f"| {label} | {money(row['profit']['mean'])} | {money(row['incremental_profit_vs_beta']['mean'])} | {money(row['available']['mean'])} |"
        )
    resource_table = [
        "| Policy | Preparation seconds | Customer reservations | Unused seconds | Weighted units / total capacity-hour |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for policy, label in LABELS.items():
        row = pressure[policy]
        resource_table.append(
            f"| {label} | {row['preparation_consumed_seconds']['mean']:,.0f} | {row['production_reserved_seconds']['mean']:,.0f} | "
            f"{row['unused_capacity_seconds']['mean']:,.0f} | {row['weighted_units_per_total_capacity_hour']['mean']:,.2f} |"
        )
    text = f"""# Evidence companion: Making the Next Opportunity Possible

**Vincent Boucher — President of MONTREAL.AI**  
27 October 2026. Research edition 1.0.1.

## Result and claim boundary

Real data-dependent numerical learning and local artifact transfer are demonstrated. A work-derived
rank-48 basis makes the final fresh eight-case damping-selection numerical workflow 2.70 times faster than the
ordinary adaptive comparator (0.172800678 s versus 0.466215899 s). Both meet the same 2 s numerical research contract. The economic model separately assumes
180 s of preparation/packaging for this offer, so the 182 s total reservation is not a measured SLA.
The Gym version takes 0.459151705 s and triggers 8 direct ranking refinements; the work version triggers 0.
There is no uniquely enabled offering, measured market demand, earned revenue, live ENS admission,
specialist ASI or sustained compounding result.

## Evidence classes

| Quantity | Classification | Source |
| --- | --- | --- |
| Numerical arrays, cases, errors, residuals, timing | Observed executions on synthetic systems | `study/technical/results*` |
| Initial protected acceptance | Observed: 64 confirmation, 32 shift cases | Original frozen code and rawCSV |
| Corrected-source A measurements | Exposed-case revalidation | `results_validated` |
| Corrected-source B confirmation | Fresh seed 7401; 8 cases, 64 settings per policy | `results_final_prototype` |
| Local process transfer | Observed recipient without training snapshots | `recipient_transfer.json`, numerical tests |
| Native trust/accounting | Observed actual pinned software with local test signer | Native manifests, tests and replay |
| Model IDs, unit prices and capabilities | Sourced official pages, 27 October 2026 | `evidence/source_notes.json` |
| Token workloads, costs, price anchors, buyer values | Explicit assumptions | Economic protocol |
| Buyers, collections, failures, profits | Simulated | Economic histories; no actual sales |
| Quality-adjusted output weights 1/3/6 | Assumed accounting weights | Protocol; not measured buyer value |
| Physical correctness and live ENS authority | Not established | No such trial was performed |

## Frozen lineage and correction history

Initial source SHA-256 is 124da4d93774f5150dee668e6ada3c8c677b1db63532075801063a7ff4b647c2.
It is preserved under `study/technical/archived_initial`. The initial acceptance numbers are:
Schur 64/64, adaptive 64/64, fixed central basis 2/64, work-24 basis 17/64, work-48 basis 62/64 and
Gym-48 basis 62/64. Under shift these are 32/32, 22/32, 0/32, 0/32, 0/32 and 0/32 respectively.

Input safety review found trusted caller damping and unconditional Schur acceptance. Both were
corrected without changing a basis, threshold or initial acceptance count. Revalidation is not called
fresh. The final new seed 7401 binds both current code files, protocol, proposal and exact arrays before
execution. The formal opportunity catalogue was serialized after exploratory 6401; it is not described
as pre-registered before that exploratory run. All failed ablations and rejected certificates remain.

The analytic residual bound assumes verified dissipativity. Norm and eigenvalue computations use
floating point; no interval-arithmetic proof is claimed. The certificate concerns the supplied numerical
model, not a physical controller or model-form error. For unit-intensity independent white noise,
zero direct feedthrough and C=I, trace covariance is squared H2.

## Three connected experiments

A learns from 6 origin solutions, probes 20 development cases and optionally adds 4 Gym solutions at fixed
rank-48. Protected cases test numerical acceptance and frozen 5 s / 0.25 s batch contracts. The standard
service is ordinary-feasible. Two timings and 62/64 individual passes do not prove a reliability SLA.

B gives both enterprises the same finite proposal grammar and ordinary tools. It executes a fresh
prototype minimizing trace(X_g)+0.15g² on g=0,.1,...,.7. Overlapping objective intervals invoke ordinary
refinement or abstention. It is a real adjacent prototype, not a live LLM opportunity-discovery trial.
Continuous monitoring is declined for lack of prototype, assurance and buyer evidence.

C freezes the code/configuration and then executes 256 paired seeds across 12 scenarios and 6 policies:
18,432 enterprise histories. The same customer draws, opportunities, seed funds and capacity allowances are used. The final corrected cohort uses seeds 11000–11255.
Forced investment treatments isolate learning/sharing costs; selective investment may decline.
No policy sees future outcomes to price or reserve a job. The audit, screen and selection reserve
95, 125 and 182 s, including assumed model work. Unused job reservations are not reclaimed within
the day; faster kernels therefore do not automatically increase order capacity. Gross unpaid invoices do not use hidden
future default outcomes. Ordinary library and shared work are identical in every history.

## Conditional central-market results

{chr(10).join(table)}

These are 60-day simulated USD values. They are not sales or evidence of actual market profitability.
The selective policy makes {counts["selective"]} optional adoptions across {seed_count * len(scenarios):,} scenario-seed
histories. Its central mean increment is USD {money(base["selective"]["incremental_profit_vs_beta"]["mean"])}.
{comparative_result}

### Conserved capacity under pressure

{chr(10).join(resource_table)}

These are means over the capacity-pressure cohort. Each policy receives exactly 108,000 seconds over
60 days. Preparation, customer reservations and unused capacity partition that amount in every
history. Backlog and unfinished tasks remain explicit at the horizon. The last column includes all
available capacity; the earlier processing-hour ratio excludes preparation and idle time and is
retained as a narrower diagnostic. Weights 1/3/6 are accounting assumptions, not measured buyer value.
`capacity_paths.json` records daily preparation/readiness. Capacity-aware acquisition also changes
which leads can be bought, and therefore the observed arrival-rate estimate used by the existing
growth rule; this effect is reported without retuning that rule.

{growth_note}

{audit_note}

The initial economic confirmation is retained under `development/economics_v1`. It exposed a policy
that stopped acquisition in the low-value market but still spent USD 110 on prototypes. One declared
amendment in `protocol/economic_amendment.json` conditioned productization on incremental
contribution from an acquisition-viable portfolio. The second cohort confirmed that optional
prototype spending stops in that scenario. Its remaining USD 874.26 loss comprises common setup
and origin research plus fixed operating commitments. The correction is researcher informed; it
does not establish autonomously learned opportunity judgment.

At assumed USD 0.50/core-hour, the final B work-basis saving is USD 0.000040752/service. A USD 61 added
budget requires about 1,496,855 eight-case services to repay by CPU savings alone. The separate browser
calculator uses 32-case A batches and therefore has a different explicitly labeled threshold.

## Costs and finances

A covers simulated customer delivery, intake/acquisition, allocated operations, corrections and refunds.
B covers extra retention, assessment, admission, recipient integration and upkeep. C covers unpaid
origin examples, optional Gym, prototypes and common setup. The six executed origins were not paid
jobs; raw stage labels are preserved, but final accounting charges them once in C and gives them zero
collections. A genuinely paid-origin deployment would charge necessary delivery cost once in A.

The USD 0.71 model allowance is an assumed role mixture: Sol preparation 30k input / 8k output = USD 0.14;
Astra 15k / 6k = USD 0.45; Sol validation 20k / 6k = USD 0.10; Terra 10k / 2k = USD 0.02. Counts include assumed
billed output/reasoning usage; no live usage metering occurred. Tools/storage/network, acquisition,
correction, payment processing, integration and upkeep are separate protocol entries. Research
oracles, repeat validation and failed candidate assessment belong to the declared setup/assessment
budgets; those budgets are hypotheses, not actual measured commercial invoices.

Seed capital never becomes revenue. Collected-basis surplus is collections minus all accrued modeled
costs. Cash subtracts paid costs; available funds additionally subtract outstanding obligations and
reserves. Refunds are paid in full when collection arrives. Invoices, token movements, customer savings
and speculative future value are excluded from earned revenue. Displaced production is counted
separately and not deducted again as cash expense.

One full simulated history (seed {example["seed"]}, selective policy) is aggregated into 27 explicit
bucket/category attestations and replayed through the unchanged native ledger. Reconciliation
differences are {native["simulation_reconciliation"]["micro_usd_differences"]} microUSD, within the
declared 27 microUSD aggregate rounding tolerance. The raw history remains in `exemplar.json`.
This executes actual accounting code; it does not turn fictional amounts into verified payments.

## Verification and independent inspection

- 6 numerical boundary/transfer tests pass; original arrays/source hashes are preserved.
- 10 native accounting/trust tests pass, including duplicate costs, unknown costs, revocation and mutation.
- 29 financial/resource integrity tests pass, including funds-before-acquisition, reservation-before-runtime,
  no future-prefix leakage, refund/default behavior, real-chain inputs, library/shared equality
  and rejection of prototypes whose portfolio cannot support acquisition. The 12 added regressions
  cover preparation carryover, delayed readiness, failed/unfinished work, capacity-aware acquisition
  and unsupported execution overruns.
- Independent resource review passed 864 closed-form fixtures and 72 histories on existing development
  seed 8000. It checked 3,461 fixture identities plus 4,320 daily scenario ledgers before fresh confirmation;
  no protected 11000-series outcome was used to change the policy.
- EN/FR local Chromium checks pass, including responsive widths 320/390 px, no-JavaScript fallback,
  negative-return calculator branches and assumption download.
- Separate AI review roles examined numerical and economic claims. They are not independent institutions.

The final PDF visual review and publication receipts are recorded separately. Passing local checks is
not full repository release qualification. The native source is frozen at
80b345828f34fd8a6e592977dd17ef37141305f4; unsupported numerical production admission remains explicit.

## Reproduction details

Run from the study directory with the pinned requirements installed:

```bash
python study/test_repository_adapter.py
python study/test_economics.py
python study/technical/test_numerics.py
python study/technical/lyapunov_study.py --out reproduction/numerical
python study/technical/prototype_study.py --seed 7401 --out reproduction/prototype --proposals protocol/opportunity_proposals.json
python study/economics.py --technical results/economic_inputs --output reproduction/economics
```

Use `--seed 7401` (with a space) for the prototype. The proposal runner loads the frozen validated
bases. Its replay of 7401 is reproduction, not another protected confirmation. The historical fallback
script writes its original validated location; copy the complete technical directory to a new temporary
directory before running it, so published observations are preserved. The complete package contains
all numerical arrays, original code, source manifests and LaTeX figure dependencies.

## Capacity correction and preserved submitted edition

Configured review found that the submitted engine discarded preparation work exceeding a daily
capacity allowance. The complete second cohort, engine, protocol, paper and figures are preserved
under `development/economics_v2`; its low-capacity comparisons are not valid matched-resource
evidence for the corrected scheduler. The original paper proposal #4968 was closed unmerged.

A further declared correctness amendment precedes seeds 11000–11255. Preparation carries forward
in a finite queue, readiness follows completion, and cash is charged once at commitment. Daily
capacity equals preparation consumed plus customer reservations plus unused capacity; horizon
backlog remains visible. Acquisition stops when no ready offer fits remaining capacity, and
unsupported execution overruns fail closed. The additional correctness pass exceeds the first
amendment's one-correction budget and is explicitly disclosed as a protocol deviation. Demand,
prices, numerical criteria, learned arrays and capacity allowances are unchanged.

## Source distribution

Exact executed numerical files are retained in adjacent `.py.gz` originals. Maintained solver
modules have identical abstract syntax trees after formatting for the unchanged repository rules.
The hash regression reads the compressed original and checks the same frozen digest.
`evidence/source_formatting_equivalence.json` records both byte identities and that test-only
packaging adaptation. Use `study/restore_frozen_source.py --destination /tmp/frontier-original-replay`
to restore the full original layout before byte-exact replay. This is not a new confirmation.

## Remaining evidence before live operation

Obtain a real beneficiary and accepted input/deliverable contract; verify rights and customer effort;
test the complete frontier-model workflow and automated corrections; measure actual acquisition,
support, integration, serving and collection costs; establish an operational reliability/latency bound;
validate the physical-model boundary with the responsible domain party; extend numerical admission
only through owner-reviewed production interfaces; provision and test live ENS authority/revocation;
repeat fresh comparisons after model/tool upgrades. Preserve ordinary delivery as an allowed policy.

No live-publication claim is made by this companion. `PUBLICATION_HANDOFF.md` and the final status
receipt distinguish reviewed source, paper-only publication and full browser-edition qualification.
"""
    text = text.replace("--seed7401", "--seed 7401")
    (ROOT / "evidence_companion.md").write_text(text)
    artifact = {
        "economic_results_sha256": hashlib.sha256(
            (ROOT / "results/economics/economic_results.json").read_bytes()
        ).hexdigest(),
        "native_reconciliation": native["simulation_reconciliation"],
        "study_seed_count": seed_count,
        "confirmation_seeds": results["seeds"],
        "capacity_amendment_sha256": hashlib.sha256(
            (ROOT / "protocol/economic_capacity_amendment.json").read_bytes()
        ).hexdigest(),
        "economic_audit_sha256": hashlib.sha256(
            (ROOT / "evidence/economic_audit_v3.json").read_bytes()
        ).hexdigest(),
        "scenario_count": len(scenarios),
        "policy_count": 6,
        "actual_customer_collections_usd": 0,
    }
    (ROOT / "evidence/companion_build.json").write_text(json.dumps(artifact, indent=2))
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    build()
