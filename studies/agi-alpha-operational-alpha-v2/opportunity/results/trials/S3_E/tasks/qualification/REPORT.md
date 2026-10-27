# Scientific-model qualification report

## Delivered result

`submission.py` implements `build_packet(source_root, requests_path)` and the requested command-line interface. `packet.json` contains the four missions in request order, their source and request identities, and the required empty authority and false biological-validation fields. `test_scientific.py` supplies 13 additional tests; the unchanged public interface test also passes.

The observed results for the supplied request are:

| Mission | Qualification | Numerical result |
|---|---|---|
| H4 equilibrium | Conditional prediction of the supplied nominal model | Mean acetylation **0.37642255826743765**; the complete 16-species distribution is in the packet. |
| Unsupported physical clock | Independent clock calibration is needed | At requested time 1.25, scales 0.5 and 3.0 give a maximum species-abundance difference of **0.14331681938560425**. Their recomputed equilibria differ by at most **1.1102230246251565e-16**. |
| Hypothetical calibration | Conditional on `HYPOTHETICAL-CLOCK-01`, explicitly `assumed` | Model spectral relaxation scale **1.281539318178634**; conversion interval [0.4, 1.6] normalized units per minute gives **[0.8009620738616463, 3.2038482954465852] minutes**. |
| New Boehm mission | Fresh dynamic qualification required | **48** measurement rows, **16** finite observation times, **3** observables. The H4 equilibrium witness is inapplicable as an inherited approval. |

These values are constructed from the supplied package and requests, not new physical measurements. Source evidence is identified below and bound completely in `packet.json`.

## Construction and source evidence

For H4, the code reads `sources/h4/model.xml` and the nominal values in `sources/h4/parameters.tsv`. The XML species have a unit compartment, total initial mass one, and all initial mass in `x_0ac`. Each of the 64 explicit irreversible reactions transfers one unit between two of the 16 states. The product-only MathML is parsed directly; the kinetic coefficient is assembled from the nominal parameter table. The optimization-scale column does not cause another exponentiation of these already linear nominal values, and the XML parameter placeholders do not replace the supplied nominal fit.

Each transition from species j to i adds its rate to Q[i,j] and subtracts it from Q[j,j], giving dx/dt = Qx. The observed maximum absolute column sum is **4.440892098500626e-16**. A normalized linear solve gives the stationary distribution; its maximum absolute Qp residual is **6.938893903907228e-17**. SciPy's matrix exponential evaluates each requested finite-time state. The relaxation scale is the reciprocal of the smallest strictly positive decay rate, using real parts of the nonzero generator eigenvalues.

The dimension result is derived from the species count, kinetic symbols, estimate flags, and `sources/h4/model_space.tsv`: 16 normalized states allow at most 15 independent equilibrium mean coordinates; 32 motif factors together with the common basal acetylation rate define 33 superset kinetic parameters, giving rank deficiency at least 18. The selected fit estimates eight kinetic parameters. Neither the fixed normalization `da_b=1` nor the observation-noise parameter is counted as a newly estimated kinetic parameter. The bound does not decide identifiability of the selected eight-parameter model. The 252 rows in `sources/h4/measurements.tsv` all have time `inf`; repeated observations can improve precision without adding equilibrium mean coordinates.

Positive external clock conversion c leaves equilibrium unchanged because Qp=0 implies (cQ)p=0. It changes a finite-time trajectory to exp(cQt)x0 = x(ct). This is a hypothetical conversion of the normalized model clock, not a competing fitted biological rate. The original fixed `da_b=1` remains legitimate. The additional hypothetical calibration in the third request changes the decision: its positive interval is propagated deterministically by division, preserving its evidence ID, assumed label and physical unit.

The Boehm mission reads the fresh `sources/boehm` package. Its measurements occur at 0, 2.5, 5, 10, 15, 20, 30, 40, 50, 60, 80, 100, 120, 160, 200 and 240. Its three relative-observable formulas differ from H4's observation map (`observables.tsv`). The XML defines a time unit with a 60-second multiplier. That convention is evidence about the declared unit, not proof that every temporal interpretation is calibrated.

The requested differences between the provided simulation values at 10 and 5 are:

| Observable | Reference-simulation difference |
|---|---:|
| pSTAT5A_rel | 5.453091566800012 |
| pSTAT5B_rel | 11.784614031000004 |
| rSTAT5A_rel | 3.2240345018000056 |

Those values are read from `sources/boehm/simulations.tsv`. No nonlinear Boehm simulation or fit was performed. The fixed finite-time regime prevents automatic import of H4's equilibrium scaling witness. Finite-time measurements alone do not establish complete identifiability or physical validity.

