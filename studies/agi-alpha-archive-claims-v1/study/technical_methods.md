# Exact linear claims under transcription, shared-calibration, and sparse-error uncertainty

## Scope and evidentiary status

This document specifies and proves the finite-model calculation implemented by the frozen claim engine. It also records the construction and evaluation boundaries needed to interpret that artifact. The target is an explicitly supplied rational linear functional of numerical records. The engine returns its exact minimum and maximum over a declared family of admissible histories, together with histories attaining both endpoints.

The implementation is an ordinary exact method. Its mathematical ingredients are separability of a linear functional, aggregation of coefficients for a shared nuisance variable, and the support function of a cardinality-constrained error set. Correct implementation of these ingredients is distinct from discovering a new scientific method, identifying a new productive need, establishing real archival usefulness, or demonstrating improved discovery competence.

The analysis is conditional on a research-authored source model. No source-certified handwriting-recognition result or historical climate conclusion is established. This methods document was prepared without consulting primary confirmation outputs. Planned confirmation quantities below are design specifications, not reported outcomes.

## 1. Frozen implementation and interface

The final implementation is the Python 3.12 standard-library file **study/src/claim_engine.py**, with Apache-2.0 SPDX identification. Its final pre-confirmation SHA-256 is:

~~~text
dce5ac65b3c1cdaf625a2f9a0ee554df88d5d2853454ebad5d2cfc00265794db
~~~

The file has 239 lines. The public interface is **solve(payload, source_input_sha256=None)**, with a command-line entry point:

~~~text
python study/src/claim_engine.py --input INPUT.json --output OUTPUT.json
~~~

The accepted input schema is **agialpha.archive-claim.v1**. It includes an identifier, a common unit label, the source-model label **research-authored**, rows, calibration groups, an error budget, and a threshold. Each row contains an identifier, a source identifier, finite numerical alternatives, a rational weight, a calibration-group identifier, and a nonnegative error bound. Each calibration group contains an identifier and finite numerical alternatives.

Numbers are parsed directly from exact integer, ordinary finite decimal, or numerator/positive-denominator strings into rational numbers. JSON floating-point values, exponent notation, surrounding whitespace in numerical strings, nonfinite values, and zero denominators are outside the accepted numerical syntax. Arithmetic and comparisons use exact rational operations; displayed fractions do not result from rounding a floating-point approximation.

The input limits are 1–64 rows, 1–64 calibration groups, 1–8 numerically distinct alternatives in each row or group, and at most 40 characters in each numerical string. The error budget must be an integer between zero and the number of rows; a Boolean value is not accepted as an integer budget. Required identifier and unit strings must be nonempty, bounded in length, and free of the prohibited control characters. Row identifiers and group identifiers are unique within their respective collections. Source identifiers need not be unique. Every row refers to a declared group, although a declared group may be unused. A singleton zero calibration is available for a fixed zero offset.

Unknown fields, unknown groups, duplicate numerical alternatives, and duplicate JSON keys are refused. In particular, extra fields purporting to impose coupled constraints are not silently discarded. Nonempty alternative sets and the always-admissible zero-error vector ensure that a valid input defines a nonempty mathematical state space.

Successful output reports exact lower and upper bounds, a threshold decision, the input digest, endpoint witnesses, and a count of latent assignments. A refusal is a scope or validity result, not a scientific conclusion. CLI success exits zero; refusals exit two. A destination identifying the input file itself is refused without overwriting the source.

For the CLI, the digest hashes the exact input bytes. A direct function call without a supplied digest hashes canonical JSON using sorted keys, compact separators, UTF-8 encoding, and unescaped Unicode. These digests establish an input's identity for reproduction. They do not authenticate an archive, certify an interpretation, or establish a physical calibration history.

## 2. Mathematical source model

Let there be \(n\) rows, indexed by \(i\), and a finite collection of calibration groups \(G\). Let \(g(i)\in G\) be the group assigned to row \(i\).

For each row, define:

