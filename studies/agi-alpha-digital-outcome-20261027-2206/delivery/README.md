# DIGITAL-20261027-R1: a bounded beta-quantile delivery

This edition delivers an inspectable scalar beta-quantile kernel, a JSON command-line interface, three frozen
implementations, their common acceptance contract, independently generated confirmation cases and an evidence-bound
replay. A recipient can obtain a usable answer for documented numerical failures and inspect how that answer was checked.
The ordinary implementation is the recommended starting point. It passed the primary bank and the separately identified
minimum-subnormal midpoint diagnostic; no special expert-only capability is required to use it.

## What was accepted

All three frozen arms passed the same 64 confirmation checks: 56 numerical/endpoint checks and eight correct refusals.
These are 64 authored cases for **one public numerical-software mission**, with one implementation trial per arm.
They are not 64 independent missions, customers or population samples. Research acceptance is not customer acceptance.

The strongest early conventional challenge solved all five supplied public examples before the new construction.
The public issue already supplied a numerical formulation; every arm received it. This study therefore establishes no
exclusive numerical invention, equal-information discovery advantage, general Operational Alpha or fresh-transfer benefit.

A separate, known post-confirmation diagnostic found a conventional-arm rounding defect at
`q = 2**-1074, a = 1, b = 2`: the frozen conventional arm returned underflow zero, while ordinary and expert returned the
correct minimum positive float. This case was **not in the frozen 64-case bank** and is not additional fresh confirmation.
The original remains unchanged. The separate correction and its checks are under
`experiment/repairs/conventional_midpoint/`; the independent diagnostic is
`audit/independent_known_midpoint.json`. This does not change the primary 64/64 result or establish expert superiority
because the ordinary arm also succeeds.

## Run the complete replay

Use Linux with Python 3.11–3.13 and a C++17 compiler named `g++`. The observed environment used Python 3.12.14 and GCC 13.3.
The pinned Boost.Math headers and mpmath 1.3.0 are included; numerical replay does not need SciPy or network access.
The optional native journal check additionally needs `pydantic>=2,<3` and `cryptography` in the Python environment.

From the extracted edition root:

```bash
python -B delivery/reproduce.py --output ../beta-replay --native
```

The output directory must not already exist. The script:

1. Verifies the pinned vendored dependency inventory and hashes before importing or compiling those sources, then verifies all 98 frozen arm files, the confirmation evidence and the 24 reused upstream files.
2. Copies each arm into an isolated working tree and rebuilds its C++ wrapper from the pinned headers.
3. Executes the exact recorded 64-case bank, recomputes the 80/120-digit references and applies the frozen scorer.
4. Checks that acceptance counts match the published result and that original files remain unchanged.
5. Optionally exercises the existing journal, accounting and fitness components with explicit unknown actual costs.

This is a **reproduction of the recorded bank**, not a new confirmation experiment. To replay only against the verified
stored references, add `--skip-reference`. Resource observations vary with the host; no runtime or model-cost speedup is
inferred from them. The work tree links to the extracted edition's immutable dependency directory, so keep that directory
in place while using the replayed kernel. The outputs include every command, stdout/stderr, resource result, independent
score and `reproduction_report.json`.

## Use the accepted digital deliverable

After replay, send one JSON request or a JSON list to the ordinary arm:

```bash
printf '%s\n' '{"id":"reported-failure","q":1e-16,"a":0.5,"b":3}' |
  python -B ../beta-replay/work/experiment/arms/ordinary/run.py
```

The result is approximately `2.844444444444444e-33`, with `status: "ok"`. The installed SciPy 1.17.0 reproduction returned
`0.5` for the same public example. That installed-version observation is distinct from the issue reporter's environment.
The other two arms are accessible by replacing `ordinary` with `expert` or `conventional`; the frozen conventional arm's
known midpoint defect remains intentionally visible. The fixed conventional copy is a separately labelled diagnostic repair.

The program also accepts a path to a JSON input file. The callable API is `solution.solve(request)`. All input numbers are
interpreted as their received Python binary64 values. Booleans, strings and nonfinite values are refused. Request keys are
`id`, `q`, `a`, `b`.

