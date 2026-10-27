# Reporting amendment — 27 October 2026

## Purpose and timing

The user requested a revised commercial priority and presentation:

**PROFITABLE WORK FIRST. COMPOUNDING CAPABILITY WHEN WORTHWHILE.**

The amended edition leads with competent Beta delivery, complete modeled operating
economics and available cash, then considers retained Alpha and separate R&D as optional
allocation decisions. Profitable service delivery does not require a positive incremental
shared-capability result. A capability investment still requires its own evidence,
prospective economic justification and affordable cash.

This is a **post-results reporting amendment**. The user request followed completion and
inspection of the frozen experiment and its first publication edition. It changes the
order and emphasis of the explanation, together with explicitly labeled derived reporting
tables. It is not a new scientific protocol, a new confirmation exercise, or a retrospective
claim that a newly preferred hypothesis was preregistered as the exclusive primary endpoint.

## The scientific record remains fixed

The preexisting v2 protocol already separated four hypotheses in section 3:

| Frozen hypothesis | Its original role, preserved in this edition |
| --- | --- |
| `Hbeta` | Complete-cost ordinary commercial surplus of competent Beta delivery under a selected pricing policy, with the matched human service in the buyer choice set. |
| `Halpha` | A scoped incremental benefit of a candidate or bundle beyond competent Beta and currently available methods after complete incremental costs. |
| `Hshare` | Network availability's increment over isolated retention under comparable initial resources, including sharing and integration costs. |
| `Hdurability` | The persistence of those incremental effects under moving Beta, overlap, copying and obsolescence. |

Their definitions, estimands, labels and declared priorities remain exactly as frozen.
The original protocol lists `Hbeta` first and requires that economic hypotheses be
evaluated separately. The amended narrative emphasizes that existing commercial result;
it does not reorder the frozen hypothesis table or convert a null Alpha result into a
positive one.

The following remain unchanged:

- The 20 frozen scientific source, test, calibration and protocol files.
- The 32-policy family, training objective, sample cash-risk constraint, scenarios,
  resources, accounting, role assumptions and buyer model.
- All original prices, seed schedules, training decisions, confirmation samples,
  sensitivity cases, ablation outputs and retained negative findings.
- The 6,048 simulated histories: 2,304 training, 768 primary confirmation,
  2,736 sensitivity and 240 ablation histories.
- The known-method mathematical witness, graph lifecycle, source-bound modeled admission
  replay, cryptographic fixture boundary, and native accounting projection.

No new model run, customer observation, price search, production event or transaction is
introduced by this amendment. Presentation scripts derive views of existing records; they
do not execute new economic worlds or replace an adverse result. The change is distinct
from the earlier disclosed scientific v1-to-v2 amendment concerning paid-job learning,
which remains preserved in `evidence/development/protocol-v1/`.

### Frozen and result identities

| Record | SHA-256 |
| --- | --- |
| `results/protocol_freeze.json` | `7cb1683c08090d68cef5e847438446dda8032b67163c5368c2cbdaddce180dcb` |
| `results/summary.json` | `16aaa53ee1e14c625bac0cd86a19b351a76ff16e512e991a2bde2bedd4419f7f` |
| `results/selected_policies.json` | `807d31c1de6072c577091cb028451edba415ac491e7d31e52b31199f47122bfd` |
| `results/confirmation_runs.jsonl` | `dbab57901445f88696dd03f331eaf52abe8d3ffbe2fb64c3531e24a9065c628a` |

All frozen source hashes matched when this amendment was prepared. After restoring the
raw evidence where necessary, the same scientific identity check is available from the
study root:

```sh
python3 - <<'PY'
from pathlib import Path
from src.run_study import verify_freeze
verify_freeze(Path('results'))
print('Frozen scientific source identities match.')
PY
```

## What the revised reporting says

The commercial core's mean **modeled collected operating surplus** is unchanged:
$411,421 in the conservative scenario, $3,702,395 in the central scenario and $6,763,479
in the favorable scenario. These figures deduct complete accrued costs and unexpensed
closing obligations. They exclude initial seed capital and future receivables. They are
conditional simulator results, not realized provider earnings or market return estimates.

The commercial-core companion also reports existing available cash and a derived view,
`max(0, available_cash − initial_seed)`, to show cash remaining after setting aside the
original seed **at closing**. The seed was available for use during the original simulation;
this reporting comparison does not impose a new historical reserve constraint. This
derived view is separately identified; it is not retrospectively presented as a
preregistered primary estimand or an automatic investment allocation.
Reported available cash already excludes funded commitments, warranty reserves and
accrued unpaid costs. Remaining refund exposure and the policy's operating reserve still
matter for any new allocation. Profit, cash, closing obligations, reserve requirements
and optional spending therefore remain distinct.

