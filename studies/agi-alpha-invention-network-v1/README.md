# AGI Alpha Flywheel — The Network That Learns to Invent

**Vincent Boucher**  
**President of MONTREAL.AI**

An executable research edition about useful numerical work, an experience-trained component, peer use, specialist composition and their economic limits. The study changes and transfers an actual reduced PDE basis. It preserves the strong ordinary solvers, failed approximations, shifted-distribution losses and additional costs needed to judge that capability.

The main finding is bounded: the selected basis improves fresh approximation quality and saves a small amount of forward-solve time on related work, while a competent ordinary solver already meets every final accuracy requirement. Its speed advantage weakens against the upgraded ordinary baseline and reverses under distribution shift. Sensor design improves difficult finite inverse missions, but the equally equipped generalist obtains the same acceptance. Millisecond numerical savings do not establish profitable retention, authenticated live sharing or a self-improving enterprise.

## Read and inspect

| Deliverable | File |
| --- | --- |
| Full paper | [PDF](paper/The_Network_That_Learns_to_Invent.pdf), [LaTeX source](paper/paper.tex), [browser edition](demo/paper.html) |
| Executive brief | [Markdown](executive_brief.md), [PDF](paper/Executive_Brief.pdf) |
| English/French interactive demonstration | [Open demo](demo/index.html) |
| Detailed evidence, provenance and limitations | [Evidence companion](evidence_companion.md), [browser companion](demo/evidence.html) |
| Foundation and integration audit | [Audit](integration_audit.md) |
| Numerical protocol and method explanation | [Protocol](technical_protocol.json), [technical README](README_technical.md) |
| Frozen numerical source and artifact identities | [Freeze record](evidence/technical_freeze.json) |
| Source bibliography and read coverage | [Primary-source register](sources/primary_sources.json), [BibTeX](sources/sources.bib), [source memo](sources/source_memo.md) |

These links name local release assets. They are not evidence that a stable public publication has occurred. Publication must follow the repository's authorized process and preserve the current v1.46 source-release lease and previous editions.

### Complete archive and repository source

The complete research archive includes the original PDF, executive brief, all numerical checkpoints and solution arrays, every enterprise history, the complete LaTeX project, figures, browser editions and a minimal, hash-verified native source closure. It is distributed as a separate experimental research release; it does not qualify a live platform deployment. The intended immutable edition is `study-network-learns-to-invent-v1-2026-10-27`; consult its publication receipt for observed availability and exact asset hashes.

The experimental Git source tree deliberately contains text source and text evidence only. The repository's existing binary-integrity policy admits manuscript PDFs through the research catalog and complete archives through research-release assets. Numerical `.npy`/`.npz` files, compressed histories, figure binaries and PDF copies therefore remain in the complete archive. `publication/repository_inventory.json` identifies those archive-only files with exact SHA-256 values; it is not a replacement for their bytes. To inspect the archived checkpoints or reproduce the original handoff, extract the complete research archive. A source-only checkout can regenerate a new development campaign using the commands below, but must not claim its new timing records are the original measurements.

## What ran, and what did not

The numerical experiment ran locally. Twelve founder thermal responses create a rank-12 basis. Thirty-two bounded Gym enrichments produce four candidate checkpoints; the frozen rank-44 candidate is evaluated on 64 fresh thermal cases, 64 fresh transfer cases, 64 shifted cases and 32 finite inverse missions per composition arm. Recorded values include actual solver outputs, independently recomputed residuals, elapsed runtime and available process CPU measurements.

The enterprise is a conditional simulation. Human-service prices, work hours, demand, model usage, quality, collections and optional learning decisions are explicitly attributed. There were no customer sales, observed API-model trial or live ENS authentication. The paper's authoring was AI-assisted; the algorithms and task design were constructed by the research team. Numerical basis updates happened through executed experience, without an autonomous invention claim.

