# Existing-marker accounts: direct CREATE qualification (unreleased)

For ordinary deployment without account-specific qualification reports, use
`conventional-eoa-direct-create.v1` as described in
[the Ubuntu creator guide](ubuntu-ephemeral-creator.md#wallet-selection-and-account-code).
It makes only conventional transaction-correctness claims. The stronger marker
profile documented below retains all its original requirements.

`marker-eoa-direct-create.v1` is an additive creator-account profile. It describes
outgoing direct Ethereum type-2 CREATE from an account that already has an exact
EIP-7702 designation. It neither installs that designation nor chooses delegated
execution. The existing empty-code profile and the stricter
`delegated-eoa-direct-create.v1` profile retain their original behavior.

The creator remains an explicit selectable address. The new Manager's governor is
separately and explicitly selected as d76 by the current operator plan. Creator
selection does not rotate fee wallets, treasury, ENS custody or any old deployment.
The present coordinator supports exact direct CREATE envelopes; factory, smart
wallet, wrapped, self-call, batched and type-4 routes remain unsupported.

## Exact policy and evidence

The profile requires only the following policy fields:

```
{
  mode: 'marker-eoa-direct-create.v1',
  delegationCode: '0xef0100' + exact_lowercase_target_bytes,
  target: nonzero_target_distinct_from_creator,
  targetCodeHash: exact_runtime_keccak256,
  qualification: {
    consensusEvidenceSha256: exact_report_digest,
    directExecutionEvidenceSha256: exact_report_digest
  }
}
```

The two reports have different, limited propositions. The consensus report records
the direct-origination interpretation. The execution report covers the exact nine
CREATEs and records zero creator/target invocations. Neither report is a general
delegate-authority audit, account-safety guarantee or declaration of key custody.

The evidence scope binds creator, exact marker and target runtime, source commit
and tree, both source lock hashes, build/catalog identity, canonical block and
Osaka execution profile. It additionally binds all nine indexes, contiguous nonces,
CREATE predictions, initcode hashes and complete envelope digests. Envelopes remain
type2, chain1, null destination, zero value and empty access list; a signature must
recover the selected creator and reproduce every field. An authorization list is
rejected. Changing creator, nonce, linked libraries, constructor input or gas/fee
envelope requires new evidence for the resulting exact operation set.

Reports use strict versioned schemas and exact dispositions. Their artifact hashes
refer to consensus analysis, source/initcode callgraph analysis and execution trace
bytes. Those bytes and the report's claims require external inspection. Schema/hash
validation alone cannot prove truth, completeness, independent review or source
provenance. Never supply fabricated or synthetic test reports for a live campaign.

## Observation and execution boundary

At each canonical observation the implementation reads chain ID, exact creator
code, target code/hash and governor code, then rechecks the canonical pin. It makes
no eth_call to the creator or target for this profile. The existing core verifier
still checks latest/pending nonce, dependencies, expected creation prefix, gas/fee
limits and exact source/build inputs before handing off or relaying.

[EIP-7702](https://eips.ethereum.org/EIPS/eip-7702#transaction-origination) permits
origination from valid designation-bearing accounts. A null-destination type-2
transaction selects creation rather than a transaction addressed to that account.
The separate branches are visible in
[Geth v1.16.5](https://github.com/ethereum/go-ethereum/blob/v1.16.5/core/state_transition.go).
This does not prevent the supplied initcode from calling back into the creator or
target. The required source inspection and exact execution traces must rule that
out, including swallowed failed CALL, CALLCODE, DELEGATECALL and STATICCALL paths.
Checking only CALL destinations is insufficient: a callee can itself carry a
designation pointing at another code address. The narrow analyzer therefore
retains every called address's runtime/hash at the canonical receipt block and
rejects marker-bearing callees, including an alias pointing at creator or target.
It also rejects incomplete/oversized traces, missing stacks, unexplained frame
entries and nested creation/destruction outside its bounded proof scope.

The current Manager constructor reads USDC decimals. A real-state qualification
must include the actual token/proxy implementation path. A local synthetic token
test covers only its own execution path and cannot qualify that dependency.

An existing marker can expose out-of-band behavior. Another transaction, a prior
capability, an account invocation or key compromise can change nonce or balance.
The protocol/profile does not revoke them or establish exclusive control. Any
observed drift or ambiguity stops the campaign; no automatic fee bump, replacement,
new signature or resend is allowed. Local locks cannot coordinate an adversarial
host or another machine.

## Trusted Mac and low-trust Ubuntu

The intended owner workflow uses Ledger USB on the trusted Mac Studio and Hardhat
in Ubuntu Terminal. The Mac must independently obtain and validate the reviewed
source/build, effect intent and exact transaction. Its durable campaign history is
authoritative. Ubuntu may propose inputs and relay an already validated signed
transaction, but its hashes, journal and reported receipt cannot authorize signing
or advance the campaign. The Mac independently verifies the known transaction hash
and canonical receipt before the next physical approval.

The existing core session can recover an externally broadcast transaction from its
durable signed state. An automated cross-machine exchange, external-relay release
transition, physical Ledger transport and global campaign registry still require
separate implementation/qualification. This profile adds none of those capabilities
and creates no persistent device or network access.

Changing creators before any handoff requires a regenerated plan and preflight.
Once a handoff/signature/submission exists, preserve and reconcile it before a new
campaign. The current per-creator locks do not create a global cross-wallet barrier;
a trusted Mac coordinator must track all outstanding capabilities. A new creator
does not invalidate a signature already handed out for the previous one.

## Regression scope

Dedicated policy tests cover exact scope/artifact binding, nonce drift, zero target
calls and retained older profiles. The disposable Osaka trace test uses real
compiled Manager/library initcode, a synthetic pre-existing marker/target and a
synthetic token. Nine genuine signed type-2 CREATEs must leave the marker unchanged,
advance nonce by exactly nine and finish with paused d76 ownership and no creator
moderator/agent/validator exemptions. Every executed call is inspected.
An actual disposable negative creates through an alias-marker callee and swallows
its failing target execution; the analyzer must still reject it. This negative
uses synthetic addresses and does not invoke any selected public account or target.

These tests do not qualify actual 6c8 state, a provider-backed mainnet fork, the final
clean source checkpoint, Ledger hardware, Ubuntu/Mac transport or explorer service.
Owner-accepted audit and Sepolia omissions remain omissions, not test passes.
