# Foundation synthesis and additive integration plan

Source freeze: `47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`, MontrealAI/AGI-Alpha-Agent-v0.
Exact local SHA-256/Git blob/size/URL records are in `foundation_sources.json`.
This is a source audit, not a rerun of the historical experiments. Main paper mechanisms,
methods, results boundaries, economics, limitations, and publication instructions were inspected.

## 1. Transformational Intelligence: Learning to Change the Game

Source: `docs/Transformational_Intelligence.tex`.

The authorized purpose and hard constraints belong to an intent charter; the inherited
problem formulation and the evaluation instrument are separate objects. The permitted
innovation changes representations, information acquisition, dependencies, intermediate
targets, or coordination while preserving the charter. An unknown constraint is not
automatically removable, and repeated solver failure is not an upper bound.

The retained object is an executable package `(new formulation, construction, realization,
transformation witness)`. The witness names the old restriction, why it is instrumental,
its replacement, the bridge to the original useful outcome, and a falsifier. A feasibility
bridge does not establish optimum quality, side-effect safety, or actual permission.

The exact causal example uses a researcher-supplied two-world model. Passive observations
cannot exceed 1/2 accuracy; a supplied active intervention policy reaches 8191/8192 with
twelve queries. An unrestricted Bellman planner matches it. The example is not an LLM
result, a new causal algorithm, or autonomous model discovery. Query cost can favor less
experimentation or immediate stopping.

Three distinctions transfer directly to the new study:

- Improvement over named tested baselines is weaker than a certified old-formulation ceiling escape.
- Giving the discovered formulation to the original solver separates formulation value from execution skill.
- A no-op, ordinary method, or stop decision remains legitimate; complementary changes can be explored
  within a bounded portfolio without prematurely admitting them.

The source asks to count construction, abandoned candidates, validation, integration,
retries, and ongoing cost. Freeze finalists and confirmation rules before fresh trials.
Holding the entire post-intervention distribution fixed would incorrectly rule out legitimate
interventions; hold initial evidence, tools, authority, requirements, and resource accounting fixed.

## 2. Invent the Economy: Transformational Intelligence for Creating Viable Markets

Source: `docs/Invent_the_Economy.tex`.

An economic possibility is the joint package of technical capability, prospective parties,
transfers/responsibilities, financing/delivery schedule, rights/authority, and evidence.
Technical possibility, modeled viability, accepted arrangement, realized exchange, and a
repeatable market are distinct evidence levels. An AI-generated buyer row supplies none of
the counterparty actions needed for the later levels.

Its exact reference model assumes a common qualification event with probability `p`, shared
construction cost `K`, upfront coordination cost `A`, accepted success price `q_i`, delivery
cost `d_i`, route cost `f_i`, buyer benefit `v_i`, and adoption cost `a_i`:

`expected venture contribution = p * sum(q_i - d_i - f_i) - (K + A)`

`buyer surplus_i = p * (v_i - q_i) - a_i`.

For homogeneous buyers with positive contribution margin, strict profitability requires
`n > (K + A) / [p(q - d - f)]`. Rights, voluntary participation, actual technical validity,
and funding are additional requirements. Because every buyer shares the same qualification
event, adding customers does not diversify that technical risk.

The main supplied four-buyer case uses monetary values in thousands: `K=600`, `q=300`,
`d=75`, `p=0.8`, `B0=900`. Four shared commitments yield expected contribution 120; a
success earns 300 and a failure loses 600. Three buyers have positive success contribution
75 but negative expected contribution -60. Ordinary enumeration with identical options
matches the constructor. Neither customers nor technical cores were discovered.

The cash path is separate: delivery-before-payment requires `K + A + sum(d_i)` before
receipts. The same profitable four-buyer case with only 600 opening cash is rejected.
The source explicitly cautions that the favorable all-adapters-success two-state reference
must gain partial delivery, withdrawal, default, refunds, support failures, and financing
costs in a natural study. Conditional invoices and refundable funds are not free working capital.

The second-stage illustration supplies, rather than measures, reduced setup costs. Setup
300 produces a profitable but unfundable next project when only 300 earned surplus is
available above reserve; setup 150 makes it fundable. No perpetual compounding follows.

For the present study, test technology-only, coordination-only, joint construction, and an
unrestricted ordinary entrepreneur given the same evidence/options. If ordinary methods
find the same package, useful delivery may still exist without a discovery-policy advantage.
Token operations, customer outcomes, and venture revenue/obligations remain separate.
No token price follows from service profit.

## 3. Transformational Autonomous Enterprises: SUCCESSOR Omega Harness

Source: `docs/papers/transformational-autonomous-enterprises-v1.tex`.

This paper implements mission-relative revalidation. Reuse can preserve generic,
content-bound module qualification if source, dependencies, policy and other relevant
identity fields are unchanged and the evaluator owns the cache. Every new mission still
requires fresh input/output and meaning checks, and authority is granted separately.
Descendants start with `currentProof: null` and `authority: []`.

The synthetic compiler changes from weighted bill-of-materials propagation to Boolean
unique-impact propagation. Graph structure is reusable, but a diamond-shaped graph makes
clear why the old arithmetic cannot certify the new purpose. Both algorithms and the finite
grammar are supplied; the construction is typed assembly rather than autonomous graph-theory invention.

