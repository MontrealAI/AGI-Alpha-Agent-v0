// SPDX-License-Identifier: Apache-2.0
const SOLC_VERSION = "0.8.37";

function assertNoCompilerWarnings(output) {
    const warnings = (output.errors || []).filter(item => item.severity === "warning");
    if (warnings.length) throw Error(`Solidity emitted ${warnings.length} warning(s); resolve every diagnostic before release.`);
}

function pinnedCompiler(version = SOLC_VERSION) {
    if (version !== SOLC_VERSION) throw Error(`Unsupported compiler profile: expected Solidity ${SOLC_VERSION}`);
    const solc = require("solc");
    const longVersion = solc.version();
    if (!longVersion.startsWith(`${SOLC_VERSION}+commit.`))
        throw Error(`Solidity package differs from ${SOLC_VERSION}; run npm ci with the committed lockfile.`);
    return { compilerPath: require.resolve("solc/soljson.js"), isSolcJs: true, version, longVersion };
}

module.exports = { SOLC_VERSION, assertNoCompilerWarnings, pinnedCompiler };
