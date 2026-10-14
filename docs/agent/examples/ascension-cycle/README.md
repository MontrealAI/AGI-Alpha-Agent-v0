[Project notice](../../../DISCLAIMER_SNIPPET.md)

# Disposable Ascension cycle evidence

This bundle is a public synthetic example from the maintained production Studio, actual installed
bounded numerical executor and disposable exact-source EVM. It is historical evidence, not a deployment
profile to enable production writes. The full report identifies the exact source files, test contracts,
fixture actors, environment and actual outcomes. Test wallet addresses and separate local signing roles
do not establish independently controlled people.

The first cycle contains an accurate negative numerical report that is accepted and paid, followed by a
fresh preregistered comparison. The next cycle consumes the accepted report's exact calculation recipe
on different polynomial coefficients and has its own assignment, run, reviewed result and settlement.
Historical payouts, burns and refund custody remain separate from current balances. Reinvestment is an
owner-specific nonbinding proposal followed by the existing separate funding confirmations.

## Read the records

- `cycle-report.json` records the headless production workflow, exact fixture profile and source hashes.
- `cycle-browser-report.json` records the actual Studio browser journey, rendered graph, recovery,
  numerical comparison, reuse, reconciliation and accessibility checks.
- `cycle-*-preposting.json`, `cycle-*-runtime-result.json` and `cycle-*-settlement-record.json` retain
  headless exact requests, prior term seals, native result envelopes and signed settlements.
- `browser-cycle-*-*.json` retain the browser's actual downloads and imported signed records. Ordinals
  identify executed jobs: the first two belong to the first cycle and the third to the successor.
- `candidate-evaluation.json` and `browser-evaluation-*.json` retain frozen comparison criteria and
  original results. The inputs are operator-visible; no independently protected holdout is claimed.
- `financial-*.json` and `browser-financial-*.json` retain receipt-rechecked flows and current-custody
  observations. Historical income is never added to current wallet balances.
- The prepublication kits contain readable exact packages and plans. The private-recovery files retain
  authenticated encrypted full project history, including the original signed record strings.
- `MANIFEST.json` gives the SHA-256 digest of every bundled file and external screenshot references.
  Its checksum is an integrity aid, not current chain state, observer trust or permission.

Original signed files are copied byte for byte. The bundle excludes native homes, private keys, API
credentials, role-approval tokens and active grants. Production qualified profiles remain unchanged.
The separately retained public evidence archive includes the two inspected actual browser PNGs.
This repository copy retains their original digests and text records, respecting its no-binary-diff gate.
No separate remote CI artifact or publication is implied by this archive.

## Open the encrypted examples locally

These passphrases are deliberately public fixture data and are not credentials for an account:

| Example | Passphrase |
|---|---|
| Headless full-project recovery | `encrypted full project passphrase` |
| Headless first-cycle capsule | `local cycle capsule passphrase` |
| Headless second-cycle capsule | `second local capsule passphrase` |
| Browser full-project recovery | `browser encrypted project history` |
| Browser capsules in both cycles | `browser complete cycle capsule` |

From the repository root with Node 22.17.1, the following performs only local decryption and validation.
For a separately extracted archive, change `root` to that extraction directory:

```sh
node --input-type=module <<'JS'
import { readFile } from 'node:fs/promises';
import { importProjectKit } from './docs/assets/nova-studio/cycle.mjs';
import { recoverPackage } from './docs/assets/nova-studio/package.mjs';
const root = './docs/agent/examples/ascension-cycle/';
const project = await importProjectKit(
  await readFile(root + 'browser-two-cycle-private-recovery.json', 'utf8'),
  'browser encrypted project history'
);
for (const cycle of project.cycles) {
  await recoverPackage(cycle.package, 'browser complete cycle capsule');
  console.log({projectId: project.projectId, cycleId: cycle.cycleId,
    seedId: cycle.seedId, planRoot: cycle.package.plan.planRoot,
    retainedRecords: cycle.signedRecords.length});
}
JS
```

The retired disposable chain will not provide new canonical observations. Imported history remains
historical-unverified; a new local chain with the same numeric chain ID is not the original deployment.
Do not install this fixture's registry in production or replay old transactions/grants. For a fresh browser
trial, regenerate the fixture below and use that run's actual identities and explicit prerequisites.

## Reproduce a fresh run

Follow the repository's locked contributor/runtime/browser setup first. Select the pinned Node 22.17.1,
install the contract dependencies from their lock, and provide an absolute supported Python interpreter
with the native runtime and Playwright dependencies. From `tests/contracts` run:

```sh
ALPHA_PYTHON=/absolute/path/to/qualified/python \
ASCENSION_CYCLE_BROWSER=1 \
ASCENSION_CYCLE_EVIDENCE=/absolute/path/to/new-evidence-directory \
npx --no-install hardhat run scripts/ascension-cycle.js
```

The harness creates its own unforked in-process EVM and isolated temporary profile. It invokes maintained
native APIs using test-only loopback transport and preconfigured fixture principals. The separately
retained local-operator test report exercises the supported installation, pairing and role-approval UI;
initial trust/key/token provisioning remains an administrator prerequisite. No paid model or actual
storage service account is used. Physical wallets, human accessibility and Mainnet operation remain
separate unperformed trials.

The harness removes its temporary application/native state. Dispose of retained public fixture outputs
when no longer needed; retain the reviewable reports and required run artifacts for the declared release.
No cleanup or frontend rollback reverses an external transaction. The
[80-case index](../../ascension-cycle-acceptance.json) states the release blockers and prevents this
normal-path example from being mistaken for all requirements passing.