- A finite, nonempty set \(A_i\subset\mathbb{Q}\) of numerical glyph interpretations.
- A fixed query weight \(w_i\in\mathbb{Q}\).
- A nonnegative error magnitude \(b_i\in\mathbb{Q}_{\geq 0}\).

For each group \(h\in G\), define a finite, nonempty set \(C_h\subset\mathbb{Q}\) of admissible additive calibration offsets. Let \(k\in\{0,\ldots,n\}\) be the maximum number of rows with nonzero errors.

The permitted error vectors are

\[
\mathcal E_k =
\left\{
e\in\mathbb{Q}^n:
e_i\in\{-b_i,0,b_i\}\ \text{for every }i,\quad
\lVert e\rVert_0\leq k
\right\}.
\]

Here \(\lVert e\rVert_0\) counts nonzero entries. When \(b_i=0\), the row has only the zero error choice.

A latent history is

\[
\omega=(a,c,e)\in\Omega
=\left(\prod_{i=1}^n A_i\right)
\times\left(\prod_{h\in G} C_h\right)
\times\mathcal E_k.
\]

The implied row values are

\[
x_i(\omega)=a_i+c_{g(i)}+e_i.
\]

The queried linear functional and the strict threshold claim are

\[
q(\omega)=\sum_{i=1}^n w_i x_i(\omega),
\qquad
\mathcal P(\omega): q(\omega)>\tau,
\]

where \(\tau\in\mathbb{Q}\).

The engine supports arbitrary signed rational weights. Their sum need not be zero. A statistical contrast is one special case of the supported linear functional. The common unit string is metadata: the implementation performs no unit conversion and no dimensional-analysis proof. Treating the weights as dimensionless, or otherwise justifying the output's unit interpretation, is a caller obligation.

The factorization of \(\Omega\) is substantive. Glyph choices are independent coordinates of the admitted set, not random variables assumed statistically independent. A single offset is shared by all rows in the same group. Error signs and positions may vary freely subject only to the magnitude choices and the count budget. There is no probability distribution over histories.

## 3. Exact bound formula

For each calibration group, aggregate the weights of its member rows:

\[
W_h=\sum_{i:g(i)=h} w_i.
\]

For each row and group, define the one-coordinate extrema:

\[
\begin{aligned}
\ell_i^A &= \min_{a\in A_i} w_i a,
&u_i^A &= \max_{a\in A_i} w_i a,\\
\ell_h^C &= \min_{c\in C_h} W_h c,
&u_h^C &= \max_{c\in C_h} W_h c.
\end{aligned}
\]

Negative coefficients are included in these definitions. Thus the minimizing numerical alternative need not be the numerically smallest alternative.

Set

\[
r_i=|w_i|b_i,
\]

and order these nonnegative values as
\(r_{(1)}\geq\cdots\geq r_{(n)}\). Define

\[
R_k=\sum_{j=1}^{k}r_{(j)}, \qquad R_0=0.
\]

The exact endpoints are

\[
\boxed{
L=\sum_i\ell_i^A+\sum_{h\in G}\ell_h^C-R_k
}
\]

and

\[
\boxed{
U=\sum_i u_i^A+\sum_{h\in G}u_h^C+R_k.
}
\]

If fewer than \(k\) values \(r_i\) are positive, the remaining terms contribute zero. The implementation constructs sparse witnesses using only positive-contribution positions. Ties in the error ranking are resolved by input row order. Ties between alternatives select the first listed alternative. These conventions determine reproducible witnesses but do not affect the endpoints.

### Lemma 1: shared-variable decomposition

For every admitted history,

\[
q(\omega)
=\sum_i w_i a_i+\sum_{h\in G}W_h c_h+\sum_i w_i e_i.
\]

**Proof.** Substitute the definition of \(x_i\) into the query and collect all terms multiplying the same group offset. Each row belongs to exactly one group, so its calibration contribution occurs exactly once. \(\square\)

This identity is why a calibration offset must be handled once per shared group. Replacing it with separately chosen row offsets changes the admitted histories.

