// SPDX-License-Identifier: Apache-2.0
// Lightweight native-entry and explicit extra-CA contracts; no EVM or public provider.
const { test } = require('node:test');
const assert = require('assert/strict');
const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');
const { spawn } = require('child_process');
const terminal = require('../scripts/creator-terminal');
const { createFixtureCertificate } = require('./clean-checkout-cli.cjs');
const source = name => fs.readFileSync(path.join(__dirname, name), 'utf8');
const harness = source('creator-clean-checkout.cjs'), driver = source('creator-native-pty.py');
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
test('optional extra CA requires a canonical exact-file public policy and detects changed bytes', () => {
    const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-creator-ca-test-'));
    try {
        const { certificate } = createFixtureCertificate(temp), declaration = path.join(temp, 'policy.json');
        const bytes = fs.readFileSync(certificate), policy = { schema: 'agialpha.creator-ca-policy.v1', certificate, sha256: digest(bytes) };
        const save = value => fs.writeFileSync(declaration, JSON.stringify(value)); save(policy);
        const env = { NODE_EXTRA_CA_CERTS: certificate, ALPHA_CREATOR_CA_POLICY: declaration };
        assert.equal(terminal.observeCaPolicy({}), null); terminal.assertTerminalEnvironment(env, []);
        assert.deepEqual(terminal.observeCaPolicy(env), { policyFile: declaration, certificate, sha256: digest(bytes) });
        for (const unknown of [{ NODE_EXTRA_CA_CERTS: certificate }, { ALPHA_CREATOR_CA_POLICY: declaration }, { ...env, NODE_EXTRA_CA_CERTS: './relative.pem' }])
            assert.throws(() => terminal.observeCaPolicy(unknown));
        for (const value of [{ ...policy, sha256: 'a'.repeat(64) }, { ...policy, extra: true }, { ...policy, certificate: '/wrong' }]) {
            save(value); assert.throws(() => terminal.observeCaPolicy(env));
        }
        save(policy); fs.appendFileSync(certificate, '\n'); assert.throws(() => terminal.observeCaPolicy(env)); fs.writeFileSync(certificate, bytes);
        const alias = path.join(temp, 'alias.pem'); fs.symlinkSync(certificate, alias); save({ ...policy, certificate: alias });
        assert.throws(() => terminal.observeCaPolicy({ ...env, NODE_EXTRA_CA_CERTS: alias }));
        save(policy); assert.throws(() => terminal.assertTerminalEnvironment({ ...env, NODE_TLS_REJECT_UNAUTHORIZED: '0' }, []));
        assert.throws(() => terminal.assertTerminalEnvironment({ ...env, NODE_OPTIONS: '--inspect' }, []));
        save('PRIVATE_CA_JSON_SENTINEL'); assert.throws(() => terminal.observeCaPolicy(env), error => !error.message.includes('PRIVATE_CA_JSON_SENTINEL'));
    } finally { fs.rmSync(temp, { recursive: true, force: true }); }
});
test('extra CA rejects bundles, non-CA material and private key content even with a matching checksum', () => {
    const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-creator-ca-material-'));
    try {
        const { certificate, key } = createFixtureCertificate(temp), declaration = path.join(temp, 'policy.json'), original = fs.readFileSync(certificate);
        for (const bytes of [Buffer.concat([original, original]), Buffer.from('not a certificate'), fs.readFileSync(key)]) {
            fs.writeFileSync(certificate, bytes); fs.writeFileSync(declaration, JSON.stringify({ schema: 'agialpha.creator-ca-policy.v1', certificate, sha256: digest(bytes) }));
            assert.throws(() => terminal.observeCaPolicy({ NODE_EXTRA_CA_CERTS: certificate, ALPHA_CREATOR_CA_POLICY: declaration }));
        }
    } finally { fs.rmSync(temp, { recursive: true, force: true }); }
});
test('creator native entry anchors clean Git before EVM and uses the actual Hardhat script with a PTY', () => {
    assert.ok(harness.indexOf('const revision = reviewedRevision()') < harness.indexOf("require('hardhat')"));
    assert.match(harness, /revision.commit, process.env.ALPHA_EXPECTED_HEAD_SHA/);
    assert.match(harness, /requireDisposableLocalNetwork/); assert.match(harness, /network.config.hardfork, 'osaka'/);
    assert.match(driver, /pty.openpty\(\)/); assert.match(driver, /hardhat\/internal\/cli\/cli.js/);
    assert.match(driver, /hardhat.creator.config.js/); assert.match(driver, /scripts\/deploy-mainnet-creator.js/);
    assert.match(driver, /url.hostname == "127.0.0.1"/); assert.match(driver, /termios.tcgetattr\(slave\) == initial/);
    assert.doesNotMatch(driver, /PRIVATE_KEY|MNEMONIC|SEED_PHRASE/);
});
test('creator native campaign covers source/trust refusals, five receipts, zero bindings and no-key checkpoint recovery', () => {
    for (const name of ['undeclared-ca-refused', 'mismatching-ca-refused', 'dirty-source-refused', 'self-declared-source-refused', 'wrong-key-refused', 'five-creates', 'checkpoint-without-key-or-resend']) assert.ok(harness.includes(name));
    assert.match(harness, /assert.equal\(requests, before\)/); assert.match(harness, /session.validateSigned/);
    assert.match(harness, /assert.equal\(relayHashes.length, 5\)/); assert.match(harness, /governorBindings: 0/);
    assert.match(harness, /actorLocksRetained: true/); assert.match(harness, /assert.equal\(state.complete, false\)/);
    assert.match(driver, /rawTranscriptRetained": False/); assert.match(harness, /fs.rmSync\(privateRoot/);
});
test('creator workflow adds bounded serial coverage without changing legacy campaigns or privileges', () => {
    const workflow = fs.readFileSync(path.join(__dirname, '../../../.github/workflows/alpha-authority-v2.yml'), 'utf8');
    for (const name of ['creator-unit', 'creator-pty', 'creator-local', 'native-creator']) assert.match(workflow, new RegExp(`run_check ${name} `));
    assert.match(workflow, /timeout-minutes: 45/); assert.match(workflow, /permissions:\n  contents: read/);
    for (const profile of ['empty', 'delegated', 'marker']) assert.match(workflow, new RegExp(`ALPHA_NATIVE_PROFILE=${profile}`));
    assert.doesNotMatch(workflow, /secrets\.|contents: write|id-token:|continue-on-error|\|\| true/);
    assert.match(source('native-ci-evidence.cjs'), /creatorNative/);
});
test('creator actual entry refuses missing expected source before fixture, output or key activity', async () => {
    const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-creator-anchor-test-'));
    try {
        const output = path.join(temp, 'must-not-exist');
        const code = await new Promise((resolve, reject) => {
            const child = spawn(process.execPath, [path.join(__dirname, 'creator-clean-checkout.cjs')], { env: { ...process.env, ALPHA_EXPECTED_HEAD_SHA: '', ALPHA_CREATOR_NATIVE_OUTPUT: output }, stdio: 'ignore' });
            child.on('error', reject); child.on('exit', resolve);
        });
        assert.equal(code, 1); assert.equal(fs.existsSync(output), false);
    } finally { fs.rmSync(temp, { recursive: true, force: true }); }
});
