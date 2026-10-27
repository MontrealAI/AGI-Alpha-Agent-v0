# Inspection evidence instrument — interface contract 0.1

Development interface, to be frozen with source hashes before confirmation. Maintainer: foundations agent. Independent confirmation/verifier must not import the core's proof routines as its oracle.

## Invocation

```sh
python studies/agi-alpha-opportunity-discovery-v4/instrument/cli.py --request request.json --output report.json
```

Python API: `instrument.audit.audit(request: dict, base_dir: Path) -> dict` after adding the study directory to `sys.path`. Relative input paths resolve relative to the request file, not cwd. `base_dir` is that request directory. CLI exit 0 means a report was produced, not that any physical claim was accepted; exit 2 means invalid request, changed source digest, or unsupported file/version prevented a report. No network calls or mutations of inputs.

## Request

```json
{
  "schema_version": "0.1",
  "mission": {"id": "plate-development", "purpose": "evidence_audit", "statement": "Audit whether the supplied first-article evidence can support incoming obligations."},
  "assets": {
    "source_qif": {"path": "Plate_FAIR.qif", "sha256": "EXACT_64_HEX"},
    "incoming_qif": {"path": "Plate_incoming.qif", "sha256": "EXACT_64_HEX"},
    "cad_step": {"path": "Plate_AP242.STP", "sha256": "EXACT_64_HEX"},
    "reference_owl": {"path": "Plate_integrated.owl", "sha256": "EXACT_64_HEX"}
  },
  "family": {"source_characteristic_ids": ["71", "89", "92"], "incoming_characteristic_id": "101"},
  "counterfactual": {"source_linear_unit": {"name": "mm", "factor_to_metre": "0.001"}},
  "guards": {"feature_set_identity": "unverified", "specimen_scope": "unverified", "requirement_requalification": "unverified", "measurement_adequacy": "unverified", "current_authority": "unverified"}
}
```

`source_qif` and `incoming_qif` are required. CAD and existing reference graph are optional; absence yields an explicit missing-evidence result, not fabricated geometry. `family` is optional: otherwise the instrument enumerates candidate same-kind/raw-nominal groups, clearly separating formal units from a proposed unit repair. `counterfactual` is optional and always researcher-supplied: it never changes the raw source or establishes intended units. Guard values are `unverified`, `researcher_assumed`, or `externally_evidenced`; this code does not authenticate external authority, so guards do not authorize part release.

Mission purposes: `evidence_audit`, `recorded_values_all`, `family_all`, `feature_localization`, `physical_release`. The exact requested purpose is preserved in output. `recorded_values_all` quantifies the explicitly selected records and does not require a physical-feature bijection. `family_all` adds complete receiving-family coverage. Both requested quantified purposes require explicit `family` IDs; automatic candidate generation remains exploratory. A family-all proof does not satisfy localization or physical release. Physical release is unsupported by this instrument. Unknown purposes/versions fail closed. QIF input support is explicitly version 2.1.0, namespace `http://qifstandards.org/xsd/qif2`.

## Report (stable top-level keys)

- `schema_version`, `instrument_version`, `identity`: source hashes, schema/policy/runtime dependency identity, mission hash.
- `mission`: unchanged mission; `mission_result`: `supported_audit`, `conditional`, `refuted`, `unsupported`, or `blocked` with reasons. This is a computational audit status, not physical acceptance.
- `facts`: normalized source records with exact QIF IDs/source lines and raw literals; formal SI quantities; no silent unit/sign repair.
- `findings`: typed witnesses. Each includes `id`, `kind`, `status`, `evidence_basis` (`observed_source`, `derived`, or `researcher_counterfactual`), source references, conclusion, and limitations.
- `geometry`: actual CAD import/validity, surface inventory, candidate cylindrical correspondences, tolerances/coordinate assumptions, source hashes. No CAD result is invented when import fails.
- `traces`: complete incoming characteristic → nominal/definition → actual feature → feature nominal/definition → CAD candidate chain for supported cylinder-diameter records; parent result/overall status preserved.
- `family_proofs`: formal and separately labeled counterfactual results, intervals, all observed values, admissible mapping assumptions, invariance or explicit assignment counterexample, unproved guards. No automatic physical admission.

Within each family proof, `all_source_intervals_subset` is a numeric implication theorem, `all_observed_values_satisfy_destination` quantifies available selected numeric records, `permutation_invariance_proved` concerns the conjunction under the conditional family-bijection model, and `family_all_recorded_values_pass` additionally requires complete target-family cardinality. An interval implication cannot establish a passing observed record that lies outside the receiving interval. A partial record family can support `recorded_values_all` while remaining insufficient for `family_all`.
- `repair_requests`: exact missing evidence/identity/unit/standard/measurement/authority requirements, bound to affected assertions and mission.
- `limitations`, `execution`: observed runtime/tool metadata only; no complete-dollar claim.

Numeric literals are preserved as strings and SI normalization uses Decimal. Geometric floats carry explicit residual tolerances. Every source reference is `{asset, sha256, element_id, line}` (plus relevant path/field where needed). Unsupported kinds remain raw facts with `supported_predicate:false`; they are never coerced into a supported diameter predicate. Negative geometric-tolerance literals are preserved and flagged, never converted to absolute values. Exact QIF 2.1 defaults are sourced from the standards owner's archived schema.

## Verifier obligations

Verify report/source hashes; independently resolve source IDs and values; check unit conversion/default rules; check interval inclusion/counterexamples; independently enumerate finite permutations where used; verify overall status preservation and guard separation. Reimport CAD or independently inspect its geometric signatures for claims using geometry. A numerical family certificate must never be reported as locating a particular feature or releasing a part. Source alterations, unsupported kinds, absent guards, and stale identities must fail closed.

The interface will gain detailed JSON schemas and example files during Plate-only development. Final source/policy/dependency hashes will be announced before any Box/Cover execution.

## Frozen v0.1.0 identity details

Runtime source/policy/schema freeze is recorded in `freeze.json`. This explanatory section documents the
already-frozen algorithm; it does not change runtime code or schemas.

The hash serialization is Python `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`
encoded as UTF-8, then SHA256. It is a specified implementation serialization, not a claim of RFC 8785 canonicalization.
`mission_hash` hashes the unchanged `request["mission"]` object.

For `request_hash`, shallow-copy the parsed request, replace the entire `assets` value with
`{role: {"sha256": verified_digest, "bytes": actual_file_size}}` for each supplied role, and retain every other
request field unchanged. Local mount paths are excluded. Changing source bytes, role, size, mission, family,
guard labels or counterfactual parameters changes the semantic request identity. Remounting identical bytes does not.

`generic_identity_sha256` hashes the runtime identity before adding mission/source information: runtime files,
declared dependency versions, Python version, platform system/machine, schema ID and policy ID.
`complete_identity_sha256` hashes the entire identity including generic identity, asset identities,
mission hash and semantic request hash, before adding the complete hash field itself. The independent evaluator's
identity and authorization policy are additional external qualification requirements, not silently inherited here.

For `target_feature_ids`, union the target characteristic item's declared `FeatureItemIds` with the `FeatureItemId`
of every feature actual referenced by that characteristic's actual records across result sets; sort unique IDs
numerically. This union records supplied coverage relationships; it does not establish cross-provider set identity.
