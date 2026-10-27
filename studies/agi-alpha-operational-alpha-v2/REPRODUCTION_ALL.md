# Reproducing the complete additive edition 2.1.0

The top-level command replays the preserved supporting studies **and** the opportunity-first scientific-model reuse
qualification extension. It performs local computations from archived, source-bound evidence. It makes no model,
network, wallet or browser calls and does not publish anything.

```sh
PYTHONDONTWRITEBYTECODE=1 python reproduce_all.py --report validation/my_complete_replay.json
```

Run from `studies/agi-alpha-operational-alpha-v2/`. Report paths must be new. The programs refuse to overwrite a
report or place it in a frozen evidence directory; `validation/` is allowed. Without `--report`, JSON is printed
to standard output. A failing check returns a nonzero exit status and a nested failure description.

For a complete re-execution of all **13,824 selected economic histories**, in addition to their default accounting
and summary checks:

```sh
PYTHONDONTWRITEBYTECODE=1 python reproduce_all.py --full-economics --report validation/my_complete_full_replay.json
```

Do not use `python -O` or `PYTHONOPTIMIZE`: the frozen evaluators contain assertions. The new entrypoints explicitly
refuse optimized execution. No source, scorer, historical finding or previously selected policy is replaced.

## The two additive layers

`reproduce_all.py` calls the original `reproduce.py` unchanged and then calls `opportunity/reproduce.py`. The original
supporting script remains bound to SHA-256
`598fe56134ed1f745568a9b31bdd513bfc8cab94ccf01add5cfcdaf585490010`. Its guide and completed review remain intact:
[REPRODUCTION.md](REPRODUCTION.md) and [supporting review](validation/final_supporting_review.md).

The S3 extension can also be replayed separately:

```sh
PYTHONDONTWRITEBYTECODE=1 python opportunity/reproduce.py --report validation/my_s3_replay.json
```

| Layer | What executes | What the counts mean |
|---|---|---|
| Preserved supporting evidence | Development, twelve primary repair outputs, three C5 outputs, actual-byte native fixture, economic summaries and prescreen | Four primary task families and one C5 task; assertion categories do not increase those units |
| S3 development | Eighteen frozen instrument tests | Developer-authored local tests, not fresh independent scientific observations |
| Scientific acceptance controls | Conventional direct method plus thirteen adverse packet mutations | Four positive mission classes and thirteen rejected controls under the independent evaluator |
| S3 recipients | Saved U, E and E+ submissions; exact declared-packet reconstruction; both frozen request variants | One four-mission campaign over two public source families per arm |
| S3 transfer | Capsule contents, recovered bytes, recipient bytes, ordinary library and 31 native controls | Actual local cryptography with synthetic authority; no monetary production admission |
| Arrangement checker | Exact finite search, fresh stress, historical arithmetic, timing illustrations, reusable package example and independent auditor | Conditional arithmetic under supplied prices, costs, values, rights and scenario weights |

The S3 acceptance evaluator constructs its H4 oracle from source reaction identifiers, an SVD stationary nullspace
and Poisson uniformization. It does not import the retained instrument or conventional implementation. The
conventional method uses direct MathML construction, a normalized linear solve and matrix exponentials. Development
tests additionally compare against a separate motif-rule construction and ODE integration. These implementation
comparisons are internal computational validation, not independent external scientific replication.

The whole S3 campaign passes for all three arms and the conventional method. Acceptance differences E−U and E+−E
are zero. Three mission classes reuse H4, which was present during instrument development; Boehm supplies the other
family and tests refusal of an inapplicable inherited witness. Changed requests are not additional independent
families or businesses. The replay does not turn the already public source models into protected fresh evaluation.

The arrangement reconstruction preserves **60 configuration records**, **4,320 enumerated candidate plans**
(including repeated restricted-menu alternatives), **32 fresh synthetic stresses**, **17 negative-contribution
outcomes**, and **38 independently reconstructed fresh/historical ledgers**. The independent auditor also checks
60 comparisons against a conventional entrepreneur with the same complete alternative menu. The six timing cases
are explicitly post-confirmation arithmetic illustrations. None is market evidence or an earned revenue forecast.

## Frozen commitments, archived outputs and deterministic comparison

The new replayer verifies the opportunity selection, instrument, scientific protocol, exact participant messages,
exposure freeze, public source manifests, original development corrections, native adapter closure, arrangement
freeze and fresh-result bindings. The S3 confirmation summary is separately bound as a **post-result archive**;
its hash is not described as a prospective commitment.

All participants must be recorded closed before saved-output acceptance runs. Initial inventories, immutable
sources and public contract files, frozen submission inventories, logs, runner counters and aggregate hashes are
checked. The exact participant spawn text was frozen before exposure in this extension. Its original absolute
workspace strings are preserved as provenance; replay uses the archived relative files and requires no external
`research_runs/` directory.