### Lemma 2: the sparse-error support

Over \(\mathcal E_k\), the minimum and maximum of the error contribution are \(-R_k\) and \(R_k\), respectively.

**Proof.** For any admitted error vector, let \(S=\{i:e_i\neq0\}\). Then \(|S|\leq k\), and

\[
\left|\sum_iw_i e_i\right|
\leq\sum_{i\in S}|w_i|b_i
\leq R_k.
\]

Choose \(S^\star\) to contain up to \(k\) positive values with the largest \(r_i\). The vector

\[
e_i^+=
\begin{cases}
\operatorname{sgn}(w_i)b_i,&i\in S^\star,\\
0,&i\notin S^\star
\end{cases}
\]

belongs to \(\mathcal E_k\) and has weighted contribution \(R_k\). Its negative \(e^-=-e^+\) has contribution \(-R_k\). Positions with zero weight or zero bound need not be selected. Both endpoints are therefore attainable. \(\square\)

### Theorem: sharp extrema over the declared model

For every valid input, \(L=\min_{\omega\in\Omega}q(\omega)\) and \(U=\max_{\omega\in\Omega}q(\omega)\).

**Proof.** By Lemma 1, every glyph contribution is bounded by its corresponding one-coordinate extrema, and every group contribution is bounded by its corresponding group extrema. Lemma 2 bounds the remaining error contribution. Summing yields \(L\leq q(\omega)\leq U\) for every admitted history.

For attainment of \(L\), independently choose a glyph value attaining each \(\ell_i^A\), a calibration value attaining each \(\ell_h^C\), and the error vector \(e^-\) from Lemma 2. All sets are finite and nonempty, so these coordinate extrema exist. The Cartesian-product form of \(\Omega\) makes their combination admissible. Its query value equals \(L\). The analogous combination of maximizing glyphs, maximizing calibrations, and \(e^+\) attains \(U\). \(\square\)

The output interval has sharp endpoints. It does not imply that every rational number between those endpoints is attained by some history; the underlying state space is finite.

### Corollary: threshold classification

The decision policy is

\[
D=
\begin{cases}
\mathrm{TRUE},&L>\tau,\\
\mathrm{FALSE},&U\leq\tau,\\
\mathrm{UNRESOLVED},&L\leq\tau<U.
\end{cases}
\]

TRUE means that every admitted history satisfies the strict claim. FALSE means that none does. In the remaining case, the lower witness fails the claim and the upper witness satisfies it, so the state space contains conflicting answers.

Equality matters: \(U=\tau\) produces FALSE, whereas \(L=\tau<U\) produces UNRESOLVED. These are logical classifications over the admitted set, not probabilities, confidence levels, or statistical significance declarations.

### Corollary: cancellation of a shared offset

If \(W_h=0\), every admissible value of \(c_h\) has zero contribution to the query. Individual row values can remain uncertain even when this component of the query is fully determined.

This cancellation depends on the evidence supporting a shared offset. Assigning different groups to physically different calibration histories changes the coefficients and can remove the cancellation.

### Remark on continuously bounded errors

For this linear query, the same endpoint formula also bounds, and attains its extrema over, the larger error family

\[
\{e:|e_i|\leq b_i,\ \lVert e\rVert_0\leq k\},
\]

because the proof of Lemma 2 still applies and its endpoint vectors remain available. This observation is a consequence of the linear calculation. The implemented contract nevertheless declares the finite three-choice error model, and its finite state count refers only to that model. It does not count a continuous family or establish that physical errors satisfy the stated bounds.

## 4. Witness representation and independent checking

Each endpoint witness contains maps of chosen glyph values and calibration offsets, a sparse map of signed row errors, the resulting row values, and the query value.

An independent witness checker should verify all of the following:

1. Every glyph choice belongs to its row's normalized numerical alternative set.
2. Every group choice belongs to that group's alternative set, and every member row uses that same choice.
3. Every reported nonzero error equals one of the row's allowed signed bounds, and at most \(k\) row errors are nonzero.
4. Every reported row value equals its glyph choice plus group offset plus error.
5. Recomputing the rational weighted sum yields the claimed endpoint.

