# Recorded deployments and read-only inspection

`DEPLOYMENT_COMPATIBILITY.json` is the shared integration inventory. Its immutable
source-record URLs, original byte SHA-256 values and Git blobs identify the actual
public projections used for all 39 contract rows. The deployed source revisions are
separate from current application source. Missing creation blocks, ABI/compiler
pins, proxy evidence, ENS attachment and operator acceptance remain explicit.

This inventory records the current instances designated in the 21 October owner
continuation mandate. It does not select wallet defaults, migrate existing work,
carry an older Manager's helper/namespace authority to another address, or establish
current chain state. Fleet's historical Manager and its obligations remain separate.
Manager retains six reported Exact Matches and three retained Similar Matches.
Alpha has no global pause and has no activation or public-funding approval. Jobs'
eight paused modules and Manager's paused intake describe their dated records.

## Verify and consume

```sh
node --test examples/successor-capability/discovery-lab-deployments.test.mjs
```

Load the inventory with `loadDeploymentInventory(raw)` from
`examples/successor-capability/discovery-lab-deployments.mjs`. The compiled expected
canonical SHA-256 authenticates one inert snapshot before asynchronous processing.
Other repositories must use that same exact inventory and consumer source, pinned
by source commit and hashes; an independently copied address list is not compatible
configuration. An ordinary JSON object cannot impersonate an authenticated handle.
`deploymentSummary(handle)` exposes dated status without a readiness promotion.
`assessDeploymentContext(handle, route, context)` rejects wrong chain, stale address,
wrong code, role, token denomination or identity root. A missing ABI/root pin remains
unavailable, rather than an inferred successful check.

`inspectReadOnlyDeployment(handle, deploymentName, options)` accepts the deployment
name `alpha`, `manager` or `jobs`. The installed application must independently
supply a trusted `rpc({method, params, signal})` function, a trusted
`keccak256(hexCode)` implementation and a public credential-free provider label.
Neither function is loaded from imported mission evidence. The observer permits
only `eth_chainId`, `eth_getBlockByNumber`, `eth_getCode` and the fixed `owner()`
`eth_call`. All contract reads use the same finalized block number and the block
hash is rechecked at completion. It retains the method/parameter trace, runtime
hashes, recorded-owner comparisons, block identity and provider label. Failed or
cancelled attempts retain their selected block, partial checks and stopped phase.
Both successful and incomplete attempts retain RPC count and observed elapsed time. Calls are
bounded by per-call and total deadlines, cancellation and a 100-call ceiling.

The inspector establishes only its named code/owner observations. ABI/compiler,
proxy/external authority, token and identity roots, pause/balances/allowances/policy,
participant readiness and activation approval remain separate. A rejected, timed
out, cancelled, absent or failed provider never produces a successful observation.
Fresh live inspection has **NOT_RUN** status in this implementation's evidence;
the tests use an explicitly synthetic provider and establish the adapter contract.
No credential or approved live RPC provider is provisioned by an imported file.

JobRegistry is directly owned by the recorded SystemPause contract; the Ledger
governor is the controller of that owner, not the direct JobRegistry caller. The
inventory and assessments keep those roles separate. Its unqualified SystemPause
execution path produces no wallet transaction draft.

## Operator-controlled intents

`prepareOperatorIntent(handle, route, input)` produces an unsigned draft bound to
the inventory's exact chain, target, denomination and required actor. It requires
explicit consequences and admits no caller-selected target or value. Every draft
is blocked pending current readback, correct ABI identity and operator approval;
its calldata is not presented as decoded or executable. It has no signing,
submission, token approval, funding, minting or activation operation. The operator
must independently decode the call against the actual verified ABI and close all
instance-specific prerequisites before acting through the existing operator path.

These source and synthetic adapter tests are not fresh on-chain evidence, package
installation, public-site reconciliation or operational acceptance. The inventory's
unresolved list is the remaining acceptance scope; changing a status inside an
imported document grants no authority.
