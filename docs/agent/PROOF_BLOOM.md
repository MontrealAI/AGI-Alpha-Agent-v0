# Nova-Seeds Proof Bloom

[Open the foundry](../bloom/index.html). Five guided experiences share a complete, local proof workflow:
claim → explicit debt → executable jobs → returned evidence → reviewer decisions → capability gate → Chronicle → next mission.

## The five experiences

| Experience | Useful work | What the evidence establishes |
| --- | --- | --- |
| Nova-Seeds Proof Bloom | Allocate a laboratory budget and stress costs | Exact optimal selection among the supplied items |
| Sovereign Bloom Engine | Compare production job priorities and slowed operations | Best schedule within the bounded serial priority policy |
| Alpha Business Ω-Lattice | Allocate a pilot portfolio under budget and risk constraints | Modeled contribution under explicit assumptions |
| Invention Automation Machine | Select a forecasting policy on training data, then challenge the holdout | Error on the specified historical and synthetic stress splits |
| Proof Debt → AGI Jobs | Trace unsupported pilot claims to exact source passages | Quotation provenance and retrieval, not source truth |

The first source job traces the operator's claim and scope. The benchmark job runs the supplied Mission.
The third job changes costs, durations, held-out observations or source ordering according to a disclosed rule.
All inputs are editable. Native research Missions exported from the Insight Atlas can be imported here.

## Run a mission

1. Choose an experience and edit its objective, claim, inputs and stress intensity.
2. Compile the jobs. Changed inputs invalidate the current workbench until compilation creates fresh job commitments.
3. Run the pending jobs. Each return contains the exact job and seed hashes plus a bounded engine result.
4. Inspect every job in the Evidence Docket. Record an accept, reject or repair decision, reviewer name and reason.
5. Promote only when all gates pass. Use **Seed the next mission** to reuse an unchanged benchmark and create fresh probes.

Running a job never accepts a review or promotes a capability. Returning another revision clears its local review.
Reviewer names are self-recorded operator labels. They are not authenticated external reviewer identities.

## Gates with explicit meanings

| Gate | Implementation |
| --- | --- |
| RSI: replay + review | All three returns replay against exact job inputs and all three explicit local reviews accept them |
| ECI: executed advantage | The benchmark improves over the declared baseline; research requires matching exact quotations |
| Move-37: challenge + persistence | The acceptance rule also passes the disclosed stress probe |
| Lineage | Every prerequisite capability is active |

The baseline is input-order allocation or scheduling, last-value forecasting, or zero retrieved passages for research.
Allocation and scheduling use exact bounded enumeration. Forecast selection never reads the holdout; the stress probe
changes only that holdout. Research verifies every quoted passage against its supplied source.
Research's nonzero quotation count is a retrieval result, not proof of a claim's truth or economic advantage.

These are definitions of this implementation, not claims of a universal RSI, ECI, Move-37 or Evidence Docket 6.1 standard.
The portable protocol is explicitly named `agialpha.bloom.v1`.

## Native agents, humans and signed returns

Each job exports a strict native `Mission`, accepted by the existing `alpha-agent` CLI and API.
Use the [operator guide](OPERATIONS.md) to submit the Mission, execute it, inspect the result, record an explicit native
review and export its signed receipt. In the foundry, choose that job, enter an independently obtained Ed25519 public
key and import the approved receipt. The browser verifies the signature over the original Python canonical bytes,
approved result hash, successful native verification and exact normalized Mission input.

A native receipt is attached to the job as evidence of that agent's approved work. The displayed benchmark is separately
computed by the local bounded engine. A signed native result is not relabeled as the browser algorithm's output,
and a valid signature does not establish source truth. Different inputs, unapproved receipts, unknown keys and changed
signatures are rejected before the current workspace changes.

For a portable browser ProofBundle, return the actual downloaded JSON. The receiver recomputes its entire result;
declared `replay_result=pass`, `validator_verdict=accepted` or other extra fields cannot bypass the gate.

## JobSpecURI and NFT plans

The dossier contains job specifications, native Missions, evidence, decisions and local publication plans.
The JobSpec download uses canonical UTF-8 JSON without a trailing newline. Its SHA-256 is the hash in the publication plan.
`jobSpecURI` is `null` until an operator actually publishes those bytes to a content store.
There are no invented IPFS locations, funded jobs or transactions. An AGIJobManager integration requires a separately
chosen deployment, schema adapter, verified publication location and explicit transaction authorization.

Nova-Seed NFT metadata is an unminted plan bound to the seed hash. It does not assert NFT ownership, financial rights,
certification, guaranteed profit or real-world wealth. The visionary claim stays **unproven**, including after promotion;
verified economic value stays zero. Use [Ascension Lab](../ascension/index.html) for the separate encrypted Nova-Seed,
funding and settlement models, and [Insight Atlas](../insight/index.html) for opportunity and agency experiments.

