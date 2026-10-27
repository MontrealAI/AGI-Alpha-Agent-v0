# Scientific-model reuse qualification — four-mission portfolio

## Beneficiary and useful purpose

A scientific modeling service is deciding which statements it can responsibly deliver when a published model is reused. Produce an executable, source-bound qualification packet. Preserve valid uses of the fitted model, demonstrate why unsupported physical-time interpretations require more evidence, propagate an explicitly hypothetical calibration, and withdraw a previously useful witness when a different model and measurement regime arrive.

This is a computational research service. No real customer, wet experiment, biological discovery, physical calibration or production authority is represented by these tasks. H4's published fixed `da_b=1` is a legitimate normalization; it is not a newly estimated free parameter. Do not describe the original paper as wrong because a later request needs additional evidence.

## Common resources and operating envelope

All arms receive these exact files, the same hosted frontier-model access, Python 3.12.14, NumPy 2.3.2, SciPy 1.17.0, PyYAML 6.0.2, and file/test/correction access through the logged runner. Established structural-identifiability reasoning, exact algebra, conservation, scaling and numerical methods are permitted. SymPy is not installed in the observed runtime; no unavailable package is assumed. The direct algebra needed here is available without it. You may implement the appropriate conventional method directly. You are not required to discover a new algorithm or use any provided helper.

You have 1,200 wall seconds from the first logged operation, at most 48 successful logged read/write/run operations, and at most 45 seconds per Python execution. The runner is a logging/protocol boundary, not an OS security sandbox. Token counts and actual billing are unavailable. Do not access private evaluation material, other arms, the internet, or unprovided research directories. Source files, this brief, requests and canonical public test are immutable. Add `submission.py`, tests and a concise `REPORT.md` under the task directory. All interactions must use the assigned runner. Call `finish` to freeze your work.

## Entry point and packet schema

Implement `build_packet(source_root, requests_path)` in `submission.py`. Both arguments are filesystem paths. It returns a JSON-serializable dictionary. Also support:

```bash
python submission.py --sources sources --requests requests.json --out packet.json
```

The packet must include `packet_version: 1`, `authority: []`, and `missions`, a list of one record per request in request order. Every record contains:

- `id`: exact request ID;
- `source`: exact source ID;
- `source_fingerprint`: SHA-256 over the canonical JSON object mapping `model.xml`, `parameters.tsv`, `measurements.tsv`, `observables.tsv`, and `conditions.tsv` to their SHA-256 strings; use `json.dumps(mapping, sort_keys=True, separators=(",", ":"))` encoded as UTF-8;
- `source_file_hashes`: mapping every regular file recursively under the selected source directory to its SHA-256 string, using relative POSIX paths as keys; this includes supplied model-space and reference-simulation files;
- `evidence_fingerprint`: SHA-256 of that complete `source_file_hashes` mapping with the same canonical JSON settings;
- `request_fingerprint`: SHA-256 of that individual request encoded with the same canonical JSON settings;
- `authority: []`;
- `biological_validation: false`;
- the mission-specific fields below.

The five-file `source_fingerprint` identifies the core model package. The complete `evidence_fingerprint` additionally binds all supplied evidence used to interpret it; these are deliberately distinct identities.

The output must be recomputed from the supplied sources and request parameters, not copied from a remembered answer. Tests may change mission IDs, requested numerical values and calibration intervals within the stated envelope. Those are request variants within one campaign, not independent biological datasets.

### 1. `stationary_qualification`

Use **nominal values from `parameters.tsv`**, not a different published parameter vector. In the supplied H4 SBML, construct the closed, linear mass-action generator `Q` with `dx/dt = Qx`; the initial distribution is given by the source. Evaluate the normalized stationary vector with total mass one. Return:

- `decision: "conditional_model_prediction"`;
- `conditional_on_supplied_fit: true`, `full_parameter_identifiability_established: false`;
- `stationary`: mapping every H4 species ID to its stationary abundance;
- `mean_acetylation`: sum of abundance times the species' number of acetylated sites (0 for `x_0ac`, 4 for `x_4ac`, otherwise the count of `k` groups);
- `dimension_check`: `{ "independent_equilibrium_mean_coordinates_at_most": 15, "selected_kinetic_parameters": 8, "full_superset_kinetic_parameters": 33, "full_superset_rank_deficiency_at_least": 18, "selected_model_identifiability": "not_decided_by_dimension_bound" }`.

These dimension values must be derived from the source's 16-state normalized equilibrium, 32 motif-specific factors and common basal rate. A necessary dimension bound is not a complete identifiability verdict, an uncertainty interval, or a reason to reject the published eight-parameter fitted model. Repeated measurements improve precision but do not add independent equilibrium mean coordinates.

### 2. `clock_witness`

