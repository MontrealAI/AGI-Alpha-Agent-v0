# Proposed offering: bounded campaign audit

**Selected proposal:** `bounded-campaign-audit` from `offerings.json`.

**Deliverable:** an executable, reproducible campaign recovery and reconciliation packet: the read-only `audit(packet)` function, regression tests, documented limits, and a release/hold result tied to a digest of the entire submitted evidence.

## Beneficiary and useful decision

The beneficiary is a software team operating a small multi-tenant job campaign. An engineer responsible for releasing campaign outputs can use this auditor to determine whether the exported execution, artifact, reservation, and internal-credit records jointly satisfy the declared campaign contract. A release result means all specified evidence checks passed. A hold gives a reason to investigate the supplied packet before releasing outputs.

The useful distinction is cross-record consistency: independently successful services may still refer to different tenants, jobs, artifacts, or amounts. The auditor joins those identities and checks each job's charge before reconciling totals. The full-packet digest lets the engineer identify the precise evidence reviewed, including retries, without confusing financially equivalent histories with identical evidence.

This is an inspectable decision aid for the synthetic brief. The brief supplies no customer interview, willingness-to-pay observation, sale, measured failure cost, or timing comparison with an engineer's manual reconciliation. No commercial price or quantified savings is asserted.

## Acceptance

Acceptance remains executable and fixed: `CONTRACT.md`, the unchanged canonical `python test_public.py`, and the independent finite contract evaluator. This proposal does not replace any part of that acceptance with documentation or a narrower claim.

The delivered repair passes the observed public smoke test (1 test) and the added regression suite (22 test methods, including table-driven cases). `REPAIR.md` records the reproduced failures and corrected behavior. No independent private acceptance result has been observed.

For a concrete submitted packet, the accepted output must use the exact schema and canonical full-input hash; release requires successful component replays, all jobs succeeded, settled Journal records with exact owner/cap binding, the exact set of committed verified artifacts, one correct logical batch for each positive-consumption job, no batch for a zero-consumption job, and final per-owner and sink reconciliation. Every malformed or inconsistent in-scope packet must return hold without mutating caller evidence.

## Missing live inputs and deployment decisions

The current inputs are synthetic exported records and verified in-memory components. A live team would still need to supply complete campaign declarations, initial-credit provenance, ordered Journal events and scheduler commands, artifact snapshots with bytes and digests, and original settlement batches including expected revisions. The team would also need to establish how those exports were obtained consistently and how asserted tenant identities were authenticated. This prototype does not supply that provenance.

Adoption would require a team-owned release policy, a human responsible for resolving holds, agreement on supported component/export versions and workload limits, and a way to associate the returned packet digest with the reviewed evidence. Observing actual review time, false-hold investigation cost, and avoided release mistakes would be necessary before claiming economic value. Live credentials, automatic repair, rollback, signatures, customer notification, real currency, and production operational certification are not included in this deliverable.

## What would falsify the offering

A single in-scope false release, erroneous hold of a valid history, wrong full-packet hash, missed changed-intent retry, duplicated charge, tenant/artifact confusion, caller mutation, or cross-audit state leak would falsify the executable contract claim and require repair and revalidation. The independent finite evaluator can reject the prototype regardless of the proposal wording.

The practical usefulness hypothesis would be weakened or rejected if teams cannot export complete compatible evidence, if the digest cannot be associated with trustworthy records, if they do not make this release decision, or if measured review effort and mistakes do not improve relative to manual replay. Those outcomes cannot be decided from the synthetic brief.

The stronger menu alternatives, live self-healing and a universal exactly-once certificate, require capabilities and evidence absent from this bounded read-only task. No promise of either is made here.
