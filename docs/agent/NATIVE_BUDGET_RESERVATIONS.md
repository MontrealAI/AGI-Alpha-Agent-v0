[See disclaimer](../DISCLAIMER_SNIPPET.md)

# Native planning reservations

A single existing native agent journal can coordinate a declared owner's planning
budget across browser sessions. Its existing operator authentication is required.
No new key, token, wallet connection or remote listener is created by this feature.
An owner address is an operator declaration, not proof of wallet ownership.

Each pool is scoped to the exact owner address, chain ID and token address.
Amounts are canonical decimal strings in token base units, never floating point.
The operator explicitly sets a cumulative planning ceiling. Available capacity is
ceiling minus active reservations minus committed amounts. The ceiling is an
operator assumption, not an observed wallet balance or verified profit.

## Authority and deployment boundary

Use one authoritative journal for each owner/chain/token pool. Native processes
sharing that same local SQLite database serialize each check and signed append
with `BEGIN IMMEDIATE` and full synchronization. Independent agent homes, copied
backups, replicas, network filesystems and split-brain deployments do not share
this guarantee. Stop the old authority before restoring or moving a journal.
Do not expose the loopback API or expand authentication scope to enable access.
Use the existing native browser connection and approved deployment mechanism.

A successful reservation constrains cooperating planning sessions only. It cannot
lock wallet funds, prevent external transfers, intercept another application's
transactions, prove solvency or authorize a purchase/payment. Marketplace escrow,
runtime resource grants, validator decisions and wallet confirmations retain their
own independent rules. Browser-only project totals remain observations; they
cannot manufacture a reservation or use an offline snapshot as permission.

## Protocol

The authenticated same-origin endpoints are:

- `POST /api/budget/inspect`: `{owner, chain_id, token}`; returns retained signed
  journal revision, reservations and exact-unit summary. An unknown pool is 404.
- `POST /api/budget/operate`: `{scope, request_id, action, expected_revision,
  reservation_id, amount, purpose}`. Scope has the three fields above. Optional
  reservation ID and amount default to empty string and `"0"`.

Actions:

1. `set_limit`: no reservation ID; amount is the cumulative ceiling. Only an
   unknown pool uses revision zero. A later adjustment requires its current
   revision and cannot reduce the ceiling below existing obligations.
2. `reserve`: a new stable reservation ID, positive amount, purpose identifying
   the project/cycle, and current revision. Insufficient capacity fails closed.
3. `release`: a retained active reservation, amount `"0"`, current revision and
   explicit reconciliation reason. This frees its exact retained amount.
4. `commit`: a retained active reservation, amount `"0"`, current revision and
   explicit reconciliation reason. This retains the amount as consumed planning
   capacity. It records an operator decision, not a verified chain payment.

Every mutation must send `X-AGIALPHA-Journal` with the exact connected journal identity. Missing or changed identity fails closed.

Every mutation carries a unique bounded request ID. Retry lost responses using
exactly the same payload and request ID; no second mutation is made. Reusing that
ID with different terms is rejected. An idempotent response reports the **current**
retained pool state and `replayed: true`, not an old capacity promise. A stale
revision is rejected; refresh and explicitly review changed terms before issuing
a new request. Reservation IDs cannot be reused, including after release.

## Interruption and reconciliation

There is no automatic expiration. A disconnected browser cannot reserve new
capacity. A crash before commit rolls back; a committed reservation survives a
lost response or native restart. If a wallet action's effect is uncertain, retain
the reservation and inspect its actual receipt before deciding to release or
commit. Never infer failure or safely retry a financial action merely because a
browser timed out. Native planning retries do not retry wallet transactions.

Backups include the signed journal history. Full-state snapshots grow with retained reservations and retry identities. Each pool has a 64 MiB logical history budget (UTF-8 event bodies plus conservative row overhead), with additional space conservatively reserved for every active terminal reconciliation. This is not a disk, WAL, index or backup size guarantee: physical SQLite storage and copies consume additional space, other pools share the disk, and operators must monitor capacity. Each pool retains at most 1,024
reservation identities and 4,096 mutation request identities; limits fail closed
rather than prune replay protection or erase obligations. One terminal-operation
slot is reserved per active reservation, so retention limits do not strand its
release or commitment. Reconcile and preserve
history when a limit is reached. Do not create a second independent coordinator
to bypass a full or unavailable one.

## Verification scope

The tests exercise exact arithmetic beyond JavaScript safe integers, independent
native processes competing for the same capacity, process termination before and
after SQLite append but before commit, committed response loss, restart/retry,
stale revisions, identity conflicts, and existing authentication/origin boundaries.
These are software guarantees within the single-journal boundary, not production
wallet safety, audited economic policy, or demonstrated human benefit.

## Same-origin browser desk

Open **Planning budget** in the installed Ascension Studio navigation, or visit
`/budget-studio` on that same native server. English and French forms reuse the
existing token and same-origin API. The page does not contact the hosted Studio,
request a wallet, create credentials, change permissions or widen CORS.

1. Connect explicitly. The existing access token stays in page memory and is
   cleared on reload, disconnect or leaving the page. It is never put in a URL,
   browser storage or a recovery download.
2. Enter the exact declared owner, chain ID and token address. Inspect the
   retained state before preparing a ceiling, reservation or reconciliation.
   Amounts are canonical integer strings in base units; no floating-point token
   conversion occurs. The displayed ceiling is a planning assumption, not funds.
3. Review a request bound to the inspected revision, exact scope and connected
   journal identity. The preview does not mutate the journal. Confirm it
   explicitly to send. The server checks the `X-AGIALPHA-Journal` precondition;
   changed journals, stale revisions and unavailable responses fail closed.
4. Before sending, the page keeps a bounded copy of the exact pending request in
   this tab's session storage, as disclosed beside confirmation. It contains the
   declared owner, scope, purpose, amounts and journal identity, never an access
   token. Storage failure blocks dispatch. Recovery data is untrusted: the page
   validates exact fields, bounds and canonical form and never auto-submits it.
5. After a lost response or reload, reconnect to the same journal, inspect the
   original scope and explicitly retry the unchanged request ID and payload.
   A retry returns current retained state and cannot repeat the mutation. It
   never retries a wallet action. Disconnecting does not release a reservation.
6. An explicit rejection must be inspected and reconciled before clearing its
   local copy and preparing different terms. A malformed copy blocks mutations
   until the operator preserves/reconciles the uncertainty and explicitly clears
   only the unusable tab copy. These controls never remove native journal history.

Inspection expires after one minute of monotonic browser time. Scope edits and
connection changes immediately invalidate previews. Another session may change
capacity at any time; the native atomic revision check remains authoritative.
A recovery download is a private request copy, not a signed receipt or authority.
