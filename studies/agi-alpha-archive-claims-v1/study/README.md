# AGI ALPHA FLYWHEEL — research edition

**AGI ALPHA FLYWHEEL — When Capability Creates Opportunity**  
**Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work**  
**Vincent Boucher — President of MONTREAL.AI**

27 October 2026. Based on MontrealAI/AGI-Alpha-Agent-v0 main `47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`.

## Read

- [Complete browser-readable manuscript](manuscript.md)
- [Publication PDF](paper/agi-alpha-flywheel.pdf)
- [Executive brief](executive_brief.md) and [brief PDF](paper/executive-brief.pdf)
- [Standalone HTML reader](paper/index.html) — download and open locally; GitHub displays its source.
- [Connected example](connected_example.md)
- [Full mathematical methods and proof](technical_methods.md)
- [Discovery record](discovery/selection_record.json), [ordinary arm](discovery/ordinary_search_raw.md) and [expert arm](discovery/expert_search_raw.md)
- [Final economics](economics/RESULTS.md), [model definitions](economics/README.md) and [independent audit](economics_audit.md)
- [Actual-work A/B/C classification and unknown-cost ledger](provenance/cost_classification.json)
- [Native research bridge](integration/README.md) and [executed artifacts](integration/actual-run/)
- [Next validation proposal](config/next_validation_plan.json)
- [LinkedIn draft](linkedin_draft.md) — prepared for review, not posted.

## Result and scope

An exact rational instrument passed 50/50 comparisons covering 877,728 latent histories. It resolved 12 of 36 fresh authored queries; a calibration-independence control resolved six. Strong exact conventional methods tie. All 12 successor queries are unresolved, and an ordinary library with the same source gives byte-identical results.

No candidate passes the required substantive novelty gate. The archival idea was generated during discovery, but identified prior art already covers its core. The final commercial model rejects the baseline launch: a frozen USD 800 fee gives a modeled 90-day operating loss of USD 809.68 and a 69% loss frequency. A favorable scenario gives +USD 6,282.96 before sunk development; the declared robust profitable region is empty. Actual customer revenue and collections are zero; actual complete research expense is unknown.

All inputs are authored simulations. No historical source is certified by the finite engine, no human trial or actual buyer observation is represented, and no live ENS/on-chain action or production-scope expansion is performed.

## Reproduce

Preserve the literal `study/` folder inside the downloaded package. Core and economics use Python's standard library; the observed runtime is Python 3.12.14. From the package root:

```sh
python study/reproduce.py --out /tmp/new-alpha-reproduction
```

The destination must not exist. The wrapper copies eight frozen inputs, executes from a separate working directory, preserves command logs and compares deterministic outputs. It fails on mismatches. Core timings vary by platform and are excluded; JSON key/whitespace order and CSV column order are the only permitted serialization normalizations. Cell strings and row order remain exact. The observed clean run matched 189 core files, 25 economic files and the regenerated frozen policy; see [receipt](provenance/reproduction_receipt.json).

The underlying commands are:

```sh
python study/run_study.py --out /tmp/new-claim-results
python study/economics/runner.py check
```

The economic `explore`, `confirm`, `robustness` and `supplementary` steps refuse to overwrite the included evidence. Use the wrapper for a fresh complete run. Its final seeds and all policy/source hashes appear in [policy_frozen.json](economics/policy_frozen.json). Historical corrections are retained under `economics/versions/` and `economics/results_superseded_scheduling_v1/`.

The native bridge has external dependencies and an explicitly bounded source closure. Its reproduction instructions and preserved failed isolated-import attempt are in [integration/README.md](integration/README.md). This is not a full installed-runtime qualification.

## Build the publication

`finalize_manuscript.py` binds the manuscript template to final reported economic values. `build_report.py` renders figures, the self-contained HTML reader, the paper PDF and executive brief using matplotlib, Markdown and ReportLab. Observed dependency versions are recorded under `paper/`. These presentation dependencies are separate from the standard-library study.

For an environment with a restricted default cache path, run the renderer with an explicit writable cache: `MPLCONFIGDIR=/tmp/alpha-flywheel-mpl python study/build_report.py`.

## Integrity, rights and publication

New implementation and authored research data are provided under Apache-2.0; the exact retained upstream closure keeps its original license and notices. External papers and restricted images are not redistributed. Source links are attributed, and public metadata access corrections are preserved.

The project uses a dedicated directory and leaves active owners, canonical publication state and runtime permissions unchanged. Mixed source/data/HTML require the existing full qualification lane before canonical integration. This is an immutable research review edition in a draft PR, not a release or external peer review. See [publication handoff](PUBLICATION_HANDOFF.md). No broader repository gate is reported as passed.

Operating economics are pre-tax scenarios; cash restrictions cover the listed modeled obligations. Unknown actual research expense, actual tax obligations and unavailable billing prevent an actual free-funds or net-profit claim.
