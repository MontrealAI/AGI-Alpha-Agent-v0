# Explicit historical qualification path — 2026-10-23 UTC

**The same nine frozen integer cases passed from `tests/contracts/qualification/ascension/payout-small-integers.local.test.js` at 00:27:02–00:27:06 UTC.** No existing contract, fixture, compiler config, dependency or test was changed. The preceding 38-case suite and allocation demo were not rerun.

This path supersedes the initial bundle README's proposed destination under `test/ascension/`. Keep this historical source qualification outside automatic discovery: it intentionally requires the frozen protocol and an explicit evidence output directory and asserts the historical source hash. It is not a permanent immutability requirement for ordinary contract CI.

The unchanged Hardhat configuration sets `paths.tests` to `./test`. Installed Hardhat 2.29.1's test-file selection task reads only that directory when no filenames are passed. A separately recorded read-only invocation confirmed that default discovery excludes the qualification probe and that its explicit pathname selects exactly that one file; no test or compilation ran during this discovery check. See `discovery.stdout.json`, `discovery-phase.json` and the retained checker source.

The test bytes remain SHA-256 `c88f3c4839b69957144de3b9acb374845dd50f93fa420600f3c9763d5cd8b36c` (13,386 bytes), and the original frozen protocol remains SHA-256 `d72950970e93bec2d8cfd58323c2cb2ca1789e6ea018a44bc8604cb619b57a01`. The new directory has the same depth as the initial test location, so `../../scripts/fixture` and both production/mirror source paths resolve unchanged. `placement.json` records their exact paths and hashes.

The new invocation is `qualification-integers-1.json`; full stdout/stderr and all nine raw case receipts under `cases/` are preserved. It ran only:

```sh
node node_modules/.bin/hardhat --config hardhat.config.js --network hardhat test \
  --no-compile qualification/ascension/payout-small-integers.local.test.js
```

Run from `tests/contracts` in an isolated checkout of the recorded source, after documented locked dependency installation and compilation. Set `ASCENSION_SMALL_INTEGER_PROTOCOL` to the frozen protocol's absolute path and `ASCENSION_SMALL_INTEGER_OUTPUT` to a new evidence directory. The phase receipt records the exact Node 22.17.1 command and scrubbed environment used here. No workflow or package script was added.

For p=1,39,40,99, the actual source rejects both posting and bidding below its 100-base-unit minimum; the payout numbers are arithmetic-only. The actual payout journeys were p=100,103,104,3999,4000. All required recipient, supply, escrow and collateral checks passed again. This remains unforked local EVM execution with simulated tokens, mock admission and distinct fixture actors, without live authority, organizationally independent review or thermal/full-harness acceptance.

The earlier 66-file publication ZIP remains unchanged and retains its original invocations and failures. This follow-up is additional evidence, not a replacement result. Its own `MEMBERS.json` and `SHA256SUMS` identify the additional bytes.
