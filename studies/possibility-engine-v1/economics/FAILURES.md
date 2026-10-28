# Preserved development failures

1. First execution failed before any simulated world: an extra closing parenthesis in the Gumbel-choice
   expression caused a Python SyntaxError on model.py line 140. Corrected the expression; no economic
   parameter, acceptance condition, seed or output was changed by this syntax correction.

2. Independent pre-freeze accounting review found an unrealized25%late-payment penalty in buyer utility. Removed it: payoff now uses principal recovery and relationship value only. All prior outputs/source remain archive-v1.
3. Independent review found support/refund cash postings bypassed the finite credit helper. Factored ensure_cash and applied it before every unrestricted liability settlement.
4. Initial12-policy grid was overpriced relative to its own self/free alternatives. One bounded redesign added$3k/$4.5k/$6k prices;24entries(20unique) were compared on the same12development seeds. No demand or quality assumptions were made more favorable.
5. Strongest-free alternative initially still had a longer modeled delivery delay. Corrected to equal delay before final development/freeze; retained interim outputs under archive-v2-pre-free-delay.
6. Conventional economic parity is assumed by identical inputs and delivery costs, not a measured empirical cost advantage. Labels and protocol state this explicitly.

7. Strict static typing initially found10annotation/inference errors. Added explicit collection/result types, a typed max-key lambda and float return conversion. Ruff and strict mypy then passed; no economic parameter changed.