| Requirement | Contract |
| --- | --- |
| Probability | `0 <= q <= 1` |
| Supported shapes | `0.25 <= a,b <= 1e6`, with `min(a,b) <= 100` |
| Interior value | `status: ok`, finite `x` in `[0,1]` |
| Exact probability endpoints | `status: endpoint`, `x = q` |
| Interior quantile rounding to zero | `status: underflow`, `x = 0` |
| Invalid input | `status: invalid`, `x: null` |
| Positive finite shapes outside supported bounds | `status: unsupported`, `x: null` |
| Numerical failure | `status: failed`, `x: null` with available error detail |

For a positive interior reference `r < 1`, the frozen error allowance is
`max(2*ulp(r), 1e-11*min(r, 1-r))`; zero is never accepted for a representable positive answer.
The nominal per-call ceiling is five observed CPU seconds; workers impose a ten-second wall guard and bounded process
resources. These are finite empirical checks, not a proof for every possible input. This is a scalar compatibility component,
not a complete vectorized SciPy replacement or an upstream-approved patch. Buyer-specific integration remains separate work.

## Existing-system reuse and honest accounting

`native_bridge.py` uses the existing `Journal`, `CostLedger`, signatures and `compute_fitness` implementations. The exact
24-file closure is in `native_reuse/`; `native_reuse_manifest.json` verifies it against repository commit
`3947e4ec8fd74ad40e13e8ff825a149fa98a10e9`. The native record binds 192 implementation checks across the same 64 cases,
retains all nine actual cost categories as unknown and records zero observed customer receipts. It does not create a
native commercial completion or fabricate an approval. Its keys are ephemeral local test identities, and private keys are
not exported. No `*.agent.agi.eth` authentication occurred.

The scenario economics in `economics/` remain explicitly modelled and are not inserted as measured ledger charges.
Reported wall time and tool counts are not token invoices. Model backend identity, temperature, tokens and provider bills
were not independently exposed. Agents ran live code and tool operations; no graphical computer-use benchmark was run.

## Source and correction record

The original problem and formulation are credited to the public SciPy issue and existing numerical prior art.
`provenance.json` lists source pins, licenses, limitations and confirmation hashes; `claim_map.json` links claims to evidence.
The reference's subnormal-rounding correction preceded fresh-case generation and followed independently reported concerns
from both ordinary and expert arms. Both the original evaluator and its correction remain in `experiment/`.

The prior kinetics package is preserved as `AGI_ALPHA_Gap_Experiment.zip`, SHA-256
`be2fd06f7ed3dde74741799020c566ae78609a91ab0afc5a6026f5dec9fe5921`. Its conventional parity, thin conditional margin and
untested physical assumptions are unchanged. It remains supporting engineering, with no revived breakthrough claim.

## Licensing and review status

New delivery source is Apache-2.0. The exact reused repository closure retains its original Apache-2.0 license.
Boost.Math retains the Boost Software License 1.0; mpmath and inspected SciPy source retain their BSD notices.
Frozen experiment sources are retained byte-for-byte as research evidence, including their original missing SPDX headers;
publication normalization, if supplied, must remain a separate mapped copy. Third-party issue prose is attributed, not
relicensed as original AGI ALPHA discovery.

This is a review edition. A public source branch, readable article and verified downloads do not constitute canonical
production publication. Required owner review, exact-head qualification and deployment verification remain separate gates.

## Rebuild the paper, brief and browser edition

Use a working copy of the extracted package. The authoring workflow needs Python with Matplotlib, Pandoc, XeLaTeX with standard Pandoc/TeX Live packages, and the DejaVu Serif, DejaVu Sans and DejaVu Sans Mono fonts. The style file lists its LaTeX packages. The checked PDF/SVG figure sources and complete generated LaTeX are already included.

From the extracted root:

```sh
python edition/build_figures.py
python edition/build_edition.py
python edition/build_brief.py
```

The builders regenerate both PDFs, the complete self-contained HTML and the GitHub-readable Markdown in `edition/`. The main builder resolves the bibliography with Pandoc citeproc and runs XeLaTeX twice with shell escape disabled. The included `.tex` files can also be compiled directly with XeLaTeX from `edition/`; their bibliography text is already resolved. The published paper has 14 pages and the brief has two. PDF metadata and pagination can vary with the local TeX/font versions; the supplied checked originals and their hashes remain the publication record. When placing `edition/browser_reading.md` at the study root, prefix its two `figures/` image paths with `edition/`.
