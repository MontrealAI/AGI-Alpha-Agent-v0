# Check a Local Skills task before authorizing it

The bounded Linux preview now exposes an authenticated, read-only `admission` operation. It derives a versioned `agi-fleet/local-admission/v1` report from the existing role package, task format and a fresh sandbox probe. It creates no grant, budget reservation, model request or execution authority.

Use the same private request file shape as `prepare`: `{ "actor": "ACTOR_UUID", "task": { ... } }`. With the installed supervisor running:

```sh
node local-runtime/cli/main.mjs request admission /absolute/path/to/private-request.json
```

The file must have the existing private-file permissions. The operator can inspect any actor; a scoped client can inspect only its own actor using its existing preparation permission. Credential scopes are unchanged. The pinned OpenClaw tool retains its existing action allowlist; this check is currently available through the authenticated CLI/IPC route and is always enforced internally by preparation, authorization and execution.

| Report status | Meaning | Next action |
| --- | --- | --- |
| `SUPPORTABLE` | This exact bounded offline operation satisfies current runtime admission. | Inspect the exact contract, prepare a grant, then authorize explicitly. |
| `MISSING_PREREQUISITE` | A host prerequisite, activation, STOP reconciliation or verified review arrangement is absent. | Follow the named issue and request a fresh check. |
| `OUTSIDE_SCOPE` | The requested task format, platform, operation or authority has no eligible implementation in this preview. | Use a supported format or wait for its adapter; no fallback or grant is created. |

The report includes an exact-input hash, task family, role package/registry/source hashes, machine/session and backend identity, supported tools, the offline provider route, permissions, review arrangement, required artifacts, fixed checks, limits, grant deadline and recovery behavior. A descriptive purpose, rights statement or requested business outcome is retained as the user's declaration; the runtime does not imply that it has evaluated or guaranteed those claims. The deadline is the five-minute authorization window, not a delivery service agreement. Model calls and spend remain zero because this path cannot invoke a provider.

The report's qualification fields are separate: bounded implementation, component/native evidence required for the exact source, current host probe, live observation, operational qualification, independent review and commercial measurement. A synthetic backend remains `SYNTHETIC_OR_UNVERIFIED_PROBE`, even when its fixture succeeds. A native host readiness probe does not qualify the complete product. Historical CI or Dedicated Fleet evidence does not qualify new Local Skills bytes, Mac execution, browser tools, model routes or independent review.

`prepare` records the report and accepted contract inside the committed grant. `authorize` and `run` rederive admission from fresh facts and compare the bound configuration. A changed session, tool descriptor, provider/network arrangement or runtime identity cannot reuse the old grant. Refusal happens before the grant is consumed or a run reserves budget. Grants created before this admission schema must be prepared again. The existing expiry, identity, STOP, one-use, queue and daily-budget checks remain mandatory. Pausing intake retains its existing meaning: already authorized bounded work may finish unless explicitly stopped.

Custom missions previously passed format validation and then failed inside the worker after reservation. They now receive `RUNTIME_UNAVAILABLE` before a grant exists. Browser/desktop work, native Mac local execution, arbitrary code, live models, signing/settlement and independent market review remain blocked. Internal Node checking remains internal regardless of actor count.

## Evidence and remaining work

Run `node --test local-runtime/tests/admission.test.mjs local-runtime/tests/authority.test.mjs` for contract, drift, malformed-format, custom-mission, scope and existing authority regressions. These are synthetic boundary/component tests; exact-archive, native Linux, real provider, physical host, independent review and commercial outcomes require their own observations. This increment preserves all 22 original [acceptance rows](acceptance.json) and does not promote any full-product row to PASS.

Missing implementation includes general files/code/browser/desktop adapters, native Mac isolation/session handling, provider/tool credential admission, operational signer/protocol services, independently verified eligibility/placement, and cross-host authority fencing. Provisioning a live credential or an independent reviewer does not replace those adapters. Once implemented, the qualification owner must provide a declared compatible Linux or Apple silicon host, supported provider access with a specific bounded-spend authorization, exact installed artifacts, a separately controlled eligible reviewer and physical/endurance/human usability observations. None are claimed or activated by this check.

## Français

`admission` indique, sans exécuter ni réserver un budget, si la tâche exacte est prise en charge, si un prérequis manque ou si elle dépasse le périmètre de cet aperçu. Le rapport reste lié au moteur, à la machine/session, aux outils, aux données et au type de vérification. L’autorisation et l’exécution refont ces contrôles; une ancienne autorisation ne couvre pas une configuration modifiée. Une vérification interne ne devient pas indépendante et une réussite synthétique ne qualifie ni un fournisseur réel ni le mode local Mac.