Each saved S3 `packet.json` must reconstruct with exact JSON equality in the reviewed numerical environment.
Independent scientific acceptance uses its original floating-point tolerances. Different BLAS/LAPACK builds may
produce last-bit numerical differences even when scientific acceptance remains unchanged; the strict packet
comparison would expose that difference rather than silently rewriting the archive. A numerical compatibility
issue should be reported as such and evaluated separately.

The arrangement code uses integer cents and exact `Fraction` arithmetic. Its declared search, selection, frozen
stress sequence and all original JSON results reconstruct exactly. The independent auditor never imports its
simulator. Programs that write audit or control reports are executed in temporary copies, preserving original
results. Fresh native runs compare control outcomes and identical transported bytes; ephemeral signature keys,
local journal identifiers and elapsed times need not be identical.

The complete replayer keeps the original economic results unchanged. `--full-economics` repeats the **selected**
original and value-controller histories; it does not rerun their earlier policy search. The earlier guide includes
optional reconstruction commands for that separate development stage. S3 outcomes are not retroactively inserted
into the earlier economic input or posterior.

## Runtime dependencies

The observed runtime is Python **3.12.14**, Node.js **24.22.1**, NumPy **2.3.2**, SciPy **1.17.0**, PyYAML **6.0.2**,
Pydantic **2.11.7** and cryptography **50.0.2**. Python 3.11–3.13 is the repository-supported Python range. The original
guide records native transitive dependencies. These versions describe the reviewed environment, not a complete
binary/container lock or a claim that every numerical-library build is bit-identical.

When creating a separate environment, the reviewed direct Python dependencies can be installed explicitly:

```sh
python -m pip install numpy==2.3.2 scipy==1.17.0 PyYAML==6.0.2 pydantic==2.11.7 cryptography==50.0.2
```

Dependency installation may need network access; replay itself does not. Node uses built-in modules, so this path
needs no npm install. It requires no model/API entitlement, keys, live customer data or account session.

If fresh native execution is unavailable, the explicitly limited option is:

```sh
python reproduce_all.py --skip-native --report validation/my_limited_replay.json
```

Both replayers still verify native source pins, archived controls and actual capsule bytes. Their reports say fresh
native execution was skipped; this option cannot support a fresh 31-control conformance claim. Complete default
replay requires the native dependencies.

## Portable archive layout and additional source closure

Preserve the following relative layout:

- `studies/agi-alpha-operational-alpha-v2/`, including both replayers, the complete supporting evidence and
  `opportunity/` discovery, development, protocol, instrument, conventional comparator, integration, arrangements
  and archived results;
- `studies/agi-alpha-capability-opportunity-v1/integration/`, containing the same **34 files** required by the
  supporting edition: five adapters/manifests and all 29 source-manifest entries;
- `docs/Invent_the_Economy.tex`, the hash-bound historical source cited by the arrangement regression;
- the repository `LICENSE` as a distribution notice.

The exact supplemental copy list, byte counts and hashes are in
[validation/full_edition_review.sources.json](validation/full_edition_review.sources.json). The historical source
has SHA-256 `51605532c48edc5465b562e8699f473c42f437c4a288795a610fb61dc2a70a47`. It is historical arithmetic
provenance, not an S3 price or demand source. The 34-file native closure is unchanged from the supporting edition.
All H4 and Boehm model/data bytes and their retained BSD-3-Clause notices are already inside `opportunity/`.
The generic scientific capsule excludes these datasets and all evaluation/test material.

Preserve rejected discovery directions, bounded follow-ups, corrections, original failed checks, source manifests,
all frozen submissions and earlier economic outcomes. Exclude generated Python bytecode and tool caches from a
distribution. No Git repository, external solver workspace, network fetch or source substitution is needed to run
the packaged evidence. SHA-256 checks establish agreement with the archived bindings; they do not independently
re-fetch or notarize historical GitHub ancestry.

## Evidence boundaries and admission

The instrument and recipient adapters use established mathematics and researcher-authored operating expertise.
They do not change proprietary model weights or establish autonomous biological discovery. The source models,
observations, nominal fits and reference simulations belong to the attributed original sources. The research team
constructs the reuse requests and qualification experiment.

Actual model tokens, itemized provider charges, complete research labor, customer effort and residual human
attention remain unknown. Actual customer collections are zero. A numerical replay supplies none of those missing
quantities. It cannot establish positive complete-cost margin, net recipient benefit, commercial feasibility
crossing or sustained compounding.

The current S3 admission observation is recorded separately in
[validation/opportunity_review.admission.json](validation/opportunity_review.admission.json): the scientific workflow
is outside the unchanged native production scope; one campaign/two public source families do not meet its existing
six-independent-cluster requirement; complete monetary evidence is absent. A synthetic-authority transport fixture
is not admission of an economically qualified capability. Separate mission execution, rights, Jobs-validator,
governance and settlement authority remain necessary.

The outcome/prose review is [validation/opportunity_review.md](validation/opportunity_review.md). The complete
same-host standalone replay and changed-source control are reported in
[validation/full_edition_review.md](validation/full_edition_review.md). They cover executable research evidence,
not all-project CI, package security, paper/browser rendering, live service behavior, publication or deployment.