The existing research lifecycle carries actual artifact bytes under synthetic authority and exercises private/shared rights and revocation. Its positive transfer control uses artificial monetary outcomes. The measured scientific candidate is assessed separately. Main's protected capsule only supports `bounded-public-source-selection/v1`, so scientific production admission remains **`NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE`**. Existing native Journal/TrustRegistry/CostLedger code is imported, not rewritten.

## Repository and environment

The required native foundation is the exact repository commit:

```text
80b345828f34fd8a6e592977dd17ef37141305f4
```

The study lives at `studies/agi-alpha-invention-network-v1/`. If using a detached study archive, place that complete directory at this path in a checkout of the frozen foundation. The study does not include or emulate a replacement native registry. Its bridge refuses changed native import hashes. The separate research lifecycle is included byte-for-byte under `upstream/beyond_beta/`, pinned by [SOURCE_MANIFEST.json](upstream/SOURCE_MANIFEST.json) to commit `2727262caa52766a78916f2ed81f5afaf668edce`.

Executed environment: Python **3.12.14**, NumPy **2.3.2**, SciPy **1.17.0**, threadpoolctl **3.6.0**, and Node **v24.22.1**. [requirements-research.txt](requirements-research.txt) lists exact installed versions of the Python dependency closure for the research, figures and directed checks. It is not a wheel-hash lock or a claim that another platform reproduces bitwise timing. Node is a separate prerequisite. The repository's production Node qualification target is not replaced by this research runtime.

From the repository root:

```bash
STUDY=studies/agi-alpha-invention-network-v1
python -m venv .venv-research
. .venv-research/bin/activate
python -m pip install -r "$STUDY/requirements-research.txt"
node --version
PYTHONPATH="$STUDY" python -m pytest --noconftest -q "$STUDY/test_technical.py" "$STUDY/test_lifecycle_bridge.py" "$STUDY/test_research_lifecycle.py" "$STUDY/test_economics.py"
```

No model API key, wallet, customer credential or proprietary model weight is needed. Temporary accounting keys are generated only for local tests. All scientific inputs are synthetic and researcher-generated. The numerical commands themselves limit thread pools to one; avoid other heavy work when comparing very short runtimes.

Verify the published numerical source and artifact freeze before reproducing it:

```bash
python - <<'PY'
import hashlib, json
from pathlib import Path
study = Path("studies/agi-alpha-invention-network-v1")
freeze = json.loads((study / "evidence/technical_freeze.json").read_text())
for name, expected in freeze["files"].items():
    actual = hashlib.sha256((study / name).read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"Frozen numerical source or evidence changed: {name}")
print("All published numerical freeze identities match.")
PY
```

## Reproduce without overwriting evidence

Use a new, initially nonexistent directory. The published seed is for reproduction, not fresh independent confirmation after publication. The original freeze time is `2026-10-27T12:04:34.688405+00:00`; the exact seed, source and artifact hashes are in `evidence/technical_freeze.json`.

```bash
STUDY=studies/agi-alpha-invention-network-v1
NEW_OUT="$STUDY/reproduction_run_01"
python "$STUDY/technical.py" confirm --development "$STUDY/technical_dev_final" --out "$NEW_OUT/technical_confirm" --seed 3782992104 --count 64
python "$STUDY/economics.py" --development "$STUDY/technical_dev_final/results.json" --output "$NEW_OUT/economy" --freeze
python "$STUDY/economics.py" --development "$STUDY/technical_dev_final/results.json" --confirmation "$NEW_OUT/technical_confirm/results.json" --output "$NEW_OUT/economy" --worlds 200
PYTHONPATH="$STUDY" python "$STUDY/run_research_lifecycle.py" --development "$STUDY/technical_dev_final" --confirmation "$NEW_OUT/technical_confirm" --enterprise "$NEW_OUT/economy" --output "$NEW_OUT/lifecycle"
```

This reuses the archived trained component and reruns the public cases, matched enterprises and lifecycle. Timing-sensitive quantities may change with host contention and numerical-library versions. Policy and case distributions remain fixed. Source freezing prevents a changed economics script from silently consuming an old policy lock.

