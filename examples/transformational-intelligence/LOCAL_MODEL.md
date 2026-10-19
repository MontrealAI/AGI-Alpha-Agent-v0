# Local model proposals

The optional `ti-model-discovery/v1` adapter asks an explicitly configured,
operator-attested no-charge model on numeric loopback HTTP for one bounded JSON
proposal. It uses the maintained OpenAI-compatible runtime provider. It never
executes model code, accepts model scores, changes the evaluator, or sends fresh
confirmation sources to the model. Only native `SelectionProgram` values are
accepted. The unchanged native discovery loop then compares those programs with
its incumbent and strong controls, under a separately approved execution binding.

This is a working provider interface. Tests use a labeled local HTTP contract
fixture, not real model weights or evidence of a model advantage. The configured
and reported model names and the operator-declared revision are provenance claims,
not independently verified weight identities. Zero monetary allowance remains
fixed. Human review, energy, hardware and maintenance costs are unmeasured.

Use your initialized runtime or a new home. Set `operator_ids` in the original
`DiscoveryRequest` to `["local-model-proposals"]`. Keep its original purpose,
public source, output limit, permissions and zero payment allowances. Prepare a
configuration file:

```json
{
  "schema_version": 1,
  "endpoint": "http://127.0.0.1:8080/v1",
  "model": "your-installed-model",
  "declared_revision": "your-installed-weight-revision",
  "no_charge": true,
  "max_output_tokens": 1200,
  "timeout_seconds": 30,
  "max_input_bytes": 40000
}
```

Run each command separately and inspect the returned record before approving:

```sh
python -m alpha_factory_v1.core.runtime.successor.transformation_model_cli --home /absolute/new-home create request.json local-model.json
python -m alpha_factory_v1.core.runtime.successor.transformation_model_cli --home /absolute/new-home approve CAMPAIGN_UUID --binding EXACT_MODEL_BINDING
python -m alpha_factory_v1.core.runtime.successor.transformation_model_cli --home /absolute/new-home propose CAMPAIGN_UUID
python -m alpha_factory_v1.core.runtime.successor.transformation_model_cli --home /absolute/new-home prepare-native CAMPAIGN_UUID
python -m alpha_factory_v1.core.runtime.successor.transformation_model_cli --home /absolute/new-home approve-native CAMPAIGN_UUID --binding EXACT_NATIVE_BINDING
python -m alpha_factory_v1.core.runtime.successor.transformation_model_cli --home /absolute/new-home step CAMPAIGN_UUID --operation-id diagnose
python -m alpha_factory_v1.core.runtime.successor.transformation_model_cli --home /absolute/new-home step CAMPAIGN_UUID --operation-id develop
python -m alpha_factory_v1.core.runtime.successor.transformation_model_cli --home /absolute/new-home step CAMPAIGN_UUID --operation-id freeze
python -m alpha_factory_v1.core.runtime.successor.transformation_model_cli --home /absolute/new-home confirm CAMPAIGN_UUID fresh-documents.json --freeze EXACT_FREEZE_DIGEST
python -m alpha_factory_v1.core.runtime.successor.transformation_model_cli --home /absolute/new-home export CAMPAIGN_UUID --output /absolute/new-model-evidence.json
```

The confirmation file has exactly one `documents` array containing explicit native
`SourceDocument` records. Exact development-clause reuse is refused; this does not
establish semantic independence or source custody. Candidate retention remains
pending independent review. The unrestricted exact comparator may tie the model
proposal; the adapter makes no general intelligence or discovery advantage claim.

`show`, `pause`, `resume` and `cancel` retain the native campaign controls.
Before proposal acceptance, pause and cancel revoke the call permit. Resuming a
queued pause requires a new exact approval. Pausing an in-flight call consumes its
permit and prevents its response from activating a proposal; it cannot be resumed
or retried. Cancellation remains effective if the old response later arrives.
Construction is one-shot: the Journal records `in-flight` before network I/O. A
crash, timeout, malformed response or failed validation consumes that permit and
retains uncertainty. It cannot be retried implicitly; inspect the failed attempt
and create a fresh campaign and permit if another call is warranted. Accepted
proposals resume without calling the model again. Exports contain no approval or
capability; `validate_model_envelope` only inspects inert evidence.

The host and installed provider are trusted. Numeric loopback, disabled redirects,
no environment proxies, a bounded response, timeout and absent credential lookup
limit this adapter; they do not sandbox a malicious local model server or attest
its billing behavior. Remote and paid providers are unsupported in this version.
