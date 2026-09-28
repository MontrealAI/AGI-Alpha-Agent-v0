[Project notice](../DISCLAIMER_SNIPPET.md)

# Meta-Agentic AGI v3 — Curriculum Lab operating guide

The [Curriculum Lab](../meta_agentic_agi_v3/index.html) generates small integer-program tasks, searches for solutions
from examples, and lets a meta-agent choose the next solver configuration. Separate tasks review the final frozen
candidate. No account, API key, Docker installation or model download is needed for this workflow.

## First useful result

1. Open the lab and keep **A curriculum that can challenge its solver** selected.
2. Read the frozen solver accuracy, improvement over the baseline and counted operation cost.
3. Move the round slider to inspect the examples, inferred program and predictions. Reveal the reference to compare
   it with the hypothesis; the solver itself never receives the reference or expected test answers.
4. Compare candidate configurations and expand their parent/child lineage.
5. Read all four review gates, then inspect a held-out task. **Eligible for review** does not mean approved.
6. Download the six-file evidence ZIP and retain it outside browser storage.

Try **When the curriculum misses an entire skill** to see a coverage failure and **Accuracy has a resource cost**
to see a candidate held despite high accuracy. A hold is a valid experiment outcome.

## Run locally

Install the matching release using [Start here](START_HERE.md), then:

```bash
curriculum-lab --list
curriculum-lab --case balanced --output curriculum-runs
curriculum-lab --serve
```

Open the printed loopback URL (`http://127.0.0.1:7863/meta_agentic_agi_v3/` by default). Stop with Ctrl+C.
If the port is occupied, use `--port 7864`. The server exposes only packaged static assets and a health check;
it has no upload, credential, shell or execution API. `python -m alpha_factory_v1.demos.meta_agentic_agi_v3`
is equivalent to `curriculum-lab`.

The core is standard-library-only. Cloud-related environment variables do not change its behavior.

## Customize before evaluating

| Setting | Allowed values | Meaning |
|---|---|---|
| Seed | Integer 0–4294967295 | Private, reproducible xorshift random stream |
| Rounds | 1–12 | Number of curriculum/selection iterations |
| Tasks per round | 3–12 | Requested unique behaviors; a saturated grammar may yield fewer |
| Maximum depth | 1–3 | Maximum operators in a composed hypothesis |
| Families | Unique subset of arithmetic, nonlinear, remainder | Training curriculum coverage |
| Positive examples | Boolean | Restrict training examples to positive inputs to expose ambiguous hypotheses |
| Entropy weight | 0–1000 | Weight for diversity of solved task families |
| Review policy | Accuracy, weakest-family accuracy, baseline gain, operation ceiling | Independent eligibility thresholds |

The visible controls cover common settings; expand **Inputs & reproducibility** for complete JSON. Apply edited
JSON before running. Every change invalidates existing exports. Save, restore and forget are explicit device-local
operations; unrelated browser storage is retained. Saved settings do not restore results.

Choose seeds and policies before examining evaluation results. This public synthetic test set is an educational
control, not a secret benchmark. Repeated evaluation-guided tuning requires new independent data.

## Retain and verify

The ZIP and native run directory contain:

| File | Contents |
|---|---|
| `scenario.json` | Exact accepted settings and stated assumptions |
| `run.json` | Tasks, solver attempts, complete candidate metrics, lineage and independent review |
| `solver-proposal.json` | Frozen candidate, input hash and UNAPPROVED status; baseline remains active |
| `jobs.json` | Unsubmitted Ascension review job with goal, success metric and draft AGIALPHA bounty |
| `review.md` | Human-readable outcomes, exact comparisons and scope |
| `SHA256SUMS` | Hashes of the five preceding files |

```bash
curriculum-lab --verify path/to/run.json
curriculum-lab --input my-scenario.json --output curriculum-runs
```

Verification recomputes all evidence and rejects rehashed forgeries. Identical native reruns reuse the identical
SHA-256 named directory; altered or incomplete bundles are rejected. Back up complete directories. Checksums do
not authenticate a person or prove validator approval.

The [Ascension protocol](ASCENSION_PROTOCOL.md) can compile the exported job into a FusionPlan. The draft bounty
is 100 $AGIALPHA, expressed as `100000000000000000000` base units. This lab neither posts nor funds the job;
separate identity/staking, escrow, validator and settlement contracts govern that lifecycle.

## Scope and preserved research

This is an actual finite hypothesis search, configuration evolution and adaptive curriculum. It is not AZR model
training, PPO, NSGA-II, a general-purpose autonomous agent, a measured financial-alpha system, or live enterprise
commissioning. Its free-energy diagnostic is a cost-minus-entropy proxy, not thermodynamic energy or an ELBO.
Counted interpreter operations are a reproducible resource proxy; they are not measured dollars, carbon or latency.

The [source README](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/v1.18.0/alpha_factory_v1/demos/meta_agentic_agi_v3/README.md) explains the complete algorithm and
keeps the original architecture diagram visible. The [original research archive](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/v1.18.0/alpha_factory_v1/demos/meta_agentic_agi_v3/RESEARCH_ARCHIVE.md),
[notebook](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/v1.18.0/alpha_factory_v1/demos/meta_agentic_agi_v3/colab_meta_agentic_agi_v3_original.ipynb),
[configuration](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/v1.18.0/alpha_factory_v1/demos/meta_agentic_agi_v3/configs/research_original.yml) and
[visual replay](../meta_agentic_agi_v3/research.html) are preserved. Historical claims do not expand the validated scope.
The updated notebook runs the finite lab. The original provider experiment and RoyaltyRadar reconciliation remain
available with corrected safety/accounting behavior and explicit limits.

## Troubleshooting

- **No export:** apply pending JSON and run again. Downloads never silently use old settings.
- **Import rejected:** restore the original source scenario and correct its validation error. Inputs are limited to
  1 MB, bounded UTF-8 JSON, known fields and finite values. Do not patch a run report to force acceptance.
- **Offline reload fails:** first load the public lab online, wait for its service worker, then reload. The packaged
  loopback server works without caching or network access. Other pages or models may need separate downloads.
- **Legacy code evaluation fails:** generated Python requires a usable Docker daemon and sandbox image. There is no
  host-execution fallback. Use the finite lab for a dependency-free local experience.
- **Royalty settlement requested:** the example prepares evidence only. Assumed revenue discrepancies are not debt
  findings; it never sends claims or native-currency transfers masquerading as AGIALPHA payments.

Evaluation probes use −8, −6, 6 and 8, disjoint from training probes −5, −2, 0 and 5.
Reference functions are independently sampled from the same finite grammar and may recur across the two sets;
this tests a frozen solver configuration on fresh input probes, not transfer to an unseen language or domain.
