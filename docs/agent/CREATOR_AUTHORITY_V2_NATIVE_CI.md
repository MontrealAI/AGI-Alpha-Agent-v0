# Native qualification of the v2 operator candidate

The additive `Alpha creator authority v2 candidate` workflow runs against the actual PR head
commit, or the exact pushed/manual commit. It checks out that SHA with read-only repository
permission and no persisted checkout credential. A merged commit needs its own run. Existing
release workflows, archived deployments and source records are not edited by this workflow.

## What the workflow exercises

- Existing Node 22.17.1, Python 3.12 and hash-locked toolchains; moderate-severity npm audit,
  strict production/fixture compilation and historical manifest integrity.
- All 111 original contract tests and all 38 authority tests. The authority tests run in four
  non-overlapping serial processes with 17, 1, 1 and 19 cases. The 384 MiB Node heap bound does
  not limit native EDR allocations. Neither failed tests nor ambiguous results are skipped.
- Six lightweight workflow/source/TLS checks plus thirteen offline Git-observer regressions,
  then two separate actual-CLI campaigns: empty
  EOA creation with the guarded raw relay, and delegated EOA creation with external broadcast.
  Each campaign has five CREATEs and two governor bindings. Every successful operational CLI
  independently reads the real clean checkout's commit, tree and lockfile hash.
- Phase-aware preflight, predicted and receipt-proven export, exact unsigned handoff/signature
  import, lost handoff/import output, hashless reconciliation, an accepted local relay whose
  response is lost, refusal to retry, and completion-output recovery. Wrong source labels,
  dirty source, in-checkout/symlinked output, wrong signed value and missing checkpoint fail.

`clean-checkout-cli.cjs` uses a newly created, unforked in-process Osaka EVM only. All dependencies
are mocks; latest-as-finalized is synthetic. Funding, signatures and EIP-7702 authorization
exist solely in that disposable fixture. The fixture's HTTPS server binds numeric loopback,
has no upstream provider and separates read methods from its explicit raw-relay path.

The runner's existing OpenSSL creates a per-run test certificate. Only CLI child processes
trust that certificate through `NODE_EXTRA_CA_CERTS`; normal TLS verification remains enabled.
An untrusted-certificate test must fail before an HTTP request reaches the fixture. There is
no production insecure-transport option, injected source revision or hardware-wallet adapter.

## Evidence and reproduction

The workflow generates its state and XDG directories outside the checkout under `RUNNER_TEMP`.
The actual CLI harness requires `ALPHA_EXPECTED_HEAD_SHA`, `HARDHAT_CONFIG=hardhat.authority.config.js`,
an explicit `ALPHA_NATIVE_PROFILE=empty` or `delegated`, and a NEW outside-checkout
`ALPHA_NATIVE_EVIDENCE_DIRECTORY`. Invoke it from `tests/contracts` using:

```sh
node --max-old-space-size=384 authority-test/clean-checkout-cli.cjs
```

Run both profiles in separate processes, each with a different new evidence directory. The
expected SHA must be the reviewed checkout's actual head. A materialized source snapshot or
an invented Git history cannot establish this qualification. Never substitute a hardcoded
historical source label or reuse a plan from another commit.

The unique run/attempt artifact contains exact source and build-info hashes, runtime versions,
test counts, hash identities of private logs, safe CLI outcomes, and synthetic public receipts
and source packages. Raw runner logs, signed capabilities and private fixture keys are not
uploaded. The harness checks its public files against every signed raw transaction it created
and removes private fixture scratch on exit. Failed or unexecuted checks remain failed or
incomplete; a partial artifact is not a passing result. The full private logs are intentionally
not included because an unexpected library failure could print signed transaction bytes.

## Required source-record and release versioning

The workflow produces a new exact-head inventory and separately scoped result. It does not
promote old `ascension-cycle-current-audit` records to current passes, change their declared
scope, replace the original 80-case acceptance history or imply a fresh human/economic study.
Any later current-source audit must rerun its approved suites and retain new source/run records.

