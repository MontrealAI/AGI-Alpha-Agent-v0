// SPDX-License-Identifier: Apache-2.0
// Lightweight source contracts and real loopback TLS. These are not clean-Git CLI passes.
const { test } = require('node:test');
const assert = require('assert/strict');
const fs = require('fs');
const path = require('path');
const os = require('os');
const https = require('https');
const { spawn } = require('child_process');
const { createFixtureCertificate } = require('./clean-checkout-cli.cjs');
const { summarizeLog, CHECKS, EXPECTED_COUNTS } = require('./native-ci-evidence.cjs');
const root = path.resolve(__dirname, '../../..');
const source = file => fs.readFileSync(path.join(root, file), 'utf8');
const workflow = source('.github/workflows/alpha-authority-v2.yml');
// The original native job retains its exact action/shard contract. Global
// permission and dangerous-command checks still inspect the entire workflow.
const offlineWorkflow = workflow.split('\n  conventional-qualification:\n')[0];
const harness = source('tests/contracts/authority-test/clean-checkout-cli.cjs');
async function child(args, env) {
    return new Promise((resolve, reject) => {
        const process = spawn(global.process.execPath, args, { env, stdio: ['ignore', 'pipe', 'pipe'] });
        const timer = setTimeout(() => process.kill('SIGKILL'), 15000); let stdout = '', stderr = '';
        process.stdout.on('data', b => { stdout += b; }); process.stderr.on('data', b => { stderr += b; });
        process.on('error', reject); process.on('exit', code => { clearTimeout(timer); resolve({ code, stdout, stderr }); });
    });
}
test('native workflow has only exact reviewed action pins and read-only checkout permission', () => {
    const actions = [...offlineWorkflow.matchAll(/uses: ([^\s]+)(?: # ([^\n]+))?/g)].map(m => m[1]);
    assert.deepEqual(actions, ['actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd',
        'actions/setup-node@53b83947a5a98c8d113130e565377fae1a50d02f',
        'actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405',
        'actions/upload-artifact@bbbca2ddaa5d8feaa63e36b76fdaad77386f024f']);
    assert.match(workflow, /permissions:\n  contents: read\n/);
    assert.match(workflow, /persist-credentials: false/); assert.match(workflow, /fetch-depth: 0/);
    assert.doesNotMatch(workflow, /pull_request_target|secrets\.|contents: write|id-token:|git push|gh release|npm publish|environment:/);
    assert.match(workflow, /ref: \$\{\{ github.event.pull_request.head.sha \|\| github.sha \}\}/);
});
test('native workflow keeps pinned installs, all serial shards and three native profiles', () => {
    assert.match(workflow, /node-version: '22\.17\.1'/); assert.match(workflow, /python-version: '3\.12'/);
    assert.match(workflow, /npm ci --prefix tests\/contracts/);
    assert.match(workflow, /pip install --require-hashes -r requirements-agent\.lock/);
    assert.match(workflow, /070e3c6652f4939fabe14788a0c80b38ed3d6e2ad792cebad4a5bbf842308667/);
    assert.deepEqual([...offlineWorkflow.matchAll(/^          run_check ([a-z-]+) /gm)].map(m => m[1]), CHECKS);
    assert.equal(Object.values(EXPECTED_COUNTS).reduce((sum, n) => sum + n, 0), 157);
    for (const label of ['policy', 'empty-session', 'delegated-session', 'io-relay', 'origination', 'native-contract', 'native-empty', 'native-delegated', 'native-marker'])
        assert.match(workflow.split('\n').find(line => line.trim().startsWith(`run_check ${label} `)), /--max-old-space-size=384/);
    assert.match(workflow, /ALPHA_NATIVE_PROFILE=empty/); assert.match(workflow, /ALPHA_NATIVE_PROFILE=delegated/); assert.match(workflow, /ALPHA_NATIVE_PROFILE=marker/);
    assert.doesNotMatch(workflow, /--invert|continue-on-error|\|\| true/);
});
test('native artifacts use outside-checkout safe summaries and never private runner logs', () => {
    // GitHub resolves global/job env before a runner exists; YAML parsing alone cannot catch this.
    const globalEnv = workflow.split('\nenv:\n')[1].split('\njobs:')[0];
    assert.doesNotMatch(globalEnv, /\$\{\{\s*(?:runner|env|job|steps|needs|strategy|matrix)\./);
    assert.match(workflow, /ALPHA_NATIVE_STATE_DIRECTORY=\$RUNNER_TEMP\/alpha-authority-/);
    assert.match(workflow, />> "\$GITHUB_ENV"/);
    assert.match(workflow, /path: \$\{\{ env.ALPHA_NATIVE_STATE_DIRECTORY \}\}\/public\//);
    assert.match(workflow, /\> "\$ALPHA_NATIVE_STATE_DIRECTORY\/logs\/\$label.log"/);
    assert.match(harness, /Raw signed capability escaped into public evidence/);
    assert.match(harness, /fs\.rmSync\(privateRoot, \{ recursive: true, force: true \}\)/);
    assert.match(source('tests/contracts/authority-test/native-ci-evidence.cjs'), /historicalRecordsRewritten: false/);
    const summary = summarizeLog(Buffer.from('  ✔ one (12ms)\n  ✔ two\n  2 passing (1s)\nPRIVATE KEY synthetic failure text\n'));
    assert.equal(summary.passing, 2); assert.deepEqual(summary.names, ['one', 'two']);
    assert.ok(!JSON.stringify(summary).includes('PRIVATE KEY'));
});
test('native harness requires independently observed clean HEAD before any fixture or signer', () => {
    assert.ok(harness.indexOf('const revision = reviewedRevision()') < harness.indexOf("require('hardhat')"));
    assert.ok(harness.indexOf('assert.equal(revision.commit, process.env.ALPHA_EXPECTED_HEAD_SHA)') < harness.indexOf('createFixtureCertificate(privateRoot)'));
    assert.match(harness, /assert\.deepEqual\(reviewedRevision\(\), revision\)/);
    assert.match(harness, /network.config.hardfork, 'osaka'/);
    assert.match(harness, /requireDisposableLocalNetwork/);
    assert.match(harness, /rejectLateMutation/); assert.match(harness, /restoreLateMutation = mutate\(\) \|\| null/);
    assert.match(harness, /assert\.equal\(relays, relayBefore\)/); assert.match(harness, /lateInputDriftCase/);
    assert.match(harness, /\[0, 0, 0, 0, 0, 1, 2\]/);
    for (const file of ['mainnet-authority.js', 'authority-cli.js', 'authority-verification-package.js', 'authority-session.js'])
        assert.doesNotMatch(source(`tests/contracts/scripts/${file}`), /ALPHA_NATIVE_PROFILE|ALPHA_EXPECTED_HEAD_SHA|NODE_EXTRA_CA_CERTS|NODE_TLS_REJECT_UNAUTHORIZED/);
});
test('native harness refuses a missing expected HEAD without creating an evidence directory', async () => {
    const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-native-anchor-test-'));
    try {
        const output = path.join(temp, 'must-not-exist');
        const result = await child([path.join(__dirname, 'clean-checkout-cli.cjs')], { ...process.env, ALPHA_EXPECTED_HEAD_SHA: '', ALPHA_NATIVE_PROFILE: 'empty', ALPHA_NATIVE_EVIDENCE_DIRECTORY: output });
        assert.equal(result.code, 1); assert.equal(fs.existsSync(output), false);
    } finally { fs.rmSync(temp, { recursive: true, force: true }); }
});
test('real HTTPS and fetch accept child-scoped fixture trust and reject the untrusted certificate', async () => {
    const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-native-tls-test-')); let server, requests = 0;
    try {
        const { certificate, key } = createFixtureCertificate(temp);
        server = https.createServer({ cert: fs.readFileSync(certificate), key: fs.readFileSync(key) }, (req, res) => { requests++; res.writeHead(200); res.end('synthetic fixture'); });
        await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
        const url = `https://127.0.0.1:${server.address().port}`;
        const program = `const https = require('https'); (async()=>{ await new Promise((resolve,reject)=>https.get(${JSON.stringify(url)},r=>{r.resume();r.on('end',resolve)}).on('error',reject)); const response=await fetch(${JSON.stringify(url)}); if(await response.text()!=='synthetic fixture') throw Error('fixture mismatch'); })().catch(()=>{process.exitCode=1});`;
        const env = { ...process.env, NODE_EXTRA_CA_CERTS: certificate }; delete env.NODE_TLS_REJECT_UNAUTHORIZED;
        assert.equal((await child(['-e', program], env)).code, 0); assert.equal(requests, 2);
        assert.equal((await child(['-e', program], { ...env, NODE_EXTRA_CA_CERTS: '' })).code, 1); assert.equal(requests, 2);
    } finally { if (server) await new Promise(resolve => server.close(resolve)); fs.rmSync(temp, { recursive: true, force: true }); }
});