## Chronicle and useful reuse

A promotion stores the exact seed, returned bundles and reviews in a hash-linked event. Recovery replays every admission
and validates the chain; a renamed status or a forged result cannot open the gate. These local hashes detect alteration
against the supplied history; they are not a trusted timestamp or external attestation. Someone controlling an unsigned
file can invent a new self-consistent local review history. Native identity requires a separately trusted key.

The next mission carries an explicit dependency on an active capability and reuses exactly one unchanged benchmark.
It must execute a fresh source job and a different stress probe, then collect fresh decisions for all three jobs.
The interface reports reused jobs, not fabricated revenue or time savings. Reuse still replays evidence for validation.
Changed benchmark inputs require new execution. Revoking a foundation transitively closes every descendant and blocks
future influence. Revocation history remains visible and survives a recovery round trip.

## Recovery, bounds and privacy

The workspace is saved in browser storage after successful actions. Download a recovery file before clearing that storage.
Native public keys are pinned separately on that device; imported recovery files cannot silently establish their own
identity anchors. On a new device, enter each independently trusted key and use **Pin this agent key**, then restore.

Portable JSON is limited to 250,000 UTF-8 bytes and 24 nesting levels. Downloads use readable JSON when it fits, otherwise
canonical JSON. An action that would exceed the complete workspace bound fails before committing state. Each workspace
holds at most 20 Chronicle events. Start a separate workspace when the bound is reached; keep the prior recovery file.
Allocation accepts up to 12 items, scheduling six jobs, forecasts 240 observations and research six sources.

Work runs on the device. No LLM call, external source fetch, wallet connection, NFT mint or treasury payment is performed.
After the first successful cache install, canonical and mirrored pages support offline execution and recovery.
User-supplied text is rendered as text, including source excerpts and reviewer notes.

## Source provenance and implementation differences

The reference HTML was retrieved from `MontrealAI/MontrealAI.github.io` on 2026-09-26. The supplied X text guided the
intent; the X pages were unavailable to retrieval. The original HTML is not copied into this implementation.

| Reference | Git blob | Source SHA-256 |
| --- | --- | --- |
| [v49: Nova-Seeds Proof Bloom](https://montrealai.github.io/goalos-v49-nova-seeds-proof-singularity-console-standalone.html) | `2a2b24b274f56b8c3f1b096ae9c339fcb8f9a349` | `f2f85730093b6cf4db4967a59d75f5520efbf61bb402d17d248da194dbdc03c6` |
| [v50: Sovereign Bloom](https://montrealai.github.io/goalos-v50-nova-seeds-sovereign-bloom-engine-interface.html) | `09d19b03167a87a0dacbca029689a170bdb5eda1` | `4dec291c5959a24a6315348b8ee54027114c5a0c29b267a0a9533ee544b1d0e7` |
| [v48: Ω-Lattice](https://montrealai.github.io/goalos-v48-alpha-business-omega-lattice-sovereign-foundry-interface.html) | `5ef2b01ba902f5dfaca1056a17c15ef13eb7de2a` | `f80fc98c49d4e9a1e931f933f7a666ea2cb1193284292b2df932c839e716df50` |
| [v43: Invention Automation](https://montrealai.github.io/goalos-v43-invention-automation-machine-interface.html) | `398985497aa4d0d2be0ad82f75841253ec540022` | `396170bcc42b9060c954823d2595c2ba60fd4af619f8ee4007b3595b2db0a70a` |
| [v41: Proof Debt → Jobs](https://montrealai.github.io/goalos-v41-proof-debt-to-agi-jobs-interface.html) | `9aee54ba47fdf885f41a45d5ab598460859af6a8` | `e7cc4a3bd16bbc2ad930a5eb08a5ea05225a2f4cb5ef7ef2d40d444832a384c2` |

The reference interfaces include sample acceptance flags, heuristic readiness or leverage metrics, and placeholder
evidence locations. Proof Bloom implements actual bounded computation, exact input commitments, replayed returns,
explicit artifact-bound decisions and revocable lineage. Its design combines the [AGI Alpha](https://agialpha.com/)
visual reference with a new botanical gold sculpture, forest and ivory palette, readable evidence tables and guided actions.

## Validation and release gates

`tests/browser/bloom_engine.test.mjs` covers positive and adversarial engine paths.
`python -m scripts.validate_proof_bloom` exercises all five UI journeys, runs downloaded Missions through the actual native
agent, imports signed returns, rejects altered evidence, checks exact JobSpec bytes, replays unchanged downloads,
revokes dependent capabilities, checks keyboard focus, runs axe WCAG A/AA checks, checks mobile overflow, and executes
offline on the mirrored route. The release workflow requires this on both gallery asset builds and the public site.

[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
