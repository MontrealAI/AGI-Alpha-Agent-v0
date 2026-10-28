<!-- SPDX-License-Identifier: Apache-2.0 -->
# Publication CAD factual review

Reviewed at 2026-10-28T01:54:10Z. This is an author fact check by the agent
that authored the nominal constructor. It is not an independent external
validation, human peer review, industrial acceptance or another fresh test.
Only this review file was written. Frozen sources and reports were not changed.

## Reviewed publication identities

- PAPER.md: `87b908aee42a1c8cef74aa993c4a17076126471882b8db356af37844ed3942ee`
- EXECUTIVE_BRIEF.md: `f52f0a8e52c7bee85ba8683983cc5f3abbae352ff481337140f95d1151c85732`
- Current constructor: `5c2be43b6e014a34465eb249d6f30e5e278c9a0975f0d8fc59a6ccc8cf4b058e`
- Fresh checker: `38f49c711fe0d03e74972d6e85ae2adfc40a705f3d3ef8d84500082fee24674c`
- Fresh request protocol: `df7002de8eb4f66446aa9e23d7875b213140d91fd39e65275d105c116c03321e`
- Fresh report: `ba5d80725cddd1ade056c575234d252cc20962ef23ee38dd961248b3eb941dfd`
- Supplementary verification: `6009bbefde5c553a327d64ce09addd597561021a8a8fefbfd6c42e618547278b`
- Independent-audit record inspected: `90489c8cbdcfd872f0c470e3dcadaf36103de9f60bce4566a375f0da4710af04`

## Verdict

The main CAD result and STOP conclusion are supported. The paper and brief
accurately distinguish historical reconstruction from fresh researcher-specified
requests and from industrial or buyer validation. No unsupported positive
novelty, design-intent-recovery, units, physical-qualification or commercial
acceptance claim was found in the reviewed text. Two wording corrections and
three precision improvements are recommended below.

This review did not independently re-audit the full economic model, external
market/prior-art sources, API pricing, GitHub publication or completed rendering.
Those claims require their own cited source and execution records.

## Corrections to carry into the publication

### C1 — A modeled zero-value control is not an observed buyer assessment

Location: PAPER.md, Executive finding, final sentence of the economic paragraph.

Current wording: "The actual public-source control favors stopping, because the
free source already supplies the relevant outcome."

Issue: The free source demonstrably supplies the central nominal solids. It
does not itself contain every new CSV, checker, provenance record or delivery
obligation. No buyer assessed those additions. The control's zero incremental
willingness to pay is an assumption, not observed refusal or a proven absence
of customer value. A negative commercial claim needs the same evidentiary care
as a positive one.

Suggested replacement: "The modeled public-source zero-value control selects
stopping. It assumes no incremental willingness to pay for reproducing geometry
already available from free source; no buyer refusal or zero-value assessment
was observed."

The executive brief already calls the table modeled conditional economics;
it can retain its table label, preferably adding one sentence that the
public-source zero-value control is an assumption rather than observed demand.

### C2 — Disclose repair self-review beside the wrapper correction

Location: PAPER.md, Section5.1, after the supplementary-verifier repair account.

Evidence: evidence/independent_audit.json, repair_authorship_disclosure says the
reviewer authored the corrected supplementary verifier and adapted reproduce.py;
its repair checks are self-checks. The initial constructor critique was by a
separate agent. The general shared-session authorship disclosure is correct but
does not make this specific change of role visible next to the repair claim.

Suggested addition: "The reviewer also implemented the supplementary verifier
correction; its repair checks are self-checks, rather than an independent review
of that corrected code. The original constructor critique came from a separate
agent in the same session."

## Precision improvements

### P1 — Name exactly what the Boolean measurement establishes

Locations: PAPER.md Sections5 and16 and brief result table.

Reports store symmetric_difference_volume=0.0, calculated from the sum of the
volumes of the two Boolean differences. Prefer "zero measured Boolean
symmetric-difference volume" to unqualified "zero Boolean symmetric-difference"
or generic "equivalent" where practical. The numerical rubric and common
OpenCascade limitation are already correctly disclosed. This does not change
any acceptance count.

### P2 — Clarify analytical reference and numerical dimensions

Location: PAPER.md Section5 opening paragraph.

The implemented volume tolerance is based on the analytic reference volume in
both the historical and fresh checkers. Replace "reference volume" with
"analytic reference volume". Bounding dimensions have a separate absolute
threshold of1e-7 model units; the quoted max(1e-6,1e-8*|volume|) applies to
volume comparisons. If the text is intended to give the entire numerical
rubric, state the bounding-box threshold separately.

### P3 — State the exact extent of fresh-checker code separation

Location: PAPER.md Section5, sentence about the independently authored native
construction and analytic volume.

The native_reference and independent_volume functions are separately authored
and do not import the constructor's construction or volume function. The
checker does reuse the constructor module's metrics and export_case helpers.
Suggested wording: "A separately authored native CadQuery construction and
analytic-volume function checked each request; export and bounding-box helpers
were reused from the constructor. Both geometry paths use OpenCascade."

This is a precision improvement, not a reversal of the fresh geometric result.

## Claims confirmed against source and execution records

| Claim | Observed support | Boundary |
|---|---|---|
| Original frozen run0/3 | results/construction_v1/acceptance.json | Bounding-box/roundtrip criteria failed; no replacement of that result |
| Measurement-corrected historical run3/3 | results/construction_v1_1/acceptance.json | Same disclosed cases, no new confirmation |
| Scope-hardened historical run3/3 | results/construction_v1_2/acceptance.json | Same geometry and criteria; narrower input admission |
| Fresh post-freeze requests3/3 | protocol/FRESH_FREEZE.json; fresh acceptance report | New researcher-specified nominal cases, not customer or industrial cases |
| Six geometric refusals6/6 | fresh report negative_cases | Six named cases only; not a complete robustness guarantee |
| Feature-ID defects0/2 refused | fresh report exploratory_schema_cases | Missing and duplicate IDs remain open semantic limitations |
| Six supplementary STEP comparisons | evidence/final_verification.json | Six valid reimports, all measured Boolean difference volumes zero; retrospective same-kernel check |
| Source interpretation manually authored | Source construction task and explicit program | No autonomous drawing/STEP parser or learned model |
| Ex003 inset discrepancy | Source rect(length-12,width-12) and source comment | Six units from edges, not comment's twelve |
| Ex003 edit dependency loss | Source computes centers; recipe stores +/-34,+/-44 | Stock-only changes do not preserve original relation |
| Ex019 physical units unresolved | Source script lacks physical-unit declaration | STEP unit metadata cannot establish design intent |
| Free native source generates central geometry | Executed source/reference comparisons | Does not prove that all packaging/support additions have zero value |
| Buyer usefulness remains hypothetical | No customer task/acceptance record | CAD-developer beneficiary is a plausible use, not observed demand |
| Flagship not admitted | Prior-art comparison plus absence of productive/commercial crossing | Positive engineering checks do not supply missing enterprise evidence |

## Publication completion checks outside this factual review

Before final delivery, make sure the statements that LaTeX/browser rendering
checks were executed and pinned public reading/download routes exist are tied
to completed QA and publication receipts. The reviewed manuscript describes
those as completed activities, but this CAD-author review did not verify them.
