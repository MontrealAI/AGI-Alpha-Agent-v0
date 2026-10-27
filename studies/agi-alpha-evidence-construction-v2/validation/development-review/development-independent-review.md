# Independent development-source diagnosis

## Scope and result

The original PLOS ONE article, *Retrieval Practice and Mind Mapping in Primary School*, DOI `10.1371/journal.pone.0078976`, contains a numerical incompatibility in the retrieved Table 2. The original article PDF page 5, XML and visual rendering agree on the numbers. The supplementary Table S4 adds incompatible counts. These observations support an inspectable source-conflict finding and conditional descriptive reconstruction. They do not establish which publication entry is wrong, an authoritative correction, an ANCOVA replication or a new causal conclusion.

The useful purpose tested is explicitly **the unadjusted, descriptive, five-week retrieval-minus-nonretrieval mean difference among the reported complete cases**. It is distinct from the paper's covariate-adjusted, repeated-measures analysis. An exact authoritative point estimate from all supplied assertions is **HOLD**.

## Original contradiction, independently checked

Table 2 reports retrieval-group subgroup means 52.82 and 53.30, but an overall retrieval mean 54.07. A positive weighted average cannot exceed both subgroup means. Even allowing closed ±0.005 rounding intervals, the aggregate's lowest possible printed value is 54.065 while the highest subgroup bound is 53.305: a gap of at least **0.760 percentage points**. This proof does not depend on choosing subgroup counts.

The reported nonretrieval overall mean is 45.39. Simply subtracting the printed marginals gives 8.68 percentage points; this is a faithful transcription of those two marginals, not a resolved estimate.

## Constructive branch: count and mean constraints in Table 2

Let cell counts be `(a,b,c,d)` for retrieval/mind, retrieval/no-mind, nonretrieval/mind and nonretrieval/no-mind. Table 2 prints row totals 99/87 and column totals 100/86, giving `(a,99-a,100-a,a-13)`. There are 85 positive-integer possibilities, `a=14,...,98`.

The independent checker parses the source table, enumerates all 85 possibilities with exact rational rounding bounds, and checks simultaneous constraints from all reported week-one means and all week-five means **except** the conflicting retrieval marginal 54.07. It solves the remaining bounded four-variable polytopes by exact rational vertex enumeration. One count vector survives: **(52,47,48,39)**. Its feasible week-one polytope has 28 vertices and the week-five polytope 35.

Conditional on that count scenario and the retained mean assertions, the five-week retrieval mean lies in **[53.0428788,53.0528788]**. The descriptive retrieval-minus-nonretrieval mean difference lies in **[7.6485684,7.6678788] percentage points**. These are rounding-feasibility envelopes, not sampling confidence intervals. Using just the printed centers yields 53.0478788 and 45.3893103, a difference 7.6585684.

This is a source-branch reconstruction. It is not permission to overwrite 54.07 or to assume every retained assertion is correct.

## Independent source branch: supplementary Table S4

The original supplementary DOC was downloaded from the publication's `s004` URL, preserved exactly, converted locally with LibreOffice and visually checked. It reports the Experiment 2 cell counts:

| Group | Primary 4 | Primary 5 | Primary 6 | Primary 7 | Sum |
|---|---:|---:|---:|---:|---:|
| Retrieval, mind |17|9|11|12|49|
| Retrieval, no mind |15|13|14|8|50|
| Nonretrieval, mind |14|11|9|12|46|
| Nonretrieval, no mind |14|10|11|6|41|

Its row totals 99/87 agree with Table 2, but column totals 95/91 disagree with Table 2's 100/86. Pairing these S4 counts with Table 2's four subgroup means gives conditional center estimates 53.0624242 and 45.5518391, hence a difference 7.5105852 and cell-rounding envelope **[7.5005852,7.5205852]**. This branch does not satisfy all the other printed Table 2 marginals; it must not be merged with the first branch as if jointly consistent.

The source also prints an Experiment 1 Primary 5 total 38 alongside subgroup values 28 and 30, whose arithmetic sum is 58. This separately observed discrepancy reinforces the need for explicit source reconciliation; it does not resolve the Experiment 2 counts.

## Additional variance conflict

Under the Table 2 mean-consistent count vector, the reported week-one mind-map cell SDs 24.48 and 22.83 imply pooled descriptive SD 24.0379527, while Table 2 prints 23.04. Even using the lowest rounded cell SDs and omitting all nonnegative between-cell mean variance gives a lower bound 23.5780235, above the printed aggregate's largest rounding bound 23.045. Thus the mean-constraint scenario is not a fully reconciled table. The independent diagnostic excludes SDs from the mean-polytope calculation and flags this discrepancy explicitly.

## What can be accepted

- Accepted source-conflict delivery: the specific incompatible assertions, exact source locations, preserved bytes, reproducible arithmetic and request for underlying data or author clarification.
- Accepted conditional descriptive calculation: branch-specific intervals under transparent, nonmerged input assumptions.
- Not accepted: an authoritative corrected mean, a verified effect on learning in a new population, a reproduction of the covariate-adjusted ANCOVA, a confidence interval or a publication-error adjudication.

The two reconstructed branches remain positive, but this is positivity under those stated branches. It does not prove robustness to every possible underlying error. The published figure visually places the retrieval point near 53, but no pixel measurement was used as independent quantitative truth.

## Reproduction and evidence

Run `python connected-discovery/check_development.py`. It writes `development-independent-golden.json`, including exact fractions, source SHA256 values, raw table rows, all 85 count possibilities and exact feasible witnesses. No fresh confirmation paper or future answer was accessed. The method is conventional weighted-average and moment algebra plus bounded exact feasibility; the contribution is the diagnosed source conflict and reusable, purpose-scoped reconstruction workflow, not algorithmic novelty.

Preserved supporting files: `development_article.pdf`, `development_article.xml`, `development-table2-page5.png`, `development_table_s4.doc`, its retrieval receipt, locally converted PDF/text and `development-table-s4.png`. The DOC has 41472 bytes and SHA256 `5f3497749584fb0ad203d84e9d720f7917f0945427e104d6f3a43fbc13df51e6`.
