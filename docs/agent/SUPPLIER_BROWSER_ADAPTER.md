# Synthetic supplier-browser Jobs adapter

This separate native adapter connects an exact Jobs v0 assignment to the existing
isolated computer executor and a separately reviewed supplier comparison. It uses
`agialpha.supplier-browser-spec.v1` and `alpha-supplier-browser-v1`. The four-kind
bounded WorkSpec and Fleet execution contract are unchanged.

## Readiness and scope

The supplied task is a synthetic laboratory. The fixed interface has no purchases,
messages, wallets, logins or browser network capability. Its inputs are bounded
integer quotes for the same quantity. The model must select the commissioned
delivery limit and produce an actual visible comparison. A deterministic reviewer
recomputes totals, eligibility and supplier-ID tie-breaking before a separate local
operator decision. Marketplace validation and settlement remain separate.

Three evidence levels must remain visible:

1. Laboratory protocol tests use explicitly scripted provider/actuator fixtures.
2. A locally configured computer path needs actual Docker isolation and cleanup
   qualification for the exact worker source, image and host before operational use.
3. A commissioned live provider additionally needs explicit account/model setup,
   permitted screenshot sharing, provider-side spending limits and measured live
   acceptance. Neither laboratory tests nor a configured profile prove this level.

The production execution entrypoint always uses `DockerComputer`; it has no host
browser fallback. No executor profile is installed by default. This implementation
is restricted to synthetic inputs and exports no production or settlement approval.

## Prepare exact work and authority

Start from `examples/ecosystem/supplier-browser-spec.json`. Preserve the exact file
bytes when committing its SHA256 as Jobs v0 `specHash`. Input is limited to 64,000
bytes and 16 unique suppliers. Prices are integer cents and are not token balances.
The generated browser interface is shipped code; a work file cannot supply HTML,
commands, provider settings, credentials or network destinations.

Install an independently checked Jobs profile using the existing ecosystem setup.
Separately configure `supplier-browser-profile.json` in the existing agent home:

- `schema`: `agialpha.supplier-browser-profile.v1`
- `scope`: `synthetic-laboratory`
- `image`: the reviewed, already installed immutable Docker `sha256:...` image
- `provider`: `responses` or `vision-json`
- `model`: explicitly selected available model
- `base_url`: explicit provider endpoint; remote HTTPS or local loopback HTTP
- `key_env`: the name of an existing operator-managed credential environment variable

This file contains no key value. The adapter never creates credentials, installs a
profile from a task, pulls an image or automatically starts paid provider work.
See [computer setup and containment](SUCCESSOR_COMPUTER_USE.md). Configure monetary
limits with the provider; action/turn/time ceilings are not guaranteed dollar caps.
Missing usage or invoice data stays unknown. Screenshots and task goals are sent
to the chosen provider only after the exact execution permit is supplied.

## Explicit operator sequence

Use `python -m alpha_factory_v1.core.runtime.supplier_browser --home AGENT_HOME`:

1. `admit --spec FILE --job-id ID --worker ADDRESS --assignment-tx HASH`
2. `prepare --binding BINDING` to inspect provider, image, task/assignment commitment
   and limits without a model call.
3. `execute --binding BINDING --permit EXACT_PREPARED_PERMIT`
4. `show --binding BINDING` to inspect retained evidence and the result hash.
5. `review --binding BINDING --revision REVISION --result-hash HASH --decision approve --note REASON`
   or use `reject` after inspecting the exact result.
6. `export --binding BINDING` returns a bounded signed artifact and exact resultHash.
   Verify the operator public key independently before trusting its local attribution.

The signed computer receipt commits the observed text bytes and screenshot inventory.
The outer artifact binds exact work bytes, assignment, provider/image/worker permission,
observed output, independent arithmetic and local review. Verify using the same pinned
adapter/worker/template source: a different installed implementation is not silently
accepted as the historical execution source. This proves attributed evidence, not
independent certification or an economic outcome.

## STOP and recovery

`stop --binding BINDING` revokes the active computer session even when market
configuration is no longer valid. Provider responses cannot reopen stopped work.
Cleanup failure remains quarantined. Duplicate execution does not replay a session.
Inspect retained screenshots, reserved actions and errors first. Only a stopped or
interrupted attempt with verified computer cleanup can be explicitly reconciled:
`reconcile --binding BINDING --revision REVISION --confirm --note INSPECTION_REASON`.
Then prepare a new revision-bound permit. This starts a new session; it never resumes
old actions. Quarantined cleanup uncertainty cannot be cleared through reconciliation.
At most 16 reconciliations are retained per binding before further execution is refused.


## Native operator screen

Open `/supplier-studio` on the installed local agent. Its English/French interface
uses the existing API token in page memory and binds every action to the connected
journal identity. Importing a 64,000-byte exact work file and preparing permission
never starts a provider. The displayed permission includes assignment, image,
provider, task limits and cost uncertainty. Starting requires a separate checkbox.
STOP remains available while execution is pending; disconnecting does not stop
server-side work. Reconnect to inspect retained attempts after a lost response.
Review, signed export and inspected reconciliation are separate controls. Missing
host profiles close admission/execution without hiding retained evidence. The
public GitHub Pages site does not host this local executor.

### Versioned compatibility evidence

The independently reviewed source tree `bc14e30f29eae669716de5a13aea081fabeee85c`
(local commit `b234de125b19544eb8cc27ee6fe6629b7e682c1f`, published core commit
`a4d6defe0e9802417214c00e89fa0b432b74e5a6`) passed a disposable local JobRegistry
v2 assignment through the actual fixed Chromium worker, scripted Responses
transport, deterministic comparison, local review and verified signed delivery.
The separately run fixture then submitted the exact artifact, approved through a
validation stub and finalized with 100 mock-token base units. The 7,322-byte
artifact SHA256 was `c074755a79ffbea9931114f867e3f2614ea6d1b340d48aad6bed7535930ba379`.
A fresh wrong-delivery-limit browser run was rejected before export; its registry
job remained Applied with a zero result hash. These prove the specific laboratory
handoff, not Docker isolation, live-provider decisions, human time savings or
production settlement. Provider charges remain unknown.
