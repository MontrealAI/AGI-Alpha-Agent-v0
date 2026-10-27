# Scientific-model reuse qualification report

## Deliverables and result

`submission.py` implements `build_packet(source_root, requests_path)` and the required command line. `packet.json` contains the four requested records in request order. `test_scientific.py` adds ten scientific, provenance and request-variation checks; the supplied `test_public.py` remains unchanged.

| Mission | Decision | Constructed result for the supplied request |
| --- | --- | --- |
| H4 stationary qualification | `conditional_model_prediction` | All 16 stationary abundances are returned; mean acetylation is **0.37642255826743765**. |
| H4 clock witness | `needs_clock_calibration` | Scales 0.5 and 3.0 at requested time 1.25 give different finite-time distributions, while the recomputed equilibria differ by at most **1.1102230246251565e-16**. |
| Hypothetically calibrated relaxation | `conditional_on_assumed_calibration` | Spectral scale is **1.281539318178634** model-time units. The assumed conversion interval [0.4, 1.6] model-time units per minute gives **[0.8009620738616463, 3.2038482954465852] minutes**. |
| Boehm inheritance boundary | `fresh_dynamic_qualification_required` | The prior equilibrium witness is inapplicable to the fresh finite-time mission. All 48 measurement rows, 16 unique times and 3 observables are identified. |

For the supplied Boehm reference simulations, the value at time 10 minus the value at time 5 is 5.453091566800012 for `pSTAT5A_rel`, 11.784614031000004 for `pSTAT5B_rel`, and 3.2240345018000056 for `rSTAT5A_rel`. These differences are read from `sources/boehm/simulations.tsv`; they are not experimental observations or results of a new nonlinear simulation.

## Supplied evidence and construction

The supplied H4 files come from PEtab-dev/petab_select commit `7b1a1528cee614e72f17eb82338472e7ba91d8de`, case 0009. The Boehm files come from Benchmarking-Initiative/Benchmark-Models-PEtab commit `c44d5ede9bf979db5aa8ae4e94fc31fba9776675`, Boehm_JProteomeRes2014/v1. These provenance identifiers and licenses were supplied by the brief and source manifest; no internet or independent provenance audit was used. Both supplied license files remain intact.

The sources supply the SBML model structures, initial state, nominal parameter table, model space, observation definitions, conditions, measurements, and Boehm reference simulations. The campaign supplies the reuse requests, clock alternatives, hypothetical calibration and public smoke test. This submission constructs only the generator, derived numerical quantities, evidence bindings, conditional decisions and tests.

For H4, the code parses the actual MathML products and reaction stoichiometry in `sources/h4/model.xml`. It explicitly checks the closed, single-compartment, unit-volume, linear transition structure. There are 64 directed transitions on 16 species. Each reaction adds its nominal rate to the destination/source entry of the column-oriented generator and subtracts it from the source diagonal, so `dx/dt = Qx`. Rates use **nominal values in parameters.tsv**, replacing the XML parameter placeholders. The initial distribution is read from the species declarations and has all mass in `x_0ac`.

The normalized stationary distribution solves `Qp = 0` with `sum(p) = 1`. The generator has maximum absolute column-sum error 4.440892098500626e-16. The computed stationary balance residual is 6.938893903907228e-17, and its smallest abundance is 0.0013405026344622901. The implementation checks conservation and nonnegativity before removing floating-point roundoff. Mean acetylation uses the species site counts required by the brief.

The dimension check is derived from the parsed state count, the selectable model-space columns and the kinetic parameters marked for estimation. Normalization leaves at most 16 - 1 = 15 equilibrium mean coordinates. The model space provides 32 motif factors; adding the common basal rate gives a 33-parameter superset and a necessary rank deficiency of at least 33 - 15 = 18. The selected nominal model estimates eight kinetic parameters. Fixed `da_b=1` is a legitimate normalization and is excluded from those free-parameter counts, as is observation noise. Repeated measurements can improve precision without increasing the number of independent equilibrium means. This dimension bound does **not** decide the selected model's full identifiability or invalidate its fitted stationary prediction.

The clock records evaluate `expm(c * Q * t) @ x0` and separately solve the stationary equations for each scaled generator. Algebraically, `Qp=0` implies `(cQ)p=0` for positive c, while the trajectory becomes `x(ct)`. The supplied c values describe hypothetical external clock conversions, not alternative parameter estimates or newly freed `da_b`. H4's 252 supplied measurement rows all use time `inf`, and its SBML declares no physical time unit. Independent evidence connecting normalized time to physical time remains necessary for the uncalibrated mission.