To reproduce learning itself, start a separate development campaign:

```bash
python "$STUDY/technical.py" develop --out "$NEW_OUT/technical_dev"
```

This regenerates the founder responses, all 32 Gym actions and all four candidates. Its artifacts, selection and timings belong to that new development record. To make an additional scientific confirmation, freeze that new record and the sources before choosing previously unused seeds. Do not relabel this edition's now-public cases as protected fresh evidence. The existing protocol must be followed; any changed hypothesis or workload requires a separately declared edition.

## Result layout

| Directory or record | Meaning |
| --- | --- |
| `technical_dev/` | Original development campaign; retained six-sensor ceiling and all candidates |
| `technical_dev_iteration2/` | Revised numerical environment, stronger ordinary router and harder sensor condition; preserved development history |
| `technical_dev_final/` | Final metering revision, founder fields, training observations, all candidates and frozen selection |
| `technical_confirm/` | Primary protected numerical confirmation; complete inputs, rows and saved solutions |
| `evidence/descriptive_statistics.json` | Post-confirmation descriptive summaries and paired bootstrap intervals |
| `economy/` | Frozen economic policy, conditional enterprise results, all worlds, every full transaction history in `all_histories.jsonl.gz`, and selected examples |
| `lifecycle/` | Empirical runtime-proxy assay, synthetic positive transport control, local B execution, rights controls and native accounting replays |
| `upstream/SOURCE_MANIFEST.json` | Exact unchanged research lifecycle source closure and license |
| `evidence/native_import_closure.json` | Frozen native Journal/trust/cost source closure |

The lifecycle's twelve-cluster rule was communicated before numerical confirmation. Its wrapper source and written protocol were finalized afterward by an implementer who had not yet inspected confirmation results. The technical source/checkpoint freeze is a separate, earlier recorded event. See the evidence companion for that chronology; no preconfirmation source-freeze claim is made for the late wrapper or descriptive figure code.

## Rebuild presentation assets

The figure and demonstration builders use the archived release paths, including `technical_confirm/`, `technical_dev_final/` and `economy/`. Run them in a separate copy if you want to preserve the delivered presentation files unchanged.

```bash
python "$STUDY/analyze_results.py"
PYTHONPATH="$STUDY" python "$STUDY/build_demo.py"
```

The demonstration embeds results for offline reading and labels visualization replays. It does not initiate paid work or authenticate a user. Building `paper/paper.tex` requires a LaTeX distribution with its declared packages and BibTeX; the observed system provides pdfTeX 1.40.25, TeX Live 2023/Debian. Compile from `paper/` so figure and bibliography paths resolve:

```bash
cd "$STUDY/paper"
pdflatex -interaction=nonstopmode -halt-on-error -jobname=The_Network_That_Learns_to_Invent paper.tex
bibtex The_Network_That_Learns_to_Invent
pdflatex -interaction=nonstopmode -halt-on-error -jobname=The_Network_That_Learns_to_Invent paper.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=The_Network_That_Learns_to_Invent paper.tex
```

These are local reproduction commands, not publication commands. Compilation is not evidence that the PDF was visually checked, that browser behavior passed the release gate, or that CI passed; those checks require their own receipts.

## Reading the evidence correctly

A better raw approximation establishes a learned representation, not accepted-output superiority. Useful peer replay establishes transport and local compatibility, not live network admission. A positive synthetic admission establishes a software conformance path, not empirical Alpha. An executed accounting program does not establish paid expenses or earned revenue. The numerical solver is a conventional technical baseline, not a measured frontier model. Sourced hourly rates do not establish task hours, willingness to buy or demand. Retention, Gym, sharing and expansion remain optional economic choices.

The scientific workload preserves the original operator, boundary, forcing and accuracy requirements. Corrected outputs are computational results only. The learned basis is tied to the grid and operator family; it is neither a general model checkpoint nor evidence of specialist ASI. No qualified productive-frontier expansion, graph advantage or self-acceleration is claimed.
