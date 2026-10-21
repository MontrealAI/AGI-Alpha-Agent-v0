[Research disclaimer](../DISCLAIMER_SNIPPET.md)

# SUCCESSOR Ω: capability-development workspace

[Open the workspace](../successor/capabilities/index.html). This first workspace is English-only; existing bilingual
flagship pages remain unchanged apart from their additive bilingual navigation link.

This additive local workspace develops a proposed **means of discovery or production**, not just an isolated task.
Describe an unmet need and a family of problems; identify a restrictive assumption; propose an instrument,
representation, experimental architecture or productive architecture; preserve the intended objective; and specify
construction, falsifiable acceptance and reuse obligations. The editable proposal is deliberately open-ended.
An unsupported proposal remains a proposal, even when the optional synthetic example passes.

## What is implemented

- An editable capability brief with purpose, constraints, scope assumptions, construction and reuse plans.
- Frozen version snapshots before evaluation, retained predecessor references and an append-only event history.
- A bounded, executable synthetic measurement instrument, including constructed coefficients and exact observations.
- Development evaluation, then reuse of the same construction for distinct threshold-screening and ranking tasks.
- Computed failure when the synthetic function violates the chosen interaction-order assumption.
- Complete JSON export/import and a separate local IndexedDB namespace using the existing mission store.
- Recomputed evidence on import: hashes alone cannot turn an invented result into an admitted computed result.
- Economic hypotheses about beneficiaries, value, costs, financing and adoption, always separate from commitments.

No model proposes a new instrument automatically. No physical platform is built or qualified. There are no fabricated
customers, contracts, revenue, funding, independent reviewers or claims of novelty. Descriptions can propose ambitious
capabilities; only the supported, explicitly selected synthetic instrument is actually constructed here.

## First complete journey

1. Describe the capability and the original objective. Select either a proposal-only record or the optional witness.
2. Save the frozen version. Editing the visible inputs creates an uncommitted draft, not a revised successful version.
3. Construct and evaluate the instrument. Inspect the calibration observations, derived coefficients and comparisons.
4. Evaluate held-out reuse without changing the instrument. Every response must match, even if a downstream decision
   happens to agree by accident. All cases and failures remain in the evidence.
5. Create a successor with an explicit change and rationale. Prior evidence remains attached to its original version.
   New versions have no active evaluation. Reusing previously exposed masks is conservatively labeled as exposed, even when the seed or world changes.
6. Save/export, reload and reopen the entire history. Keep a downloaded copy before clearing browser storage.

## The bounded synthetic witness

The fixed executable constructor uses exact integer arithmetic on four to eight binary inputs. It calibrates a
multilinear representation of degree one or two by observing basis masks and applying Möbius inversion. Users may
change the bounded seed, world coefficients and declared class. This constructs a reusable response model, rather
than recording a prewritten success result. It does not execute user-supplied JavaScript or generated code.

Development checks response reconstruction on non-calibration masks. Reuse checks exact responses, threshold screening
and ranking on disjoint non-calibration masks. The configuration and objective are frozen before either phase; the
retained construction is used unchanged. Cases are deterministic and publicly inspectable, not a blinded benchmark.
A third-order synthetic interaction is an explicit negative control against a second-order construction. It can fail
without changing the user's objective or overwriting the positive result of an earlier version.

All operation and observation counts are abstract software counts, not measured currency, physical labor, energy or
calibrated customer value. Reconstruction and import checking repeat computation and expose their costs separately.
This is not superiority over an unrestricted engineer: the known finite-class representation is the disclosed method.

## Research basis and limits

- [Transformational Intelligence](../Transformational_Intelligence.pdf): distinguish purpose from restrictive means;
  carry an executable realization, a bridge to the purpose and falsifiable evidence.
- [Invent the Economy](../Invent_the_Economy.pdf): separate technical correctness, participant benefit, profitability,
  liquidity and actual voluntary exchange. A positive model does not establish customers or commitments.
- [Out-Evolve](../Out_Evolve.pdf): construct reusable means that make a simpler model applicable, and qualify the
  assumed function class before transferring evidence to a successor.
- [The World as an Output](../The_World_as_an_Output.pdf): protect a family of future operations, not merely a first
  readout; retain the assumptions under which reuse is valid.