For relaxation, the code discards the unique conserved eigenmode and takes the inverse of the smallest nonzero decay rate. The slowest nonzero real eigenvalue is approximately -0.7803116032532135. The interval endpoints divide the model scale by the upper and lower assumed clock conversions, respectively. Evidence ID `HYPOTHETICAL-CLOCK-01`, kind `assumed`, and physical unit `minute` are preserved. The result is an asymptotic exponential scale conditional on the fit and hypothetical conversion; it is neither a biological half-life, a confidence interval, nor a finite-time settling guarantee.

For the fresh Boehm mission, the implementation reads its new model, observation definitions, measurements and reference simulations, and recomputes source identities. It does not call the H4 generator for Boehm. Fixed finite observation times generally distinguish `x(t)` from `x(ct)`, so the equilibrium equivalence cannot be inherited automatically. The model's time definition contains the supplied 60-second multiplier, which records a unit convention without establishing every possible physical-clock interpretation. Finite-time data alone also do not prove complete identifiability or physical validity.

## Bindings and scope

Every mission binds the exact individual request by canonical JSON SHA-256. Its five-file core fingerprint is separate from its all-file evidence fingerprint. The latter includes H4 model-space/YAML evidence and Boehm simulation/YAML/visualization evidence. Each record includes the complete recursive relative-path/hash mapping. Hashes are recomputed from the supplied paths on every `build_packet` call; identifiers and numerical answers are not used as lookup keys for remembered solutions.

| Source | Five-file core fingerprint | Complete evidence fingerprint |
| --- | --- | --- |
| H4 | `23046a116971f047e1561532a54f08c754dff7e8c996f8e8a76323040d8c4e78` | `18f6c9bd8fdfedd6c941271acf9aba04c773a403314da4dfb70d68a2e55815b7` |
| Boehm | `4c981fbce86d64111fa1b052cdd9faa8054ccd8e8ab5fc21e8afd3e028afed7e` | `f5aca10a7ba101cd3b82c539c84355b8d7815c588cbf95d2c83e485a609f3cc9` |

All packet and mission authority arrays are empty; every mission has `biological_validation: false`. No artifact transfers authority. No claim is made about a customer, wet experiment, biological discovery, measured clock calibration, new mathematical method or production approval. The parser is deliberately restricted to the supplied H4 mass-action structure; it is not a general SBML simulator. Boehm contrasts require values present in the reference table, with no unstated interpolation.

## Verification and corrections

The executable was run through the assigned runner with:

```text
python submission.py --sources sources --requests requests.json --out packet.json
python -m unittest -v test_public test_scientific
```

Both commands exited successfully. The test run passed **11 tests**: one immutable public smoke test and ten added tests. Scientific checks included an independent transition graph assembled from the source motif names, an SVD stationary nullspace, positive Poisson-series uniformization of finite trajectories, and a conservation-reduced spectral calculation that removes the zero mode. Bindings were independently recomputed. Every file listed in the supplied source manifest retained its exact byte count and SHA-256. Tests also verify that requests, brief, manifest, public test and sources are unchanged across packet construction and verification.

Four additional request variants changed IDs, mission order, clock scales, normalized time, calibration bounds, units, evidence IDs and reference contrast times. They included equal clock scales, equal calibration endpoints, reversed and zero reference contrasts, and Unicode evidence IDs. Expected quantities were recomputed, including trajectories through the independent uniformization method. Explicit invalid-input checks rejected nonpositive/nonfinite clock scales and reversed/nonpositive calibration intervals. Temporary variant files stayed within the task directory and were removed after testing. These are tests within one campaign, not independent biological datasets.

No scientific or implementation correction was required after the first executable run. An initial inspection output was truncated, so a subsequent compact source inspection verified all 64 reaction endpoints and kinetic factors before implementation.

## Observed resource use and limitations

All filesystem reads/writes and Python executions used the assigned logged runner sequentially. No other participant workspace, private evaluator, unprovided research directory, conventional answer, or internet source was accessed. No delegation occurred.

At the end of the complete numerical test run, the runner reported **11 successful logged operations**, **37 remaining operations**, and **257.1940071582794 seconds elapsed** since the first logged operation. The unittest process reported **11 tests in 0.107 seconds**. The packet CLI and test commands were well below the 45-second execution cap. This operational checkpoint precedes report writing and final artifact verification/freezing; the runner's final status is authoritative for the completed run. Actual model token usage and billing are unavailable and are not estimated here. No private acceptance feedback was accessed, so passing public and added tests is not represented as a private acceptance result.
