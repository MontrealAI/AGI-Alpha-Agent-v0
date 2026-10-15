[Project notice](../DISCLAIMER_SNIPPET.md)

# Explicit market and executor adapters

The selectable Jobs v0 adapter is separate from Alpha's existing MARK route.
Deployed MARK remains fixed to AscensionJobMarket. Sharing $AGIALPHA does not
transfer balances, approvals, identities, grants or settlement rights. Manager's
USDC workflow is a third protocol; no token conversion is performed.

## Exact work convention

`examples/ecosystem/jobs-v0-work-spec.json` is an interoperable test specification.
Its schema is `agialpha.bounded-work-spec.v1`, market is
`agijobsv0-jobregistry-v2`, and executor is explicitly `alpha-native-v1` or
`fleet-linux-v1`. The mission is the strict bounded native Mission model.

The JobRegistry `specHash` is SHA-256 of the **exact UTF-8 file bytes**, represented
as `0x` plus 64 lowercase hexadecimal characters. Do not reserialize, add a newline,
substitute Ethereum Keccak, or hash only the mission. Whitespace changes are a new
specification. The precommission file excludes the subsequently assigned job ID.
Its assignment envelope independently binds chain, registry, token, job, worker,
exact spec hash, profile digest and canonical assignment receipt.

The sample digest is
`0x1cb2ef99471efe7d7213d35ce64d87ed0f67dc8d60988501129a38e06a3ec815`.
Its allocation units are explicitly test resource units, not money or realized value.

## Native Jobs v0 path

A host operator installs `jobs-v0-profile.json` in an **existing** agent home.
This adapter never generates credentials, installs a signer or enables remote access.
`JobsProfile` in `core/runtime/ecosystem.py` defines the strict schema. It requires:

- Explicit backend/version source revision, chain, read-only RPC and confirmations
- Full Ethereum runtime Keccak pins for registry, all three immutable delegates,
  StakeManager, ValidationModule, IdentityRegistry and token
- Exact dependency addresses, 18 decimals and canonical AGIALPHA on mainnet
- A non-mainnet loopback RPC for the disposable-local-fixture scope

A historical deployment manifest or masked runtime-template SHA256 is insufficient.
Full code pins establish selected implementation identity, not an independent
security audit, correct governance configuration or production approval.

After separate wallet admission has actually assigned a job, explicitly run:

```sh
python -m alpha_factory_v1.core.runtime.ecosystem --home EXISTING_HOME admit \
  --spec work-spec.json --job-id 1 --worker 0x... --assignment-tx 0x...
python -m alpha_factory_v1.core.runtime.ecosystem --home EXISTING_HOME execute \
  --binding @ecosystem:EXACT_RETAINED_DIGEST
```

Admission rechecks code, module pointers, paused state, canonical successful
AgentAssigned receipt, exact worker/spec, current Applied state and deadline.
It atomically stores the market binding and one queued native mission. Repeating
the same job returns that retained mission; changed terms conflict. Execution
rechecks admission and uses existing native policy, pause, limits and recovery.
A running/failed/review/completed record is not silently re-executed.

Review the exact artifact through the existing native mission review interface.
Only an explicitly approved completed artifact can be exported:

```sh
python -m alpha_factory_v1.core.runtime.ecosystem --home EXISTING_HOME export \
  --binding @ecosystem:EXACT_RETAINED_DIGEST
```

Export returns the exact artifact bytes as base64 and their SHA256 `result_hash`.
The signed envelope binds the original specification, assignment and reviewed
native receipt. Its signer must be pinned independently; an embedded public key
cannot supply trust. Marketplace submission is a **separate wallet action**.
Repeat exports are byte-identical. After submission/finalization, readback requires
its on-chain resultHash to match those retained bytes. Completed is distinct from
Finalized; this adapter does not infer payment, successful validation or profit.

## Fleet execution boundary

`python -m alpha_factory_v1.core.runtime.fleet_work` accepts the exact specification
on stdin and emits `agialpha.fleet-work-result.v1` JSON. It requires explicit Fleet
selection and supports only supplied-input research, allocation, scheduling and
forecasting. Code execution, model calls, network access, identity generation and
marketplace approval are not provided by this entry point.

The output binds spec hash, mission hash, result hash and deterministic verification.
It remains `computed-unreviewed`. Fleet must independently pin the installed
interpreter and complete source/dependency closure, enforce its stronger process
limits, bind/consume its existing actor/role/source/boot/generation grant, and retain
STOP and uncertain-result handling. A local function test alone does not qualify
that separate Fleet adapter. No imported task may select a shell, Python source,
interpreter path or a new permission.

## Qualification

Focused tests cover wrong chain, bytecode, delegates, dependency token, worker,
specification, state, expiry, missing/reverted/duplicate/removed/foreign logs,
idempotent admission, bounded computation, explicit review, stable signed export,
post-finalization exact readback and cross-job rejection.

A joint local run used real modular Jobs v0 contracts and the actual bounded Alpha
executor, with fixture token/identity/validation dependencies. The independently
reviewed production lifecycle, human benefit, real storage publication, browser
wallet combinations and live deployments remain separate gates. Candidate source
changes require fresh integrated qualification; retained fixture records do not
silently upgrade a later source revision or an external service.

## Native workspace and explicit compatibility choices

The installed agent serves `/ecosystem-studio`, an EN/FR workspace using its existing
bearer token only in page memory. It shows the installed market profile, exact work
file digest, assignment references and retained history before admission. Each
execution and local review requires a separate explicit action. Exports are checked
against their exact SHA-256 before download. Refresh and reconnect read retained
state without replaying execution; an uncertain response calls for inspection first.
Changing installations disconnects the page. The public Studio's goal/market/executor
chooser is navigation only: it cannot install profiles, connect to native services,
change MARK's market, convert tokens or enable an unqualified Fleet adapter.

Native work specifications are limited to 512,000 bytes (the browser uses a
350,000-byte ceiling to leave room for base64 within its HTTP request bound).
Reviewed delivery artifacts have one shared 8 MiB exact-byte limit on both export
and verification; the limit excludes the outer base64 transport representation.
Exports exceeding that limit fail closed. Native Coding remains subject to the
existing host execution policy; Fleet supports only research, allocation, schedule
and forecast. Neither a local review nor a signed artifact establishes marketplace
acceptance or independent human validation.
