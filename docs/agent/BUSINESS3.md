[Project notice](../DISCLAIMER_SNIPPET.md)

# Business 3 — a plan with its assumptions attached

**Release 1.16.0.** [Open Enterprise Studio](../alpha_agi_business_3_v1/index.html),
choose a case and select **Calculate the portfolio**. No account, wallet or API key is needed.
Change capital, staffing, review time, job budget and downside assumptions; then calculate again.
Expand a candidate to edit its costs, three annual cash flows, resource needs and evidence score.

The five cases use constructed data. The optimizer calculates the best feasible subset of at most
16 candidates under your declared constraints. It does not validate the assumptions or predict returns.
The result remains **Review required**, **Hold** or **No feasible portfolio**. None of those actions
approves spending, mints a token or submits a job.

## Read the result

1. Compare expected and policy-downside net present value. Capital includes the overrun reserve.
2. Inspect resource use, source descriptions, evidence screening and dependency constraints.
3. Read the fixed-portfolio stress table. A worse outcome remains visible; the selection is not silently changed.
4. Review each goal, measurable success metric, deadline and separate AGIALPHA bounty.
5. Download the complete ZIP. Save a draft explicitly if you want to resume on this device.

Annual cash flows are net operating cash flows in whole USD over three years. There is no terminal value.
The model floors each discounted cash flow, increases negative cash flows under an adverse shock and rounds
stressed capital up. The exact search compares every bounded subset. Ties favor downside value, lower
resource use and finally project IDs. The greedy comparison is an algorithm comparison on supplied inputs.

## Run the same calculation locally

The maintained planner needs only **Python 3.11–3.13**. From a source checkout:

```sh
python -m alpha_factory_v1.demos.alpha_agi_business_3_v1 --list
python -m alpha_factory_v1.demos.alpha_agi_business_3_v1 --case industrial --output business3-runs
```

An installed release wheel also provides `alpha-agi-business-3-v1`. The common catalog launcher supports:

```sh
python -m alpha_factory_v1.demos check alpha_agi_business_3_v1
python -m alpha_factory_v1.demos run alpha_agi_business_3_v1 --output-dir business3-runs
```

Each distinct dossier gets its own full SHA-256 directory. Identical runs reuse verified identical files.
Modified, partial or redirected prior output is rejected without replacement. Retain it and choose a new
output root if you need to recover. Paths containing spaces work; quote them in your shell.

| File | Use |
|---|---|
| `scenario.json` | Editable assumptions and source descriptions |
| `dossier.json` | All inputs, computed results, unreviewed status and content commitment |
| `decision-brief.md` | Readable decision, units, method and limitations |
| `selected-projects.csv` | Selected resource and value figures |
| `jobs.json` | Unsubmitted goal ↔ success metric ↔ bounty specifications |
| `seed-draft.json` | Unminted, unencrypted content commitments for review |
| `SHA256SUMS` | Exact checksums for the other six files |

Import `dossier.json` into the browser or run the verification command printed by the CLI:

```sh
python -m alpha_factory_v1.demos.alpha_agi_business_3_v1 --verify path/to/dossier.json
```

Verification recomputes every decision and exported job. Changing a result and recomputing its hash does
not bypass this check. A matching hash does not prove source truth or authenticate an independent reviewer.

## Continue through the full vision

For a nonempty plan, install the [operator release](START_HERE.md) and compile its exact jobs:

```sh
alpha-agent ascension-compile path/to/jobs.json --output fusion-plan.json
alpha-agent ascension-check fusion-plan.json
```

| Stage | Continue with |
|---|---|
| Insight and source investigation | [Insight Atlas](../insight/index.html) and native research missions |
| Nova-Seed commitments and recovery | [Ascension Lab](../ascension/index.html) |
| MARK, Sovereign, staked ENS agents and validators | [Protocol Desk](../ascension-protocol/index.html) and the [local-EVM guide](ASCENSION_PROTOCOL.md) |
| Review, promotion and revocation | [Proof Bloom](../bloom/index.html) |
| Test retained experience on new work | [Compounding Lab](../compounding/index.html) |

The protocol reference implements funding gates, treasury restrictions, indexed jobs, auctions, exact
artifact validation, refunds, slashing and the 1% payout burn. It remains undeployed; a browser dossier is
not an ERC-721, verified ENS identity, legal approval or operating autonomous enterprise.

## Containers, notebooks and original research

The [complete demo README](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/alpha_agi_business_3_v1) contains the
network-isolated container launcher, executable Colab notebook, full schema and original flowcharts.
The original PDF/PPTX are unchanged. The research narrative and notebook are retained as labeled archives.
The original Ω-Lattice loop remains available through `--legacy-loop`; commentary and research adapters
require explicit opt-in. Its dimensionless toy score is not a thermodynamic measurement or market forecast.
No built-in proof verifier or autonomous weight training is claimed.

Release acceptance requires exact Python/browser parity, real output verification, installed-wheel launches,
notebook execution, a real container run, both browser routes, keyboard accessibility, mobile layout,
explicit recovery, offline recalculation and rejection of tampered evidence. The public receipt is bound
to the exact release commit, version, asset bytes and five recomputed cases.

## Read the decision visuals and research collection

After calculation, **See what earns a place** compares every candidate's expected and policy-downside NPV
on one common scale, including negative values. Each row identifies selection or insufficient evidence and
prints both exact USD amounts. Standalone value does not override portfolio constraints or dependencies.
Changing inputs clears the result until you recalculate.

The **Research collection** retains the original artwork at a compact size, with direct access to the
flowcharts, founding research and capital-committee workspace. The original synthetic replay remains available
with explicit unitless axes. Expand **Inspect the original event log and exact chart values** to inspect its
unchanged source records. Optional OpenAI and Python controls remain explicit, separate research tools.