Every record includes SHA-256 hashes of all regular files recursively under its selected source directory. The five-file model identity and complete evidence identity are canonical-JSON hashes of different mappings, as required. This binds the H4 model-space file and Boehm reference simulations in addition to the five core files. The individual request hash includes all its current parameters and ID. The inherited identities are recomputed from the requested previous source.

## Applied workflow and invariants

I applied the supplied `EXPERT_WORKFLOW.json`, capability `durable-service-contract-workflow`, version 1.0.0, as an established operating method. Its contribution was organizing the contract, invariants and regression probes. The mathematical methods here are conventional; no model-weight change, learned new method or new mathematical discovery is claimed.

The public operation is a fresh packet construction. Each mission's exact ID and source are preserved, while the request fingerprint distinguishes changed intent under the same ID. Repeated builds do not reuse persistent answers. The construction invariants are source-byte preservation, complete evidence binding, finite normalized state vectors, mass-conserving generator columns, and claim scope matching the mission. No authority or biological validation is created. The CLI completes all parsing, request checks and numerical construction before atomically replacing its output. A rejected request therefore leaves an existing output untouched.

No preexisting defective submission was supplied. The first implementation passed the public test and the subsequent independent regression suite; no failing scientific test required a numerical correction. One verbose source-inspection response was truncated, so I repeated that inspection in a compact format and verified all reaction forms.

## Verification performed

The command `python -m unittest -v test_public test_scientific` completed successfully: **14 tests in 0.165 seconds**, as reported by unittest. The following checks cover concrete risks beyond serialization:

- An independent construction from the four-site subset lattice and motif parameter IDs agrees with the XML-derived generator.
- Directed matrix-tree cofactors independently recover the stationary vector; normalization, positivity, Qp and the acetylation mean are checked.
- DOP853 ODE integration agrees with matrix-exponential trajectories for the supplied clocks and changed requests.
- Eigenvalues of a finite-time transition matrix independently verify the relaxation scale obtained from the generator spectrum.
- Three request variants exercise renamed and reordered missions, changed finite times and clocks, equal clocks, changed calibration evidence IDs and physical units, degenerate positive calibration intervals, and reversed reference contrast times.
- Exact source, evidence and request fingerprints are checked, including recursive auxiliary files and previous-source identities.
- Repeated calls, changed values under the same ID, and mutation of a returned packet do not contaminate subsequent results.
- Temporary test-owned source copies show that an added evidence file changes the complete identity without changing the core identity, and that a changed nominal basal value recomputes the model output. These are synthetic software probes, not additional biological datasets. Original source files are untouched.
- An invalid calibration after earlier missions have been computed leaves a preexisting output byte-for-byte unchanged. An unavailable reference contrast time raises an error instead of inventing an interpolated value.
- All supplied source files, including both license notices, match the hashes and sizes in `SOURCE_FILES.json`.

The requested CLI was executed successfully to generate `packet.json`. No private evaluation or feedback was accessed. Passing these finite tests does not establish general validity beyond the stated source and contract.

## Remaining assumptions and limits

The H4 outputs condition on the supplied nominal fit, reaction model and initial distribution. No fitted-parameter uncertainty, biological generalization or complete structural-identifiability result is inferred. The equilibrium clock witness identifies one unsupported physical-time interpretation; it does not invalidate the original paper or every stationary quantity. The assumed calibration interval is neither observed nor a confidence interval. Its spectral scale is neither a measured half-life nor a finite-time settling guarantee.

The executable uses a deliberately source-specific H4 interpreter for closed first-order product laws with fixed unit compartments. It rejects unsupported SBML structures and is not a general SBML engine. Computations use double precision. Boehm contrast times must be represented in the supplied reference table. Neither the source authors nor any human authority is represented as endorsing this qualification.

## Actual resource observations

All filesystem interactions, Python execution and artifact generation used the assigned frozen logged runner sequentially. At the pre-report status snapshot, the runner recorded **14 successful operations of 48**, **296.576860666275 elapsed wall seconds of 1,200**, and **2.061960695005837 cumulative tool elapsed seconds**. It labeled **9** Python run invocations as `test_executions`; these included evidence inspection, the two unittest invocations, CLI generation and numerical inspection, so that counter is not a count of distinct scientific tests. The last full test invocation was logged at 277.18987917900085 elapsed seconds. All Python calls completed well within the 45-second limit.

These are actual pre-report observations, not final-total estimates; the runner's freeze receipt records completion totals. Token counts, API snapshot details and actual billing were unavailable. No token usage, cash cost, customer, revenue, human approval, physical calibration or biological validation is invented.
