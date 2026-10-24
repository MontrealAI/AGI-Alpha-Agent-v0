# BLOOM ∞ — Every successor must earn its proof

[Read the complete paper](paper/bloom-independent-capacity-v1.pdf) · [Open the recorded demonstration](results/public-demo/index.html) · [Inspect the evidence](reporting/evidence-index/evidence.html)

![BLOOM ∞ — verified capacity, conditional value](paper/cover.png)

**A working dependency-impact tool, a real artifact-consuming successor, and a
candid test of whether construction earns its complete cost.**

A maintainer changes a package and needs to know which application roots could
be affected. This edition builds a graph-bound impact operator, checks its
certificate independently, and passes its actual answers to a distinct
minimum-coverage planner. The local demonstration uses public Alpha and Manager
package-lock snapshots. It produces an inspectable plan and stops; it does not
execute tests, deploy software, or transact.

The study established exact resolution within its declared complete-graph
scope. It did **not** establish the prespecified competitive advantage or the
prespecified 20% receiver benefit. The delivered demo therefore defaults to the
strong conventional `expert` policy. BLOOM remains available for transparent
comparison. [Results and evidence](reporting/evidence-index/evidence.html) preserve
both findings. [Protocol](protocol/PROTOCOL.md) and [freeze](protocol/FREEZE.json)
were fixed before the confirmatory cases were generated.

## Try the actual public case

Work from the directory containing `demo.py`. With the pinned integration
packages already installed, run one command:

```sh
python3 demo.py --case public_case/case.json --method expert --output runs/public-demo-local
```

Choose a new output directory on each run; existing evidence is preserved. Open
`runs/public-demo-local/index.html` in a browser. The report embeds its data and
works offline. For a no-execution walkthrough, open the shipped
[recorded public demonstration](results/public-demo/index.html).

