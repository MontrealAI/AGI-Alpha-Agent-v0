# One fixed query, one explicit grant

The reserve-pool computation opens one aggregate feasibility bit for each authorized independent world.
That output can reveal information when combined with side information. Fixed scope and explicit output
consent are therefore part of the offering, alongside the established MPC protocol.

`query_authority.py` reuses the existing native **TrustRegistry**, **SignedEnvelope**, Ed25519 checks and
transactional **Journal**. The ten source/license files are unchanged and hash-pinned in
`native_source_manifest.json`, with original commit and provenance records preserved from the battery study.
This study adds only a small, local query-binding wrapper. It does not create a production registry or change
existing validator roles.

## Driver integration

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from query_authority import FixtureQueryAuthority, bind_query

with TemporaryDirectory(prefix="reserve-query-") as temporary:
    authority = FixtureQueryAuthority(Path(temporary) / "journal")
    binding = bind_query(manifest_path, worker_path)
    grant = authority.issue(binding)
    consumption = authority.consume(grant, manifest_path, worker_path)
    # Start the three already configured local workers only after consumption.
    # Do not automatically retry a query after failure or an uncertain outcome.
    # After collecting the result, check the same public inputs and executable:
    assert bind_query(manifest_path, worker_path) == binding
    public_evidence = authority.public_receipt()
```

The driver owns execution. This helper does not run a model, MPC worker, provider, wallet or network request.
It reads only the public manifest and worker source, never a private owner-input file.

**Keep the Journal directory outside the publication tree.** Native initialization creates a private local
identity and API token even though no API is used here. Publish the returned public receipt only; it contains
signed public events, the separately supplied public controller context and an exact journal checkpoint.
Temporary private state is destroyed after the research execution.

## What the grant binds

The signed payload binds the exact manifest bytes, worker bytes, complete scenario family, three owner-input
commitments, public padded dimensions, maximum simultaneous claims, output count and recipients, scope ID,
input epoch, nonce, expiry and retained journal identity. An original 21-scenario authorization cannot approve
the successor's 41-scenario mission. Source reuse does not confer new authority.

Consumption uses the original SQLite `BEGIN IMMEDIATE` transaction. It checks and reserves **both** the nonce
and the `(scope_id, scenario_epoch)` slot before computation. A new nonce cannot reopen an already consumed
scope and epoch. Replay through a new journal also fails because the grant binds the original journal identity.
If execution fails after reservation, the query remains consumed; recovery requires an explicitly reviewed
new authorization and cannot silently repeat an uncertain disclosure.

The research confirmation batch explicitly authorizes **120 independent synthetic worlds and 120 output
bits**. That is a batched experiment, not one prospective customer query. The bounded prospective offering
has **one world and one bit per authorized epoch**. Changing scope, epoch, input commitments or the supported
function requires fresh review and authorization.

## Meaning and limits of the control evidence

`query_authority_controls.py` accepts the study's actual origin and successor public manifests:

```sh
python integration/query_authority_controls.py \
  --origin data/origin_confirmation/manifest.json \
  --successor data/successor_confirmation/manifest.json \
  --worker src/mpc_worker.py \
  --output integration/artifacts/authority-controls-01
```

The exact dataset directory names follow the study driver. Controls preserve old-grant refusals for changed
scope, epoch, source, input and output shape; expired, revoked and altered signatures; scenario omission;
origin-to-successor reuse; replay in a fresh process; and a second nonce for the same epoch. A concurrent
two-caller test checks that the native transaction admits exactly one consumer. A fresh explicit successor
grant is accepted separately. These are authority and integrity controls, not additional independent worlds
or scientific acceptance trials.

All keys and identities are **local simulated roles**. The controller has only the existing controller role;
a validator-only role is tested as insufficient for query control. This does not demonstrate live ENS ownership,
real utility consent, independent organizations, or production authorization. The retained journal and host
are trusted: signatures do not protect against compromise of all keys or rollback of every retained state.
The receipt's checkpoint can be retained independently, but no independent retention service is claimed here.

The fixed query contract reduces opportunities for unapproved adaptive repetition. It does not make the
authorized bit uninformative, establish truthful private declarations, supply malicious-party security, or
qualify remote deployment. Those remain separate obligations of the same offering.
