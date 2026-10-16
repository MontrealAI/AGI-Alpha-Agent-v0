// SPDX-License-Identifier: Apache-2.0
// Operational read-only commands always observe the actual clean checkout themselves.
const fs = require('fs');
const path = require('path');
const legacy = require('./mainnet');
const policy = require('./mainnet-authority');
const { createReadOnlyRpc, scopeForPlan } = require('./authority-rpc');
const { assertOutsideCheckout } = require('./authority-paths');
function readJson(filename) {
    const fd = fs.openSync(filename, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    try { const stat = fs.fstatSync(fd); if (!stat.isFile() || stat.size > 16 * 1024 * 1024) throw Error('Bounded ordinary JSON file required');
        return JSON.parse(fs.readFileSync(fd, 'utf8')); } finally { fs.closeSync(fd); }
}
function writeNew(filename, value) {
    const target = assertOutsideCheckout(filename);
    if (fs.realpathSync(path.dirname(target)) !== path.dirname(target)) throw Error('Output parent must be a real existing directory');
    const fd = fs.openSync(target, 'wx', 0o600);
    try { fs.writeFileSync(fd, JSON.stringify(value, null, 2) + '\n'); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
    const directory = fs.openSync(path.dirname(target), 'r'); try { fs.fsyncSync(directory); } finally { fs.closeSync(directory); }
    return target;
}
async function runReadOnly(mode, plan, input, revision, rpc) {
    await policy.checkPlan(plan, undefined, revision);
    if (mode === 'preflight') {
        if (!input || Object.keys(input).sort().join(',') !== 'creationHashes,governanceHashes,journal') throw Error('Exact progress hashes and current journal required');
        return policy.preflight(plan, rpc, revision, input.creationHashes, input.journal, input.governanceHashes);
    }
    if (mode === 'verify') return policy.verifyAuthority(plan, rpc, input, revision);
    throw Error('Only preflight or verify is supported');
}
async function main() {
    const [mode, planFile, inputFile, output, extra] = process.argv.slice(2);
    if (!['preflight', 'verify'].includes(mode) || !planFile || !inputFile || !output || extra) throw Error('Usage: authority-cli.js preflight|verify PLAN.json INPUT.json NEW_REPORT.json');
    const revision = require('./authority-revision').reviewedRevision(), plan = readJson(planFile);
    assertOutsideCheckout(output);
    await policy.checkPlan(plan, undefined, revision);
    if (!process.env.ALPHA_READ_ONLY_RPC_URL) throw Error('Explicit ALPHA_READ_ONLY_RPC_URL required');
    const rpc = createReadOnlyRpc(process.env.ALPHA_READ_ONLY_RPC_URL, scopeForPlan(plan));
    const report = await runReadOnly(mode, plan, readJson(inputFile), revision, rpc);
    const destination = writeNew(output, { report, transport: rpc.stats() });
    console.log(JSON.stringify({ output: destination, externalTransactions: false, activationAllowed: false }));
}
module.exports = { readJson, writeNew, runReadOnly };
if (require.main === module) main().catch(error => { console.error(error.publicMessage ? error.message : 'Read-only v2 check failed; check exact clean sources, input files and bounded provider availability.'); process.exitCode = 1; });