Historical results: reuse, full replay, and a supplied direct specialist accept all 40 valid
tasks and reject all eight invalid requests. Reuse executes 64 instead of 1600 generic
qualification cases (96% reduction); fresh checks remain, giving an 88.85% reduction in
the reported reference-step count. The direct specialist matches quality with fewer events,
lower pooled CPU, and better final median wall time. The principal outcome is reduced
redundant checking inside the harness, not a universally cheapest service.

Important correction history: the first Boolean bank was too densely connected and was
corrected before scored construction; a later lineage-metadata repair has a disclosed
known-bank confirmation. The local four-source/API/mock-EVM journey is separate from
installed production-host qualification and settlement. A static view is a replay; fresh
local execution and live reads are separate labels.

Costs are the union of unique attributable lineage events. A shared ancestor is charged once;
alternative arms are not added as if disjoint. Counts of operations, seconds, bytes, token
units, and human minutes remain in natural units until observed prices and allocation rules
justify conversion. Full authoring/model/human costs are unknown in the historical study;
the $100-to-$10,000 ambition was not established.

## 4. The connected contribution to build

The mechanism connecting all three papers is:

1. Discover a consequential requirement and a genuinely binding instrumental restriction.
2. Construct a useful instrument and the arrangement required for affordable delivery together.
3. Preserve the original acceptance conditions and run strong ordinary alternatives.
4. Record complete A/B/C costs and every cash obligation without counting transfers twice.
5. Retain a versioned executable asset only when measured/conditional future value supports it.
6. Execute that asset for a different recipient and a freshly specified useful mission.
7. Recheck semantics, identity, scope, and current authority; stop where evidence runs out.

Use the original studies as design foundations and historical evidence, not as transferable
qualification of the new opportunity or a reason to assume markets, gains, or authority.

## 5. Smallest existing-interface integration

Existing production code at the main freeze:

- `alpha_factory_v1/core/runtime/store.py`: signed append-only `Journal` with atomic transactions.
- `successor/trust.py`: operator-configured `TrustRegistry`, role checks, typed domain signatures,
  explicit revocation, and retained checkpoints. Incoming artifacts cannot install their trust root.
- `successor/flywheel_costs.py`: `CostLedger`, exact signed operations, disjoint A/B/C activity IDs,
  unknown accruals, collection/capital separation, payment reconciliation, and completeness seals.
- `successor/flywheel_access.py`: exact direct ASCII `*.agent.agi.eth` labels; fresh two-reader
  ENSv1 checks pinned to approved code; scope/service/request-bound authorization. No live use is needed.
- `successor/flywheel_capsules.py`: protected capsule scope remains closed. New scientific/other
  arbitrary executable artifacts must not be represented as admitted production capsules.

The recent research adapter is at immutable `231834269599d85e49cfe1ca9917a1a874522d44`:
`studies/agi-alpha-capability-opportunity-v1/integration/bridge.py`, `replay.mjs`,
`source_manifest.json`, and its unchanged vendor closure. It already provides
`run_lifecycle(candidates, operations, ...)` with real artifact bytes plus fixture identity,
and `replay_native(commands, controls=False)` for actual signed accounting. Its native
`flywheel_costs.py` SHA-256 matches current main: `4d2e19b937471bdc247a9b0bb66bd4c315da5a9c6498591bc9f24496e07feb13`.

Minimal new fixture: source-check the existing closure; create a temporary native Journal;
sign one originating A charge, one incremental B charge and any separate C charge; leave
unmetered actual authoring/model costs unknown; verify duplicate cross-bucket refusal,
idempotency, revoked signer refusal, unknown-cost completeness refusal, and production-scope
refusal. Exercise existing research lifecycle retrieval separately with actual capability
bytes and an ordinary-library equal-content control. An independent recipient process must
then execute recovered bytes on fresh work; byte retrieval alone is not transfer performance.

Artificial positive admission evidence, if needed solely to reach encryption/access branches,
must remain a conformance record separate from the real economic admission decision. The
actual zero-collections/unknown-cost ledger should return null complete profit and available
funds. Real Ed25519/AES checks with fixtures do not become live ENS or customer receipts.

## 6. Publication process and current coordination

`AGENTS.md` permits a draft PR with candid failed or unrun local checks. It never authorizes
bypassing installed hooks, access controls, required hosted checks, or owner release sequencing.

`docs/agent/PAPER_UPLOADS.md` defines the existing paper route: the canonical importer adds new
versioned PDF/TEX originals and generates catalog/homepage/worker outputs. Prior originals
are immutable. A passive paper-only history can take the narrow qualification lane; new code,
HTML, dependencies, templates, or mixed histories require full software qualification.
The paper overlay never qualifies executable HTML and waits for its matching public software.
New HTML must be byte-identical in the qualified public software/site pack before a passive
catalog link can use it. The owner must verify actual companion release downloads.

A distinct labeled research prerelease can distribute source/evidence without replacing the
software release. A stable canonical deployed reader still requires the existing publication
owner process. Current coordination preserves main47c17, #4960/#4961/#4963/#4972/#4975/#4978,
their exact reviews and the already allocated publication lane. No new publisher/version
allocation or main merge is implied by this source audit.

The finite held native-source coverage boundary in `FAST_RELEASE_POLICY.md` preserves four
unqualified native/browser outcomes and their original restrictions. Static source matching
does not exercise those outcomes or grant permission to do so.
