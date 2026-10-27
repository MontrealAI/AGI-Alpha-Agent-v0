# Scientific-model reuse qualification report

## Delivered result

`submission.py` implements `build_packet(source_root, requests_path)` and the requested command-line interface. `packet.json` contains all four mission records in request order. `test_qualification.py` supplies recipient-authored numerical and scope checks; `verification.json` records observed diagnostics. All records have empty authority and explicitly deny biological validation.

| Mission | Decision | Source-derived result for the supplied request |
| --- | --- | --- |
| H4 stationary qualification | `conditional_model_prediction` | Mean acetylation **0.3764225582674377**; all 16 stationary abundances are in the packet. |
| H4 hypothetical clock alternatives | `needs_clock_calibration` | At normalized time 1.25, scales 0.5 and 3.0 give a maximum state difference of **0.14331681938560514**, while the independently recomputed equilibria differ by only **1.11e-16**. |
| H4 assumed calibration | `conditional_on_assumed_calibration` | Spectral model relaxation scale **1.2815393181786314**. The supplied interval [0.4, 1.6] yields **[0.8009620738616446, 3.2038482954465786] minutes**, conditional on `HYPOTHETICAL-CLOCK-01`, explicitly labeled `assumed`. |
| Fresh Boehm mission | `fresh_dynamic_qualification_required` | **48** measurements, **16** distinct finite observation times, and **3** observables. The previous equilibrium witness is inapplicable. |

The supplied Boehm reference-simulation contrasts, value at time 10 minus value at time 5, are 5.453091566800012 for `pSTAT5A_rel`, 11.784614031000004 for `pSTAT5B_rel`, and 3.2240345018000056 for `rSTAT5A_rel`. These are differences read from `simulations.tsv`, not observed differences, fresh nonlinear simulations, refits, or new physical evidence.

## Construction and evidence boundaries

The supplied scientific files provide SBML networks, nominal parameter values, observation definitions, measurements, model-space evidence, reference simulations, and provenance notices. The request file supplies the four reuse questions and the hypothetical clock quantities. This work constructs an adapter, calculations, bindings, tests, and this report; it supplies no new biological dataset or independently measured calibration.

I inspected `EXPERT_WORKFLOW.json` and the complete frozen instrument documentation and implementation. The expert workflow's contract mapping, identity checks, invariants, and regression probes apply here. Its stated stateful-service-repair scope does not make it a scientific domain solver. There was no preexisting failing submission to repair. The frozen scientific instrument was used where its inspected scope applies: H4 generator construction, stationary calculation, equilibrium clock witness, dimension bound, conditional spectral response, and broader source inventory. The capsule was not changed. Boehm was inventoried separately; its nonlinear dynamics, rules, multiple compartments, finite-time measurements, and different observation formulas do not fit the H4 solver or equilibrium-only witness.

H4 rates use **`parameters.tsv` nominal values**, overriding the SBML placeholders. The instrument checks first-order conversions, exact rational column conservation, normalized initial mass, and graph connectivity before producing `dx/dt = Qx`. Stationarity solves `Qp = 0` with total mass one. The computed vector has mass 0.9999999999999996, minimum component 0.0013405026344622973, and maximum residual 6.94e-17. The initial source distribution is wholly in `x_0ac`. Acetylation counts come from the species IDs.

The dimension bound is derived from the 16-state normalized equilibrium, the observed coordinates, and actual estimated/candidate kinetic parameter names. The model-space table exposes 32 motif factors; including the estimated common basal rate gives 33 candidate kinetic parameters. The selected fit has 8 estimated kinetic parameters. At most 15 equilibrium mean coordinates imply rank deficiency at least 18 for the full 33-parameter superset. This necessary bound **does not decide identifiability of the selected eight-parameter model**, specify an uncertainty interval, or invalidate its conditional stationary prediction. Replicates improve precision without adding independent mean coordinates. The noise parameter is not counted as a kinetic parameter, and fixed `da_b=1` remains a legitimate normalization.

