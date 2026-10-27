# Economic results audit — revision 3

**Status: PASS**. Audited 2026-10-27T14:23:48.163714+00:00.

Read-only review of 18,432 rows (12 scenarios × 6 policies × 256 seeds, 11000–11255). The engine was neither imported nor rerun. This output-consistency audit was built by the capacity-scheduler implementation lane. A separate technical agent independently reviewed the resource source and fixtures; neither review is external institutional certification.

## Accounting, resources and provenance

The audit executed 2,035,802 checks and recorded 0 discrepancies. It reconciles financial identities, horizon capacity and backlog, both productivity denominators, aggregate means/Monte Carlo mean intervals, exact shared/library scalar equivalence, daily exported capacity/readiness, the detailed exemplar ledger/tasks, and frozen source/input hashes. The JSON receipt retains per-family counts, maximum numerical residuals, exact hashes, and all discrepancies.

Revision 3 follows the disclosed post-review capacity/readiness correctness repair. Earlier editions remain historical evidence; this audit does not recast the repaired policy as unchanged preregistration. Cash commitments are retained once; preparation is conserved across days and readiness follows completion. End-of-day readiness can coexist with zero remaining production capacity.

## Base-case distributions

Amounts below are simulated USD means; counts refer to the 256 histories for each policy.

| Policy | Mean surplus | Mean increment vs Beta | Positive paired increments | Loss histories | Mean orders | Mean full-capacity units/hour |
|---|---:|---:|---:|---:|---:|---:|
| competent_beta | 51,423.19 | 0.00 | 0 | 0 | 209.96 | 2.170 |
| private_work | 51,263.20 | -160.00 | 0 | 0 | 209.96 | 2.170 |
| shared_work | 51,362.20 | -61.00 | 0 | 0 | 209.96 | 2.170 |
| shared_gym | 51,337.19 | -86.00 | 0 | 0 | 209.96 | 2.170 |
| ordinary_library | 51,362.20 | -61.00 | 0 | 0 | 209.96 | 2.170 |
| selective | 51,415.19 | -8.00 | 0 | 0 | 209.96 | 2.170 |

Base-case financial components (simulated USD means):

| Policy | Collections | A costs | B costs | C costs | Unpaid obligations | Available funds |
|---|---:|---:|---:|---:|---:|---:|
| competent_beta | 59,021.02 | 7,333.56 | 0.00 | 264.26 | 196.38 | 53,823.19 |
| private_work | 59,021.02 | 7,333.56 | 160.00 | 264.26 | 196.38 | 53,663.20 |
| shared_work | 59,021.02 | 7,333.56 | 61.00 | 264.26 | 196.38 | 53,762.20 |
| shared_gym | 59,021.02 | 7,333.56 | 61.00 | 289.26 | 196.38 | 53,737.19 |
| ordinary_library | 59,021.02 | 7,333.56 | 61.00 | 264.26 | 196.38 | 53,762.20 |
| selective | 59,021.02 | 7,333.56 | 8.00 | 264.26 | 196.38 | 53,815.19 |

Available funds subtract outstanding obligations and the reserve from cash. The audit reconciles cash separately; seed capital and unpaid future invoices are excluded from collections. The full receipt includes cash, all cost buckets, refunds, obligations and available-funds distributions for every scenario/policy.

## Stress and readiness findings

| Scenario | Beta mean surplus | Selective mean increment | Selective committed modes | Loss histories, all policies | Positive increments, all policies |
|---|---:|---:|---|---:|---:|
| base | 51,423.19 | -8.00 | beta:256 | 0 | 0 |
| low_demand | 3,537.41 | -8.00 | beta:256 | 45 | 0 |
| low_wtp | -874.26 | -8.00 | beta:256 | 1536 | 0 |
| high_failures | 29,498.65 | -8.00 | beta:256 | 0 | 0 |
| high_integration | 51,423.19 | -8.00 | beta:256 | 0 | 0 |
| poor_transfer | 51,423.19 | -8.00 | beta:256 | 0 | 0 |
| capacity_pressure | 205,413.76 | -8.00 | beta:256 | 0 | 0 |
| regime_shift | 51,423.19 | -8.00 | beta:256 | 0 | 0 |
| slow_collections | 23,184.73 | -8.00 | beta:256 | 0 | 0 |
| rapid_frontier_progress | 51,466.86 | -8.00 | beta:256 | 0 | 0 |
| high_compute_price | 51,422.66 | -8.00 | beta:256 | 0 | 0 |
| growth_financed_by_surplus | 296,665.43 | -8.00 | beta:256 | 0 | 0 |

