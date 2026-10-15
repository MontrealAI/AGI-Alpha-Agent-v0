[Project notice](../DISCLAIMER_SNIPPET.md)

# Browser and local-EVM interruption qualification

The opt-in interruption harness extends the existing production-browser, genuine fixed-executor and disposable-EVM
journey. It does not edit the ordinary browser test or enable a production profile. Synthetic wallet actors, storage and
reviewers remain explicit. None of these results establish independent participants, physical wallet behavior, live
provider use, Mainnet operation, profit or human benefit.

## Run against a frozen integrated tree

Install the repository's pinned Node, Python, contract and Playwright dependencies and build the archived profile first.
Use a new evidence directory for every attempt; preserve failed attempts rather than replacing them.

```sh
python -m scripts.build_mark_wallet
cd tests/contracts
ALPHA_PYTHON=/absolute/path/to/qualified/python \
ASCENSION_CYCLE_BROWSER=1 ASCENSION_CYCLE_INTERRUPTION_BROWSER=1 \
ASCENSION_CYCLE_EVIDENCE=/absolute/path/to/new-evidence \
npx --no-install hardhat run scripts/ascension-cycle.js
```

The default harness is unchanged when the interruption flag is absent. The opt-in flag selects
`cycle-interruptions-browser.py` and `cycle-interruptions-native.py`; both identities are added to the retained source map.
The latter delegates ordinary execution to the existing native helper and exposes only extra read-only retained-output
and settlement observation inside the disposable fixture. The actual production runtime and wallet implementations
remain the subjects under test.

## Named points and required assertions

| Point | Injection and recovery |
|---|---|
| Upload | Interrupt the next upload after the capsule CID is saved; restore in a fresh context and explicitly resume without uploading the completed capsule again |
| Mint | Drop the wallet response after an actual local seal transaction; restore the exact pending intent and reconcile its original canonical receipt |
| Approval | Drop the actual approval response; restore and reconcile the allowance transaction before a separately prepared purchase |
| Purchase | Drop the actual purchase response; restore and reconcile without purchasing again |
| Route | Drop the actual route response; restore and recover the exact indexed job from its original receipt |
| Runtime start | Drop the returned output after actual bounded work completes; restore the browser and recover the retained output from a new native process without executing again |
| Delivery | Drop the actual worker submission response; restore and reconcile the exact delivered artifact receipt |
| Review | Drop a real local committee vote response; restore and reconcile before the next distinct vote |
| Settlement import | Drop the response after the native signed settlement import commits; recover the original retained record with no new journal event |
| Claim | Drop the actual rightful-holder reclaim response; restore and reconcile the original receipt without reclaiming twice |
| Successor | Close the browser after explicitly preparing the distinct unminted successor; restore prior cycles and the shared journal without inherited authority |

Each recovery uses a new Chromium context with empty local storage, imports the encrypted project through the production
UI and checks zero wallet requests before explicit connection. Original transactions are reconciled individually. The
account nonce must remain unchanged during recovery; fixture-side send, upload and native-operation counters must also
remain unchanged. Original transaction hashes cannot occur twice in the journey. The transaction hash comes from the
separate synthetic wallet observer, simulating retained wallet transaction history; unknown-hash discovery is not tested.
Native retained observers must leave the verified journal head unchanged. The journey then continues through a distinct
second input, actual execution, review and settlement. A successor session must explicitly re-review and authorize the
retained accepted artifact before consuming it; imported history does not restore the prior authorization token.

Each context closure follows a completed encrypted project export that contains the current pending journal. These are
actual lost-response and fresh-context recovery drills with available portable state, not operating-system power loss
before that state has been saved. The original uncertainty is retained until explicit receipt reconciliation.

The final `cycle-interruptions-report.json` is written only after all eleven points and the complete continued journey
succeed. A partial `cycle-interruptions-progress.json` is useful diagnostic evidence but is not a passing matrix. Review
its exact source map, environment, original pending intents, current receipts and individual recovery records. Full
ordinary browser and financial ledger reports remain separate artifacts in the same run.

## Limits and remaining variants

The upload case covers a retained successful upload followed by a transport failure before the next upload reaches the
fixture provider. It does not claim a solution for an unknown real service-account charge after a lost upload response.
The runtime case covers loss of a completed fixed-work response. Active effectful provider crashes, stop races and
cleanup quarantine retain their separate native qualification requirements.

A passing named lost-response path does not cover every variant: reorgs during recovery, concurrent quote changes,
review-quorum/deadline branches, physical mobile backgrounding and hardware-wallet interruptions need their own retained
results where advertised. All unsupported or unperformed variants remain explicitly disclosed; no acceptance requirement
is weakened or erased to obtain a green report.