An extremal witness proves attainability. Two feasible endpoint examples, by themselves, do not prove that no other history lies outside their interval. Universal enclosure follows from the formula and proof above; independent exhaustive enumeration supplies an additional finite-instance implementation check.

## 5. Exact assignment count and computational cost

Let \(m=|\{i:b_i>0\}|\). There are

\[
N_E=\sum_{j=0}^{\min(k,m)}\binom{m}{j}2^j
\]

distinct error assignments: choose the \(j\) nonzero rows and then one of two signs for each. The full latent-assignment count is

\[
|\Omega|
=\left(\prod_i|A_i|\right)
\left(\prod_{h\in G}|C_h|\right)
\left(\sum_{j=0}^{\min(k,m)}\binom{m}{j}2^j\right).
\]

The count includes zero-weight rows and unused declared calibration groups. Their latent choices still distinguish histories even when the query, or all observed row values, stays the same. Distinct histories may map to the same numerical observation vector. Thus this is not a deduplicated count of observation vectors.

The engine does not enumerate these assignments to find extrema. It scans alternatives, aggregates group coefficients, and ranks row error contributions. As written, group aggregation rescans the rows for each group, so the arithmetic-operation count is

\[
O\!\left(n|G|+\sum_i|A_i|+\sum_h|C_h|+n\log n\right),
\]

apart from the small counting calculation and serialization. This is an operation count, not a constant-time bit-complexity claim. Rational numerators and denominators can grow, and arbitrary-precision arithmetic and output length depend on their bit sizes.

## 6. Assumptions and failure boundaries

### Coupled glyph or calibration restrictions

The attainment proof uses the ability to combine coordinate extrema. A constraint linking glyph choices, a restriction jointly relating offsets, or a dependence between an error pattern and a glyph interpretation can prevent that combination.

If the true feasible set is a subset of the declared Cartesian product, the computed interval can remain a conservative outer bound while ceasing to be sharp for the smaller set. Its endpoint witnesses may then be impossible under the omitted restriction. The engine does not accept such restrictions as additional input and does not claim sharpness for them.

The opposite inclusion failure is more dangerous. If an assumed shared offset is actually allowed to differ across periods, the declared model can exclude physically possible histories. The original finite example below demonstrates how this can turn an unsupported modeling assumption into an apparently certain claim.

### Nonlinear queries

The calculation applies to a fixed linear functional. Products, ratios, nonlinear thresholds on latent variables, and data-dependent transformations require a different derivation or exhaustive evaluation of an appropriate state space. For example, squaring a calibration value changes how its alternatives affect the query; it cannot in general be represented by multiplying the offset by a fixed group-weight sum. No nonlinear-query guarantee is supplied by this engine.

### Unknown or incorrect bounds

The glyph sets, calibration sets, row-error bounds, and error-count budget must cover the uncertainty being claimed. A missing glyph alternative, a calibration shift outside the declared choices, or more than \(k\) erroneous rows can invalidate physical coverage.

An unbounded nuisance variable with a nonzero coefficient can make a finite query bound impossible without additional constraints. A coefficient that cancels exactly can be an exception; unknown absolute calibration does not necessarily imply unknown contrasts. The implementation accepts only finite calibration choices and finite nonnegative error bounds, so it does not automatically establish either conclusion for an unbounded model.

### Unit and measurement assumptions

The additive representation presumes compatible numerical units and an additive calibration effect. Unit changes, scale-factor errors, nonlinear sensor response, date ambiguity, missing rows, and station changes are not represented merely by writing a source identifier or unit label. Some can be addressed by a richer explicitly justified model; they are not silently absorbed into this contract.

### Empty or contradictory scientific models

