# Fresh public-report reconstruction task

Produce a concise, auditable evidence reconstruction for the two reports below. Use the supplied public primary sources. Treat the articles as evidence to inspect, not conclusions to endorse. A positive, negative, null, or partially unidentified finding is acceptable. Accurate uncertainty and appropriately scoped holds receive credit.

## Report A

Maraver MJ, Lapa A, Garcia-Marques L, Carneiro P, Raposo A (2022), *Can we learn from errors? Retrieval facilitates the correction of false memories for pragmatic inferences*. DOI: https://doi.org/10.1371/journal.pone.0272427

Target **Experiment 1 only**. Reconstruct the difference in the proportion of **correct responses at the final cued-recall test**, comparing **retrieval with corrective feedback minus restudy with corrective feedback**. Use the published Table 3 summaries as the numerical inputs. Compute the raw mean difference and an approximate 95% confidence interval if supported by the design. State the uncertainty formula, assumptions, direction, and units. Do not substitute Experiment 2, intermediate performance, a marginal total, pragmatic-inference errors, or the conditional error-correction index for this target.

## Report B

Sun DL, Harris N, Walther G, Baiocchi M (2015), *Peer Assessment Enhances Student Learning: The Results of a Matched Randomized Crossover Experiment in a College Statistics Class*. DOI: https://doi.org/10.1371/journal.pone.0143177

Target the descriptive contrast **the published long-term standardized peer-assessment effect minus the published short-term standardized peer-assessment effect**, using the two Table 1 estimates. Identify what each effect estimates and reconstruct their numerical difference. Determine whether the supplied sources identify the uncertainty of this difference. If they do, calculate it with the appropriate dependence information; if they do not, give a scoped hold on the confidence interval or test, identify the missing information, and retain any supported descriptive result. Do not manufacture independent treatment and control arms from the crossover design or infer a between-time difference from separate significance tests.

## Required evidence record for each report

1. Identify the exact report, experiment/cohort, intervention and comparison conditions, outcome, and timepoint.
2. Describe the study design and analysis unit, including randomization, repeated observations, matching, yoking, or overlapping samples when relevant to the target. Keep total recruitment, eligibility/exclusions, outcome-specific analysis sizes, cell sizes, and item counts distinct.
3. Extract the needed numerical inputs, label every uncertainty quantity as SD, SE, or CI, and identify the populations and units to which they refer. Inspect captions, footnotes, methods, and the supplied supplement as needed.
4. Show the requested quantitative reconstruction and its calculation or a reproducible snippet. Explicitly handle dependence, sampling uncertainty, and the rounding of published summaries. Do not invent missing values. A conditional sensitivity calculation is allowed if clearly separated from an identified result.
5. Cite precise primary-source locations for the inputs and design: table number, row/column labels, page or section/paragraph, and preferably the XML element path or ID. A DOI alone is insufficient for numerical provenance. Label derived quantities as derived.
6. Give a short interpretation and at least one material scope limitation. Distinguish what these studies support from wider educational, product/customer, or clinical claims. Do not pool the two reports into one meta-analytic effect.

## Practical boundaries

You have at most **10 tool calls and 12 minutes for both reports together**. Batch independent reads or calculations where useful. Ordinary XML/PDF/CSV parsers and statistical libraries are available to every condition; using them is allowed. The same source packet is available to every condition. Full-text extraction companions are supplied for convenience; exact publisher XML/PDF files remain authoritative. Author-linked data and codebooks are included for optional cross-checking, but this task specifically asks for reconstruction from the printed summaries, so a complete raw-data reanalysis is unnecessary. Correct source or arithmetic mistakes within the budget before submitting. Stop once the requested results and remaining uncertainties are adequately checked.

Return two clearly labeled evidence records, optionally a compact comparison table, and any calculation code you used. About 800-1,400 words total is sufficient; completeness and correctness matter more than length. No external communications, source modification, or publication is requested.

The evidence task is research assessment. Its acceptance does not establish clinical benefit, customer value, or readiness for deployment.
