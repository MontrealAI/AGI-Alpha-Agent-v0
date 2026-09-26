[Project notice](../DISCLAIMER_SNIPPET.md)

# Use the $AGIALPHA browser workspace

Open [the workspace](../index.html). Start with **Allocate resources**, change an input and select
**Run mission**. No account, wallet, API key or installation is required for the four browser workflows.
The home page implements a bounded version of the original Identify → Learn → Think → Design →
Strategise → Execute loop. The [original vision and flywheels](https://github.com/MontrealAI/AGI-Alpha-Agent-v0#readme) remain available.

## Choose the right workflow

| Workflow | Useful input | Actual computation | Important boundary |
| --- | --- | --- | --- |
| Allocate resources | Up to 18 options with integer cost, value and risk; budget and risk cap | Compares every subset and independently checks totals | Optimum only for the supplied indivisible options and two constraints; values are assumptions |
| Research evidence | A question and up to 20 attributable source texts | Ranks exact passages by goal-term overlap and verifies quotations | Extractive retrieval, without web browsing or model synthesis; a quotation does not prove truth |
| Plan a schedule | Up to 7 jobs with ordered `machine:duration` operations and due times | Compares every job-priority permutation, checks precedence and machine exclusivity | Best within the serial priority policy, not a global job-shop optimum; due dates are soft |
| Test a forecast | 12–2,000 chronological observations, a holdout and horizon | Selects last/mean/drift/seasonal policy on training windows, then measures the untouched holdout | Simple baselines, without confidence intervals or a future-performance guarantee |

Numbers in allocation and scheduling use integer planning units. IDs and machine names use letters,
digits, underscores and hyphens. Forecast holdout uses at most one third of the observations; training
must contain two full seasons. The browser's tighter size limits keep it responsive. **Stop** terminates
its worker. Changing inputs invalidates the displayed result and its review.

The **Advanced** panel accepts the same native mission JSON shape used by the local agent. Apply edited
JSON before running. Imported text is displayed as text; it is never executed as HTML or code.

## Review, remember and continue

Inspect the method, table, checks and limits. Add a meaningful review note. **Approve & export report**
downloads a browser report with the complete inputs, evidence, review and SHA-256 digest. The digest detects
accidental changes; it is not an identity signature or proof of authorship. Approval does not execute
external actions, establish revenue or send funds. **Reject result** leaves the result unsaved.

Select **Save this reviewed mission on this device** if you want it in Mission memory. Only the most recent
20 explicitly saved reports are retained. A saved report's digest is checked before its inputs reload.
Export important reports before clearing browser data. **Clear saved mission memory** removes only this
workspace's saved reports. Storage failures remain visible and do not block a downloaded export.

Use **Download inputs** to obtain a native mission JSON file. Install the [verified release](OPERATIONS.md),
open its local console and import this file. The local runtime adds Ed25519 identity, a signed SQLite
journal, controlled inference, isolated coding, pause/recovery, human approval and $AGIALPHA payment
receipts. Browser previews and the local runtime may use different search policies; rerun and review the
native result before trusting it. The page never connects silently to localhost or requests an operator token.

## Verify a signed agent result

Expand **Verify a signed result from your agent**, select an exported result and supply the agent's
public key obtained independently through a trusted channel. The browser checks SHA-256 content,
Ed25519 signature, identity, completed state, approved result hash and agreement between displayed and
signed content. v1.4.0 exports include the original canonical bytes so Python floating-point formatting
and nanosecond timestamps cannot be changed by JavaScript number conversion. Previous exports remain
verifiable by `alpha-agent verify-export`; re-export with v1.4.0 or later for browser verification.

The file and public key stay on your device. Signature verification establishes integrity relative to
that supplied key, not the real-world identity of an unknown signer, source truth, latest journal state
or mainnet payment finality. The browser does not request a wallet secret or agent API token.

## Real local text generation

The local model lab loads the pinned quantized GPT-2 model used by the Insight studio. The first explicit
**Load model & generate** action downloads about 128 MB of model weights plus the runtime from this site.
Generation uses an ONNX WASM worker on your device. No prompt is sent to a model API. **Stop** terminates
loading/generation. A first load may take several minutes; the five-minute limit fails visibly and permits
retry. A new worker can use the cached model after an offline reload, subject to browser storage eviction.

GPT-2 is a small text-completion baseline, not a reasoning or instruction-following assistant. Its output
can repeat, invent facts or be irrelevant. It is separate from the four checked algorithmic workflows.
For model-assisted evidence synthesis or coding, configure your own local agent. The full Insight studio
preserves its simulation controls and model lab. Minimal development builds intentionally omit the model;
they show an explicit model-unavailable error rather than fabricated output.

## Explore the original demos

The gallery covers all 26 original directories: 24 demos and 2 supporting resources. Search descriptions
or open the [complete launch catalog](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos#readme). Legacy charts replay bundled
illustrative data. Their optional Python button runs a seeded synthetic example using a complete, pinned,
same-origin Pyodide runtime; it does not execute the native demo backend. Optional OpenAI generation is
labeled as paid synthetic-data generation, asks for a model ID and key, and reports provider errors visibly.
Native guides identify required packages, services, simulation modes and historical deployment templates.

## Privacy, installation and recovery

The workspace has no analytics, account system or credential storage. Mission inputs and results stay in
page memory unless you explicitly save or export them. The browser caches public site/model resources.
GitHub receives normal requests for public files; no mission content is included in those requests.
The legacy OpenAI mode sends its request directly to OpenAI only after you select it and provide a key.
Keys remain in memory and are cleared on reload. Use the local agent for private provider credentials.

A content-versioned service worker caches the lightweight workspace and replay assets. Visit online once
and allow installation to finish before going offline. Python and model downloads are separate explicit
actions. Manuals and unvisited external links may still require a connection. If an old page persists,
reconnect and reload; check the release version in the navigation bar. A hard reload or clearing this
site's public caches can recover stale assets. Export saved work before clearing all site data.

Use a current browser supporting JavaScript modules, workers, WebAssembly and Web Crypto over HTTPS.
Chromium is covered by the automated browser acceptance gate; other engines have not been certified by
that gate. Mobile layouts are checked at 390 and 320 CSS pixels. Reduced-motion preferences, keyboard
focus, live status messages and data tables accompany the visual interface.

For local hosting, extract the release's site archive and run `python -m http.server 8000` inside it,
then visit `http://localhost:8000`. Do not open the HTML with `file://`; workers require an HTTP origin.
The browser distribution ZIP remains the separate full Insight application. To roll back public Pages,
redeploy a previously tested immutable site archive; retain the previous release and do not move its tag.
The release workflow deploys the exact tested site artifact and validates the public URL before publishing.

## Publish or refresh the public site

Repository maintainers set **Settings → Pages → Build and deployment → Source → GitHub Actions** once.
There is no need to configure the suggested Static HTML or Jekyll templates. A push to `main` runs the
release acceptance workflow automatically. For a manual refresh, open **Actions → 📚 Docs → Run workflow**,
select `main` and confirm. This entry point calls the same acceptance and publication workflow, including
the complete tests, packaged site, Pages deployment and public browser checks. A branch run validates a
candidate without deploying it. The shared concurrency group serializes main runs, and the Pages job
serializes deployments. An existing published release is never overwritten. A freshness check rejects a run whose tested commit
has been superseded on main immediately before deployment and release publication.

Wait for the full workflow to finish. The site is deployed only after its prerequisite checks pass;
publication follows the public checks. Failures retain logs and evidence for diagnosis. In particular,
the older `invalid tag "$SANDBOX_IMAGE"` Docs failure came from a duplicated legacy Docker action input;
the maintained Docs entry point now uses the release workflow's tested Docker build. The preserved
`mkdocs gh-deploy` scripts are legacy helpers for forks configured to publish from a branch, not the
publishing path for this repository's Actions-based Pages site.
# Ascension Lab — version 1.5.0

[Open Ascension](../ascension/index.html) for a connected journey through the original white paper.
Choose a city, research or enterprise mission, edit its assumptions, compute a portfolio and schedule,
seal a Nova-Seed, explore modeled funding and settlement, then compare the next policy cycle.
The [white-paper implementation guide](WHITEPAPER_IMPLEMENTATION.md) includes the complete walkthrough,
encryption recovery, accounting rules, equation corrections and test commands.

The original workspace below, every demo and the six-stage flywheel remain available. The new lab runs
locally in your browser. Its economic and governance controls are explicitly labeled simulations.

## Insight Atlas

The [Insight Atlas](../insight/index.html) connects twelve opportunity frontiers, second-order agent-firm design
and a claim/evidence explorer. Choose an expedition, compare architectures, replay its evidence and save the
recovery file. All computations run locally; the opportunity envelope and task fixtures are explicit assumptions.
See the [field guide](INSIGHT_ATLAS.md) for exact methods, native mission exports, privacy and recovery.