The last two works contain conditional mathematics and executed synthetic studies, not proven physical deployment.
The browser witness is a separately implemented, much smaller illustrative construction. It does not claim to
reproduce the papers' complete studies, physical architectures or reported numerical results.

## Additive integration and preservation

Baseline: public main `a6d20a93c7c5b7430bf42d2367701b350513e90d`, fetched on 2026-10-20.
The new workspace sits beside the existing flagship and uses existing canonical JSON, bounded parsing, SHA-256 domain
separation and transactional mission persistence. Its source modules are `examples/successor-capability/`.
The deterministic generator is `scripts/generate_successor_capability.py`.

Alpha discovery, bounded Jobs commissioning/evaluation, Fleet execution/review and the existing
[guided project history](GUIDED_SUCCESSOR_JOURNEY.md) retain their existing schemas and meaning. There is no conversion
or replacement of native project files. The two payment routes remain distinct: AGIJobManager uses USDC; AGI Jobs v0
JobRegistry uses AGIALPHA. This workspace has **no payment route**, grants, wallet integration or dispatch adapter.
Nothing here commissions those systems or turns a capability description into an executable external task.

The source manifest beside the generated page records the exact included source hashes. Hashes establish byte
consistency, not publisher identity, scientific truth, independent review or authority. The record's witness version
must match its evaluator; incompatible records are rejected instead of silently being promoted. Preserve the original
file and matching source version for historical inspection.

## Recovery and limits

Local browser persistence is a convenience, not a backup or trusted external journal. It uses a separate database,
`agialpha.successor-capability.v1`, so existing missions and guided histories are not modified. Storage revisions are
independent of record event indices. A failed save leaves the new record in memory for export and retry. Conflicting
saved branches cannot be silently replaced. Imported text is bounded and duplicate JSON keys are rejected.
The saved-history list fails closed if any stored envelope is corrupt; this first slice has no per-item quarantine
interface. Retained JSON copies remain the recovery path in that case.

A record is limited to 2 MB, eight versions and 24 events; the reused store permits twelve saved workspaces. Limits
refuse additional writes rather than dropping old evidence. Export does not imply successful disk retention. Recomputed
imports validate internal consistency only; they cannot identify a fabricated author, a previously exposed external
benchmark, a deleted history prefix, or rollback if the user's independent copy is also lost.

## Reproduce and future integration

```sh
node --test examples/successor-capability/*.test.mjs
python scripts/generate_successor_capability.py
npm ci --prefix tests/browser --ignore-scripts
AXE_SCRIPT=tests/browser/node_modules/axe-core/axe.min.js \
  CAPABILITY_SCREENSHOTS=capability-evidence python tests/browser/test_successor_capability_browser.py
```

Serve the repository locally, or open the generated self-contained page in a modern browser. Storage availability for
local files varies; complete JSON export is the portable backup. No credentials, provider or model download is needed.

Future work includes user-authored bounded experimental interfaces, separately validated physical/simulation adapters,
credible alternatives, independent evaluation, measured costs, real voluntary demand, financing evidence and explicit
native project references. Every external execution or paid commitment requires its own adapter and authorization;
none is inferred from this local blueprint or a synthetic pass. Existing release, deployment and policy lanes are
unchanged. This branch is additive review material. Reconcile it against the eventual released baseline and pass all
required checks before integration; publication of the current release candidates remains separate.

The separate **SUCCESSOR capability workspace** CI lane recomputes the source bundle, checks its exact CSP/source
closure and gallery cache, and runs the real browser acceptance. Its screenshot artifact includes the tested commit
and source manifest. Existing release workflows and their concurrency groups are unchanged. Gallery generation now
regenerates this workspace and preserves its exact self-contained bytes during link postprocessing.

Browser acceptance covers proposal creation, construction, computed evidence, frozen reuse, a cubic negative control,
both mixed-phase outcomes, a later passing successor with the failed predecessor retained, exact JSON recovery,
conflicting tabs, failed-save retry and reopening IndexedDB in a new browser process. It checks keyboard navigation,
320/390/768/1440-pixel layouts, the 125% larger-text control and separate 200% text sizing. Axe checks selected WCAG
A/AA and best-practice rules; these automated checks and scoped visual inspection are not a full accessibility
certification. English-only copy remains an explicit limit of this slice.
