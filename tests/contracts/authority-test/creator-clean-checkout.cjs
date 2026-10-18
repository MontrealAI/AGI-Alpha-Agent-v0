// SPDX-License-Identifier: Apache-2.0
// Actual clean-checkout Hardhat entry point with real PTY, fixed public fixture key and local HTTPS only.
const fs = require('fs');
const os = require('os');
const path = require('path');
const https = require('https');
const crypto = require('crypto');
const assert = require('assert/strict');
const { spawn } = require('child_process');
const { reviewedRevision } = require('../scripts/authority-revision');
const { SOURCE_ROOT, assertOutsideCheckout } = require('../scripts/authority-paths');
const { createFixtureCertificate } = require('./clean-checkout-cli.cjs');
const policy = require('../scripts/mainnet-authority');
const session = require('../scripts/authority-session');
const legacy = require('../scripts/mainnet');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const write = (file, value) => fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
const read = file => JSON.parse(fs.readFileSync(file));
const readMethods = new Set(['eth_chainId', 'eth_getBlockByNumber', 'eth_getCode', 'eth_call', 'eth_getTransactionCount', 'eth_getBalance', 'eth_getTransactionByHash', 'eth_getTransactionReceipt', 'eth_getLogs', 'eth_getStorageAt']);
function publicRecord(value, rawCapabilities) {
    const text = JSON.stringify(value, null, 2) + '\n';
    assert.ok(!text.includes('PRIVATE KEY') && !text.includes('0x' + '11'.repeat(32)) && !text.includes('0x' + '22'.repeat(32)));
    for (const raw of rawCapabilities) assert.ok(!text.includes(raw), 'Raw capability escaped into public artifact');
    return text;
}
let stage = 'source-anchor';
async function main() {
    assert.equal(process.versions.node, '22.17.1');
    assert.match(process.env.ALPHA_EXPECTED_HEAD_SHA || '', /^[0-9a-f]{40}$/);
    const revision = reviewedRevision();
    assert.equal(revision.commit, process.env.ALPHA_EXPECTED_HEAD_SHA);
    const output = assertOutsideCheckout(process.env.ALPHA_CREATOR_NATIVE_OUTPUT);
    assert.equal(fs.realpathSync(path.dirname(output)), path.dirname(output));
    fs.mkdirSync(output, { mode: 0o700 });
    const privateRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-creator-native-private-'));
    const report = { schema: 'agialpha.creator-clean-checkout.v1', revision, node: process.versions.node,
        startedAt: new Date().toISOString(), commands: [], publicProviderCalls: 0, liveTransactions: false,
        hardwareQualified: false, activationAllowed: false, providerFork: false,
        scope: 'Actual clean-Git Hardhat/PTY entry; fixed public fixture key, unforked Osaka, mock dependencies, finalized=latest.' };
    let server, requests = 0, relayHashes = [], plan;
    const rawCapabilities = new Set();
    const writePublic = (file, value) => fs.writeFileSync(file, publicRecord(value, rawCapabilities), { flag: 'wx', mode: 0o600 });
    try {
        stage = 'local-fixture';
        const { ethers, network } = require('hardhat');
        await require('../scripts/disposable').requireDisposableLocalNetwork();
        assert.equal(network.config.hardfork, 'osaka'); assert.equal(network.config.chainId, 1);
        await network.provider.send('hardhat_reset');
        const creator = new ethers.Wallet('0x' + '11'.repeat(32));
        const governor = '0xd76AD27a1Bcf8652e7e46BE603FA742FD1c10A99';
        await network.provider.send('hardhat_setBalance', [creator.address, ethers.toQuantity(ethers.parseEther('100'))]);
        await require('../test/utils/token').installToken();
        for (const [name, address] of [['MockAscensionENS', legacy.ENS], ['MockAscensionWrapper', legacy.WRAPPER]]) {
            const fixture = await (await ethers.getContractFactory(name)).deploy();
            await network.provider.send('hardhat_setCode', [address, await ethers.provider.getCode(fixture.target)]);
        }
        const ens = await ethers.getContractAt('MockAscensionENS', legacy.ENS);
        for (const root of legacy.roots) await (await ens.setOwner(ethers.namehash(root), governor)).wait();
        const block = await ethers.provider.getBlock('latest');
        const config = { schema: 'agialpha.mainnet.config.v2', chainId: 1, deployer: creator.address, nonce: 0,
            block: { number: block.number, hash: block.hash }, governor: { kind: 'ledger-eoa', address: governor, addressAcknowledgement: governor },
            dependencies: {}, rootOwners: Object.fromEntries(legacy.roots.map(root => [root, governor])),
            parameters: { minimumValidatorStake: '10000000000000000000', minimumAgentStake: '10000000000000000000', quorum: 2, maximumRiskBps: 2000 },
            sender: { mode: policy.EMPTY }, envelope: { gasLimit: '8000000', maxFeePerGas: '10000000000', maxPriorityFeePerGas: '1000000000', accessList: [] } };
        for (const [name, address] of Object.entries({ token: require('../../../token.config').AGIALPHA_ADDRESS, ens: legacy.ENS, wrapper: legacy.WRAPPER }))
            config.dependencies[name] = { address, codeHash: ethers.keccak256(await ethers.provider.getCode(address)) };
        const nonceJournal = { schema: 'ethereum.cross-project-nonce-journal.v1', journalId: 'SYNTHETIC-CREATOR-NATIVE', revision: 1,
            chainId: 1, sender: creator.address, scope: ['alpha', 'jobs', 'manager'], block: config.block, latestNonce: 0, pendingNonce: 0,
            allocations: [{ project: 'alpha', startNonce: 0, count: 5 }, { project: 'jobs', startNonce: 5, count: 1 }, { project: 'manager', startNonce: 6, count: 1 }] };
        plan = await policy.makePlan(config, policy.compiledContracts(), revision, nonceJournal);
        const planFile = path.join(privateRoot, 'plan.json'), journalFile = path.join(privateRoot, 'session.jsonl'), locks = path.join(privateRoot, 'locks');
        write(planFile, plan); fs.mkdirSync(locks, { mode: 0o700 });
        const { certificate, key } = createFixtureCertificate(privateRoot);
        const caPolicy = path.join(privateRoot, 'ca-policy.json');
        write(caPolicy, { schema: 'agialpha.creator-ca-policy.v1', certificate, sha256: sha(fs.readFileSync(certificate)) });
        report.fixtureCertificateSha256 = read(caPolicy).sha256;
        server = https.createServer({ key: fs.readFileSync(key), cert: fs.readFileSync(certificate), minVersion: 'TLSv1.2' }, (req, res) => {
            const chunks = []; let bytes = 0;
            req.on('data', chunk => { bytes += chunk.length; if (bytes > 262144) req.destroy(); else chunks.push(chunk); });
            req.on('end', async () => {
                try {
                    assert.equal(req.method, 'POST'); assert.ok(++requests <= 10000);
                    const body = JSON.parse(Buffer.concat(chunks)), relay = req.url === '/relay';
                    assert.ok(relay || req.url === '/read'); assert.equal(body.jsonrpc, '2.0'); assert.ok(Array.isArray(body.params));
                    assert.ok(relay ? body.method === 'eth_sendRawTransaction' : readMethods.has(body.method));
                    if (relay) { assert.ok(relayHashes.length < 5); session.validateSigned(body.params[0], { envelope: plan.transactions[relayHashes.length].envelope }); rawCapabilities.add(body.params[0]); }
                    const params = body.method === 'eth_getBlockByNumber' && body.params[0] === 'finalized' ? ['latest', false] : body.params;
                    const result = await network.provider.send(body.method, params);
                    if (relay) relayHashes.push(result);
                    res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ jsonrpc: '2.0', id: body.id, result }));
                } catch { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Local fixture rejected request' })); }
            });
        });
        server.requestTimeout = 20000; server.headersTimeout = 10000;
        await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
        const origin = `https://127.0.0.1:${server.address().port}`;
        const baseEnv = { ...process.env, NODE_EXTRA_CA_CERTS: certificate, ALPHA_CREATOR_CA_POLICY: caPolicy,
            ALPHA_READ_ONLY_RPC_URL: `${origin}/read`, ALPHA_RAW_RELAY_RPC_URL: `${origin}/relay`, DEPLOYMENT_LOCK_DIRECTORY: locks };
        for (const name of ['NODE_OPTIONS', 'NODE_PATH', 'NODE_TLS_REJECT_UNAUTHORIZED', 'DEBUG']) delete baseEnv[name];
        let serial = 0;
        async function cli(label, action, extraEnv = {}, dirty = false, chosenPlan = planFile) {
            stage = label; if (!dirty) assert.deepEqual(reviewedRevision(), revision);
            const destination = path.join(privateRoot, `checkpoint-${++serial}.json`), command = path.join(privateRoot, `command-${serial}.json`);
            write(command, { plan: chosenPlan, journal: journalFile, output: destination });
            const summary = path.join(output, `pty-${serial}.json`);
            const child = spawn('python', [path.join(__dirname, 'creator-native-pty.py'), process.execPath, action, plan.payloadSha256, summary],
                { cwd: path.resolve(__dirname, '..'), env: { ...baseEnv, ALPHA_CREATOR_COMMAND: command, ...extraEnv }, stdio: ['ignore', 'pipe', 'pipe'] });
            let privateOutput = ''; const timeout = setTimeout(() => child.kill('SIGTERM'), 620000);
            child.stdout.on('data', b => { privateOutput += b; if (privateOutput.length > 65536) child.kill('SIGTERM'); });
            child.stderr.on('data', b => { privateOutput += b; if (privateOutput.length > 65536) child.kill('SIGTERM'); });
            const code = await new Promise((resolve, reject) => { child.on('error', reject); child.on('exit', resolve); }); clearTimeout(timeout);
            assert.equal(code, 0, `Creator rehearsal stopped at ${label}; private diagnostics omitted`);
            report.commands.push({ label, ...read(summary) });
            if (!dirty) assert.deepEqual(reviewedRevision(), revision);
            if (action === 'refuse' || action === 'wrong-key') assert.equal(fs.existsSync(destination), false);
            return destination;
        }
        // Unknown/mismatching trust and dirty source fail before any provider request or key prompt.
        const before = requests;
        await cli('undeclared-ca-refused', 'refuse', { ALPHA_CREATOR_CA_POLICY: '' });
        const badPolicy = path.join(privateRoot, 'wrong-ca-policy.json'); write(badPolicy, { ...read(caPolicy), sha256: 'a'.repeat(64) });
        await cli('mismatching-ca-refused', 'refuse', { ALPHA_CREATOR_CA_POLICY: badPolicy });
        const dirtyFile = path.join(SOURCE_ROOT, 'alpha-creator-native-untracked-refusal');
        fs.writeFileSync(dirtyFile, 'Disposable source-negative fixture\n', { flag: 'wx' });
        try { await cli('dirty-source-refused', 'refuse', {}, true); } finally { fs.unlinkSync(dirtyFile); }
        const forged = structuredClone(plan); forged.revision.commit = 'a'.repeat(40); forged.revision.tree = 'b'.repeat(40);
        delete forged.payloadSha256; const forgedFile = path.join(privateRoot, 'forged-plan.json'); write(forgedFile, policy.seal(forged));
        await cli('self-declared-source-refused', 'refuse', {}, false, forgedFile);
        assert.equal(requests, before); assert.equal(fs.existsSync(journalFile), false); assert.deepEqual(fs.readdirSync(locks), []);
        await cli('wrong-key-refused', 'wrong-key');
        assert.equal(relayHashes.length, 0); assert.equal(session.loadSession(journalFile, plan, revision).operations.length, 0);
        const checkpoint = read(await cli('five-creates', 'create'));
        assert.equal(checkpoint.status, 'awaiting-governor-bindings'); assert.equal(checkpoint.finalAuthorityVerified, false);
        assert.deepEqual(checkpoint.creationHashes, relayHashes); assert.equal(relayHashes.length, 5); assert.deepEqual(checkpoint.governanceHashes, []);
        const state = session.loadSession(journalFile, plan, revision), prefix = state.operations;
        assert.equal(state.complete, false); assert.equal(prefix.length, 5); assert.ok(prefix.every(op => op.status === 'finalized'));
        assert.ok(state.locks.every(lock => fs.existsSync(lock.path))); assert.equal(await ethers.provider.getTransactionCount(creator.address), 5);
        for (const name of policy.OWNED) { const contract = await ethers.getContractAt(name, plan.addresses[name]); assert.equal(await contract.owner(), governor); assert.equal(await contract.pendingOwner(), ethers.ZeroAddress); }
        assert.equal(await (await ethers.getContractAt('AscensionRiskOracle', plan.addresses.AscensionRiskOracle)).marketplace(), ethers.ZeroAddress);
        assert.equal(await (await ethers.getContractAt('AscensionJobMarket', plan.addresses.AscensionJobMarket)).mark(), ethers.ZeroAddress);
        const repeated = read(await cli('checkpoint-without-key-or-resend', 'checkpoint'));
        assert.deepEqual(repeated.creationHashes, relayHashes); assert.deepEqual(session.loadSession(journalFile, plan, revision).operations, prefix);
        assert.equal(relayHashes.length, 5);
        writePublic(path.join(output, 'checkpoint.json'), checkpoint);
        assert.deepEqual(reviewedRevision(), revision);
        Object.assign(report, { result: 'passed', completedAt: new Date().toISOString(), fixtureRequests: requests,
            fixtureRelayCalls: relayHashes.length, creationHashes: relayHashes, governorBindings: 0, actorLocksRetained: true });
        for (const name of fs.readdirSync(output)) {
            const text = fs.readFileSync(path.join(output, name), 'utf8');
            assert.ok(!text.includes('PRIVATE KEY') && !text.includes('0x' + '11'.repeat(32)) && !text.includes('0x' + '22'.repeat(32)));
            for (const raw of rawCapabilities) assert.ok(!text.includes(raw), 'Raw capability escaped into public artifact');
        }
        writePublic(path.join(output, 'report.json'), report);
        console.log(JSON.stringify({ result: report.result, revision, creations: 5, governorBindings: 0, liveTransactions: false }));
    } catch {
        if (!fs.existsSync(path.join(output, 'report.json'))) writePublic(path.join(output, 'report.json'), { ...report, result: 'failed', failedStage: stage });
        throw Error('Creator clean-checkout rehearsal stopped; no qualification inferred');
    } finally {
        if (server) await new Promise(resolve => server.close(resolve));
        fs.rmSync(privateRoot, { recursive: true, force: true });
    }
}
if (require.main === module) main().catch(() => { console.error('Creator clean-checkout rehearsal stopped; private diagnostics omitted.'); process.exitCode = 1; });
module.exports = { main, publicRecord };