The accepted syntactic model is nonempty. Consequently, the engine cannot manufacture a universal result from an empty admitted set through vacuous truth. This does not establish that a scientist's assumptions are mutually plausible. If constructing the finite alternatives requires discarding contradictory evidence or treating a fallible historical total as infallible, that is a source-model problem outside the numerical verifier.

## 7. Source-model completeness is a separate scientific problem

The mathematical theorem has the form

\[
\forall\omega\in\Omega,\quad L\leq q(\omega)\leq U.
\]

To apply it to a real source, one must additionally justify that the relevant physical or recorded history is covered by the declared model, or by a separately justified larger family for which the same enclosure has been proved. One must also show that the encoded query is the scientific quantity actually intended.

That justification involves obligations absent from the input validator:

- Detecting all relevant rows and preserving row, column, date, and instrument associations.
- Including the true numerical interpretation in each applicable alternative set.
- Distinguishing uncertainty in the manuscript from uncertainty in the original measurement.
- Establishing which offsets were shared, which changed, and which bounds are defensible.
- Accounting for uncertainty in source arithmetic and metadata rather than imposing them as convenient hard constraints.
- Preserving extreme but possible observations instead of excluding them because they are atypical.
- Establishing that the sampled records support the proposed scientific inference beyond the records themselves.

A nonempty source identifier satisfies an interface requirement. It does not verify any of these obligations. A hash can show which model was used, but a reproducible wrong model remains wrong.

The initial discovery report proposed a historical climate-table benchmark based on a cited data record. A subsequent provenance check recorded metadata for Zenodo record 12784802 with restricted access and an empty file list. That correction is retained separately from the immutable search report. The real ten-page archive benchmark was not executed, and the present work supplies no evidence about the cost or reliability of constructing complete interpretation sets from those images.

Consequently, a correct finite engine does not establish a source-complete archival measurement instrument. Constructing and validating the admissible set may be the dominant cost and the central failure point.

## 8. Original finite construction and calibration counterexample

The original construction used eight rows in measurement units, with early-period bases

\[
(20.0,\;20.1,\;20.2,\;20.3)
\]

and late-period bases

\[
(21.0,\;21.1,\;21.2,\;21.3).
\]

Each row admits its base value or that value plus \(0.6\). Early weights are \(-1/4\), late weights are \(+1/4\), and the query is the difference of the period means. The shared calibration belongs to \(\{-0.4,0,+0.4\}\). Every error bound is \(0.1\), with at most one nonzero error. The claim is

\[
q>0.35=\frac{7}{20}.
\]

The base mean difference is \(1\). Glyph uncertainty contributes a range from \(-0.6\) to \(+0.6\), giving glyph-only endpoints \(2/5\) and \(8/5\). The common calibration has group-weight sum zero. Each row error contributes a radius

\[
\frac14\cdot\frac1{10}=\frac1{40}.
\]

Therefore

\[
L=\frac25-\frac1{40}=\frac38=0.375,
\qquad
U=\frac85+\frac1{40}=\frac{13}{8}=1.625.
\]

Because \(3/8>7/20\), the strict claim holds for every declared history, although all eight glyph choices remain unresolved. The number of histories is

\[
2^8\cdot3\cdot(1+8\cdot2)=13{,}056.
\]

One valid lower witness uses the higher glyph alternative for every early row, the lower alternative for every late row, zero common calibration, and a \(+0.1\) error in an early row. One valid upper witness reverses the glyph selections and puts a \(-0.1\) error in an early row. They attain the stated endpoints. Equivalent tie choices can yield different recorded witnesses with the same query value.

Now withdraw the shared-calibration assumption. Let early and late offsets be chosen separately from the same three-element set. Their group coefficients are \(-1\) and \(+1\), so calibration contributes any admitted difference between the two offsets, with endpoints \(-0.8\) and \(+0.8\). The bounds become

\[
L'=\frac38-\frac45=-\frac{17}{40}=-0.425,
\qquad
U'=\frac{13}{8}+\frac45=\frac{97}{40}=2.425.
\]

The number of histories becomes

