# Numerical adjudication and delivery recovery

**Status: post-confirmation diagnostics.** The frozen protocol, three original evaluators, confirmation inputs and original results remain unchanged. This report does not constitute another fresh-confirmation round.

The preserved result is **62/64 declared expected outcomes for ordinary operation, 62/64 for expert operation, and 64/64 for the conventional reference**. The conventional reference was also the numeric comparator in that campaign; its comparison with itself is not an independent numerical validation. The two disputed boundaries below receive additional exact-rational and analytic adjudication here.

## 1. A negative NPV rounded to zero

Case: `tiny_negative_npv_sign`.

The input specifies capital of EUR50, annual cash margin of EUR1, a 50-year horizon and a positive discount rate of `1e-18`. Both original frontier-generated implementations returned an NPV of zero and `CONDITIONAL_NEXT_MILESTONE`. The Decimal reference returned `STOP`, with an NPV approximately **−EUR1.275 × 10⁻¹⁵**.

The correct sign does not depend on accepting the reference implementation. For every positive discount rate and every year after time zero, the discount factor is strictly less than one. Fifty discounted receipts of one euro therefore sum to strictly less than fifty euros. Subtracting EUR50 capital produces a strictly negative NPV. An independent calculation using exact rational numbers confirms that result.

**Classification:** a clear violation of the frozen strict-sign decision rule. The amount is economically immaterial in this deliberately artificial boundary case, but the returned continuation decision is wrong under the agreed rule. Neither original implementation granted physical operating authority.

**Cause:** binary64 rounding loses the difference between the discounted annuity and 50. The resulting numeric output is within the campaign's numeric tolerance, while its decision is incorrect. Numeric tolerance must not silently replace the separate strict decision rule.

**Recovery:** select the unchanged conventional Decimal calculation for the customer-facing result. Preserve the original failure and original score. A future version could use a rigorously bounded sign test; adding an arbitrary tolerance would change this protocol's semantics.

## 2. Decimal inputs versus binary approximations

Case: `decimal_literal_cancellation`.

The stated decimal cash flows are EUR0.3 savings and EUR0.1 plus EUR0.2 operating costs, with no capital and no discounting. Exact decimal arithmetic gives zero margin and zero NPV. The frozen rule accepts equality, so its decimal interpretation gives `CONDITIONAL_NEXT_MILESTONE`.

Both original implementations instead returned a margin of approximately **−5.551115123125783 × 10⁻¹⁷** and `STOP`. The exact rational values of the three binary64 inputs already produce a negative difference, **−1/36028797018963968**; rounded addition changes its magnitude again.

**Classification:** a protocol gap concerning the interpretation of input numbers, with a rejection that is incorrect under the selected decimal-literal policy. The original protocol did not explicitly declare whether a JSON decimal token or its binary approximation defines equality. This case must remain separately tagged; it should not be presented as a second unambiguous implementation violation or as meaningful financial loss.

**Recovery:** the delivery interface now states its interpretation explicitly. JSON floating-point tokens are initially read as exact decimal values. A token is admitted only when converting it to the unchanged reference evaluator's supported input and back to its shortest decimal spelling preserves that value exactly. Unsupported long or out-of-range literals are refused, with no numerical claims. Numeric strings are not silently accepted as numbers.

## 3. Customer-facing delivery selector

`src/deliver.py` selects the **unchanged frozen conventional evaluator** and, by default, executes the unchanged ordinary and expert implementations for diagnostic comparison. It exposes any decision disagreement and separately reports whether the numerical differences fall within the original tolerance. A result remains a conditional software screen; physical operations and spending are never authorized.

The selector checks the frozen protocol and evaluator hashes. It does not rewrite the protocol, alter prior code or replace historical results. Selecting this established method after learning from the failures is delivery recovery, not evidence of Operational Alpha, a new method, or an improved fresh-confirmation success rate.

From the study directory:

```sh
python src/deliver.py inputs/published_case.json --output evidence/published_delivery.json
```

For the published case, the selected result remains **DEFER**, with EUR53,370 stated annual cash margin, EUR35,370 annual accounting margin, approximately EUR121,552.40 stated-input NPV and 3.37268 years simple payback. The missing buyer specification, long-run evidence and complete costs still block progression. Small last-digit numerical differences from the original stored result do not change that decision; the original file is preserved.

## 4. Verification performed after confirmation

The machine-readable companion records **14 successful diagnostic checks**: replay of the two diagnosed cases, ten manually specified checks, and two parser-refusal checks. They cover a different tiny positive discount rate and horizon, exact zero-discount equality, distinct decimal cancellation, genuine positive and negative margins, strict quality limits, unresolved pilot evidence, discharge-only limits, unsupported operation requests, incompatible units, long decimal literals and nonstandard nonfinite JSON.

These checks are explicitly **post-confirmation diagnostics**, not an unseen evaluation set, a statistical performance estimate or another confirmation round. All nine protected protocol, input, implementation and result files had identical hashes before and after the work. Strict mypy and Ruff checks pass for the delivery selector.

## 5. Source extraction verification

Eleven checks confirm the extraction against [Simonič (2021), Table 5 and the adjacent text](https://pmc.ncbi.nlm.nih.gov/articles/PMC8705695/), DOI [10.3390/membranes11120976](https://doi.org/10.3390/membranes11120976). The article is distributed under CC BY 4.0.

| Stated item | Historical nominal EUR |
|---|---:|
| Initial plant capital | 180,000 |
| Annual energy | 7,730 |
| Annual chemicals | 3,900 |
| Annual labour | 11,000 |
| Annual wastewater discharge | 6,000 |
| Annual cash operating cost, summed | 28,630 |
| Annual depreciation | 18,000 |
| Annual accounting cost, summed | 46,630 |
| Reported annual gross savings | 82,000 |

The table's EUR208,630 total combines plant capital with one year of its listed cash operating costs; it is not a separately observed capital price. The text's under-one-year payback statement is unsupported by the tabulated values. The sodium and chloride values used by the study are the reported concentration-mode permeate observations, rather than the mixed-feed table. These historical inputs remain projected or laboratory evidence, not current quotations, sustained plant performance, customer acceptance or actual AGI ALPHA receipts.

Full calculations, case inputs, selected outputs, original-arm comparisons and integrity hashes appear in `numerical_adjudication.json`.
