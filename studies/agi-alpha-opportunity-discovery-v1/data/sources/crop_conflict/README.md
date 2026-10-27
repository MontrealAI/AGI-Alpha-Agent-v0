# Preserved real semantic conflict case

Source: Anochirim and collaborators,
https://github.com/maxanochirim/network-meta-analysis-using-crop.yield.data,
commit `623148fa24df4eef59c65bd6eef5fb53b6a433bb`. The preserved source
assets retain **AGPL-3.0** (`LICENSE.md`). Receipts bind each original byte.

This packet preserves a public notebook and source notes as an input to a
semantic refusal check. It does not execute a crop-yield analysis, redistribute
the underlying workbook in this study, or resolve scientific discrepancies.

Observed source conditions that require qualification:

- The narrative describes crop yield in kg/ha, and later calls the pairwise
  outcomes mean differences; the executable `pairwise` call sets `sm="SMD"`.
  A dimensionless standardized effect is not a yield gain in kg/ha. An
  instrument must not satisfy a physical-yield request by silently relabeling
  standardized effects.
- The inclusion narrative reports 3733 yield data, while the pairwise
  description reports 3939 rows and 3938 two-arm studies, and another section
  reports 3732 comparisons. The exact dataset version and unit of analysis
  must be reconciled before accepting count-sensitive results.
- The visible rankogram narrative says control has 100% estimated probability
  of the best value. This cannot be interpreted as an agronomic recommendation
  without checking effect direction, ranking settings, applicability and the
  original purpose.

The first two discrepancies are supplied observed source evidence. They are
not researcher-injected false statements. They support refusing an unjustified
physical or count-sensitive claim. They do not prove that every original
analysis is invalid, or that the source authors made the same interpretation
the new study tests.

These materials are a negative-control fixture. The new instrument must
report missing semantic qualification and the evidence needed to resolve it,
rather than manufacture a favorable numerical result.
