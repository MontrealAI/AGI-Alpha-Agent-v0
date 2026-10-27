# Offering: bounded campaign recovery and reconciliation audit

## Selected proposal and evidence status

Selected proposal: **`bounded-campaign-audit`** from `offerings.json`.

The deliverable is a reproducible, read-only auditor, regression evidence, a
release/hold result and a digest covering the entire submitted packet. The buyer
brief is researcher-constructed. No customer interview, sale, price observation,
willingness-to-pay result or measured demand is available. No commercial outcome
is claimed.

## Beneficiary and useful decision

The proposed beneficiary is the software engineer or operations reviewer
responsible for a small multi-tenant job campaign. The useful decision is whether
the submitted records satisfy the published requirements for releasing that
campaign's outputs.

A successful replay of each service alone does not establish agreement between
services. A campaign can have successful-looking component snapshots while an
artifact belongs to another tenant, a job never succeeded, or the correct total
credits were assigned to the wrong jobs. This auditor checks those relationships
and returns an inspectable decision tied to a complete-input digest.

The value hypothesis is that a reproducible check could reduce repeated manual
replay and cross-record comparison. Saved engineering hours, incident costs and
adoption are unmeasured hypotheses. A user still decides what action to take;
the prototype itself releases nothing.

## Concrete delivery and acceptance

Delivered files are `engine.py`, `test_regression.py`, `REPAIR.md` and this offering
note. The existing `test_public.py` and four component implementations are
preserved. The auditor consumes the exact JSON-compatible packet described in
`CONTRACT.md` and returns its exact `campaign-audit/1` envelope:

- `release` requires complete successful execution, matching settled journal jobs,
  exactly the committed tenant artifacts, exact per-job credit transfers, and
  reconciled final balances.
- `hold` includes at least one descriptive reason and an empty summary.
- `packet_sha256` commits to all supplied evidence when canonical encoding is
  possible, including retries and invalid-but-encodable packets.

Executable acceptance remains **`CONTRACT.md`, the unchanged public smoke test,
and the independent finite case evaluator**. This proposal does not substitute
for that acceptance or weaken any release gate. Observed local acceptance is the
public smoke passing and a combined run of 26 public/regression tests passing,
including 80 generated campaigns with independently derived expected summaries.
The independent evaluator was not available to this implementation run; no result
for it is asserted.

An operational evaluation, if later authorized and supplied with suitable data,
would compare the auditor's outcomes with a reviewer's labeled campaign cases
before integrating it into any release workflow. Such an evaluation is a future
input to the offering, not a completed deployment.

## Missing live inputs

The bounded prototype can execute with the synthetic records already provided.
Assessing real usefulness requires additional evidence:

- Representative, complete exports from the intended service versions, a stable
  declaration manifest and a demonstrated mapping into the packet schema.
- Evidence provenance, tenant identity validation and a way to establish that
  exports describe the intended campaign and observation boundary.
- Known-good and known-bad historical cases with independently reviewed expected
  outcomes, including the types and frequency of missing or contradictory data.
- The actual release review process, the decision owner, acceptable handling of
  holds, and measured manual effort before and after using the auditor.
- Realistic packet sizes and runtime constraints; any adapters and operational
  monitoring needed to maintain compatibility as services evolve.
- Actual user feedback, willingness to adopt, and cost/price evidence before
  making commercial claims.

Credentials, remote execution, automated rollback and customer messaging are not
required for this read-only deliverable. They would constitute a separate scope
with separate inputs and authorization.

## What would falsify the offering

**Executable correctness:** A finite contract case that releases despite an
unmet release condition, holds a valid campaign, produces the wrong complete-input
hash, changes supplied evidence, lets one audit affect another, or escapes the
required error envelope would refute the relevant correctness claim. Swapped
per-job amounts that preserve totals and cross-tenant artifact substitutions are
specific counterexamples the regression suite already exercises. Failure of the
independent acceptance evaluator would mean the delivered implementation has not
met the fixed acceptance bar.

**Decision usefulness:** Representative users may already obtain the same checks
more cheaply, lack sufficiently complete exports, find first-error reasons too
limited, or spend more effort preparing packets than they save reviewing them.
A measured evaluation showing those outcomes would weaken or falsify the value
hypothesis even if the executable contract passes.

**Commercial viability:** Absence of willingness to adopt or pay after suitable
user evaluation would falsify a commercial offering hypothesis. There is no
observed price or sale to extrapolate from today.

This proposal does not claim remote self-healing, production authorization,
authenticity of submitted evidence, exactly-once behavior in arbitrary distributed
systems, or a universal correctness guarantee. Those claims are not established
by this finite in-memory audit.
