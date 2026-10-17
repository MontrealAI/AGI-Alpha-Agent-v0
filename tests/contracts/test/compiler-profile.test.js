// SPDX-License-Identifier: Apache-2.0
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { SETTINGS, OPTIMIZER_STEPS, DEFAULT_STEPS, CLEANUP_STEPS, assertCompilerSettings } = require('../scripts/compiler-policy');
const { compiledContracts } = require('../scripts/mainnet');
const clone = value => JSON.parse(JSON.stringify(value));
const mutations = {
    defaultOptimizer: s => delete s.optimizer.details,
    restoredLoadResolver: s => s.optimizer.details.yulDetails.optimizerSteps = 'L' + OPTIMIZER_STEPS,
    restoredEqualStore: s => s.optimizer.details.yulDetails.optimizerSteps = 'E' + OPTIMIZER_STEPS,
    disabledYul: s => s.optimizer.details.yul = false,
    extraPassToggle: s => s.optimizer.details.cse = false,
    alteredCleanup: s => s.optimizer.details.yulDetails.optimizerSteps = OPTIMIZER_STEPS + 'L',
    alteredUnaffectedPass: s => s.optimizer.details.yulDetails.optimizerSteps = OPTIMIZER_STEPS.replace('d', ''),
    changedRuns: s => s.optimizer.runs = 201,
    disabledOptimizer: s => s.optimizer.enabled = false,
    changedIR: s => s.viaIR = false,
    changedEVM: s => s.evmVersion = 'shanghai',
};
describe('Exact interim compiler profile admission', function () {
    it('preserves all unaffected steps and the complete cleanup sequence', () => {
        assert.equal(OPTIMIZER_STEPS, DEFAULT_STEPS.replace(/[LE]/g, '') + ':' + CLEANUP_STEPS);
        assert.equal(CLEANUP_STEPS, 'fDnTOcmuO');
        assertCompilerSettings(clone(SETTINGS));
        for (const mutate of Object.values(mutations)) {
            const settings = clone(SETTINGS); mutate(settings);
            assert.throws(() => assertCompilerSettings(settings), /Unexpected compiler settings/);
        }
    });
    it('rejects altered details at actual Mainnet artifact admission', () => {
        compiledContracts();
        const artifact = path.join(__dirname, '../artifacts/contracts/ascension/AscensionAccess.sol/AscensionAccess.dbg.json');
        const buildPath = path.resolve(path.dirname(artifact), JSON.parse(fs.readFileSync(artifact)).buildInfo);
        const original = fs.readFileSync(buildPath, 'utf8');
        try {
            for (const [label, mutate] of Object.entries(mutations)) {
                const build = JSON.parse(original); mutate(build.input.settings);
                fs.writeFileSync(buildPath, JSON.stringify(build));
                assert.throws(() => compiledContracts(), /Unexpected compiler settings/, label);
            }
        } finally { fs.writeFileSync(buildPath, original); }
        compiledContracts();
    });
});
