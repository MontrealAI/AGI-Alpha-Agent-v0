# AGI ALPHA FLYWHEEL — research edition 01

**When Capability Creates Opportunity**  
**Vincent Boucher — President of MONTREAL.AI**  
27 October 2026 · Study ID `agi-alpha-flywheel-novelty-frontier-v1`

## Read the result

- [Full paper](paper/PAPER.md) — browser-readable source edition.
- [Designed browser edition](paper/Browser_Edition.html) — download and open locally; all figures are embedded.
- [Publication PDF](paper/AGI_ALPHA_FLYWHEEL.pdf).
- [Executive brief](paper/EXECUTIVE_BRIEF.md).
- [Connected example](CONNECTED_EXAMPLE.md).
- [LinkedIn draft](paper/LINKEDIN_DRAFT.md) — prepared for approval; not posted.

**No candidate earned the requested flagship discovery claim.** Seven serious candidates and additional inexpensive
probes were examined. The most developed opportunity—passive event-history recording with a damaged readout—was
generated during the research, not supplied as the answer. Exact constructions worked within their finite models.
Ordinary error correction and conventional monotone closure matched them, and closely related physical and event-recording
prior art was identified. This edition preserves the exploratory result without promoting familiar engineering as a
breakthrough. No physical product or customer acceptance was demonstrated.

The useful executed result is an inspectable research specimen: complete finite-model case records, independent
implementation checks, preserved counterexamples, a source-grounded novelty rejection, conditional economics for the
same proposed four-event offering, and actual use of existing Nova-Seed/FusionPlan/ledger/admission components.

## Results at a glance

| Evidence | Result | What it establishes |
|---|---|---|
| Four-event chronology with one known erased bit | 168/168 parity cases recover, versus 72/144 bare pairwise cases | Exact abstract coding result; familiar XOR repair, no physical qualification |
| New-size checks, five and six events | 1,320/1,320 and 11,520/11,520 recover | Implementation transfer of a known construction; ordinary identical-information library ties |
| Independent case audit | 198,840 saved cases; zero mismatches; 24,000 duplication checks | Agreement of separate implementations, not external scientific validation |
| Hysteretic two-event-order motif | All internal switching orders agree; conventional closure ties | Exact settled-state model; `C`, `ABA`, and `BAB` collide |
| Economics | Central expected project result −$131,303; favorable +$171,609 | Conditional constructed scenarios; physical success, buyer value and cost adequacy remain assumptions |
| Native integration | 13 checks passed; production admission denied | Real existing interfaces preserve scope, rights and authority restrictions |
| Native supplied-scenario analysis | All 128 subsets examined; empty selection | Execution on reviewer-supplied verdicts, not autonomous novelty assessment |
| Optional retention | $3,700 additional assumed cost, zero observed advantage over library | Reject the incremental retention investment under this evidence |

The 70% modeled avoided-loss fraction needs a demonstrated customer action after readout; chronology cannot undo past
damage. Broad cost allowances have unscoped categories and possible overlaps. The independent review in
`results/economics-model-review-v1.json` separates arithmetic correctness from complete commercial cost evidence.

Actual buyers, deliveries, recognized revenue and collections are zero. The complete attributable cost of this
interactive research session is unknown and recorded as `null`, never zero. Simulated receipts do not change those facts.

## Evidence map

| Directory / file | Contents |
|---|---|
| `discovery/INITIAL_BRIEF.txt` | Exact user brief; retrospective preservation, not a preregistration |
| `discovery/order-memory/discovery_record.json` | Seven candidates, beneficiaries, limitations, sources, contributions, commercial hypotheses and rejections |
| `discovery/additional_rejected_probes.md` | Further inexpensive rejection probes |
| `STUDY_PROTOCOL.json` | Actual scope, freeze order, evidence classes and missing comparisons |
| `NEXT_DISCOVERY_PROTOCOL.md` | Proposed future equal-budget discovery comparison; explicitly unexecuted |
| `discovery/order-memory/` | Four-event exploration, frozen new-size study, every saved case, independent audits |
| `experiments/confluence/` | Exact dynamics, frozen inputs, all-schedule exploration, conventional control and eight acceptance tests |
| `config/`, `src/economics.py`, `results/economics-*` | Frozen scenario inputs, development pricing, fresh confirmation, all worlds and audits |
| `integration/` | Unchanged pinned upstream sources, working local adapter, actual results and native refusals |
| `provenance/` | Foundational audit, model registry, source identities and prior Operational Alpha scope |
| `figures/` | Vector and raster figures, captions, source identities and alt text |
| `paper/` | Manuscript, brief, designed HTML, PDF, editable TeX and publication build inputs |

