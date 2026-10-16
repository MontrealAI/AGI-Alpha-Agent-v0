// SPDX-License-Identifier: Apache-2.0
// Native CI evidence only. Never copies private runner logs, raw signatures or fixture keys.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert/strict');
const { execFileSync } = require('child_process');
const { reviewedRevision, gitRead } = require('../scripts/authority-revision');
const { SOURCE_ROOT, assertOutsideCheckout } = require('../scripts/authority-paths');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const CHECKS = ['audit', 'compile', 'historical', 'regressions', 'policy', 'empty-session', 'delegated-session', 'io-relay', 'origination', 'native-contract', 'native-empty', 'native-delegated', 'native-marker'];
const EXPECTED_COUNTS = { regressions: 111, policy: 17, 'empty-session': 1, 'delegated-session': 1, 'io-relay': 19, origination: 7 };
function summarizeLog(bytes) {
    const text = bytes.toString('utf8').replace(/\u001b\[[0-9;]*m/g, '');
    const passing = [...text.matchAll(/^\s*(\d+) passing(?:\s|$)/gm)].map(x => Number(x[1]));
    const names = [...text.matchAll(/^\s*✔\s+(.+?)(?:\s+\(\d+ms\))?\s*$/gm)].map(x => x[1]);
    // Names are used only for set reconciliation. Raw text never leaves runner scratch.
    return { sha256: sha(bytes), bytes: bytes.length, passing: passing.length === 1 ? passing[0] : null, names };
}
function sourceInventory() {
    const names = gitRead(['ls-files', '-z']).split('\0').filter(Boolean).sort();
    return Object.fromEntries(names.map(name => {
        const p = path.join(SOURCE_ROOT, name), stat = fs.lstatSync(p);
        return [name, { kind: stat.isSymbolicLink() ? 'symlink' : 'file', sha256: sha(stat.isSymbolicLink() ? fs.readlinkSync(p) : fs.readFileSync(p)) }];
    }));
}
function artifactInventory() {
    const base = path.resolve(__dirname, '../artifacts/build-info');
    if (!fs.existsSync(base)) return {};
    return Object.fromEntries(fs.readdirSync(base).filter(n => n.endsWith('.json')).sort().map(n => [n, sha(fs.readFileSync(path.join(base, n)))]));
}
function writeNew(file, value) { fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n', { flag: 'wx', mode: 0o600 }); }
function main() {
    const [action, extra] = process.argv.slice(2); assert.ok(['init', 'finish'].includes(action) && !extra);
    assert.equal(process.versions.node, '22.17.1');
    assert.match(process.env.ALPHA_EXPECTED_HEAD_SHA || '', /^[0-9a-f]{40}$/);
    const revision = reviewedRevision(); assert.equal(revision.commit, process.env.ALPHA_EXPECTED_HEAD_SHA);
    const root = assertOutsideCheckout(process.env.ALPHA_NATIVE_STATE_DIRECTORY);
    assert.equal(fs.realpathSync(path.dirname(root)), path.dirname(root));
    if (action === 'init') {
        fs.mkdirSync(root, { mode: 0o700 }); fs.mkdirSync(path.join(root, 'public')); fs.mkdirSync(path.join(root, 'logs'));
        writeNew(path.join(root, 'public/start.json'), { schema: 'agialpha.native-ci-start.v1', revision, time: new Date().toISOString(),
            node: process.versions.node, hardhat: require('hardhat/package.json').version, ethers: require('ethers').version,
            compiler: require('solc').version(), python: execFileSync('python', ['--version'], { encoding: 'utf8' }).trim(),
            openssl: execFileSync('openssl', ['version'], { encoding: 'utf8' }).trim(),
            requirementsLockSha256: sha(fs.readFileSync(path.join(SOURCE_ROOT, 'requirements-agent.lock'))),
            scope: 'Disposable unforked Osaka only; mock dependencies, synthetic finality, local fixture keys.',
            publicProviderCalls: 0, liveTransactions: false, activationAllowed: false });
        return;
    }
    const checks = {}, shardNames = []; let allPassed = true;
    for (const name of CHECKS) {
        const log = path.join(root, 'logs', `${name}.log`), code = path.join(root, 'logs', `${name}.exit-code`);
        const exitCode = fs.existsSync(code) && /^\d+\n$/.test(fs.readFileSync(code, 'utf8')) ? Number(fs.readFileSync(code, 'utf8')) : null;
        const summary = fs.existsSync(log) ? summarizeLog(fs.readFileSync(log)) : null;
        checks[name] = { exitCode, result: exitCode === 0 ? 'passed' : exitCode === null ? 'not-completed' : 'failed',
            logSha256: summary?.sha256 || null, logBytes: summary?.bytes || 0, passing: summary?.passing || null };
        if (name in EXPECTED_COUNTS && summary?.passing !== EXPECTED_COUNTS[name]) allPassed = false;
        if (['policy', 'empty-session', 'delegated-session', 'io-relay', 'origination'].includes(name) && summary) shardNames.push(...summary.names);
        if (exitCode !== 0) allPassed = false;
    }
    const unique = new Set(shardNames);
    const countCoverage = shardNames.length === 45 && unique.size === 45;
    if (!countCoverage) allPassed = false;
    const campaigns = {};
    for (const name of ['empty', 'delegated', 'marker']) {
        const report = path.join(root, 'public', `native-${name}`, 'report.json');
        campaigns[name] = fs.existsSync(report) ? JSON.parse(fs.readFileSync(report, 'utf8')) : null;
        const actual = campaigns[name];
        if (!actual || actual.result !== 'passed' || actual.selectedProfile !== name || JSON.stringify(actual.revision) !== JSON.stringify(revision) || actual.campaigns.length !== 1) allPassed = false;
    }
    // Do not rewrite old acceptance reports; record their current source identities as ordinary tracked files.
    const sources = sourceInventory(); assert.deepEqual(reviewedRevision(), revision);
    writeNew(path.join(root, 'public/source-inventory.json'), { revision, sourceFiles: sources, artifacts: artifactInventory() });
    writeNew(path.join(root, 'public/result.json'), { schema: 'agialpha.native-ci-result.v1', revision, time: new Date().toISOString(),
        result: allPassed ? 'passed' : 'failed-or-incomplete', checks, candidateTestCount: shardNames.length,
        uniqueCandidateTestCount: unique.size, countCoverage, candidateNamesSha256: sha([...unique].sort().join('\n')),
        nativeProfiles: Object.fromEntries(Object.entries(campaigns).map(([name, r]) => [name, r ? { result: r.result, commands: r.commands.length, sourceBound: JSON.stringify(r.revision) === JSON.stringify(revision) } : null])),
        sourceInventorySha256: sha(JSON.stringify(sources)), historicalRecordsRewritten: false,
        sourceRecords: 'This exact-head run is additive. Existing historical/current audit records retain their original scope and are not promoted to current passes.',
        publicProviderCalls: 0, independentSecurityReview: false, hardwareQualified: false, activationAllowed: false });
    assert.ok(allPassed, 'Native qualification failed or is incomplete; retained public evidence is not a pass');
}
if (require.main === module) { try { main(); } catch { console.error('Native evidence stopped; inspect bounded result and job status. No qualification inferred.'); process.exitCode = 1; } }
module.exports = { CHECKS, EXPECTED_COUNTS, summarizeLog, sourceInventory, artifactInventory, main };