\[
2^8\cdot3^2\cdot17=39{,}168.
\]

For an explicit counterexample to the original claim, take every early glyph at its higher alternative, every late glyph at its lower alternative, early offset \(+0.4\), late offset \(-0.4\), and a \(+0.1\) error in one early row. The early mean is \(21.175\), the late mean is \(20.75\), and the contrast is \(-0.425\). This admitted history fails \(q>0.35\). Reversing the choices yields a history attaining \(2.425\), which satisfies the claim.

The resulting UNRESOLVED classification is the required behavior. The original positive result depends on substantive evidence of shared calibration. Neither an agent's confidence nor the successful arithmetic establishes that evidence.

Both original state spaces were exhaustively checked in the exploratory prototype. They are research-authored constructions, not historical measurements, samples from a natural population, or demonstrations of a new inference method.

## 9. Construction, selection, and confirmation design

### Discovery and selection

The expert discovery arm recorded six web search queries and four candidate records. It retained the archival direction conditionally while identifying substantial prior art and rejecting the other broad headlines. A coordinating follow-up then selected this direction for a falsifying construction. The protocol records follow-up searches separately from the independent arm.

The construction is therefore a post-selection refinement. It is not an independent demonstration that the selected need was discovered more effectively than competing needs. The exact finite example was developed during this exploratory stage and cannot be reclassified as a held-out confirmation result.

### Freeze history

Three implementation hashes are retained:

| Stage | SHA-256 | Role |
|---|---|---|
| Initial exploratory implementation | 0cea250d7ad8299edcfea7c37432e7b7dbc7f2c8f597b50b926d5ecfe0326c69 | Original exact engine |
| Required path and SPDX packaging | ae357866f167cf61eacb86681f48dcf99f783641699ff3a46cf6fa3912da2336 | Same parsed program, plus license comment |
| Final annotation and local-function cleanup | dce5ac65b3c1cdaf625a2f9a0ee554df88d5d2853454ebad5d2cfc00265794db | Primary pre-confirmation implementation |

The final cleanup added type annotations and an internal row type and replaced a local encoding lambda with a named function. It did not change the numerical method or input policy. On the unchanged hand-authored exploratory cases, all valid outputs and invalid-input refusal messages matched the original implementation.

The exploratory engine check used one manually authored three-row case with unequal weights and an error budget of two. Its 608 latent histories were enumerated, yielding exact bounds \([-137/10,139/20]\). Additional hand-authored variations covered threshold equality, zero budgets, zero weights, and zero error bounds, as well as ten invalid-input classes and CLI behavior. These are development checks, not the primary confirmation sample.

Ruff and strict mypy passed on the final implementation. The attempted Black invocation was blocked by an installed dependency problem; no formatting-check pass is claimed. These checks concern implementation quality and interface discipline, not scientific source completeness or discovery novelty.

### Planned primary and successor cases

The frozen construction protocol specifies:

| Component | Planned quantity | Seed recorded in protocol |
|---|---:|---:|
| Primary confirmation cases | 36 | 27102731 |
| Successor cases | 12 | 27102779 |

The specified order is to implement and hash the core before generating fresh cases and comparing it with independent implementations. The engine author read the protocol, including its seeds, but recorded that no confirmation seed was used and no held-out cases or outputs were inspected. The separation is a development holdout, not cryptographic concealment of the generating procedure.

The primary acceptance criterion is equality of exact endpoints with independent exhaustive enumeration on every valid case, valid endpoint witnesses, and correct refusal of malformed or unsupported cases. Errors must be retained; corrections must receive separate versions and hashes rather than replacing the original evidence. Primary policy must not be tuned against confirmation outcomes.

The specified controls are:

1. An independently implemented exhaustive possible-world oracle.
2. A competent conventional analytic implementation.
3. Bounds that decorrelate cell offsets.
4. A single preferred transcription.
5. An ordinary library containing identical inherited content.

