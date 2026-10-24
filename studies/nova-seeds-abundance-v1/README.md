# Nova-Seeds: The Value That Survives Abundance

**From Copyable Intelligence to Verified Productive Advantage**  
MONTREAL.AI · Writer #10 · Research edition `nova-seeds-abundance-v1`

[Read the 20-page paper](Nova_Seeds_Abundance_v1.pdf) ·
[Standalone LaTeX](Nova_Seeds_Abundance_v1.tex) ·
[Get the complete source archive](DOWNLOADS.md)

The study constructs a calibration-sharing capability for a **simulated**
instrument, discloses it, and tests complete replication, conventional scheduling,
drift, failures and substitutes. The [abundance map](research/figures/abundance-map.svg)
is conceptual artwork; the paper's result diagrams show recorded measurements.

## What the evidence says

The confirmation contains 3,072 worlds and 21,504 method records. Ordinary useful
output rises from 23.8125 to 32.6875 synthetic units against redundant immediate
recalibration. The complete clone, disclosed planner and stationary exact expert
match the verified artifact's plans and outcomes in every world. Greedy scheduling
obtains the same ordinary output with lower measured compute cost.

The negative findings remain central. Under hidden measurement drift, conservative
recalibration yields 23.8125 units, adaptive planning 22.7552 and the verified
artifact 11.125. Capacity expansion, short calibration validity and zero-duration
calibration dissolve the ordinary baseline gap. Neither the NFT layer nor the
signed-registry counterfactual changes the allocator, and no instrument-output
benefit from the NFT layer was observed. This does not establish institutional
equivalence for escrow, custody or public consensus. Physical truth, commercial
demand, exclusive profit and a permanent moat are not established.

Browse the [result table](research/results/holdout-01/analysis/means.csv),
[claim–evidence–cost ledger](research/evidence/claim-evidence-cost-ledger.json),
[independent confirmation audit](research/evidence/holdout-independent-audit.json),
and [contract review](contracts-audit/CONTRACT_AUDIT.md).

## Reproduce in three steps

Start in this publication directory with Python 3.8+ and Node 24 available.
Use a new extraction directory; Linux or WSL matches the recorded path conventions.
The small Node demonstration needs no npm installation, wallet or external endpoint.

**1. Assemble the unchanged canonical ZIP from its two transport parts.**

```sh
python ASSEMBLE_ARCHIVE.py
```

The helper checks both part hashes and the complete archive hash. It preserves an
identical existing ZIP and refuses to overwrite a conflicting file. See
[download instructions](DOWNLOADS.md) and [part identities](PART_IDENTITIES.json).

**2. Extract the complete package and verify its original manifest.**

```sh
python -m zipfile -e Nova_Seeds_Abundance_v1_Source.zip reproduction
cd reproduction/nova-seeds-abundance-v1
python verify_manifest.py
```

**3. Run and independently audit the six-world demonstration.**

```sh
node research/src/run_experiment.mjs --mode pilot --out research/results/my-pilot
node research/audit/verify_results.mjs research/results/my-pilot
```

The archive's original `README.md` contains the full confirmation, figure/paper
rebuild and optional integration instructions. The recorded confirmation took
12 minutes 35 seconds; the runner has a 30-minute study budget. New timings, keys
and signatures differ, while deterministic workload outcomes should agree.

## Immutable research, separate publication packaging

The complete experimental implementation, frozen protocol, all raw records,
reproduction instructions and licenses remain inside the original ZIP. This
publication tree exposes the paper, figure sources, selected read-only evidence
and transport materials. It does not replace or rewrite the frozen research.
The [immutable original source snapshot](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/afcdeedd7d7e744cd09d0d4280a4f0f9537c2ee8/studies/nova-seeds-abundance-v1)
also preserves direct browsing of the unpacked implementation and its original
review state.

| Canonical artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Source ZIP | 15,317,764 | `b8785b08bf0a7d66e50dd28a5729e25705579a8774feb55aa02427710d2dba51` |
| Original compiled PDF | 480,978 | `405a7f2fdd6d5e3929f9eeb263499a36613d9cc26ecedcc059d113f6c1b3eaf9` |
| Standalone LaTeX | 496,252 | `2f4a416b7f6f800123a780199edf0ec3352caa7c89a70c5f68150cfcf42a66bc` |

The frozen experimental source inventory is
`0011228ddfd4a2e822659a0286864211b6c8eb99b93a3e39b9ba2cd3a582d08a`.
The [archive inventory](ARCHIVE_MANIFEST.json) describes the complete extracted
package, not this smaller publication tree; its original filename inside the ZIP
remains `MANIFEST.json`. The full ZIP remains available in the saved deliverable.
The existing coordinator can publish its public release attachment after
acknowledgement and required review.

## Review and publication status

The original unpacked submission in [PR #4883](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4883)
failed hosted Ruff with 109 findings in nine Python files. That failure remains
part of the review history. The archived frozen implementation is **not represented
as lint-clean**. Its bytes have not been reformatted; no Ruff exclusions or workflow
changes are introduced by this packaging correction.

Normal required review and full source qualification still apply to the publication
change. Local scientific checks and archive integrity do not establish runtime
integration acceptance, a qualified merge or a successful Pages deployment.
The [existing coordinator in issue #4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850)
retains shared catalogue, release and Pages ownership. Historical publication URLs
and unrelated integration holds remain intact.