Growth-scenario terminal worker counts (worker count: histories):

- **competent_beta:** 0.0:174, 1.0:6, 2.0:76.
- **private_work:** 0.0:180, 1.0:5, 2.0:71.
- **shared_work:** 0.0:178, 1.0:3, 2.0:75.
- **shared_gym:** 0.0:179, 1.0:4, 2.0:73.
- **ordinary_library:** 0.0:178, 1.0:3, 2.0:75.
- **selective:** 0.0:174, 1.0:6, 2.0:76.

Resource-sensitive output diagnostics (means; units are the protocol's assumed 1/3/6 weights):

| Scenario / policy | Orders | Weighted output | Units / total capacity hour | Mean extra workers | Increment vs Beta |
|---|---:|---:|---:|---:|---:|
| capacity_pressure / competent_beta | 868.97 | 2044.33 | 68.1443 | 0.0000 | 0.00 |
| capacity_pressure / private_work | 848.97 | 1997.61 | 66.5871 | 0.0000 | -5,256.86 |
| capacity_pressure / shared_work | 863.98 | 2032.16 | 67.7387 | 0.0000 | -1,377.68 |
| capacity_pressure / shared_gym | 856.59 | 2015.59 | 67.1865 | 0.0000 | -3,214.57 |
| capacity_pressure / selective | 868.97 | 2044.33 | 68.1443 | 0.0000 | -8.00 |
| growth_financed_by_surplus / competent_beta | 1313.35 | 2954.32 | 63.3838 | 0.6172 | 0.00 |
| growth_financed_by_surplus / private_work | 1235.43 | 2782.95 | 63.4435 | 0.5742 | -18,098.35 |
| growth_financed_by_surplus / shared_work | 1289.46 | 2898.38 | 63.3643 | 0.5977 | -5,680.67 |
| growth_financed_by_surplus / shared_gym | 1263.57 | 2843.84 | 63.4587 | 0.5859 | -11,531.04 |
| growth_financed_by_surplus / selective | 1313.35 | 2954.32 | 63.3838 | 0.6172 | -8.00 |

The growth scenario has policy-dependent capacity purchases. Its mean of within-history output/capacity ratios can rise while total output and surplus fall; compare these quantities jointly. The historical processing-only ratio excludes preparation and idle capacity, so it remains a separately labeled diagnostic.

Across all recorded policy histories: 298,415 failed package deliveries, 5,412 failed completed prototypes, and 0 histories ending with unfinished preparation. These totals count matched policy histories separately; they are not distinct real customers or experiments.

Capacity-pressure first day with any ready recipient (zero-based; `None` means absent throughout):

- **competent_beta:** audit=0, screen=0, select=1; mean consumed preparation 2700.00 seconds; mean horizon backlog 0.00 seconds.
- **private_work:** audit=0, screen=2, select=2; mean consumed preparation 5100.00 seconds; mean horizon backlog 0.00 seconds.
- **shared_work:** audit=0, screen=1, select=1; mean consumed preparation 3300.00 seconds; mean horizon backlog 0.00 seconds.
- **shared_gym:** audit=0, screen=1, select=2; mean consumed preparation 4200.00 seconds; mean horizon backlog 0.00 seconds.
- **ordinary_library:** audit=0, screen=1, select=1; mean consumed preparation 3300.00 seconds; mean horizon backlog 0.00 seconds.
- **selective:** audit=0, screen=0, select=1; mean consumed preparation 2700.00 seconds; mean horizon backlog 0.00 seconds.

## Limits

- Market demand, prices, service acceptance, model workload, preparation time and complete cash costs remain assumed/simulated.
- Scalar conservation covers every history; daily conservation covers exported capacity-pressure means and the full base/selective exemplar. Individual daily histories for every seed are not stored.
- Readiness is end-of-day availability. It does not imply that an offer was available before preparation or had remaining same-day production capacity.
- File consistency cannot by itself establish absence of information leakage; the separate source review and controlled prefix/sentinel regressions cover that concern.
- Monte Carlo intervals describe simulation variation, not market evidence. No live customer revenue or external certification is established.
