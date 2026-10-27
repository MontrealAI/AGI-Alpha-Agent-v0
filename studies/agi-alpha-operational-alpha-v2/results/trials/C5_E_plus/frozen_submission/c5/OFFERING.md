# Offering: bounded campaign audit

## Beneficiary and useful decision

Select bounded-campaign-audit from offerings.json: a reproducible campaign recovery and reconciliation packet for a software team operating a small multi-tenant job campaign.

The useful decision is whether the submitted execution, artifact, reservation, and internal-credit evidence consistently describes a completed campaign whose outputs are eligible for release. An engineer can inspect a deterministic release/hold result, its reasons, the reconciled summary, and the digest of the exact evidence reviewed. A hold directs further evidence correction or operational investigation. The auditor itself performs no release, transfer, remote repair, or customer notification.

The deliverable is engine.py, test_regression.py, the unchanged test_public.py and supplied components, and REPAIR.md. The full packet digest supports reproducibility and identification of reviewed evidence; it is not a signature or proof of source authenticity.

## Fixed executable acceptance

The acceptance specification is the unchanged CONTRACT.md, including all six release conditions and the exact response and canonical-hash rules. The reproducible local acceptance commands are:

    python test_public.py
    python test_regression.py

Both must exit zero. The local delivered result is 1 passing public smoke test and 23 passing regression test methods, including 120 deterministic generated valid campaigns and associated positive-consumption corruption checks. Test fixtures calculate expected results independently of the supplied component implementations.

Specific required outcomes include:

- Complete, consistent packets release with exact independently calculated wallet, consumption, byte-count, job-count, and sink summaries.
- A pending, failed, canceled, or running job holds.
- Missing, extra, wrong-tenant, uncommitted, incomplete, or corrupt artifact evidence holds.
- A per-job owner or amount swap holds even when aggregate balances agree.
- Missing, additional, misrouted, malformed, or changed-identity settlements hold; valid exact retries preserve financial results.
- Boolean and float substitutions cannot exploit retry equality to pass integer fields.
- The digest always covers the entire encodable supplied packet; independent re-audits and caller mutation checks satisfy the read-only contract.

The specified independent finite evaluator remains an additional acceptance gate. It was not available to this delivery and no result from it is asserted. Prose, an attractive offer, or successful smoke tests cannot waive a failed executable contract case.

## Available evidence and missing live inputs

Available inputs are the synthetic buyer brief, exported-record schema, complete public contract, four verified component implementations, public smoke test, and task-created regression evidence. The expert method and frozen helper provide development guidance and reusable assertions, not buyer evidence.

A real pilot would still need authorized, complete exports from one actual campaign; known initial credit baselines; a mapping from operational job and artifact identifiers to this schema; verification of export provenance and completeness; and a responsible human's release policy. Its usefulness would also need observed manual review effort, defect frequency, false-hold and false-release consequences, integration effort, and acceptance by the intended engineering team. Live credentials are not needed for this read-only prototype, and none were accessed.

The brief contains no customer interview, purchase, willingness-to-pay observation, price, sale, or measured demand. No revenue, savings, accuracy percentage, or universal guarantee is claimed. Any proposed commercial price would be a separate untested hypothesis.

## What would falsify this offering

A valid in-scope packet that incorrectly holds, or an invalid packet that releases, falsifies the auditor's claimed behavior for that case. Incorrect summaries, wrong input digests, mutation of caller evidence, nondeterministic results, or output aliasing also fail acceptance. Such counterexamples require a repair and rerun of executable acceptance before using the result.

The usefulness hypothesis would be undermined if authorized campaign exports cannot supply the required evidence, if the target team needs production actions rather than an inspectable read-only decision, or if measured export and review effort outweighs the engineer's benefit. An internally consistent fabricated or incomplete export also exposes the boundary: reconciliation alone cannot establish external authenticity or completeness.

Automatic live remediation and universal exactly-once certification are outside the available evidence, permissions, and finite contract. They are not part of this offering.
