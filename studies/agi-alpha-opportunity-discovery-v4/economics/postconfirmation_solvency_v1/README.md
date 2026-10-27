# Adverse contractual-solvency audit: completed result

This calculation supplements the original frozen results. It is a post-confirmation adverse audit, not a new commercial confirmation. Actual collections and earned revenue remain USD0; actual complete research cost is unknown.

Protocol/code/input freeze SHA256: `847a5abe0b7efedc5e0a9a84c9e9477ada4adeb8a6c3308f9382f5523b802f78`.

Result SHA256: `70423143134e3f7f4eb87175283daff9600b83545b2adece0fc440c78a75293f`.

The original 3,520 arm-horizon rows contain 1,889 selected financeable commitments. If all committed precollection work is incurred, the development milestone is then rejected, every advance must be refunded, and no final collection finances work, 114 commitments require more opening cash than their unchanged seed. Eleven of these commitments were later cancelled after withdrawal in the original realization; these are conditional exposures, not observed insolvencies.

Payment-on-acceptance arms have zero additional exposure: expert 0/772; retained 0/127. Commission arms are shown below. Each cell reports exposed/selected original commitments. The scenarios reuse declared simulation seeds and are not independent market populations.

| Scenario | Seed USD | Expert commission exposed/selected | Expert max shortfall USD | Retained commission exposed/selected | Retained max shortfall USD |
|---|---:|---:|---:|---:|---:|
| central_assumptions | 6,000 | 2/75 | 559.57 | 15/38 | 739.85 |
| low_opening_cash | 1,500 | 50/75 | 3,311.46 | 6/6 | 5,222.25 |
| high_opening_cash | 12,000 | 0/75 | 0.00 | 0/38 | 0.00 |
| high_common_cost | 6,000 | 2/75 | 559.57 | 0/0 | 0.00 |
| negative_transfer | 6,000 | 2/75 | 559.57 | 5/14 | 748.15 |
| efficient_incumbent | 6,000 | 0/60 | 0.00 | 0/4 | 0.00 |
| low_demand | 6,000 | 0/62 | 0.00 | 0/9 | 0.00 |
| full_refund_contract | 6,000 | 0/75 | 0.00 | 0/30 | 0.00 |
| payment_and_withdrawal_stress | 6,000 | 2/74 | 559.57 | 15/33 | 739.85 |
| ordinary_defaults_progress | 6,000 | 2/75 | 559.57 | 11/22 | 661.72 |
| quality_obsolescence | 6,000 | 2/75 | 559.57 | 0/0 | 0.00 |

Across the declared scenarios, expert commission exposure is 62/796, maximum USD3,311.46; retained commission exposure is 52/194, maximum USD5,222.25. This does not supply a rejection probability or revised expected profit.

The independent input generator matched all 36 buyer objects retained in the original cash examples. Reconstructed precollection costs reconcile to the original partial-refund cash formula within USD1.0688e-12. The audit imports no original planner, job-cost or realization functions. Original freeze hashes are checked before calculation. No original plan, source program, result or policy was changed.

Other nonperformance, disputed/partial milestone acceptance, legal enforceability, strategic default, payment delays, insurance and credit are unmodeled. The full committed-work assumption is a conservative adverse envelope; it does not infer actual costs or final outcomes. See `PROTOCOL.md`, `audit.py`, `FREEZE.json` and `RESULTS.json`.
