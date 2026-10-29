# SPDX-License-Identifier: Apache-2.0
"""Build a research handoff from the saved evidence, never from desired outcomes."""

from __future__ import annotations
import argparse, json, hashlib
from fractions import Fraction
from pathlib import Path
from typing import Any


def read(p: Path) -> Any:
    return json.loads(p.read_text())


def build(study: Path, patch: Path) -> None:
    main = read(study / "confirmation-v2/summary.json")
    final = read(study / "final-untouched-v2/summary.json")
    reproduced = read(study / "reproduction-v2/summary.json")
    commercial = read(study / "commerce/requalification-v4/summary.json")
    shared = read(study / "shared-confirmation/summary.json")
    policy = read(study / "SEED_AND_COST_POLICY.json")
    costs = []
    for prefix in ["confirmation-v2", "final-untouched-v2", "reproduction-v2"]:
        for suffix in ["-process.json", "-audit-process.json"]:
            p = study / (prefix + suffix)
            if p.exists():
                value = read(p)
                costs.append(
                    {
                        "id": str(p.relative_to(study)),
                        "stage": "distinct-measured-process",
                        "quantity_cpu_seconds": value["cpu_seconds"],
                        "rate_usd_per_cpu_second": "1/36000",
                        "amount_usd": value["amount_usd"],
                        "basis": "measured enclosing CPU; constituent stage CPU not added again",
                    }
                )
        p = study / (prefix + "-independent-audit.json")
        if p.exists():
            value = read(p)
            costs.append(
                {
                    "id": str(p.relative_to(study)),
                    "stage": "distinct-independent-auditor-process",
                    "quantity_cpu_seconds": value["child_cpu_seconds"],
                    "rate_usd_per_cpu_second": "1/36000",
                    "amount_usd": value["modeled_cpu_cost_usd"],
                    "basis": "separate actual audit invocation; distinct from runner audit-process",
                }
            )
    measured = sum((Fraction(c["amount_usd"]) for c in costs), Fraction())
    ledger = {
        "currency": "simulated USD resource equivalent",
        "actual_external_spend_usd": "0",
        "ai_development_estimate_usd": policy["development_estimate_usd"],
        "development_events": policy["events"],
        "unmetered_early_development_and_packaging_cpu": {
            "quantity_seconds": "1800",
            "rate_usd_per_second": "1/36000",
            "amount_usd": "1/20",
            "basis": "explicit conservative engineering CPU allowance; includes v1, smoke failures, tests, shared and merchant experiment fragments, external diagnostics and packaging not separately charged as actual CPU events",
        },
        "measured_processes": costs,
        "known_incremental_before_final_retention_usd": str(
            Fraction(policy["development_estimate_usd"]) + Fraction(1, 20) + measured
        ),
        "nested_commerce_development_usd": "11/25",
        "nested_commerce_included_in_parent_envelope_usd": "89/100",
        "historical_known_allocation_usd": policy["historical_known_allocation_usd"],
        "historical_other_transfer_work": "full incurred allocation not aggregated; cumulative whole-program payback unknown",
        "counterfactual_world_costs": "Separate scenario financial books; not summed as88 real customer invoices or88 actual seed developments",
        "deduplication": "Measured enclosing process costs replace their own scoped stage costs. Early measured fragments are inside the1800CPU-second estimate. Merchant.44 is inside parent.89, not an extra project expense. One retained archive month is a separate final bytes×rate event.",
        "quantity_10x_model_sensitivity_usd": str(10 * Fraction(policy["development_estimate_usd"])),
        "earned_new_construction": False,
        "resource_cap_usd": policy["seed_resource_equivalent_cap_usd"],
    }
    (study / "COST_ACCOUNTING.json").write_text(json.dumps(ledger, indent=2) + "\n")
    arms = ["none", "A", "S", "C", "AS", "AC", "SC", "ASC", "frontier_program"]
    cells = main["factorial"]["cells"]
    table = "\n".join(
        f"| {a} | {cells[a]['accepted']}/{cells[a]['n']} | {cells[a]['accepted_feasible']} | {1e6 * cells[a]['mean_execution_cost_usd']:.3f} |"
        for a in arms
    )
    cps = main["learning"]["checkpoints"]
    learn = "\n".join(
        "| "
        + str(i)
        + " | "
        + " | ".join(
            f"{cps[str(i)]['systems'][a]['accepted']}/48" for a in ["cumulative", "frozen", "reset", "retrieval"]
        )
        + " |"
        for i in range(4)
    )
    held = final["learning"]["checkpoints"]["3"]
    h = held["systems"]
    ratio = float(Fraction(h["cumulative"]["mean_marginal_cost_usd"]) / Fraction(h["frozen"]["mean_marginal_cost_usd"]))
    assert commercial["positive_complete_cost_worlds"] == 0 and commercial["worlds"] == 88
    report = f"""# AGI ALPHA: executed compounding-discovery handoff

**Mission status: NOT COMPLETE.** The local repository now has an executable,
reviewed A/S/C workflow and source-bound experiments. This bounded instantiation
did not earn combination superiority, progressively greater useful output, or a
profitable earned-funded successor. It should not replace the stronger
conventional defaults.

## Direct answers

**Does the combination help?** No improvement was observed in this study. All
eight configurations and the independently authored frontier-program reference
accepted48/48 factorial cases. All seven main/interaction estimates and the
full-minus-none acceptance contrast are zero. Extra transfer, search and critics
incur costs. This is a ceiling on a known linear model, not evidence that these
mechanisms can never help elsewhere.

**Does experience make it progressively more useful?** No. The untouched final
panel accepted{h["cumulative"]["accepted"]}/48 cumulative outcomes versus
{h["frozen"]["accepted"]}/48 frozen,{h["reset"]["accepted"]}/48 reset and
{h["retrieval"]["accepted"]}/48 ordinary-retrieval outcomes. Full-minus-frozen is
−4.167 percentage points, paired task-cluster95% interval[−12.5,0]; full-minus-
retrieval is zero. Mean final modeled marginal CPU cost is{ratio:.2f}times frozen.
Retained programs reduce LP calls but repeated checked-memory reconstruction
raises cost and retained strategies have adverse transfer. No multiplication or
compounding benefit is supported.

## What was actually built

The base is MontrealAI/AGI-Alpha-Agent-v0 commit
`12770c22b4a9f90f2013bbfb64242f912ba5071e`, verified against public main at initial
inspection. The preceding private transfer/claim/flood/payment implementation is
preserved and integrated additively. The exact public-base integration patch is
`{patch.name}`, SHA256`{hashlib.sha256(patch.read_bytes()).hexdigest()}`.

`work.kind="compounding-discovery"` runs through the ordinary signed Journal,
review and export lifecycle. `discovery run/check/learn/resume` provides explicit
inputs, artifacts, exclusive outputs, failure records and checked chronological
promotion. Normal review is still required before export. Source hashes and
self-hashes do not authenticate a malicious filesystem owner; the existing
signed journal supplies operator identity.

A replays completed simulated productive source work, extracts a typed capacity
principle, validates a total causal-role/unit mapping and constructs the target
model. It does not discover a physical law or convert currency to energy.
S invents within a restricted executable grammar of six LP method/presolve
programs; a first-task portfolio tests three unique programs. This is bounded
solver-portfolio invention, not unrestricted investigation/coordination synthesis.
C performs a certificate-corruption challenge and two seeded moderate operator
perturbations. Every criticism requires the independent raw-model checker before
retention. C-off retains exactly the same final acceptance checks.

Versioned memory retains actual principles, strategies, applicability limits,
full criticism witnesses once, cost provenance and chronological parent bindings.
Assets reference witnesses by hash. Twelve teaching tasks fit the unchanged1MiB
contract; final memory is{main["retention_bytes"]}bytes. Old duplicated-memory
failures remain. A loaded old certificate cannot answer a new task by hash alone;
new output is freshly solved and independently checked.

The original SUCCESSOR Ω Strategy Laboratory archive was located but not reused
as if its description were implementation. Existing successor companion source
was inspected. The new restricted LP grammar and adaptation code are inspectable
repository source.

## Opportunity and beneficiary scope

`OPPORTUNITIES.md` compares shared-charger paratransit repair, county flood
information and laboratory QC against practical alternatives, documented need,
pricing evidence and demand uncertainty. No candidate earned broad Blue Sky
commercial admission. Shared charging was pursued as a specific missing
repository construction, not promoted as a civilization-scale discovery or a
novel scheduling algorithm. Existing specialist work already couples energy
resources; free alternatives remain serious competition. Public service expense
and adjacent API prices never become revenue or buyer willingness to pay.

A separate **initial seed-funded** joint charging-port construction creates
independently checkable complete passenger/time/charging/battery artifacts. On32
fresh simulated operator updates to known public16-passenger raw data, joint
construction passed{shared["joint_accepted"]}/32, versus{shared["relaxation_accepted"]}/32 for the prior
per-vehicle relaxation. Thirteen cases pass only with joint construction;
{shared["unresolved_joint"]}joint searches remain UNRESOLVED. The old relaxation omits the new
shared-port requirement, so this demonstrates added model scope rather than
superiority to a competent joint specialist. No global optimality, physical
fleet safety, new city, actual passenger service or customer value was tested.

## Component-combination experiment

Each task/seed block has all eight arms with the same raw task, historical source
availability, solver options, authority and cap:100operations,16LP calls,30CPU
seconds. Unspent budget is allowed. Strategy search, adaptations, critics,
verification and failed calls are charged. Four strata × four tasks × three
run seeds produce48observations per arm but only16distinct task clusters.
The none arm is the full conventional LP, not a deliberately weak solver. The
frontier reference is a real separately authored and pinned deterministic
program, not a fresh live-model call. Its original output and fixed format
translation are retained; the common checker remains unchanged.

| Configuration | Accepted certificates | Accepted feasible schedules | Mean modeled CPU cost, microUSD |
|---|---:|---:|---:|
{table}

Acceptance is FEASIBLE or independently witnessed INFEASIBLE. A correct
infeasibility diagnosis does not transport passengers. There are no new feasible
factorial outcomes unique to the full arm. No independently contradicted accepted
model conclusion was found; this does not establish external physical truth.

The fixed practical minimum is5percentage points. Task-cluster paired bootstrap
uses2000draws. Main effects average paired differences, pairwise effects average
differences-in-differences, and the three-way effect is the alternating eight-cell
contrast on accepted-certificate proportion. Zero empirical bootstrap intervals
at this saturated endpoint are not population equivalence proofs. Every contrast
is retained. Multiplication was neither tested nor claimed.

## Chronological experiment and untouched final

Three training cycles add four chronological cases each. Evaluation panels are
fresh instances from common difficulty strata; probes never update memory. The
full and ordinary retrieval systems share exactly the same historical records;
retrieval may independently find the same strategy. Frozen and reset are
intentionally behaviorally equivalent here. Clean context is not claimed to
remove pretrained knowledge.

| Learning cycles | Cumulative | Frozen | Reset | Ordinary retrieval |
|---|---:|---:|---:|---:|
{learn}

The independent untouched final panel was evaluated once after final-state
freeze, without training on its labels. It has the adverse counts stated above.
Final/full memory and candidate bytes are unchanged. No threshold, budget,
acceptance rule or method was repaired into success. A new separate full
reproduction uses the same inputs/seeds; it is replay, not new confirmation.
`figures/learning-curves.csv`, PNG and vector PDF show all checkpoints, acceptance,
cost and solver calls. Exact paired uncertainty and lifecycle costs remain in
`summary.json` for every system.

Original unsupported wrappers preserve request, seed, memory identity, incurred
costs and failure type. They did not retain the inner rejected candidate bytes.
The separately labeled read-only diagnostic replay captures new inner artifacts
and independent reasons; it cannot recover the original missing bytes and must
not be silently substituted for them. The diagnostic replay found12 rejected witness artifacts with a contradiction
string whose redundant fractional trailing zero gives Decimal exponent−31,
outside the checker contract≥−30. This is new replay evidence of a serialization
contract failure; it does not recover the original missing bytes. A future
producer-only exact trailing-zero removal must be frozen and tested fresh; no
locked result here has been relabeled.

## Frozen rounds, failures and resource compliance

All original attempts are retained. Development exposed malformed old contracts,
frontier witness-format/precision incompatibility, fabricated memory lineage,
negative resource counters, unsupported A/C promotion, duplicate criticism
storage, missing thin-checkout dependencies and invalid simulated keys. Those
were repaired on development evidence without weakening acceptance.

The first full round `confirmation-v1` has1212records and its unfavorable learning
results. Its source/math audit passes, but it violated the declared free-disk
floor and is **not resource-qualified confirmation**. It was not erased or
relabeled as compliant. Only exact recoverable copies created in this turn's
isolated checkout were omitted; prior source and evidence remain intact.

The resource-only evaluator revision freezes a prospective200,000,000-byte
floor and pauses before work. Candidate hashes, metrics and allocation are
unchanged. New `confirmation-v2` seeds were generated after freeze. All1224
observation/promotion guards qualify, minimum316,674,048free bytes. Final's192
new guards qualify, minimum283,369,472; historical promotion receipts are checked
separately. Source snapshots, memory versions, configurations, task identities,
programs, artifacts, costs and all adverse outcomes are retained. V2 contains
1212observations,1204accepted certificates and8unsupported outcomes; these8
are not audit failures or accepted false claims. The final has192observations,
184accepted and8unsupported outcomes. Reproduction results and guard receipts
are separate outputs.

## Simulated economics and funding

The protected exchange is reused with task/source-bound encrypted private output,
independent checking, assured simulated funding before release, refunds,
reversals, delays, refusal, duplicate settlement protection and restart recovery.
All payments remain simulated. A local provider assumption is not external
settlement finality or a qualified multiwriter service.

The frozen commerce run has88worlds/44pairs. Current-source requalification
replays the same authored scenarios and is not fresh market evidence. Every SQL,
cost/funding audit and24encrypted entitlement reconstructions pass. **Zero worlds
are complete-cost profitable; zero earned-funded successors exist.** Profit
ranges from−1.784807to−0.248599USD in the current-source repetition. A free
completed equivalent produces zero paid participation. Conditional assumed
integration-cost cases can trade, but do not repay complete costs. No customers,
purchase intent or empirical willingness to pay were observed. No paid demand
was manufactured.

New shared charging is seed-funded, not an earned-funded successor. No new
investment is authorized from the adverse modeled commerce. Historical county
construction and its subsequent complete reversal remain supporting history,
with original funding provenance and loss unchanged. Account balance, escrow,
collections and unrestricted earned permission remain distinct.

## Costs and practical limits

`COST_ACCOUNTING.json` contains exact quantity-times-rate events. New AI
construction/review work is estimated at{policy["development_estimate_usd"]}USD, with explicit
per-activity token quantities and inherited5USD/million input,30USD/million
output reference-rate assumptions; these are not invoices, measured token counts
or fresh provider quotes. A10×quantity sensitivity is{ledger["quantity_10x_model_sensitivity_usd"]}USD.
No fictional human workforce is used.

CPU is modeled at0.10USD/hour. New whole-process receipts include their stage
CPU, serialization and analysis; those stage totals are not added again. Separate
actual auditor invocations are separate events. An explicit1800CPU-second
allowance prices early uninstrumented development, failed work and packaging at
0.05USD; covered fragments are not additional actual expenses. The merchant's
0.44USD development is inside the parent's0.89USD commerce envelope, not another
project charge or88actual invoices. The known incremental allocation before final
retention is{float(Fraction(ledger["known_incremental_before_final_retention_usd"])):.6f}USD. Final artifact
bytes times the declared0.03USD/decimal-GB-month assumption are recorded separately.
Actual external spend is zero. Historical known allocated work20.609070USD remains
separate; wider incurred historical transfer cost and whole-program payback are
not fully aggregated and are not asserted to be zero or recovered.

The retained improvement hypothesis failed in this instantiation. The current
memory index does not guarantee strategy applicability under numerical/operator
changes; full replay of growing history is expensive. Broad strategy invention,
new-domain generalization, a qualified beneficiary paid gap, native provisioning
and earned-funded successor benefit remain unestablished. A stronger opportunity
requires actual beneficiary specifications/data and evidence against competent
completed alternatives; the prohibited outreach, spending, provisioning and
publication edges have not been bypassed. Further mathematical fixtures alone
cannot establish those missing links.

## Usable entry points and writer claim boundaries

Run from repository root with the existing Python3.11–3.13 environment and project
`compounding-discovery` optional dependencies; SymPy is additionally needed for the
118historical claim regressions. See `docs/compounding_discovery.md` for normal
mission and review commands.

```sh
python -m alpha_factory_v1.core.runtime.cli discovery run contrib/compounding_discovery/example-request.json --output NEW_DELIVERY
python -m alpha_factory_v1.core.runtime.cli discovery check NEW_DELIVERY
python -m alpha_factory_v1.core.runtime.cli discovery learn NEW_DELIVERY --output NEW_MEMORY.json
python contrib/compounding_discovery/audit.py --campaign studies/compounding-discovery-v1/confirmation-v2
python contrib/compounding_discovery/experiment.py --resume --output studies/compounding-discovery-v1/confirmation-v2
python contrib/compounding_discovery/experiment.py --reproduce-from studies/compounding-discovery-v1/confirmation-v2 --output NEW_REPRODUCTION
```

Use a new output for reproduction; never overwrite historical evidence. The
original final seed is already consumed; replaying it is not another untouched
final. Old-version reproduction requires its exact archived source snapshot.
The integration patch was checked against the exact public base.118inherited
regressions and137focused profile checks pass; four resource-boundary checks are
included. Ancillary diagnostic testing is separate. The complete repository,
held-source, hosted release, cross-platform, physical and live-native campaigns
are not claimed. Strong symbolic default and source/release boundaries remain.

For the LaTeX series, cite the exact frozen round, task cluster count, model scope,
program limitations and modeled-cost assumptions for every result. Report the
negative held result and unprofitable exchange prominently. The shared-port
construction is evidence of added repository scope, not proof of AGI, autonomous
scientific discovery, empirical market success or a compounding enterprise.
"""
    (study / "AGI_ALPHA_Compounding_Discovery_Report.md").write_text(report)
    claims = {
        "combination_usefulness": "not supported in saturated known-model panel",
        "progressive_usefulness": "not supported; adverse untouched final",
        "synergy": "no nonzero acceptance interactions",
        "new_joint_scope": shared,
        "commercial_success": False,
        "earned_successor": False,
        "mission_status": "NOT COMPLETE",
        "source_freeze": main["source_freeze"],
        "reproduction_source_freeze": reproduced["source_freeze"],
        "final_source_freeze": final["source_freeze"],
        "paper_claim_limit": "Bounded deterministic model investigation, not a live frontier-agent or general cross-domain test",
    }
    (study / "WRITER_CLAIM_MAP.json").write_text(json.dumps(claims, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--study", type=Path, required=True)
    p.add_argument("--patch", type=Path, required=True)
    a = p.parse_args()
    build(a.study, a.patch)