The further-allocation reporting view is
`max(0, min(profit, available_cash − initial_seed) − operating_floor)`, calculated per
world before aggregation. The profit cap respects unexpensed closing obligations; the
additional operating floor is $2,640 in each primary Beta scenario and is not a new
expense. Its means are $408,312, $3,698,570 and $6,758,482. These are conditional closing
resources for possible delivery, reserves or justified investment, not a spending mandate.

A separate postconfirmation reporting sensitivity joins receipts to the simulator's
correct, on-time useful outcomes. It excludes other receipts while retaining all accrued
enterprise costs and unexpensed closing obligations. Mean useful-receipts-only surplus is
$343,435, $3,522,731 and $6,527,982. The conservative minimum is −$30,129. These results
retain the original failure costs and make explicit that the all-worlds-positive
conservative finding depends on counting the model's full receipt stream. This filter
uses latent simulation truth, not empirically validated delivery quality, and is not a
new confirmatory endpoint.

The derived register is `results/commercial_core.json`, SHA-256
`dbe982f54b364db7b9874cd5ce30e3dc06ff344e42e39eeffe9e37788d6fc85a`.
Its provenance records unchanged input identities and no new economic seeds. Its
reporting arithmetic and reconciliation checks do not constitute additional scientific
trials or customer observations.

**Pricing provenance is unchanged.** The original training procedure selected policies
on the network policy family, then applied each selected policy unchanged across the
primary arms, including Beta. The Beta commercial results evaluate those policies. This
edition does not claim an independent Beta-specific optimizer, a new optimum, or a new
price experiment. The selected human-reference-relative prices and their calibration
remain the original ones.

**Quality remains a modeled assumption.** The experiment includes errors, false passes,
correction failures, refunds, abstention and demand/trust assumptions. No empirically
qualified service-quality floor, matched live frontier acceptance rate, human-only effort
measurement or customer willingness-to-pay estimate is established. Positive modeled
surplus cannot qualify an actual offering by itself. The commercial emphasis preserves
the proposed task-matched operational validation requirements.

**Optional Alpha findings are preserved.** The primary paired network-minus-Beta surplus
increments remain approximately −$13,947, −$12,063 and −$8,766 for the three scenarios.
The favorable interval spans zero. No selected primary policy undertakes separate C R&D.
The deterministic retention panel's conditional advantage remains separate from enterprise
confirmation, and its declared assumptions do not become empirical Alpha. Component-mask
ablations remain total intervention effects, including policy and queue responses, rather
than isolated marginal capability benefits. No new commercially validated offering,
durable moat, separate-R&D feedback loop or self-acceleration is claimed.

The permitted decision set continues to include profitable delivery, holding reserves,
deferring investment, incremental retention, joint bundles, separate R&D when worthwhile,
and no investment. There is no compulsory reinvestment count or percentage. `$AGIALPHA`
utility remains separate from operating earnings; issuance or appreciation supplies no
profit in the model.

## Preservation of the first publication edition

The prior finalized Source ZIP and the original PDF's retained version 0 preserve the
first publication edition. The original raw-evidence archive is unchanged. These are
identities of the earlier release, not claims about the current bytes of a working
filename after a later publication update. Public package documentation does not require
private artifact identifiers.

| Earlier artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `AGI_Alpha_Flywheel_Source.zip` | 2,387,643 | `d07295dd4481f5ee3ab890f82ae68645f93e7a2aa131e23038a4894ffe189885` |
| Released paper PDF, retained version 0 | 476,599 | `2ed25789a9ee5cedc52939695087e073fce6bf5711bb10c434ce4c55b79613bc` |
| Original raw-evidence ZIP, retained version 0 | 89,373,338 | `cbbd661915f580004ab4467a32b300736e71f6358ab70a324ea2b4872af94ceb` |

The Source ZIP was checked before editing the README. It contains the earlier README
headed “AGI ALPHA FLYWHEEL: PAID WORK. RETAINED ALPHA. EXPANDING POSSIBILITY.” Its original
README SHA-256 is `dccd20478e67cd7cce4b60778e64d31094b51e7c081123dc27cdddbedb957441`.

Local prior-edition paper sources and the postprocessor are retained under
[`editorial-priority-v1/paper/`](editorial-priority-v1/paper/). The original main LaTeX
source has SHA-256 `c7f4e98daa38f2f6d174e1f5252b6e2bc9144975ea5d929bfef2e693f5ff2061`, and
its generated results section has SHA-256
`91f202e839b69cb52a10d6c723ebe30a7ca902072ac83eaafc465746d5ecf72e`. Both match the earlier
Source ZIP. Prior demo assets are retained under `editorial-priority-v1/demo/`, with a
[preservation receipt](editorial-priority-v1/demo_preservation_receipt.json).

## Publication and authority

The amended materials remain an isolated draft study under
`studies/network-invented-economy-v1/`. Existing authors, owners, experiments, contracts,
AGI Jobs club roles and settlement routes remain unchanged. The publication owner will
coordinate the reporting update through issue 4850 and preserve prior artifact versions.
This amendment does not authorize a deployment, provider purchase, live engagement,
credential change, financial transaction or execution bypass.