The v2 data schemas do not bump the project release version. Published v1.33.0 remains immutable.
A future published release needs a new approved unused version, updated release metadata and
the complete exact-commit release gates. The release packager's existing document allowlist
also needs an approved additive update before these new operator guides can be claimed as
included in a release package. This draft does not publish or replace an asset.

Passing native CI establishes only the stated synthetic execution and clean-checkout CLI scope.
Physical wallet/SDK operation, actual historical-deployer delegation, public-provider fork and
real dependencies, full Mainnet consensus qualification, explorer acceptance, independent
security review, cross-machine nonce coordination and production activation remain separate
requirements. This workflow makes no live transaction and never automatically unpauses a graph.

## Offline source observation

The v2 observer preserves the historical v1 helper and sanitizes inherited Git repository,
worktree, index, object and configuration overrides. Every Git subprocess forbids lazy fetch,
replacement objects, hooks, fsmonitor, prompts and protocol access. It uses plumbing reads and
raw byte/mode comparisons, never status/diff or content filters. The index must match HEAD
without hidden flags, every HEAD blob must exist locally, and untracked source files reject.

The supported boundary is a standalone, non-shallow SHA1 checkout with no repository config
includes or alternate object store. Linked worktrees and other closure models fail explicitly.
Tracked files are bounded to 64 MiB each and 512 MiB total; missing objects fail without fetching.
Acquire a complete checkout separately before use. No observer failure authorizes a fetch,
repair, filter execution, source-label substitution or retry through a denied path. Small Git
regression fixtures demonstrate these boundaries and are not candidate source qualification.

## Post-RPC input drift

Every operational v2 CLI pins the validated compiler artifacts, build-info files, compiler
input sources and exact operator-input bytes. It re-observes the independent source revision
and pinned inputs synchronously after asynchronous reads, before durable handoff/signature/
submission transitions, before the raw relay call, and before report/package publication.
Late drift fails closed. A failure after a durable submission-attempt record retains uncertainty
even when the local relay callback has not yet run; it never authorizes a retry.

The native harness mutates plan, artifact, dependency and tracked-source bytes during read-only
RPC, restores each fixture before continuing, and requires no handoff/output/journal transition
or relay call. These mutations are disposable tests only. The ten additional lightweight input
boundary tests do not claim full CLI qualification. Exported library routines receive independent
revision/context from their caller; the operational CLIs install the input boundary unconditionally.
Repeated observations assume operator control of the local filesystem and processes. They cannot
prove a hostile filesystem immutable between checks; stop concurrent editors/builds and keep
source, dependencies and private operator inputs under exclusive local control during use.

Signed-raw input files must also be outside the reviewed checkout, including ignored paths and
symlink aliases. Alpha never persists signed raw bytes. Mutable output/journal/lock parent
directories are pinned by canonical path and device/inode across asynchronous reads; session
saves also recheck actor-lock ownership. Replaced parents fail closed under the same trusted
local-filesystem assumption. A status query reports commandBlocked and withholds a relay
acknowledgement while any command-lock entry remains, including a dangling symlink. No status
or acknowledgement is independent permission to send. Malformed private JSON produces generic
CLI diagnostics; private parser input is not echoed into logs or public artifacts.

Command gates are also pinned by parent and file identity. Failure cleanup checks both before
unlinking; if a parent or gate was replaced, the original gate is retained for manual recovery
and the replacement entry is never removed by that command. This check has the same
between-check trusted-filesystem limitation as the other local path observations.

Across each asynchronous command, shared actor parents, actor directories and owner files are
also pinned by identity. Start-error cleanup prevalidates every lease before removing any lock;
copied owner JSON at replacement paths is insufficient. Before journal append, cleanup release
or relay, the command rechecks its gate, actor leases, journal/head device/inode and exact byte
hashes, and the fully validated loaded session. Only its own durable append advances that
expected checkpoint. Already-complete finish retries still perform these checks before release.
