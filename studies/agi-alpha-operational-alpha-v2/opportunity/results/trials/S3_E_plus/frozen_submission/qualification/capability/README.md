# Scientific model reuse instrument 1.0.0

Import `model_reuse.py` or execute it against your local source directory:

```bash
python model_reuse.py /path/to/petab
python model_reuse.py /path/to/petab request.json --out receipt.json
```

The first command inventories the source; the second rechecks the specified mission. `ScopeError` is raised for invalid source input. Unsupported scoped requests normally return `status: "scope_not_qualified"`. Neither form establishes biological invalidity. Every receipt has `authority: []`, `physical_validation: false`, `full_identifiability_proved: false` and a SHA-256 binding to current source/request content. The receipt is not an authentication credential.

## Python interfaces

```python
from model_reuse import inventory, build_generator, stationary, clock_witness
from model_reuse import dimension_bound, qualify

info = inventory(source)
generator = build_generator(source)  # JSON-compatible columns convention: dx/dt = Qx
point = stationary(source)          # species list and conditional probabilities
witness = clock_witness(source, scales=(0.5, 2.0), time=1.0)
bound = dimension_bound(source, kinetic_parameters=20)  # caller must justify scope/count
```

These examples are API demonstrations, not approved scientific requests. Parameters come from `parameters.tsv` nominal values, overriding placeholder SBML values. Explicit `param_overrides` or request `parameter_overrides` must use known parameter names, finite values and supplied bounds. These represent a changed conditional parameter point, not a refit.

## Request schemas

All requests require a nonempty `mission_id`. Optional `expected_source_fingerprint` rejects stale source identity. The value comes from `inventory(source)["source_fingerprint"]`.

```json
{"mission_id":"current-stationary-question","type":"stationary"}
```

```json
{"mission_id":"current-clock-question","type":"clock_witness","scales":[0.5,2.0],"time":1.0}
```

The clock alternatives are hypothetical physical embeddings of the same normalized model. An unsupported physical interpretation is reported only where the applicable witness separates at the requested time. A nonseparating example is not evidence that the physical clock is identified. Supplying a calibration requires both alternatives to lie within its interval; it changes the interpretation to residual clock uncertainty.

```json
{"mission_id":"current-parameter-question","type":"dimension_bound","kinetic_parameters":20}
```

The bound is necessary only, scoped to means from one normalized equilibrium and direct abundance observations. Replication increases precision, not this mean-coordinate dimension. The default requested parameter count is the selected estimated kinetics, not every parameter symbol. With model-space evidence absent, the candidate-space count is unknown. Read the source or study definition before supplying a different candidate count.

```json
{
  "mission_id":"current-relaxation-question",
  "scope_id":"current-purpose-and-condition",
  "type":"response",
  "quantity":"spectral_relaxation_time",
  "time_basis":"physical",
  "calibration":{
    "model_fingerprint":"REPLACE_WITH_CURRENT_INVENTORY_FINGERPRINT",
    "scope_id":"current-purpose-and-condition",
    "evidence_id":"hypothetical-clock-assumption-v1",
    "evidence_kind":"assumed",
    "physical_unit":"hour",
    "scale_per_physical_unit":[0.8,1.2]
  }
}
```

The interval means normalized model-time units per physical unit. It is supplied evidence, not inferred from the source or established by its label. The response propagates `[lo,hi]` to `[tau/hi,tau/lo]` for the numerically computed spectral scale. It is not a confidence interval, observed half-life, general settling time or physical validation. To calculate normalized model time alone, use `"time_basis":"model_unit"` and omit calibration.

`quantity: "state_at_time"` also requires nonnegative `time`. With uncertain clock conversion, it returns a midpoint vector and a conservative coordinate enclosure based on `t * ||Q||_1 * (hi-lo)/2`. It deliberately avoids assuming each coordinate is monotone in clock rate. The bound can be very loose, and floating-point computations are not interval-certified.

For changed parameter points, calibration additionally needs `parameter_overrides_sha256`: SHA-256 of sorted, compact UTF-8 JSON (`ensure_ascii=False`, `allow_nan=False`) for the exact request `parameter_overrides` object. This binds an assumption to the stated point; it does not prove the assumption true.

## Adapting a recipient contract

This is a generic capability, not a prewritten answer adapter. A recipient must recheck the actual requested output schema, units, source paths and mission meaning. A contract requiring a five-file fingerprint must compute that separately if the instrument also ingests optional model-space evidence. `build_generator` exposes the states and kinetic names for independently justified functionals or candidate definitions. A fresh nonlinear or timed model can still be inventoried; an equilibrium-only witness cannot be transferred merely because an earlier source qualified.

Protected acceptance cases and evaluator internals are intentionally excluded. See CAPABILITY.md for scope, provenance, limitations, rights and admission boundaries. `manifest.json` pins the generic files; the enclosing freeze record and capsule digest are maintained outside the capsule to avoid self-referential hashes.
