# Mathematical prose and figure review

Reviewed the pre-integration `publication/paper.md`, the mathematical figure source and images, `fresh_conventional/verify_weight.py`, the independent geometric checker, and its PASS receipt. The new full Appendix fragment is `final_proof_fragment.md`. I did not edit `paper.md` or the figure source.

## Required corrections when promoting the stronger certificate

1. State the main theorem as `h >= J = 17902560/18258529`, not `h > J`. The retained polynomial proof separately establishes `h > I`, with `I = 1891871140656049/1929687500000000`. The exact difference `J-I` is about 0.0001011023264891.
2. The new main witness is the linear interpolant W normalized by M=18258529/18240. Its normalized integral is J. Its integer knot values, total variation and integral are exact. Do not relabel the plotted degree-20 polynomial as this interpolant: change the plotted object or retain an explicit secondary-witness caption.
3. The main certificate checks cardinalities2–20 by exact line arrangements, then handles21 and above by the variation estimate. The existing78 Bernstein patches,2–40/41+ split, degree20, and midpoint-average identity describe the valid secondary polynomial proof.
4. The cell-integral transfer proves the main bound for every admissible n directly. No small-n table or positivity refinement in1/n² is necessary for the new main theorem.
5. The4.61/4.08-second wrapper figures and512-class/four-midpoint-length confirmations refer to the previous polynomial package unless the wrapper is separately extended and rerun. Keep their provenance distinct from the independent geometric audit of the conventional weight.
6. The fresh workstream's original convenient scaleT=2003/2 gives1963/2003. The sharper J is normalization by its already computed exact maximum. This improvement needs no new search, altered knots or changed requirements.

## Source correction

`publication/references.bib` currently names “Poon, Calvin” for the2009 paper. The official Macquarie record explicitly names Gerry Myerson, Jacky Poon and Jamie Simpson:

https://researchers.mq.edu.au/en/publications/incongruent-restricted-disjoint-covering-systems/

Use “Poon, Jacky”; using “Simpson, Jamie” also matches that primary institutional metadata exactly. The DOI, journal, volume, issue and pages match the existing entry.

## Figure observations

The old mathematical figures are consistent with the older polynomial, and the coefficient file already includes its2499/2500 scale. They are not plots of W/M. On the bound comparison, the0.98 threshold and certified endpoint are visually almost coincident at the full prior-to-new scale. A small inset or explicit numeric J−0.98 label would make the new margin legible without enlarging it deceptively. A main-witness plot should have normalized ordinate W(x)/M, integral J, and visible linear knots. The raw integer W is around1858 at its midpoint; a normalized plot is around1.856, so copying the old ordinate scale is reasonable only after dividing by M.

## Proof audit conclusions

No additional mathematical defect was found in the retained polynomial prose examined. Its midpoint recurrence, two-square parameterization and analytic-tail statements are consistent with the stated independent checks. For the promoted construction, the all-boundaries arrangement proof, variation including endpoint jumps, exact transfer to finite intervals, and non-strict main inequality are explicitly included in the new fragment. Same-session independent verification remains distinct from external peer review or formal proof-assistant verification.