For any positive conversion c, `Qp=0` implies `(cQ)p=0`, whereas the trajectory becomes `exp(cQt)x0=x(ct)`. The clock alternatives therefore represent hypothetical physical embeddings of one fitted normalized model. They are not newly estimated rates or observed biology. The source's equilibrium observations and absent declared physical time unit do not provide an independent physical-clock conversion. Supplying an explicitly assumed conversion interval does support conditional inverse scaling of the computed spectral time; it does not justify retaining a blanket rejection after that assumption arrives.

The Boehm record binds its own current source and all evidence, along with both requested inherited H4 identities. Fixed finite observation times do not automatically preserve the previous equilibrium scaling equivalence. Finite-time data alone also do not establish complete identifiability or physical validity. Boehm's actual `time` unit definition contains a 60-second multiplier; that declaration alone is not proof of temporal calibration. No authority transfers with either source or receipt.

## Bindings and verification

Each record independently binds the canonical request, the exact five core source files, and every regular file recursively in the selected source directory. The five-file identity is deliberately separate from the full evidence identity, which includes H4 model-space/YAML evidence and Boehm reference simulations/YAML/visualizations. The capsule's internal six-file H4 fingerprint is used only when adapting its calibration schema. It is never substituted for either required portfolio identity. Source bytes are rechecked before a completed mission is returned.

The CLI generated `packet.json`; a later direct `build_packet` call reproduced it exactly. The supplied public test plus **12 recipient-authored tests all passed** in one suite run. Verification covered:

- A separately constructed H4 site-subset graph against the instrument's SBML generator, including all 64 directed transitions and nominal parameter use.
- Stationarity against independent DOP853 ODE integration and conservation/residual checks.
- Transient trajectories against a positive Poisson-series uniformization calculation.
- Spectral time against the eigenvalues of a 15-dimensional conservation-reduced matrix, avoiding the full matrix's zero-eigenvalue filter.
- The source-derived 8/33/15/18 dimension counts and legitimate fixed deacetylation normalization.
- Fresh Boehm inventory, simulation contrasts, inherited identities, and the capsule's refusal to transfer the equilibrium witness.
- Request variants with changed IDs, Unicode content, reversed mission order, changed clocks and calibration bounds/units/IDs, reversed contrast times, and equal clock scales or calibration endpoints.
- Repeat-call determinism, caller-mutation isolation, invalid input rejection, and recursive evidence binding/recalculation on temporary source copies. Supplied originals were never edited.
- All source hashes against `SOURCE_FILES.json` and all pinned capsule hashes against its manifest.

There were no observed failing tests and no post-test correction was necessary. Explicit adaptation choices addressed the five-versus-six-file fingerprint mismatch, equal positive clock alternatives permitted by this portfolio, and the fresh-source witness boundary before the suite was run. The tests are local development evidence, not private acceptance results or proof of general correctness.

## Actual operating observations and remaining limits

Every filesystem/Python interaction used the assigned logged runner, sequentially. At operation 13, the completed computational verification was recorded at **304.91 elapsed seconds** from the first logged operation, with **35 of 48 successful operations remaining**. The CLI tool call reported 0.4024 seconds of process wall time. The test tool call reported 1.2690 seconds, including startup; unittest itself reported 0.649 seconds for 13 tests. These are local execution observations, not model-inference or full delivery costs. The runner's subsequent finish record gives the final freeze time and operation count. Observed versions were Python 3.12.14, NumPy 2.3.2, and SciPy 1.17.0. Actual tokens and billing are **unknown**, represented as null in verification data.

No internet, other participant workspace, protected evaluator, private acceptance feedback, or external research directory was accessed. The supplied source, request, public test, and capability bytes were preserved. No biological validation, customer outcome, human approval, revenue, autonomous discovery, or new mathematical method is claimed.

Results remain conditional on the supplied model and nominal fit. They do not propagate parameter-estimation uncertainty. The relaxation quantity is an asymptotic exponential scale, not a measured biological half-life or a finite-time settling guarantee. Its hypothetical physical interval is deterministic propagation, not a confidence interval or certified outward-rounded arithmetic. The capsule's numerical eigensolver uses a fixed zero threshold; here the slowest nonzero decay rate is approximately 0.78031 and is well separated from numerical zero. Materially different rate scales or source structures require requalification. The adapter does not solve the nonlinear Boehm model or establish full parameter identifiability for either family.
