# Existing-owner integration handoff

Run identity: **discoverability-20261022-v1**. This is a prepared, unapplied handoff for the existing native and publication owners. The functioning candidate remains in PR #4872. No shared runtime, publication workflow, permission, contract or version is changed by this file.

## Native registration

The agreed seam is documented in [owner comment 6353311292](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6353311292). The inspected native module is the existing #4871 owner's `examples/successor-workbench/native.mjs` at `34a068e311451ce1d4fcc0a6cea85970a8faf457`, Git blob `d13dd3474483870ee2cd951ea1bda37fa6ba22f0`. It namespace-imports the released engine and registers the thermal adapter through `core.createWorkbench([...])`.

After reviewing this candidate, that owner can make one focused registration addition:

```javascript
import { createDiscoverabilityAdapter, discoverabilityMission }
  from '../successor-discoverability/workbench-adapter.mjs';
import { digitalFault } from '../successor-discoverability/domains.mjs';

const runtime = core.createWorkbench([
  thermalWitnessAdapter,
  createDiscoverabilityAdapter(),
]);
// In the existing example(family) function, before its current fallback:
if (family === 'discoverability') return discoverabilityMission(digitalFault());
```

This is a proposed edit, **not an executed native registration**. Preserve that owner's current source and later changes; the snippet names the semantic addition, not permission to overwrite their file. Regenerate the shared executable closure through the existing generator and use the existing worker/CLI acceptance path on the supported pinned runtime. Review source-bound recovery under the changed closure. The candidate's 13 direct adapter tests establish the pure workbench seam only.

Registration does not repair inherited aggregation-specific Jobs drafts. A subsequent typed commissioning change must preserve the finite decision criterion, acquisition budget, independent evidence check and rejection states. It must not turn `REVIEW_REQUIRED` into institutional approval. Studio/Ascension admission, independent acceptance and candidate-linked settlement remain absent. The original #4863 restriction and #4865 dependency remain intact; this proposal imports none of their held code.

## README and website placement

Prepared copy for the existing flagship catalogue owner:

> **Discoverability Compiler — SUCCESSOR Ω.** Construct a measurement program that makes a bounded decision possible, inspect its independent checks, and reuse valid construction structure for a changed mission. Three synthetic families, conventional ties and losses, invalidated inheritance and two load campaigns are retained. The downloadable experience performs new local computation. Native enterprise commissioning, physical validation and the $100 → $10,000 commercial challenge remain unproven.

Candidate assets already live in the additive `docs/research/discoverability/` namespace: `index.html`, `paper.pdf`, complete LaTeX and bibliography, and `evidence/manifest.json`. Keep these assets together so the relative evidence downloads resolve. Preserve every older paper URL and file. Use the existing reviewed catalogue/site generator and release sequence; do not create an alternate publisher or redirect historical URLs.

Before claiming a live launch, the existing publisher must verify the actual deployed HTML/PDF bytes and evidence links, then perform desktop, mobile and keyboard interaction checks. The current package has static link-closure checks, a minimal DOM control test, and visual review of all 24 final PDF pages. Its local browser opening was denied by the supplied browser policy; that denial was not bypassed. No public deployed route is claimed here.

## Smallest economically useful pilot

Prepare one owner-supplied diagnostic acceptance packet with lawful real inputs, a concrete beneficiary decision, an unchanged acceptance criterion, a competent conventional comparator, a separate acceptor and complete cost recording. The detailed one-bundle protocol is in [VALUE-MECHANISM.md](VALUE-MECHANISM.md). Any customer outreach, executable purchase offer, financial signing or payment needs separately scoped authorization. No demand or price is presumed by this source handoff.

## Generated asset correction for the existing CI gate

The unchanged repository generator was run against an isolated public checkout at `5aef0c1a` with the corrected Discoverability HTML. This PR includes only its three required generated outputs: `docs/service-worker.js`, `docs/assets/service-worker.js`, and `docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js`. Their program and cache policy are unchanged after normalizing the generated cache and asset constants. The existing publisher retains deployment and release authority. `evidence/generated-service-workers.json` binds the 433 inputs and exact outputs; no alternate publisher or workflow was introduced.
