// SPDX-License-Identifier: Apache-2.0
// Native-CI rehearsal only. Every signature and chain mutation uses an unforked disposable EVM.
// Production CLIs keep their real source anchoring and normal TLS verification throughout.
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const https = require('https');
const { spawn, execFileSync } = require('child_process');
const assert = require('assert/strict');
const legacy = require('../scripts/mainnet');
const { reviewedRevision, gitRead } = require('../scripts/authority-revision');
const policy = require('../scripts/mainnet-authority');
const { SOURCE_ROOT, assertOutsideCheckout } = require('../scripts/authority-paths');
const scripts = path.resolve(__dirname, '../scripts');
const HASH = '0x' + 'ab'.repeat(32); // Clearly synthetic qualification placeholder, never a live approval.
const readMethods = new Set(['eth_chainId', 'eth_getBlockByNumber', 'eth_getCode', 'eth_call', 'eth_getTransactionCount', 'eth_getBalance', 'eth_getTransactionByHash', 'eth_getTransactionReceipt', 'eth_getLogs']);
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const write = (file, value) => fs.writeFileSync(file, typeof value === 'string' ? value : JSON.stringify(value, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
function createFixtureCertificate(directory) {
    const certificate = path.join(directory, 'fixture-certificate.pem'), key = path.join(directory, 'fixture-key.pem');
    execFileSync('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-sha256', '-nodes', '-keyout', key, '-out', certificate,
        '-days', '1', '-subj', '/CN=Alpha disposable native CLI fixture', '-addext', 'subjectAltName=IP:127.0.0.1',
        '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,digitalSignature,keyEncipherment,keyCertSign'], { stdio: 'ignore' });
    return { certificate, key };
}
let stage = 'source-anchor';
async function main() {
    assert.equal(process.versions.node, '22.17.1', 'Use the source-qualified Node runtime');
    assert.match(process.env.ALPHA_EXPECTED_HEAD_SHA || '', /^[0-9a-f]{40}$/);
    const selectedProfile = process.env.ALPHA_NATIVE_PROFILE;
    assert.ok(['empty', 'delegated'].includes(selectedProfile), 'Explicit single native profile required');
    const revision = reviewedRevision(); // Actual clean candidate checkout; never supplied from a plan.
    assert.equal(revision.commit, process.env.ALPHA_EXPECTED_HEAD_SHA);
    const output = assertOutsideCheckout(process.env.ALPHA_NATIVE_EVIDENCE_DIRECTORY);
    assert.equal(fs.realpathSync(path.dirname(output)), path.dirname(output));
    fs.mkdirSync(output, { mode: 0o700 });
    const privateRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-native-private-'));
    const report = { schema: 'agialpha.native-clean-checkout-cli.v1', revision, startedAt: new Date().toISOString(),
        selectedProfile, node: process.versions.node, openssl: execFileSync('openssl', ['version'], { encoding: 'utf8' }).trim(),
        publicProviderCalls: 0, providerFork: false, hardwareWallet: false, realFunds: false, activationAllowed: false,
        chainScope: 'Unforked in-process Osaka; mock dependencies, disposable local keys and synthetic finalized=latest', commands: [], campaigns: [] };
    const rawCapabilities = new Set(); let server;
    try {
        stage = 'local-fixture';
        const { ethers, network } = require('hardhat');
        await require('../scripts/disposable').requireDisposableLocalNetwork();
        assert.equal(network.config.hardfork, 'osaka'); assert.equal(network.config.chainId, 1);
        const { installToken } = require('../test/utils/token');
        const { certificate, key } = createFixtureCertificate(privateRoot);
        report.fixtureCertificateSha256 = sha(fs.readFileSync(certificate));
        let count = 0, relays = 0, mutationOnRead = null, restoreLateMutation = null, loseRelayResponse = false;
        server = https.createServer({ key: fs.readFileSync(key), cert: fs.readFileSync(certificate), minVersion: 'TLSv1.2' }, (req, res) => {
            const chunks = []; let size = 0;
            req.on('data', bytes => { size += bytes.length; if (size > 262144) req.destroy(); else chunks.push(bytes); });
            req.on('end', async () => {
                try {
                    assert.equal(req.method, 'POST'); assert.ok(++count <= 30000, 'Fixture request budget');
                    const body = JSON.parse(Buffer.concat(chunks));
                    assert.equal(body.jsonrpc, '2.0'); assert.ok(Array.isArray(body.params));
                    const relay = req.url === '/relay'; assert.ok(relay || req.url === '/read');
                    assert.ok(relay ? body.method === 'eth_sendRawTransaction' : readMethods.has(body.method));
                    if (!relay && mutationOnRead) { const mutate = mutationOnRead; mutationOnRead = null; restoreLateMutation = mutate() || null; }
                    const params = body.method === 'eth_getBlockByNumber' && body.params[0] === 'finalized' ? ['latest', false] : body.params;
                    const result = await ethers.provider.send(body.method, params);
                    if (relay) { relays++; if (loseRelayResponse) { loseRelayResponse = false; req.socket.destroy(); return; } }
                    res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ jsonrpc: '2.0', id: body.id, result }));
                } catch { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Disposable fixture request rejected' })); }
            });
        });
        server.requestTimeout = 20000; server.headersTimeout = 10000;
        await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
        const origin = `https://127.0.0.1:${server.address().port}`;
        const baseEnv = { ...process.env, NODE_EXTRA_CA_CERTS: certificate, NODE_OPTIONS: '--max-old-space-size=384', ALPHA_READ_ONLY_RPC_URL: `${origin}/read` };
        delete baseEnv.NODE_TLS_REJECT_UNAUTHORIZED; delete baseEnv.ALPHA_ENABLE_USER_RUN_RAW_RELAY; delete baseEnv.ALPHA_RAW_RELAY_RPC_URL;
        let serial = 0;
        async function cli(label, file, args, expected = 0, extraEnv = {}, intentionalDirtyNegative = false) {
            stage = label;
            if (intentionalDirtyNegative) { assert.equal(expected, 1); assert.notEqual(gitRead(['ls-files', '--others', '--exclude-standard', '-z']).trim(), ''); }
            else assert.deepEqual(reviewedRevision(), revision);
            const child = spawn(process.execPath, [path.join(scripts, file), ...args], { cwd: path.dirname(scripts), env: { ...baseEnv, ...extraEnv }, stdio: ['ignore', 'pipe', 'pipe'] });
            let stdout = '', stderr = ''; const timer = setTimeout(() => child.kill('SIGKILL'), 90000);
            child.stdout.on('data', chunk => { stdout += chunk; if (stdout.length > 65536) child.kill('SIGKILL'); });
            child.stderr.on('data', chunk => { stderr += chunk; if (stderr.length > 65536) child.kill('SIGKILL'); });
            const code = await new Promise((resolve, reject) => { child.on('error', reject); child.on('exit', resolve); }); clearTimeout(timer);
            if (restoreLateMutation) { const restore = restoreLateMutation; restoreLateMutation = null; restore(); }
            assert.ok(!stdout.includes('ALPHA_PRIVATE_JSON_SENTINEL') && !stderr.includes('ALPHA_PRIVATE_JSON_SENTINEL'), 'Private malformed input leaked in CLI diagnostics');
            report.commands.push({ label, exitCode: code, expectedExitCode: expected, stdoutSha256: sha(stdout), stderrSha256: sha(stderr) });
            assert.equal(code, expected, `Unexpected CLI outcome at ${label}`);
            if (!intentionalDirtyNegative) assert.deepEqual(reviewedRevision(), revision);
        }
        async function fixture(mode) {
            await network.provider.send('hardhat_reset');
            const [sponsor, governorSigner] = await ethers.getSigners();
            const creator = ethers.Wallet.createRandom().connect(ethers.provider);
            const governor = ethers.HDNodeWallet.fromPhrase('test test test test test test test test test test test junk', undefined, "m/44'/60'/0'/0/1").connect(ethers.provider);
            assert.equal(governor.address, governorSigner.address);
            await (await sponsor.sendTransaction({ to: creator.address, value: ethers.parseEther('20') })).wait();
            await installToken();
            for (const [name, target] of [['MockAscensionENS', legacy.ENS], ['MockAscensionWrapper', legacy.WRAPPER]]) {
                const deployed = await (await ethers.getContractFactory(name)).deploy();
                await ethers.provider.send('hardhat_setCode', [target, await ethers.provider.getCode(deployed.target)]);
            }
            const ens = await ethers.getContractAt('MockAscensionENS', legacy.ENS);
            for (const root of legacy.roots) await (await ens.setOwner(ethers.namehash(root), governor.address)).wait();
            const dependencies = { token: require('../../../token.config').AGIALPHA_ADDRESS, ens: legacy.ENS, wrapper: legacy.WRAPPER };
            const config = { schema: 'agialpha.mainnet.config.v2', chainId: 1, deployer: creator.address, nonce: 0, block: null,
                governor: { kind: 'ledger-eoa', address: governor.address, addressAcknowledgement: governor.address },
                dependencies: {}, rootOwners: Object.fromEntries(legacy.roots.map(root => [root, governor.address])),
                parameters: { minimumValidatorStake: '10000000000000000000', minimumAgentStake: '10000000000000000000', quorum: 2, maximumRiskBps: 2000 },
                sender: { mode }, envelope: { gasLimit: '8000000', maxFeePerGas: '10000000000', maxPriorityFeePerGas: '1000000000', accessList: [] } };
            if (mode === policy.DELEGATED) {
                const target = ethers.getAddress('0x' + 'c9'.padStart(40, '0')), code = '0x600060006000f000';
                await ethers.provider.send('hardhat_setCode', [target, code]);
                const authorization = await creator.authorize({ address: target, chainId: 1, nonce: 0 });
                await (await sponsor.sendTransaction({ type: 4, to: sponsor.address, authorizationList: [authorization] })).wait();
                config.sender = { mode, delegationCode: `0xef0100${target.slice(2).toLowerCase()}`, target, targetCodeHash: ethers.keccak256(code),
                    stateChecks: [{ to: target, data: '0x12345678', resultHash: ethers.keccak256('0x') }],
                    qualification: { consensusEvidenceSha256: HASH.slice(2), forkEvidenceSha256: HASH.slice(2), delegateReviewSha256: HASH.slice(2) } };
            }
            for (const [name, address] of Object.entries(dependencies)) config.dependencies[name] = { address, codeHash: ethers.keccak256(await ethers.provider.getCode(address)) };
            config.nonce = Number(BigInt(await ethers.provider.send('eth_getTransactionCount', [creator.address, 'latest'])));
            const block = await ethers.provider.send('eth_getBlockByNumber', ['latest', false]); config.block = { number: Number(BigInt(block.number)), hash: block.hash };
            const journal = { schema: 'ethereum.cross-project-nonce-journal.v1', journalId: 'SYNTHETIC-NATIVE-CLI', revision: 1, chainId: 1, sender: creator.address,
                scope: ['alpha', 'jobs', 'manager'], block: config.block, latestNonce: config.nonce, pendingNonce: config.nonce,
                allocations: [{ project: 'alpha', startNonce: config.nonce, count: 5 }, { project: 'jobs', startNonce: config.nonce + 5, count: 1 }, { project: 'manager', startNonce: config.nonce + 6, count: 1 }] };
            return { config, journal, creator, governor };
        }
        // Separate native processes bound EDR accumulation; CI executes both explicit profiles serially.
        const campaigns = { empty: [policy.EMPTY, 'raw-relay'], delegated: [policy.DELEGATED, 'external-broadcast'] };
        for (const [profile, mode] of [campaigns[selectedProfile]]) {
            const f = await fixture(profile), directory = path.join(privateRoot, mode); fs.mkdirSync(directory);
            const next = name => path.join(directory, `${++serial}-${name}`);
            const configFile = next('config.json'), planFile = next('plan.json'), progressFile = next('progress.json'), journalFile = next('session.jsonl');
            const lockDirectory = next('locks'); fs.mkdirSync(lockDirectory);
            const env = { DEPLOYMENT_LOCK_DIRECTORY: lockDirectory };
            write(configFile, { config: f.config, journal: f.journal });
            await cli(`${mode}:plan`, 'mainnet-authority.js', ['plan', configFile, planFile]);
            const plan = read(planFile); assert.deepEqual(plan.revision, revision);
            await cli(`${mode}:predicted-package`, 'authority-verification-package.js', ['plan', planFile, path.join(output, `${mode}-predicted-package`)]);
            write(progressFile, { creationHashes: [], governanceHashes: [], journal: f.journal });
            await cli(`${mode}:initial-preflight`, 'authority-cli.js', ['preflight', planFile, progressFile, next('preflight.json')]);
            async function command(action, fields = {}, expected = 0, destination = next(`${action}-output.json`), overrideEnv = {}) {
                const input = next(`${action}-command.json`); write(input, { plan: planFile, journal: journalFile, ...fields });
                await cli(`${mode}:${action}`, 'authority-session.js', [action, input, destination], expected, { ...env, ...overrideEnv });
                return expected === 0 ? read(destination) : destination;
            }
            async function rejectLateMutation(label, target, action, fields, overrideEnv = {}) {
                const journalBefore = fs.readFileSync(journalFile), headBefore = fs.readFileSync(journalFile + '.head.json'), relayBefore = relays;
                const destination = next(`late-${label}-refused.json`); let mutated = false;
                mutationOnRead = () => { const saved = fs.readFileSync(target); fs.appendFileSync(target, '\n'); mutated = true; return () => fs.writeFileSync(target, saved); };
                await command(action, fields, 1, destination, overrideEnv);
                report.commands.at(-1).lateInputDriftCase = label;
                assert.equal(mutated, true); assert.equal(mutationOnRead, null); assert.equal(restoreLateMutation, null);
                assert.equal(fs.existsSync(destination), false); assert.ok(fs.readFileSync(journalFile).equals(journalBefore));
                assert.ok(fs.readFileSync(journalFile + '.head.json').equals(headBefore)); assert.equal(relays, relayBefore);
            }
            const lateTargets = { plan: planFile,
                artifact: path.join(SOURCE_ROOT, 'tests/contracts/artifacts/contracts/ascension/AscensionAccess.sol/AscensionAccess.json'),
                dependency: path.join(SOURCE_ROOT, 'tests/contracts/node_modules/@openzeppelin/contracts/access/Ownable.sol'),
                trackedSource: path.join(SOURCE_ROOT, 'contracts/ascension/AscensionAccess.sol') };
            // Invalid paths fail before any RPC or lock creation, even when Git ignores the path.
            const inside = path.join(SOURCE_ROOT, 'tests/contracts/node_modules/alpha-native-forbidden-output.json');
            let before = count;
            await cli(`${mode}:reject-in-checkout-plan`, 'mainnet-authority.js', ['plan', configFile, inside], 1);
            await cli(`${mode}:reject-in-checkout-package`, 'authority-verification-package.js', ['plan', planFile, inside], 1);
            await cli(`${mode}:reject-in-checkout-preflight`, 'authority-cli.js', ['preflight', planFile, progressFile, inside], 1);
            await command('start', { mode }, 1, next('forbidden-locks.json'), { DEPLOYMENT_LOCK_DIRECTORY: SOURCE_ROOT });
            assert.equal(count, before); assert.equal(fs.existsSync(inside), false); assert.deepEqual(fs.readdirSync(lockDirectory), []);
            const alias = next('checkout-alias'); fs.symlinkSync(SOURCE_ROOT, alias, 'dir');
            await cli(`${mode}:reject-symlinked-output`, 'mainnet-authority.js', ['plan', configFile, path.join(alias, 'forbidden-output.json')], 1);
            const forged = JSON.parse(JSON.stringify(plan)); forged.revision.commit = 'a'.repeat(40); forged.revision.tree = 'b'.repeat(40);
            const { payloadSha256, ...forgedPayload } = forged, forgedFile = next('forged-plan.json'); write(forgedFile, policy.seal(forgedPayload));
            await cli(`${mode}:reject-self-declared-source`, 'authority-cli.js', ['preflight', forgedFile, progressFile, next('forged-report.json')], 1);
            assert.equal(count, before);
            const sentinel = path.join(SOURCE_ROOT, `alpha-native-dirty-${crypto.randomUUID()}.txt`); write(sentinel, 'Intentional clean-checkout rejection fixture');
            try { await cli(`${mode}:reject-dirty-source`, 'mainnet-authority.js', ['plan', configFile, next('dirty-plan.json')], 1, {}, true); }
            finally { fs.unlinkSync(sentinel); }
            assert.deepEqual(reviewedRevision(), revision); assert.equal(count, before);
            await cli(`${mode}:reject-untrusted-local-TLS`, 'authority-cli.js', ['preflight', planFile, progressFile, next('untrusted-report.json')], 1, { NODE_EXTRA_CA_CERTS: '' });
            assert.equal(count, before); // TLS verification rejects before an HTTP/RPC method reaches the fixture.
            const malformed = next('malformed-command.json'), malformedOutput = next('malformed-output.json'); write(malformed, 'ALPHA_PRIVATE_JSON_SENTINEL');
            before = count; await cli(`${mode}:reject-private-malformed-json`, 'authority-session.js', ['prepare', malformed, malformedOutput], 1);
            assert.equal(count, before); assert.equal(fs.existsSync(malformedOutput), false);
            await command('start', { mode });
            const beforeReplacement = fs.readFileSync(journalFile), movedDirectory = directory + '-displaced';
            mutationOnRead = () => {
                fs.renameSync(directory, movedDirectory); fs.mkdirSync(directory);
                write(journalFile + '.command-lock', 'replacement command gate');
                return () => {
                    assert.equal(fs.readFileSync(journalFile + '.command-lock', 'utf8'), 'replacement command gate');
                    assert.ok(fs.existsSync(path.join(movedDirectory, path.basename(journalFile) + '.command-lock')));
                    fs.rmSync(directory, { recursive: true, force: true }); fs.renameSync(movedDirectory, directory);
                    fs.unlinkSync(journalFile + '.command-lock'); // Explicit disposable retained-gate recovery only.
                };
            };
            await command('prepare', { governorEnvelope: null }, 1);
            report.commands.at(-1).lateInputDriftCase = 'journal-parent-and-command-gate-replacement';
            assert.ok(fs.readFileSync(journalFile).equals(beforeReplacement));
            for (const [label, target] of Object.entries(lateTargets)) await rejectLateMutation(`prepare-${label}`, target, 'prepare', { governorEnvelope: null });
            const creationHashes = [], governanceHashes = [], phases = [];
            const relayStart = relays;
            for (let index = 0; index < 7; ++index) {
                let governorEnvelope = null;
                if (index >= 5) { governorEnvelope = next('governor-envelope.json'); write(governorEnvelope, { nonce: Number(BigInt(await ethers.provider.send('eth_getTransactionCount', [f.governor.address, 'pending']))), gasLimit: '1000000', maxFeePerGas: '10000000000', maxPriorityFeePerGas: '1000000000', accessList: [] }); }
                let prepared;
                if (index === 0) {
                    const lostOutput = next('lost-handoff-output.json'); mutationOnRead = () => write(lostOutput, 'synthetic output collision');
                    await command('prepare', { governorEnvelope }, 1, lostOutput);
                    prepared = await command('handoff');
                } else prepared = await command('prepare', { governorEnvelope });
                const packet = prepared.packet, { from, ...envelope } = packet.envelope;
                const raw = await (index < 5 ? f.creator : f.governor).signTransaction(envelope); rawCapabilities.add(raw);
                const txHash = ethers.Transaction.from(raw).hash, rawFile = next('signed.txt'); write(rawFile, raw);
                if (index === 0) {
                    const insideRaw = path.join(SOURCE_ROOT, 'tests/contracts/node_modules/alpha-private-synthetic-raw.txt'); write(insideRaw, raw);
                    const beforeInside = count;
                    try { await command('import', { signedRawFile: insideRaw }, 1); } finally { fs.unlinkSync(insideRaw); }
                    assert.equal(count, beforeInside);
                    const wrongRaw = await f.creator.signTransaction({ ...envelope, value: '1' }); rawCapabilities.add(wrongRaw);
                    const wrongFile = next('wrong-signed.txt'); write(wrongFile, wrongRaw); const beforeWrong = count;
                    await command('import', { signedRawFile: wrongFile }, 1); assert.equal(count, beforeWrong);
                    const head = journalFile + '.head.json', saved = fs.readFileSync(head, 'utf8'); fs.unlinkSync(head);
                    try { await command('status', {}, 1); } finally { write(head, saved); } // deliberate disposable corruption fixture only
                    assert.equal(count, beforeWrong);
                }
                if (index === 1) await (await ethers.provider.broadcastTransaction(raw)).wait(); // exact hashless external handoff recovery
                else {
                    if (index === 0) {
                        const lostOutput = next('lost-import-output.json'); mutationOnRead = () => write(lostOutput, 'synthetic output collision');
                        await command('import', { signedRawFile: rawFile }, 1, lostOutput);
                    } else await command('import', { signedRawFile: rawFile });
                    const status = await command('status'); assert.equal(status.state.operations[index].status, 'signed');
                    if (index === 0) {
                        const gate = journalFile + '.command-lock'; fs.symlinkSync(next('absent-gate-target'), gate);
                        try {
                            const blocked = await command('status'); assert.equal(blocked.commandBlocked, true); assert.equal(blocked.relayAcknowledgement, null);
                            const beforeBlocked = count;
                            await command('prepare', { governorEnvelope: null }, 1); assert.equal(count, beforeBlocked);
                        } finally { fs.unlinkSync(gate); } // Explicit disposable stale-gate fixture cleanup only.
                    }
                    if (mode === 'raw-relay') {
                        if (index === 0) for (const [label, target] of Object.entries(lateTargets))
                            await rejectLateMutation(`relay-${label}`, target, 'relay', { signedRawFile: rawFile, acknowledgement: status.relayAcknowledgement },
                                { ALPHA_ENABLE_USER_RUN_RAW_RELAY: 'I_REVIEWED_THIS_EXACT_TRANSACTION', ALPHA_RAW_RELAY_RPC_URL: `${origin}/relay` });
                        loseRelayResponse = index === 0;
                        await command('relay', { signedRawFile: rawFile, acknowledgement: status.relayAcknowledgement }, index === 0 ? 1 : 0, next('relay-result.json'),
                            { ALPHA_ENABLE_USER_RUN_RAW_RELAY: 'I_REVIEWED_THIS_EXACT_TRANSACTION', ALPHA_RAW_RELAY_RPC_URL: `${origin}/relay` });
                        await command('relay', { signedRawFile: rawFile, acknowledgement: status.relayAcknowledgement }, 1, next('relay-retry-refused.json'),
                            { ALPHA_ENABLE_USER_RUN_RAW_RELAY: 'I_REVIEWED_THIS_EXACT_TRANSACTION', ALPHA_RAW_RELAY_RPC_URL: `${origin}/relay` });
                    } else await (await ethers.provider.broadcastTransaction(raw)).wait();
                }
                const recovered = await command('recover', { transactionHash: null }); assert.equal(recovered.resolved, true);
                const state = await command('reconcile', { transactionHash: null }); assert.equal(state.operations.length, index + 1);
                (index < 5 ? creationHashes : governanceHashes).push(txHash);
                const progress = next('phase-input.json'), result = next('phase-output.json'); write(progress, { creationHashes, governanceHashes, journal: f.journal });
                await cli(`${mode}:phase-${index + 1}`, 'authority-cli.js', ['preflight', planFile, progress, result]);
                phases.push(read(result).report.bindings.length);
            }
            assert.deepEqual(phases, [0, 0, 0, 0, 0, 1, 2]); assert.equal(relays - relayStart, mode === 'raw-relay' ? 6 : 0);
            const lostFinish = next('lost-finish-output.json'); mutationOnRead = () => write(lostFinish, 'synthetic output collision');
            await command('finish', {}, 1, lostFinish);
            const completed = await command('finish'); assert.equal(completed.evidence.graphAuthorityVerified, true); assert.equal(completed.evidence.activationAllowed, false);
            assert.deepEqual(fs.readdirSync(lockDirectory), []);
            const evidence = { creationHashes, governanceHashes, acceptanceBlock: completed.evidence.block }, evidenceFile = next('receipts.json'); write(evidenceFile, evidence);
            const verifyFile = path.join(output, `${mode}-authority.json`);
            await cli(`${mode}:receipt-verify`, 'authority-cli.js', ['verify', planFile, evidenceFile, verifyFile]);
            const packagePath = path.join(output, `${mode}-receipt-package`);
            await cli(`${mode}:receipt-package`, 'authority-verification-package.js', ['receipts', planFile, evidenceFile, packagePath]);
            assert.equal(read(path.join(packagePath, 'manifest.json')).addressStatus, 'receipt-proven');
            write(path.join(output, `${mode}-receipts.json`), evidence);
            report.campaigns.push({ profile, mode, creationHashes, governanceHashes, phases, exactFinalAuthority: true });
        }
        report.fixtureRequests = count; report.fixtureRelayCalls = relays;
        report.sourceInventory = Object.fromEntries(gitRead(['ls-files', '-z', 'tests/contracts', 'contracts', 'token.config.js', '.github/workflows/alpha-authority-v2.yml']).split('\0').filter(Boolean).map(p => [p, sha(fs.readFileSync(path.join(SOURCE_ROOT, p)))]));
        assert.deepEqual(reviewedRevision(), revision);
        report.completedAt = new Date().toISOString(); report.result = 'passed';
        function inspect(directory) { for (const name of fs.readdirSync(directory)) { const p = path.join(directory, name); if (fs.statSync(p).isDirectory()) inspect(p); else { const text = fs.readFileSync(p, 'utf8'); assert.ok(!text.includes('PRIVATE KEY')); for (const raw of rawCapabilities) assert.ok(!text.includes(raw), 'Raw signed capability escaped into public evidence'); } } }
        inspect(output);
        write(path.join(output, 'report.json'), report);
        console.log(JSON.stringify({ result: report.result, revision, commands: report.commands.length, campaigns: report.campaigns.length, evidence: output, liveTransactions: false }));
    } catch (error) {
        const failure = { ...report, result: 'failed', failedStage: stage, completedAt: new Date().toISOString() };
        if (!fs.existsSync(path.join(output, 'report.json'))) write(path.join(output, 'report.json'), failure);
        throw Error(`Native CLI rehearsal stopped at ${stage}; no hosted qualification is inferred.`);
    } finally {
        if (server) await new Promise(resolve => server.close(resolve));
        fs.rmSync(privateRoot, { recursive: true, force: true });
    }
}
if (require.main === module) main().catch(error => { console.error(error.message); process.exitCode = 1; });
module.exports = { main, createFixtureCertificate };
