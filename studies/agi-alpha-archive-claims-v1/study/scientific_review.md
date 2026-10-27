# Scientific review of the manuscript template

## Scope and conclusion

This review concerns scientific scope, the exact model and sensitivity claims, reported finite results, prior-art attribution, and the interpretation of integration and transfer. Economics placeholders and the pending economic revision are outside scope. The reviewer contributed the engine and methods document; this is a separate review of the manuscript, not external peer review or an independent replication of the entire study.

The core scientific account is sound and appropriately limited. The endpoint examples, primary counts, recorded runtimes, refusals, and transfer flags agree with the proof and saved primary records. The manuscript does not establish novelty, an E-versus-U performance effect, real-archive source completeness, trained successor competence, or commercial success; it generally states these limits clearly.

Four corrections should be made before publication: specify both periods in the small-offset sensitivity statement, correct two bibliographic author initials, and disambiguate the statement that no tokens were used. Additional precision edits below would improve reproducibility without changing any result.

No manuscript, code, results, or other study file was edited. No experiment was rerun, no cache was generated, and no new broad search was performed. Three directly cited primary papers were opened to verify attribution.

## Required corrections

### R1. Section 4.1: the 0.0125-offset statement requires two separately uncertain periods

The reviewed sentence says that an additional independently uncertain period offset of amplitude 0.0125 consumes the remaining margin. This is ambiguous and is false if it means an offset affecting only one period.

For the originating query, the shared-model lower endpoint is 0.375 and the threshold is 0.35, leaving a margin of 0.025. If additional offsets satisfy

\[
\eta_E\in[-\varepsilon_E,\varepsilon_E],
\qquad
\eta_L\in[-\varepsilon_L,\varepsilon_L],
\]

and may be chosen separately, the worst additional change to the contrast is
\(-\varepsilon_E-\varepsilon_L\).

Thus:

- Two independently uncertain period offsets, **each** with amplitude 0.0125, consume the 0.025 margin.
- An offset affecting only one period requires amplitude 0.025 to consume it.
- An additional offset shared by both periods cancels, regardless of its amplitude within the assumed additive model.

Recommended replacement:

> If each period also has its own independently uncertain additional offset of amplitude 0.0125, the worst contrast shift is −0.025, bringing the lower endpoint to the unchanged threshold. An offset affecting only one period would require amplitude 0.025.

The other two sensitivity statements in the paragraph are correct. With equal absolute weights \(1/4\), uniform row-error bound \(b\), and count budget \(k\), the relevant lower endpoint is \(0.4-kb/4\). Either changing \(b\) from 0.1 to 0.2 at \(k=1\), or changing \(k\) from one to two at \(b=0.1\), produces 0.35. Because the claim is strict and the upper endpoint remains above the threshold, the resulting classification is UNRESOLVED, not FALSE.

### R2. Reference 7: Toussaint's initial is E., not M.

The KR proceedings identify the authors as **Etienne Toussaint, Paolo Guagliardo, and Leonid Libkin**. The reviewed reference begins “Toussaint, M.”

Correct it to:

> Toussaint, E., Guagliardo, P. and Libkin, L. (2020). Knowledge-Preserving Certain Answers for SQL-like Queries.

