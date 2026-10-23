// Read the installed Hardhat task's selection only; do not execute or compile tests.
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");
const crypto = require("node:crypto");
const root = path.join(__dirname, "source/tests/contracts");
const hardhat = require(path.join(root, "node_modules/hardhat"));
const { TASK_TEST_GET_TEST_FILES } = require(path.join(root, "node_modules/hardhat/builtin-tasks/task-names"));
const sha = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");

(async () => {
    const candidate = path.join(root, "qualification/ascension/payout-small-integers.local.test.js");
    const configured = path.join(root, "test");
    assert.equal(hardhat.config.paths.tests, configured);
    const ordinary = await hardhat.run(TASK_TEST_GET_TEST_FILES, { testFiles: [] });
    assert(!ordinary.includes(candidate));
    assert(ordinary.every((file) => path.relative(configured, file).split(path.sep)[0] !== ".."));
    assert(!ordinary.some((file) => file.endsWith("payout-small-integers.local.test.js")));
    const explicit = await hardhat.run(TASK_TEST_GET_TEST_FILES, {
        testFiles: ["qualification/ascension/payout-small-integers.local.test.js"],
    });
    assert.deepEqual(explicit, [candidate]);
    console.log(JSON.stringify({
        schema: "ascension-qualification-discovery/v1",
        recordedAt: new Date().toISOString(),
        hardhatVersion: require(path.join(root, "node_modules/hardhat/package.json")).version,
        defaultConfiguredTests: hardhat.config.paths.tests,
        defaultTestFiles: ordinary,
        explicitTestFiles: explicit,
        qualificationExcludedByDefault: true,
        qualificationSelectedExplicitly: true,
        noTestExecuted: true,
        noCompilationPerformed: true,
        configSha256: sha(path.join(root, "hardhat.config.js")),
        installedSelectionImplementationSha256: sha(path.join(root, "node_modules/hardhat/builtin-tasks/test.js")),
        candidateSha256: sha(candidate),
    }, null, 2));
})().catch((error) => {
    console.error(error.stack || error.message);
    process.exitCode = 1;
});
