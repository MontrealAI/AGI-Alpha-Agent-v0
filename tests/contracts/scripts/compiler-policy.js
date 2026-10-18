// SPDX-License-Identifier: Apache-2.0
const SOLC_VERSION = "0.8.37";
const { isDeepStrictEqual } = require("util");
// Solidity v0.8.37 OptimiserSettings.h default, with ONLY affected passes L/E removed.
// SOL-2026-7 interim workaround, not a claim that this compiler has no other bugs.
const DEFAULT_STEPS = "dfDvulfnTUtnIfxa[r]EscLMVcul[j]Trpeulxa[r]cLvifMCTUca[r]LSsTFOtfDnca[r]IulcscCTUtvifMx[scCTUt]TOntnfDIulvifMjmul[jul]VcTOculjmul";
const CLEANUP_STEPS = "fDnTOcmuO";
const OPTIMIZER_STEPS = DEFAULT_STEPS.replace(/[LE]/g, "") + ":" + CLEANUP_STEPS;
const OPTIMIZER = Object.freeze({ enabled: true, runs: 200, details: Object.freeze({
    yulDetails: Object.freeze({ optimizerSteps: OPTIMIZER_STEPS })
}) });
const SETTINGS = Object.freeze({ optimizer: OPTIMIZER, viaIR: true, evmVersion: "cancun" });
function assertCompilerSettings(settings) {
    if (!settings || !isDeepStrictEqual(settings.optimizer, OPTIMIZER) ||
        settings.viaIR !== true || settings.evmVersion !== "cancun")
        throw Error("Unexpected compiler settings: exact SOL-2026-7 workaround profile required");
}

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

module.exports = { SOLC_VERSION, DEFAULT_STEPS, CLEANUP_STEPS, OPTIMIZER_STEPS, OPTIMIZER, SETTINGS, assertCompilerSettings, assertNoCompilerWarnings, pinnedCompiler };