The first two are strong correctness and redundancy controls. An existing analytic method that provides the same result is not a defeated comparator. The decorrelated control changes the modeled dependence and can be unnecessarily wide. The preferred-transcription control chooses one history and does not, by that act, establish a universal claim. An apparent advantage over either weaker control cannot establish a novel scientific method.

Independent code is useful for detecting implementation errors, but a separately written oracle is not automatically conceptually independent. Shared misunderstanding of the contract remains possible. Exact enumeration must evaluate the same query over the same admissible histories using exact arithmetic; otherwise agreement or disagreement lacks the intended interpretation.

### Limits of confirmation

Even perfect agreement on the planned cases would establish a bounded implementation result supported by a general mathematical proof. It would not establish representativeness of the authored cases, performance on real scans, source completeness, competitive acquisition cost, willingness to pay, or broad scientific novelty.

The cases are authored within the study and selected for a known contract. Their fixed seeds do not turn them into a random sample of historical archives or productive needs. No population accuracy estimate, confidence interval for market utility, or error rate for real handwriting follows from their counts.

Choosing a query after observing available data does not invalidate the algebra for that fixed query. It can, however, invalidate claims about a predeclared task distribution, useful-query yield, or prospective utility. Those quantities require their own selection rules and accounting, including the cost of establishing the admissible source model.

## 10. Discovery novelty, E versus U, and successor inheritance

The endpoints follow from established mathematical operations. Certain-answer systems already reason about what holds across alternative data interpretations, and existing uncertainty-database work explicitly treats global conditions and symbolic alternatives [1]. This construction does not establish a new semantics or a new optimization principle.

The frozen protocol accordingly withholds flagship status unless a substantive capability or effort advantage beyond strong existing methods is demonstrated. A convenient interface, a hash, agent-generated code, or successful exact arithmetic does not satisfy that criterion by itself. A prospective contribution would need evidence such as a useful scientific question that existing competent workflows cannot answer under the same obligations, or a measured reduction in total expert work to construct and validate the model. Neither is established here.

The construction also does not measure the effect of the expert discovery protocol E relative to the baseline protocol U. It contains no randomized repeated comparison of discovery runs, no human discovery trial, and no calibrated estimate of superiority over human foresight. Assessing an engine selected from E's output measures that selected artifact's behavior, not the causal effect of E on discovery quality.

Successor use must be interpreted just as carefully. Transferring the code, input schema, proof, assumptions, tests, and counterexamples creates an inspectable technical artifact that another agent can execute or extend. Success on new instances of the same contract can demonstrate artifact portability and reuse. It does not show that a model's parameters changed or that trained discovery competence improved.

An identical-content ordinary-library control is relevant because it distinguishes access to the inherited information from claims about a special inheritance mechanism. Any stronger competence claim would require an independently specified task distribution and a design that measures the claimed learning effect. The present method makes no such claim.

## 11. Reproduction records and references

The following study records support this methods account:

- **study/src/claim_engine.py** — final implementation identified by the hash above.
- **study/config/construction_protocol.json** — selection, scope, planned counts, controls, freeze order, acceptance rule, and novelty falsifiers.
- **expert_discovery.md** — immutable six-query discovery report and prior-art assessment.
- **expert_discovery_verify.py** and **expert_discovery_exact_result.json** — original finite construction and its endpoint witnesses.
- **expert_engine_exploratory_notes.md** — successive implementation hashes, development checks, tool-check outcomes, and source-access correction.
- **study/provenance/zenodo_metadata.json** — recorded restricted-access metadata and empty file list for the proposed archive benchmark.

No confirmation outcome is asserted in this document. Confirmation results, including failures, must be reported separately against the identified final source hash.

**[1]** Su Feng, Aaron Huber, Boris Glavic, and Oliver Kennedy. *Efficient Uncertainty Tracking for Complex Queries with Attribute-level Bounds (extended version).* Primary preprint, 2021. [arXiv:2102.11796](https://arxiv.org/abs/2102.11796). This is a verified prior-art reference from the frozen discovery search, not evidence of a new result in the present construction.
