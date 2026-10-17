# SOL-2026-7 interim compiler candidate

This isolated candidate starts at `299408ccc1b8efc97f742f5ac0971b69a87a1524`
(tree `6bbb029bfd0835bbd372b25f8f6ea81451dfd9e7`). It changes the compilation
profile, not the Solidity contracts or existing deployment records. Existing
plans, bytecode, verification inputs and deployment evidence must not be reused
for this candidate. Recompile and qualify the exact new source revision.

The locked compiler remains Solidity 0.8.37, with optimization enabled, 200 runs,
viaIR and Cancun. `tests/contracts/scripts/compiler-policy.js` defines the sole
profile used by production, fixture and creator configurations. Its Yul sequence
is the v0.8.37 default with only uppercase `L` (LoadResolver) and `E`
(EqualStoreEliminator) removed. Cleanup remains exactly `fDnTOcmuO`.
This is a narrow workaround for YulOptimizerKnowledgeBaseStaleBookkeeping,
not a guarantee against all compiler bugs or an independent security audit.

Upstream references:
- https://github.com/argotorg/solidity/blob/v0.8.37/libsolidity/interface/OptimiserSettings.h
- https://github.com/argotorg/solidity/blob/develop/docs/bugs.json
- Reproducer source revision: `00d5ee65698ccc9eeeeb6b1c29f9fe694c869139`,
  `test/libsolidity/semanticTests/optimizer/` in the Solidity repository.

Three upstream semantic fixtures (only trailing file whitespace normalized) are stored outside Hardhat's compiled
source directory in `tests/contracts/test/fixtures/SOL-2026-7/`. The adjacent
`provenance.json` records both upstream and normalized SHA256 hashes. Their test
compiles both the default and candidate profiles and executes them on the local,
unforked EVM: the default must exhibit the known wrong results and the candidate
must match the upstream expected values. This control is intentionally compiled
separately from the production warnings-as-errors gate; no production warning
is suppressed or excluded.

Mainnet artifact admission requires the exact optimizer object, including all
optimizer details, plus viaIR and Cancun. Negative tests reject restored affected
passes, altered unaffected passes or cleanup, extra toggles, missing details,
disabled optimization and altered runs/EVM/IR. Source mirroring, full compiler
input hashing, runtime/constructor checking and exact-source recovery remain
mandatory. Historical archived compiler inputs remain unchanged and retain their
original historical verifier.

Qualification (local only, no public-provider calls):

    cd tests/contracts
    npm ci
    npm run compile:strict
    npm test -- --no-compile
    npm run test:authority
    npm run test:creator-terminal
    node --test authority-test/conventional-creator.test.cjs
    ALPHA_CONVENTIONAL_TEST_OUTPUT=/absolute/new/outside-checkout/prefix npx hardhat test --no-compile --config hardhat.authority.config.js authority-test/conventional-creator-local.test.js

The full existing authority CI additionally checks clean-checkout source identity,
seven-transaction sessions, interruption recovery and verification packages.
The graph still requires five creator deployments and two governor bindings;
this candidate neither authorizes nor executes any Mainnet action. A current
campaign on the earlier release must remain on its original revision and plan.
