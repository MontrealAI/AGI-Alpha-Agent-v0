# Campaign audit repair

## Delivered behavior

The public audit(packet) function remains a deterministic, read-only decision over one complete evidence packet. It returns the exact campaign-audit/1 top-level schema. Release requires every public campaign condition; rejected or inconsistent evidence returns hold, descriptive reasons, and an empty summary. Each invocation builds fresh instances of the four supplied components. The component implementations, canonical public test, contract, offering brief, and frozen helper remain unchanged.

The repair closes these integration gaps:

1. The scheduler must contain exactly the declared jobs, all succeeded, with zero used capacity. Pending, failed-to-pending, running, and canceled jobs cannot authorize release.
2. Required artifact identities are the full (owner, upload) pair. Every supplied record must already be committed. The auditor restores and verifies the bytes and SHA-256 without upgrading an active record into acceptable evidence. Missing, extra, reused, duplicate, incomplete, corrupted, or wrong-tenant artifacts hold.
3. Each positive-consumption job requires its literal settlement:job-ID request and exactly one transfer from that job's declared owner to __usage__, for that job's accepted Journal consumption. Swapping amounts or owners between jobs rejects even if all aggregate balances match. Zero-consumption jobs require no batch.
4. AccountBook still determines optimistic revision validity, ordered replay, and exact retry identity. Before invoking it, the auditor validates every batch's operation and revision integer types, including retries. Python equality between integers, booleans, and integral floats cannot bypass the public numeric contract.
5. packet_sha256 remains the SHA-256 of the entire original canonical input encoding, for both release and encodable hold results. Mapping order is irrelevant; list order and added exact retries remain evidence changes. Unencodable evidence returns a null digest.
6. Reconciliation explicitly compares accepted consumption, every Journal wallet, every final owner balance, zero reserved credits, and the usage-sink total.

Job and command shapes are validated, while component replay enforces its own dependency, ownership, lease, event, artifact, and revision rules. Journal consumption comes from the accepted export log, so exact event-ID retries are counted once. One local failure is sufficient to hold; a successful result from another component cannot waive it. Reasons report the first encountered failure rather than promising exhaustive diagnostics.

## Engineering and test evidence

The implementation followed expert_v1.json: map identity and transitions, preserve component boundaries, reproduce integration failures, repair coherent checks, and add executable regression cases. No network, additional model, private tests, other task results, or external answer sources were used.

Before repair, seven selected regression methods were run against the original engine. All seven failed, reproducing wrong full-input hashing, unfinished-job release, wrong-tenant artifact acceptance, active-artifact acceptance, per-job amount swaps, per-job owner swaps, and numeric-equal malformed settlement retries.

After repair the following actual commands succeeded:

    python test_public.py
    python test_regression.py

The unchanged public smoke test ran 1 test and passed. The regression suite ran 23 test methods and passed. It includes 120 deterministic seeded campaigns with independent expected wallet and summary calculations, plus settlement corruptions for campaigns with positive consumption. Other cases cover multiple tenants sharing an upload string, same-owner dependencies, zero consumption, empty artifacts, unused owners, Unicode/literal job IDs, failed execution followed by a new lease, old finish retries, exact journal and account retries after intervening actions, changed retries, stale revisions, malformed JSON shapes, numeric boundaries, digest fidelity, deterministic re-audits, and caller mutation.

These observations are local finite evidence. The independent finite contract evaluator was not supplied or inspected; its outcome is not claimed here.

## Use of the supplied frozen helper

The development-origin contract_probes.py was read with learned_v2.json and CAPABILITY.md and imported unchanged by test_regression.py.

- assert_idempotent checks that immediately repeating audit over the same evidence returns the same result without changing the observed packet. A separate pre-call copy also checks first-call input preservation.
- assert_independent_result mutates a returned summary and reasons, then checks the packet and a fresh audit result against independent frozen observations.
- assert_rejected_unchanged is not used: this API represents rejection with a hold result rather than a raised exception. Direct regression assertions check hold schema, reasons, digest, and unchanged input instead.

The helper supplies reusable observation assertions, not campaign semantics or a settlement oracle. Domain fixtures, expected summaries, and invalid cases were written for this task. No measured comparative benefit, model change, weight update, or new learning advantage is inferred from its use.

## Scope and remaining limits

This is a bounded sequential in-memory Python prototype over small synthetic JSON-compatible campaigns. The supplied components remain its execution foundation. There is no cross-process persistence, crash recovery, race testing, signature verification, authenticated identity, remote remediation, live release action, real currency, or physical delivery. The owner strings and exported evidence are asserted inputs; a valid self-consistent packet does not prove that unobserved external work happened.

Finite tests do not prove universal correctness. Arbitrary hostile Python objects and external side effects are outside the contract. The tool runner's final status and freeze record provide actual operation, elapsed-time, execution, and output metrics; monetary cost and hosted token totals are unavailable rather than estimated.
