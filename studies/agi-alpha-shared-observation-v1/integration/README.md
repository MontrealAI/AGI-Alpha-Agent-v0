# Existing interfaces, new retained artifact

This directory reuses the existing capability-opportunity study's lifecycle and native accounting
interfaces. It does not introduce a new registry, alter native capsule scope, or grant production authority.
The new wrapper transfers the exact observation compiler and its scope profile and executes those
retrieved bytes on a different, synthetic mission in a separate local process.

## Provenance

`custody.json` binds 34 unchanged files to research source
`231834269599d85e49cfe1ca9917a1a874522d44`. The upstream `source_manifest.json` independently binds
the 29-file vendor closure: 11 existing research-lifecycle files at
`2727262caa52766a78916f2ed81f5afaf668edce` and 18 native runtime files at
`80b345828f34fd8a6e592977dd17ef37141305f4`. Their source bytes and license headers are preserved.

New source is confined to `bundle.py`, `transfer_recipient.py`, `native_replay.py`,
`prepare_native_reference.py`, `test_bundle.py` and this documentation. The original research namespace and some fixed fixture labels
remain unchanged; those labels do not establish learned weights, calibrated physical sensors or live identity.

## Reproduce transfer and recipient execution

From the study directory, use an output directory that does not already exist:

```bash
python integration/transfer_recipient.py \
  --compiler capability/compiler.py \
  --profile capability/sensor_profile.json \
  --mission evaluation/protected/cases/confirmation-041.json \
  --out evidence/new-recipient-transfer \
  --prepared evidence/native-conformance-v1_0_1 \
  --checker evaluation/reference.py
```

The wrapper verifies all original source identities, packages only `compiler.py` and
`sensor_profile.json` with a manifest, and sends those actual bytes through the unchanged lifecycle.
It verifies the retrieved archive, unpacks only its declared payload into a new directory, copies the
fresh mission separately, and invokes the standalone compiler using isolated Python import mode.
The mission and its answers never enter the retained bundle. The scope profile is a contract, not a
learned sensor model. The receipt records source, bundle, input and output identities, process separation,
elapsed time, original fixture controls, refusal states and the resulting computation.

The optional `--prepared` parameter reuses a successful conformance receipt only when its artifact
identity matches the deterministic bundle made from the current source bytes. Omit it to run the existing
conformance suite in the new output directory. The actual recorded recipient uses confirmation-041,
selected by the first identifier in the changed-dimension withdrawal category, before inspecting gain.
The released case is now public: rerunning it is reproduction, not another protected fresh trial.

Input/output binding is not domain acceptance. The supplied independent checker separately verifies
the fresh decision tree and its original mission obligations. The ordinary-library arm receives identical
source, rights and input and invokes another process; its output is byte-identical in the recorded case.
Python import isolation is not an
adversarial operating-system sandbox. This authorized local computation grants no permission to request
a real observation or command a spacecraft.

## Native modeled accounting

The existing `Journal`, `TrustRegistry`, Ed25519 signing and disjoint `CostLedger` can check the final
scenario's declared A/B/C commands without converting them into actual receipts:

```bash
python integration/native_replay.py \
  --commands evidence/native-economics-v1/commands.json \
  --out evidence/new-native-ledger.json
```

The command document is a list of native `{action, record}` objects, or an object containing that list
under `commands`. Amounts are USD micro-units. Unique activities, categories and completeness seals
retain the existing native semantics. Every output remains labeled as executed accounting with modeled
amounts. Actual customer collections are zero; complete actual research cost and profit remain unknown.

To regenerate the reference mapping from the simulated event tree and check it against native fields:

```bash
python integration/prepare_native_reference.py \
  --assumptions economics/assumptions-v1.json \
  --events results/economics/event_tree.json \
  --out evidence/new-native-economics
```

This selects the explicitly illustrative all-available, all-paid branch. Its service revenue is USD240,
delivery cost USD135, profit USD105, terminal cash USD1,605, reserve USD300 and available funds USD1,305.
Seed capital is USD1,500, not revenue. The USD600 sensor pass-through and supplier payment are excluded
from native service revenue; interim refundable custody remains in the separately checked event ledger.
The native completeness flag closes declared model categories, not an observed complete expense bill.

## Recorded result and recipient limitation

`evidence/native-conformance-v1_0_1/summary.json` records 29/29 existing fixture controls.
`evidence/recipient-transfer-v1_0_1/summary.json` records 13/13 source, transfer, process, parity and
semantic controls, including 174 independent reference comparisons. The received instrument runs the
five-state recipient with three operators and eighteen branches. The ordinary library ties exactly.

The recipient's technically valid expected action cost falls in aggregate from USD236.84 to
USD100.6016883 under supplied risk and likelihood assumptions. These numbers exclude observation
acquisition and service fees. One participant is worse off by USD16.0291 even before those charges.
`commercial-interpretation.json` therefore rejects an automatic full-roster participation conclusion.
A voluntary subset would require a new computation and arrangement; aggregate surplus is not consent.
No real buyer acceptance, live observation, spacecraft action or collection is recorded.

## Evidence boundaries

The existing conformance suite supplies artificial favorable monetary pairs solely to exercise lifecycle
transitions. This admission is not empirical Alpha admission. Its separate negative controls retain
revocation, protected-material rejection, unknown-member refusal, no export right, changed-baseline
invalidation and the requirement for separate execution authority. The new result must still contain
`execution_authorized:false`. No live ENS check or production admission is established.

Revocation blocks future mediated retrieval; it cannot erase bytes already retrieved. An ordinary
authorized library with identical contents is expected to preserve the same executable capability.
Graph-specific benefit is not inferred from this transfer.

Run the targeted archive-boundary checks independently with:

```bash
python -m unittest discover -s integration -p test_bundle.py -v
```

These checks cover stale or corrupted contents, path injection, source symlinks and preservation of
existing recipient work. They do not qualify the full repository or the native production runtime.