Clean setup on Linux with Python 3.12:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r integration/requirements.txt
python demo.py --case public_case/case.json --method expert --output runs/public-demo-local
```

The native integration pins `pydantic==2.14.0` and `cryptography==50.0.2`.
Scientific execution and analysis otherwise use the Python standard library.
No model provider, API key, wallet, RPC, container, or external service is
required. Installing packages is a setup step; the demo itself is local.
Node is needed only for the optional independent lockfile-resolution check.
See [REPRODUCING.md](REPRODUCING.md) for exact recorded versions and commands.

## A short walkthrough

1. **Before:** the inputs contain 1,136 locked locations, 2,000 dependency-to-
   dependent edges, two package build roots, and 17 fixed change queries. These
   facts come from pinned public manifests, with 16 unresolved optional peers
   disclosed in the [case documentation](public_case/README.md).
2. **Choose a change:** the first query changes Alpha's `vite`. The qualified
   operator finds the Alpha web root affected. A later query changes both `vite`
   and Manager's `solc`, affecting both roots.
3. **Inspect the operator:** the conventional policy selects reverse traversal
   from application roots using its declared graph-operation estimate. The
   checker verifies root ownership, descending path witnesses, unset cells and
   graph-edge closure. This is an established graph construction with explicit
   qualification; it is not claimed as a new graph algorithm.
4. **Inspect the actual successor:** `successor.json` binds the hashes of
   `operator.json` and `impact.json`. It consumes the affected-root answers and
   chooses an independently checked minimum-weight cover. The first query
   selects `synthetic-alpha`, weight 7; the combined query selects
   `synthetic-both`, weight 10. These are illustrative coverage labels and
   weights, not real tests, durations, fees, or monetary savings.
5. **See a normal stop:** the final empty change query affects no root and needs
   no coverage plan. The journey exports its evidence and terminates. The native
   backup restores stopped and paused, with no active proof or grant.

The recorded public journey completed all seven stages through the **actual
published Alpha dispatcher**, with 48 valid signed journal events. Its measured
native total was **1.127727538 CPU seconds** and **1.127719499 wall seconds**,
including source checks, journal setup, dispatch, callbacks, acceptance, backup
and restoration. Final receipt serialization and caller work are outside that
measurement. Timing will vary on your machine; no speed advantage is inferred
from this single practical case. See
[its recorded summary](results/public-demo/summary.json).

## What the completed study found

The inferential unit is a graph world. Confirmation used 48 worlds and 2,544
records; fresh shifted reproduction used 24 worlds and 1,272 records. A separate
2,544-record replay used the original confirmation worlds to test deterministic
reproducibility. Replayed cases are not new samples.

| Gate | Measured verdict |
|---|---|
| Reproducibility | **Pass after independent replay:** 48 case files, 480 operator files and all 2,544 deterministic records matched. Timings and native journal identities are excluded from exact replay equality. |
| In-scope quality | **Pass:** 2,016/2,016 eligible confirmatory trials and 1,008/1,008 fresh reproduction trials resolved exactly; all 432 fresh boundary trials refused correctly. |
| Competitive advantage | **Not established:** confirmation BLOOM/expert CPU ratio 0.971 [0.938, 1.005]; BLOOM/reverse 0.958 [0.916, 0.998]. Required upper bound was below 0.90 against both. |
| Practical receiver benefit | **Not established:** retained/rebuilt receiver CPU ratio 0.778 [0.751, 0.806], with required upper bound below 0.80. The fresh reproduction ratio was 0.805 [0.764, 0.855]. |
| Full-cost economics | **Incomplete:** no cash revenue, firm offers, independently supported demand, or measured customer acceptance; material authoring and ownership costs remain unknown. |

Intervals are the predeclared 98.333333% two-sided percentile-bootstrap intervals
for a three-contrast family. Their nominal coverage is approximate. Full paired
results, denominators and analysis are in the
[evidence index](reporting/evidence-index/evidence.html). The original analysis
files retain `G1: PENDING_INDEPENDENT_REPLAY`; the later independent receipt
closes that gate without rewriting history.

Negative results matter to use. Both BLOOM and the expert selected SCC in all
48 original stable worlds, so adaptive switching in that stratum was not
established. Every one of the 72 fresh unsafe receiver-proof ablations accepted
an incorrect output. Deliberately incomplete graphs produced 1,657/2,176 false-
safe query instances in confirmation and 897/1,088 in reproduction. A valid
certificate for supplied edges cannot prove that the supplied graph is complete.
Those query instances are not independent statistical worlds.

## Working boundaries

- **Implemented:** bounded graph operators and certificates; independent
  reachability and cover checks; actual Alpha job dispatch/history/backup;
  customer-owned local JSON/ZIP export and stopped restoration.
- **Measured:** declared graph correctness, cost phases and resource counters,
  paired interventions, cold logical runs, robustness cases and deterministic
  reproduction.
- **Modeled:** synthetic coverage weights and explicit monetary sensitivity
  assumptions. They are not observed test effort, revenue, prices or demand.
- **Unestablished:** real regression safety, full monetary advantage, commercial
  succession, autonomous wealth creation, four-repository installed admission,
  or unlimited growth.

Manager and Jobs retain their distinct finite native admission semantics;
this new task was not submitted to them. Fleet external execution is not
connected. Five Ascension contracts were source-audited; local EVM execution is
**NOT_RUN** because the required dependencies were absent. The
[integration map](INTEGRATION.md) names exact interfaces and lifecycle states.

The fixture's signing material is public and deterministic. It demonstrates
local journal integrity, not a production identity or independent organization.
It grants no external authority. A restored record requires current world,
policy, environment, artifact and authority checks before useful execution.

## Find the evidence

All paths below are relative to the study directory containing `demo.py`.

| Path | Contents |
|---|---|
| `protocol/` | Original protocol and 23-source timestamped freeze |
| `core.py`, `generate.py`, `run_study.py`, `analyze.py` | Frozen scientific implementation and analysis |
| `independent/` | Separate conventional policy/checker and prefreeze review |
| `development/` | Preserved development versions, attempts and receipts |
| `results/confirmation/` | 48-world original campaign, cases, raw records, operators and analysis |
| `results/reproduction/` | 24 fresh shifted worlds and their receipts |
| `results/confirmation_replay/` | Original-world reproduction, charged separately |
| `results/independent_reproduction_review/` | Comparison and later G1 closure |
| `results/public-demo/` | Recorded useful local run and complete native receipts |
| `public_case/` | Exact public lock snapshots, parser, independent acceptance and compressed edge audit |
| `integration/` | Unchanged Alpha source subset, adapter, licenses, provenance and EVM NOT_RUN receipt |
| `reporting/evidence-index/` | Claim-to-artifact browser, tables and derived publication summary |
| `paper/` | Publication PDF, LaTeX, bibliography and source figures, as identified by the complete bundle manifest |

[Economic reconciliation](reporting/economics/ECONOMICS.md), the
[ledger](reporting/economics/ECONOMICS_LEDGER.csv), and its
[summary](reporting/economics/ECONOMICS_SUMMARY.json) explain cost coverage and
missing information. [REPRODUCING.md](REPRODUCING.md) covers reruns,
integrity checking and failure interpretation. New main study code declares
Apache-2.0; retain the original Alpha license and provenance in
`integration/vendor/`. Public manifests are data snapshots, not an installed
or license-audited distribution of their dependencies.

**The most useful next step is to validate dependency completeness and actual
test coverage on a permitted real build.** That would address the observed
false-safe failure mode and provide acceptance/value evidence that another
selector benchmark cannot supply.

## Verify and restore the complete edition

From the extracted study root, run `python3 verify_bundle.py .`. It checks every manifest member, all 23 frozen source identities and the authoritative PDF. You can also pass the complete ZIP path directly. Integrity alone does not establish semantic validity or current authority.

To rebuild the exact archive with the recorded ZIP metadata, use `python3 repack.py --root . --output ../bloom-repacked.zip`. Preserve the original manifest. Rebuilding the paper is separately documented in [paper/BUILD.md](paper/BUILD.md).

## Public export and local restoration

[PUBLIC_EXPORT.md](PUBLIC_EXPORT.md) lists the omitted local identity-key/token files and explicitly renamed sanitized backup archives. Scientific records, native run receipts and all frozen source remain unchanged. Historical receipts retain original backup hashes; use the export mapping for public inspection copies. To exercise real authenticated backup and stopped restoration, run the documented local demo to create a fresh local fixture. Public historical copies deliberately omit credential material.