`results/economics-worlds-failed-write.json` is an intentionally preserved **truncated, invalid JSON file** from a
disk-full interruption. Do not treat it as the analysis input. The unchanged rerun produced `economics-worlds.json`;
the failure record and independent audit verify the surviving prefix. No unfavorable world was removed.

## Reproduce without live accounts

Run the commands below from this study directory. Python 3.11–3.13 is supported by the parent repository; this study
ran on Python 3.12.14. The finite experiments and economics use the standard library. The native adapter additionally
uses the package versions recorded in `integration/requirements-resolved.txt`. Its observed Node was 24.22.1; the parent
repository's production pin remains 22.17.1, and this execution is not production release qualification.

Create a new output directory; never overwrite the published evidence. The examples use a fresh `reproduction/`
directory. If it already exists, choose another name.

```bash
mkdir reproduction
python3 discovery/order-memory/order_transfer_study.py \
  --config discovery/order-memory/transfer_frozen_config.json \
  --output-dir reproduction/order-transfer
python3 discovery/order-memory/order_transfer_review.py \
  --output reproduction/order-review.json
python3 src/audit_economics.py --output reproduction/economics-audit.json
```

The reviewer checks the included published case stream by default. See its `REPRODUCING_REVIEW.md` for reviewer arguments and file expectations. The original reviewer and its output remain preserved separately. The new portable reviewer has a
new source hash. The economic audit was reconstructed after the initial inline command was not retained; its separate
replay report states that provenance and compares the outcomes, rather than claiming byte-identical script recovery.

The confluence runner writes in its own directory. Copy the small experiment before rerunning so the original results
remain intact:

```bash
cp -R experiments/confluence reproduction/confluence
python3 reproduction/confluence/study.py
python3 -m unittest discover -s reproduction/confluence -p 'test_study.py' -v
```

Confirm the **existing frozen economic policies** on the original independent seed. Copy the policy receipt into a
fresh output directory first; do not rerun development and relabel its later timestamp as the historical freeze.

```bash
mkdir reproduction/economics
cp results/economics-policy-freeze.json reproduction/economics/
python3 src/economics.py --phase confirm --output-dir reproduction/economics
```

For a genuinely new exploratory price search, use a separate new output directory and `--phase develop`; it creates a
new freeze time. The historical candidate table is already included. Policy selection used 128 development worlds per
candidate; confirmation used 512 fresh-seed worlds per scenario. The scenario spreads are not empirical confidence
intervals about customers.

Execute the actual native components locally, with no model API, chain, wallet funding or ENS connection:

```bash
python3 integration/run_adapter.py \
  --input config/integration-opportunity.json --output reproduction/native
cp -R integration reproduction/integration
mkdir -p reproduction/discovery/order-memory
cp discovery/order-memory/discovery_record.json reproduction/discovery/order-memory/
node reproduction/integration/run_scenario.mjs
```

The scenario runner writes to its own `results/scenario-v1/`; the copy above preserves the published original.
The adapter refuses occupied output paths and
verifies the pinned upstream sources before importing them. Ciphertext salts, nonces and ephemeral local identities
vary, so compare semantic checks and source identities rather than ciphertext bytes. The public fixture passphrase
provides no confidentiality. A valid local signature is not current ENS authority.

Build the figures and publication only in a working copy if you want to preserve the original publication bytes:

```bash
python3 src/build_figures.py
python3 src/build_economics_figure.py
python3 src/build_publication.py
```

The publication build requires Python `matplotlib`, `numpy` and `Markdown`, plus Pandoc, XeLaTeX and the TeX packages
listed in `paper/style.tex`. `results/publication-build.json` records the observed renderer versions and output hashes.
PDF timestamps and renderer versions may change byte hashes without changing scientific results.

## Qualification and publication

This is a new, additive study at a unique path, based on repository commit
`47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`. No existing study result, validator role, shared catalogue, release tag or
Pages deployment was modified. The browser-readable Markdown and downloadable PDF can be reviewed on an immutable
source commit. A draft pull request is a review surface, not merged software or a canonical Pages release.

This package contains code and new artifacts, so the repository's paper-only overlay cannot qualify it. Full required
source-specific checks and existing release ownership remain applicable. `PUBLICATION_STATUS.md` records actual
checks, pending gates and verified public links. Cryptographic integrity establishes content identity, not truth,
foresight, market demand, rights clearance or permission to operate.

## The next useful decision

First identify one valuable, precisely specified history property that the cited event-recorder, mechanical-computation
and finite-state-machine controls cannot already satisfy at equal physical constraints. If that comparison does not
leave a substantive gap, stop this candidate. If it does, map the smallest motif into a calibrated continuous physical
model and test actual drive ramps and failure modes. A later buyer interview can calibrate value and willingness to
pay; it cannot substitute for physical acceptance or novelty. The proposed protocol preserves these separate gates.