The new request wants a physical timed response, but provides no independent mapping from the normalized model clock to physical time. The two positive `alternative_clock_scales` and positive `normalized_time` are **hypothetical alternative physical-clock conversions**, not different parameter estimates within the original fit and not observed biological rates. Return:

- `decision: "needs_clock_calibration"`, `physical_time_supported: false`;
- `same_equilibrium_under_clock_scaling: true`;
- `clock_scales`: the supplied pair;
- `state_at_request_time`: one complete species-to-abundance mapping for each clock scale, computed as `expm(scale * Q * normalized_time) @ x0`;
- `equilibrium_max_abs_difference`: the largest difference between the two recomputed stationary vectors;
- `proof_statement`: a concise explanation that `Qp=0` implies `(cQ)p=0`, while a finite-time trajectory generally changes to `x(ct)`; fixed `da_b=1` remains the original normalization;
- `additional_evidence_required`: a nonempty description of independently supported physical-clock calibration for this mission.

The source has only steady-state observations and no declared physical time unit. This witness exposes one unsupported interpretation; it does not prove every parameter or stationary quantity unidentifiable.

### 3. `calibrated_relaxation`

The request supplies a **hypothetical** conversion interval `[lo, hi]` in normalized model-time units per stated physical unit. Preserve its evidence ID and `assumed` label. Define the model's spectral relaxation scale as

`tau_model = 1 / min(-Re(lambda))` over nonzero eigenvalues of `Q`.

This is an asymptotic exponential scale of the supplied model, not a claim about a measured biological half-life or a finite-time settling guarantee. Return:

- `decision: "conditional_on_assumed_calibration"`;
- `calibration_evidence_id`, `calibration_evidence_kind: "assumed"`, `physical_unit`;
- `tau_model`, and `tau_physical_interval: [tau_model / hi, tau_model / lo]`;
- `calibration_is_observed: false`, `conditional_on_supplied_fit: true`.

The interval is a deterministic propagation of the supplied conversion bounds. It is not a confidence interval or a measured calibration. Scales are strictly positive and finite. Do not preserve the previous blanket clock rejection after this additional assumption is explicitly supplied.

### 4. `inheritance_boundary`

Read the fresh Boehm source files. It is a different public model family with finite-time observations and a different observation map. Do not reuse H4's equilibrium-only witness or its generic qualification receipt as a current approval. Return:

- `decision: "fresh_dynamic_qualification_required"`;
- `inherited_equilibrium_witness_applicable: false`, `full_parameter_identifiability_established: false`;
- `measurement_rows`, sorted `observation_times`, `observable_count`, and `all_measurements_at_equilibrium`;
- `previous_source_fingerprint`: the five-core-file fingerprint of the requested `inherited_source`;
- `previous_evidence_fingerprint`: its complete all-file evidence fingerprint;
- `source_identity_changed: true`;
- `finite_prediction_contrast`: for each observable, the value at the second `contrast_times` entry minus the value at the first in the supplied `simulations.tsv`;
- `contrast_evidence_kind: "provided_reference_simulation_not_observation"`;
- `reason`: explain why fixed finite observation times do not support automatically importing the equilibrium scaling equivalence. Finite-time observations alone do not establish complete identifiability or physical validity.

The reference simulations are supplied by the benchmark repository. Reading their differences is not rerunning the nonlinear model, fitting data, or generating new physical evidence. The new model's `time` unit definition contains a 60-second multiplier; this by itself is not proof that every temporal interpretation is calibrated. No authority transfers with either artifact.

## Acceptance and report

All four mission records must satisfy their original meanings, numerical checks and source/request bindings. Numeric values are checked with absolute/relative tolerances of roughly `1e-7`; probabilities must be finite, nonnegative within numerical roundoff, normalized and consistent with the source. Useful positive qualifications and appropriate refusals are both required; rejecting everything fails.

The public test checks interface/serialization/basic completeness. Private acceptance separately checks source-derived values, witnesses, changed requests, fresh-source scope and the stated limitations. No private feedback is supplied until all arms are frozen. Include in `REPORT.md`: how the packet was built, what is supplied versus constructed, which assumptions remain, tests/corrections and actual tool/timing observations. Do not invent token billing, human approval, customers, revenue, physical validity or a new mathematical discovery.

## Source provenance

- H4: `PEtab-dev/petab_select@7b1a1528cee614e72f17eb82338472e7ba91d8de`, case `0009`; BSD-3-Clause notice retained.
- Boehm: `Benchmarking-Initiative/Benchmark-Models-PEtab@c44d5ede9bf979db5aa8ae4e94fc31fba9776675`, `problems/Boehm_JProteomeRes2014/v1`; BSD-3-Clause notice retained.
- The original authors supplied models, observations, parameter values and reference simulations. This research team supplies the reuse requests and evaluation. Neither source author endorses this study.