The title, year, and substantive table description are supported by the primary page. Its BibTeX record independently confirms the name. Sources: [KR paper page](https://proceedings.kr.org/2020/78/) and [publisher BibTeX](https://proceedings.kr.org/2020/78/bibtex/).

### R3. Reference 10: Zhang's initial is Y., and Sieber is R. E.

The publisher identifies the authors as **Y. Zhang and R. E. Sieber**. The reviewed reference uses “Zhang, R. and Sieber, R.”

Recommended correction:

> Zhang, Y. and Sieber, R. E. Automation of historical weather data rescue. Geoscience Data Journal; first published 26 September 2024.

The first-publication date and title are correct. The publisher displays the article in its 2025 volume; distinguishing online publication from issue year is appropriate. [Primary publisher page](https://rmets.onlinelibrary.wiley.com/doi/full/10.1002/gdj3.261).

### R4. Abstract: distinguish blockchain tokens from inference tokens

The statement “No tokens, funds or live network permissions were used” can be read as claiming that hosted inference used no tokens. Appendix B correctly says actual hosted token usage and billing were unavailable, which is different from zero.

Recommended replacement:

> No blockchain token transactions, payments, or production-network permissions were exercised.

This preserves the intended on-chain and authority boundary while avoiding a claim inconsistent with the model-access disclosure.

## Recommended precision edits

### P1. Name the ablation as a calibration-decorrelated control

Read-only inspection of the harness confirms that the control deep-copies each case, gives every row a separate calibration group with the original group's choices, and leaves glyph alternatives, weights, threshold, row-error bounds, and the sparse-error budget unchanged. The six lost confirmation decisions therefore concern the relaxation of shared calibration.

“Independent intervals” can suggest that the control also treats every row error independently and drops the count budget. It does not.

Prefer **calibration-decorrelated control** in the evidence summary, abstract, results table, and Figure 2, and define it once:

> The control assigns each row its own calibration choice while retaining the original glyph sets, weights, threshold, row-error bounds, and error-count budget.

The numerical comparison does not need changing. The manuscript already correctly refuses to interpret this ablation as an advantage over competent certain-answer methods or ordinary users.

### P2. State the freeze boundary as preceding case generation, not seed availability

Appendix B says confirmation freezes precede fresh cases “or random seeds.” The fixed primary seeds were already present in the construction protocol, which the engine author read before the final source freeze. Generated cases and answers were not used for the implementation. The meaningful separation is therefore before **case generation and result inspection**, not concealed or subsequently selected seeds.

Recommended replacement:

> The implementation and comparison sources were hashed before fresh case generation. The primary seeds were recorded in the protocol and were available to the implementer; the generated cases and answers were not used to modify the frozen implementation.

This matches the methods record and avoids overstating the strength of the development holdout.

### P3. Narrow the identifier and source-label claims to the actual validator

In Section 5.1, replace “duplicate identifiers” with **duplicate row or calibration-group identifiers**. Repeated source identifiers are permitted.

Replace “attempts to label a source as verified physical evidence” with:

> source-model labels other than research-authored.

Then retain the explicit statement that the validator does not verify physical source evidence. The current prose is understandable, but this wording makes clear that the engine checks an enum-like label rather than detecting source fraud or establishing provenance.

### P4. Prefer “failed novelty qualification” over “failed novelty claim”

The abstract's phrase “a failed novelty claim” could suggest a stronger universal conclusion than the bounded search supports. **A failed novelty qualification** or **a candidate that failed the stated novelty gate** better matches the manuscript's precise conclusion: no substantive advance over the strongest identified approaches was established.

This is not a request to soften the negative result. The explicit no-flagship decision should remain.

### P5. Add the directly relevant chemistry citation to the bibliography

Reference 12 points readers to the raw candidate record for chemistry. Because the manuscript itself makes the substantive E4 prior-art comparison, a direct reference would be clearer:

> Vitale, G. A., Xia, S.-N., et al. (2025). Enhancing tandem mass spectrometry-based metabolite annotation with online chemical labeling. Nature Communications 16, 6911. DOI: 10.1038/s41467-025-61240-z.

This primary paper was already verified during the frozen discovery arm. [Primary PDF](https://www.nature.com/articles/s41467-025-61240-z.pdf). No new chemistry novelty search is needed for this citation correction.

### P6. Keep transfer parity narrower than all possible retention value

The strongest directly observed transfer statement is functional: new processes executed the same code and produced identical certificates. The manuscript correctly says this is technical portability, not trained independent competence.

For maximal precision, the Section 7 table's “special retention advantage is absent in this control” could become:

> No output-quality advantage over the identical-content ordinary library is observed in this control.

Other potential packaging or authority-management benefits were not measured by byte parity. This is a refinement of an already well-qualified statement, not a finding that the manuscript claims demonstrated learning.

## Claims cross-checked and supported

### Exact model and originating counterexample

The stated finite model matches the frozen engine: independent glyph alternatives, one shared offset per declared group, signed row errors in the allowed three-point sets, and at most \(k\) nonzero errors. The top-\(k\) formula and strict decision rule agree with the proof.

The shared-calibration example has exact endpoints [0.375, 1.625] and 13,056 latent assignments. The independent-period example has endpoints [−0.425, 2.425] and 39,168 assignments. Both preserve the contrast and threshold while deliberately changing the calibration assumption. The latter supplies a genuine counterexample to certainty under the broader model.

The manuscript correctly treats the intervals as bounds over authored histories, not statistical confidence intervals or climate findings.

### Primary and successor results

The saved primary summary supports the table:

| Family | Cases | TRUE / FALSE / UNRESOLVED | Histories |
|---|---:|---|---:|
| Original shared example | 1 | 1 / 0 / 0 | 13,056 |
| Calibration counterexample | 1 | 0 / 0 / 1 | 39,168 |
| Confirmation | 36 | 3 / 9 / 24 | 231,648 |
| Successor | 12 | 0 / 0 / 12 | 593,856 |
| Total | 50 | 4 / 9 / 37 | 877,728 |

All summary reference-equality and witness-validity flags are true. Both endpoints per case account for 100 checked witnesses. All 12 recorded refusal probes have refused=true. All 12 recorded transfer comparisons have byte_identical=true and matches_primary_certificate=true.

The manuscript correctly distinguishes 50 total comparisons from 36 fresh confirmation cases. The 12/36 decisive fraction includes nine useful FALSE answers; it does not misclassify FALSE as a failure. The 12 successor results are all unresolved, so no decisive successor delivery or profitable successor mission is demonstrated.

The point-estimate diagnostic is correctly labeled as intentionally limited. Its 24 nonuniversal confirmation assertions are not presented as 24 empirically wrong answers or as an ordinary-user baseline. That distinction should remain.

### Recorded timing

Summing the existing recorded timings gives 0.02304410898068454 seconds for the engine and 7.8380494669982 seconds for exhaustive enumeration. The manuscript's approximately 0.023 and 7.84 seconds are accurate roundings. No timings were rerun.

The exclusions for authoring, source interpretation, human work, and business cost are appropriate. So is the statement that a conventional analytic implementation has the same structural efficiency; no AI speedup follows from comparison against exhaustive enumeration.

### Source access and prior-art scope

The access correction agrees with the stored Zenodo metadata, including restricted access and an empty file list. The manuscript does not claim a completed image benchmark or a physical climate result.

The KR title and capability summary are correct after the author-initial correction. The VLDB paper's first page confirms Reynold Cheng, Jinchuan Chen, and Xike Xie; Reference 9's initials and its query-directed-cleaning description are accurate. The AU-DB discussion appropriately distinguishes richer shared-variable representations from simple bound abstractions.

### Integration and learning inference

The manuscript separates local native execution, plan compilation, scientific acceptance, production admission, and financial authority. It explicitly reports the unsupported scientific scope's admission refusal and does not turn local artifact verification into a claim of authorized network deployment.

The E-versus-U and E+-versus-E effects remain unmeasured. Same-code transfer is not described as model-parameter training or external replication. These boundaries are scientifically appropriate. This review did not independently rerun the native bridge; it evaluates the inference drawn from the reported integration evidence.

## Review disposition

Retain the core exact results and negative novelty conclusion. Apply R1–R4 and the inexpensive precision edits above before publication. There is no need to alter the frozen engine, repeat the primary experiment, manufacture a stronger baseline deficit, or reinterpret unresolved successor cases as useful scientific deliveries.
