[See docs/DISCLAIMER_SNIPPET.md](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/3947e4ec8fd74ad40e13e8ff825a149fa98a10e9/docs/DISCLAIMER_SNIPPET.md)

# AGI ALPHA FLYWHEEL — When Capability Creates Opportunity

## From a numerical failure to a verified digital answer

**Vincent Boucher — President of MONTREAL.AI**

DIGITAL-20261027-R1 · 27 October 2026 · Research review edition

This repository is a conceptual research prototype. References to “AGI” and “superintelligence” describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

**A usable bounded beta-quantile component, with three frozen implementations and a complete record.** All three workflows passed the 64 fresh checks: 56 numerical/endpoints and eight required refusals. The strongest early conventional challenge solved all five public examples before construction. One public mission and one implementation trial per workflow do not establish general Operational Alpha or a new numerical algorithm.

A known post-confirmation minimum-subnormal midpoint exposed a failure in the original conventional arm. Ordinary and expert passed; a separately labeled conventional correction passed the same 64-case replay plus that known diagnostic. The original failure remains in the archive. The ordinary implementation is the recommended research entry point.

## Read and download

- [Complete browser-readable research edition](manuscript.md)
- [14-page paper PDF](edition/AGI_ALPHA_Flywheel_Digital_R1.pdf)
- [Two-page executive brief](edition/AGI_ALPHA_Flywheel_Digital_R1_Brief.pdf)
- [Complete offline HTML edition](edition/AGI_ALPHA_Flywheel_Digital_R1.html) — download and open in a browser
- [Runnable source, evidence and prior kinetics archive](evidence/AGI_ALPHA_Flywheel_Digital_R1_Source_Evidence.zip)
- [Compilable LaTeX](edition/AGI_ALPHA_Flywheel_Digital_R1.tex), [bibliography](edition/references.bib) and [figure sources](edition/build_figures.py)
- [Complete conditional economics](economics/economics.md)
- [Claim-to-evidence map](delivery/claim_map.json)
- [LinkedIn draft for approval — not posted](edition/LinkedIn_Draft_Digital_R1.txt)

The PDF, brief and browser edition agree on the findings, known comparator failure, separate correction and commercial limitations. The source archive includes frozen prompts/configuration, all failed attempts, evaluator versions and correction, fresh cases/references/results, independent audit, source pins and licenses, complete monetary scenarios, native Journal/CostLedger/fitness reuse and reproduction instructions. Raw third-party issue prose is represented by exact source hashes and an optional retrieval script, with discovery credit preserved.

## Reproduce the accepted digital result

Download and extract the source/evidence ZIP into an empty directory. From that extracted root:

```sh
python -B delivery/reproduce.py --output ../beta-replay --native
```

Linux, Python 3.11–3.13 and C++17 `g++` are required. Boost.Math and mpmath are included; numerical replay works offline. `--native` additionally requires Pydantic 2 and cryptography. Omit it to run the numerical replay without those optional packages.

Use the rebuilt ordinary implementation:

```sh
printf '%s\n' '{"id":"public-example","q":1e-16,"a":0.5,"b":3}' |
  python -B ../beta-replay/work/experiment/arms/ordinary/run.py
```

Expected answer: approximately `2.844444444444444e-33`, status `ok`. The reproduced installed SciPy 1.17.0 `beta.ppf` returned `0.5` on this public example, accompanied by a warning. This is a scalar compatibility component under a frozen domain, not a complete vectorized SciPy replacement or an upstream-approved patch.

## Separate verdicts

| Category | Verdict |
|---|---|
| Useful research delivery | Supported within the finite frozen contract; independent build/replay passed |
| Paid commercial delivery | Not observed; buyer-specific integration and acceptance remain future work |
| Operating economics | Conditional model only; central profit is USD `2,716.30 − 4M` for four hypothetical USD1,500 engagements |
| Full-project return | Conditional `2,216.30 − 4M − D`; unknown historical development D is charged once |
| Funding | Unknown available funds; at illustrative M=USD100, base threshold USD3,966.25 and earned-milestone threshold USD3,476.55 |
| Operational Alpha | Not established; expert did not beat competent ordinary accepted quality and actual billing is unavailable |
| Transformational advance | No exclusive numerical capability beyond established methods; public formulation credited |
| Retained Alpha | No fresh-transfer benefit demonstrated; no mandatory Gym investment |

M is unknown additional model/tool cost per future engagement, including retries. The USD100 coordinate is a sensitivity, not measured billing. Buyer value, willingness to pay and demand are assumptions. Observed customers, commitments and collections are zero. The earlier kinetics constructor remains supporting engineering with its original conventional parity, thin conditional margin and untested physical assumptions.

## Publication boundary

This is an additive **review edition** under the full mixed-source/data/HTML qualification lane. It does not update the canonical catalog, runtime, homepage, service workers, software release or Pages deployment. Existing owners and the 1.46.1 publication lease remain authoritative.

Canonical publication needs exact-source owner review, required hosted checks, applicable integration/release qualification and actual served-byte verification. A pinned public reading page and matching downloads establish review availability, not canonical production release. The exact review commit and byte-verification receipt are recorded in the PR conversation and coordination issue #4850.
