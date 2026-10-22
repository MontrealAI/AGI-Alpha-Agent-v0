# SUCCESSOR enterprise → Ascension journey

This additive bridge connects a retained SUCCESSOR Ω enterprise to the existing
Ascension Studio operator. It does not add another executor, database, wallet,
contract suite or trust registry. It is not an autonomous funding service.

## What is connected

1. Activate an enterprise using `successor-harness activate` and retain its configuration.
2. Compile and verify its FusionPlan using the existing Ascension plan tools.
3. Configure the existing Studio operator with the exact enterprise UUID as both
   project and cycle ID, the selected plan index, institutional mission, producer,
   acceptance owner, and operator-pinned chain/code identities.
4. Prepare the enterprise's exact fixed-work request with this bridge.
5. Use the existing NovaSeed/MARK business workflow to seal the plan, obtain risk
   review, fund and bloom a campaign when authorized. These are distinct on-chain
   operations, not performed by this bridge. The NovaSeed must exist before the
   operator can seal the job's preposting terms.
6. Seal the exact terms before routing/posting the job. Export the existing signed
   Studio seal for the business workflow, then obtain posting and assignment receipts.
7. Bind those receipts through the existing code-hash-pinned, read-only chain verifier.
8. Execute only with the required signed, bounded grant. The maintained worker really
   runs; a previous local enterprise result is never relabeled as commissioned delivery.
9. Obtain independent review and submit on-chain settlement through the authorized
   wallet workflow. Import the actual settlement transaction for independent verification.

The enterprise UUID and complete FusionPlan/work request determine the retained
Studio identity. A caller cannot substitute another request digest. There is no
new persistent journey record to drift away from the authoritative Studio journal.

## Additive command interface

Use the same installed runtime and home as the enterprise and Studio operator:

```sh
python -m alpha_factory_v1.core.runtime.successor.enterprise_ascension \
  --home ./agent-home --enterprise-id <enterprise-uuid> \
  --plan ./fusion-plan.json --index 0 prepare

python -m alpha_factory_v1.core.runtime.successor.enterprise_ascension \
  --home ./agent-home --enterprise-id <enterprise-uuid> \
  --plan ./fusion-plan.json --index 0 show

python -m alpha_factory_v1.core.runtime.successor.enterprise_ascension \
  --home ./agent-home --enterprise-id <enterprise-uuid> \
  --plan ./fusion-plan.json --index 0 advance seal --payload ./phase.json
```

The phase file contains the exact revision the operator inspected plus existing
Studio phase fields. For sealing this is `{"revision": 0, "confirm": true}`.
Never guess a revision: inspect `show`. Other supported phases are `bind`, `run`,
`recover`, `accept`, and `settle`, with the existing Studio payload schema and checks.
Grant/acceptance envelopes come from separately authorized principals. Installation,
pairing, signer provisioning, token approvals, funding, admission, unpause and wallet
broadcast are deliberately not phase options. Read-only chain observations may
contact the previously configured RPC service.

`show` reports the authoritative full Studio record, local-work state, configured
chain scope, acceptance and settlement separately. It does not upgrade synthetic
chain observations into mainnet evidence or assume a local acceptance implies payment.
The result has `transactions_sent: false` and `authority_created: false` because
this bridge performs neither operation. An observed settled state does not imply
commercial success, independent capability qualification or measured self-improvement.

## Scope and remaining work

This is a usable software bridge for an already configured operator, not a claim
that the full Ascension economy is live. Existing role/ENS eligibility, stakes,
funds, independent validators, approvals and source-bound deployment configuration
still apply. A token balance alone does not create a business, worker or validator role.

Local tests execute the maintained fixed worker against explicitly synthetic RPC
fixtures. They do not spend tokens or establish live mainnet settlement. The five
Alpha contracts remain separate from the AGIJobsv0 and USDC JobManager protocols;
this bridge never translates a receipt between them. Existing Fleet/Jobs/Manager
adapters retain their own trust, source and operational qualification requirements.

Successor generation from commissioned acceptance, reusable capability qualification,
portfolio selection, opportunity quality and measured recursive improvement need
additional bounded implementation and evidence. The existing local harness derive
operation is not silently granted acceptance by a settled commercial job.
