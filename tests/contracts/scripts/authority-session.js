// SPDX-License-Identifier: Apache-2.0
// User-run coordinator: external signing only. No private-key, wallet or account-unlock API.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const E = require('ethers');
const policy = require('./mainnet-authority');
const legacy = require('./mainnet');
const { readJson, writeNew } = require('./authority-cli');
const { scopeForPlan, createReadOnlyRpc } = require('./authority-rpc');
const { assertOutsideCheckout } = require('./authority-paths');
const SCHEMA = 'agialpha.new-graph-session.v1';
function requireValue(ok, message) { if (!ok) { const error = Error(message); error.publicMessage = true; throw error; } }
function same(a, b, label) { requireValue(legacy.canonical(a) === legacy.canonical(b), `Session mismatch: ${label}`); }
function directorySync(directory) { const fd = fs.openSync(directory, 'r'); try { fs.fsyncSync(fd); } finally { fs.closeSync(fd); } }
function ordinaryPath(filename) {
    const target = assertOutsideCheckout(filename); requireValue(fs.realpathSync(path.dirname(target)) === path.dirname(target), 'Symlink parent is unsupported');
    if (fs.existsSync(target)) requireValue(fs.lstatSync(target).isFile() && !fs.lstatSync(target).isSymbolicLink(), 'Ordinary file required');
    return target;
}
function ownerKeys(plan) { return [...new Set([plan.config.deployer, plan.config.governor.address].map(a => `1-${a.toLowerCase()}`))].sort(); }
function acquireActors(plan, directory, journalPath) {
    assertOutsideCheckout(directory); assertOutsideCheckout(journalPath);
    requireValue(directory && path.isAbsolute(directory) && fs.realpathSync(directory) === directory && fs.statSync(directory).isDirectory(), 'Existing absolute shared DEPLOYMENT_LOCK_DIRECTORY required');
    const locks = [];
    try {
        for (const key of ownerKeys(plan)) {
            const lockPath = path.join(directory, key);
            try { fs.mkdirSync(lockPath, { mode: 0o700 }); } catch (error) { if (error.code === 'EEXIST') requireValue(false, 'Actor lock exists; reconcile its journal, never auto-break a stale lock'); throw error; }
            const lock = { schema: 'creator-nonce-lock-v1', chainId: 1, creator: E.getAddress(key.slice(2)), journalPath,
                token: crypto.randomUUID(), path: lockPath };
            // If this write fails, retain the incomplete lock for manual investigation.
            writeNew(path.join(lockPath, 'owner.json'), lock); directorySync(directory); locks.push(lock);
        }
        return locks;
    } catch (error) { for (const lock of locks.reverse()) releaseActor(lock); throw error; }
}
function assertActor(lock) {
    requireValue(path.isAbsolute(lock.path) && fs.realpathSync(lock.path) === lock.path, 'Actor lock path changed');
    same(readJson(path.join(lock.path, 'owner.json')), lock, 'actor lock ownership');
}
function actorSnapshot(lock, allowAbsent = false) {
    const parent = path.dirname(lock.path), parentStat = fs.lstatSync(parent);
    requireValue(parentStat.isDirectory() && !parentStat.isSymbolicLink() && fs.realpathSync(parent) === parent, 'Actor parent changed');
    const snapshot = { parent: [parentStat.dev, parentStat.ino], actor: null, owner: null };
    if (allowAbsent && !assertCompletedActor(lock)) return snapshot;
    assertActor(lock);
    const actor = fs.lstatSync(lock.path), owner = fs.lstatSync(path.join(lock.path, 'owner.json'));
    requireValue(actor.isDirectory() && !actor.isSymbolicLink() && owner.isFile() && !owner.isSymbolicLink(), 'Actor lease entry type changed');
    snapshot.actor = [actor.dev, actor.ino]; snapshot.owner = [owner.dev, owner.ino]; return snapshot;
}
function assertActorSnapshots(locks, snapshots) {
    locks.forEach((lock, index) => same(actorSnapshot(lock, snapshots[index].actor === null), snapshots[index], 'actor lease identity changed; preserve locks'));
}
function releaseActor(lock) { assertActor(lock); fs.unlinkSync(path.join(lock.path, 'owner.json')); fs.rmdirSync(lock.path); directorySync(path.dirname(lock.path)); }
function assertCompletedActor(lock) {
    requireValue(fs.realpathSync(path.dirname(lock.path)) === path.dirname(lock.path), 'Actor lock parent changed');
    try { fs.lstatSync(lock.path); } catch (error) { if (error.code === 'ENOENT') return false; throw error; }
    assertActor(lock); return true; // Existing replacement or incomplete locks always block cleanup.
}
function append(filename, state, previous = null) {
    const { payloadSha256, sequence, previousSha256, ...payload } = state;
    const row = policy.seal({ ...payload, sequence: previous ? previous.sequence + 1 : 0, previousSha256: previous ? previous.payloadSha256 : null });
    const fd = fs.openSync(filename, (previous ? fs.constants.O_WRONLY | fs.constants.O_APPEND : fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL) | fs.constants.O_NOFOLLOW, 0o600);
    try { requireValue(fs.fstatSync(fd).isFile(), 'Ordinary journal required'); fs.writeFileSync(fd, JSON.stringify(row) + '\n'); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
    directorySync(path.dirname(filename));
    // A separately durable head detects loss of a complete final JSONL row. A crash
    // between journal and head persistence blocks recovery rather than guessing.
    const headPath = ordinaryPath(`${filename}.head.json`), pending = `${headPath}.pending-${crypto.randomUUID()}`;
    requireValue(Boolean(previous) === fs.existsSync(headPath), 'Unexpected journal head; preserve files for manual recovery');
    writeNew(pending, { schema: 'agialpha.session-head.v1', journalPath: filename, sequence: row.sequence, payloadSha256: row.payloadSha256 });
    fs.renameSync(pending, headPath); directorySync(path.dirname(filename)); return row;
}
function normalizedEnvelope(tx) {
    return { type: tx.type, chainId: Number(tx.chainId), from: E.getAddress(tx.from), nonce: Number(tx.nonce),
        to: tx.to === null ? null : E.getAddress(tx.to), value: tx.value.toString(), data: tx.data.toLowerCase(), gasLimit: tx.gasLimit.toString(),
        maxFeePerGas: tx.maxFeePerGas?.toString(), maxPriorityFeePerGas: tx.maxPriorityFeePerGas?.toString(), accessList: tx.accessList };
}
function canonicalEnvelope(envelope) { return { ...envelope, from: E.getAddress(envelope.from), to: envelope.to === null ? null : E.getAddress(envelope.to), data: envelope.data.toLowerCase() }; }
function validateSigned(raw, intent) {
    requireValue(typeof raw === 'string' && /^0x[0-9a-fA-F]+$/.test(raw) && raw.length <= 200000, 'Bounded serialized signed transaction required');
    const tx = E.Transaction.from(raw);
    requireValue(tx.isSigned() && tx.type === 2 && !tx.authorizationList && !tx.blobVersionedHashes && tx.serialized.toLowerCase() === raw.toLowerCase(), 'Only canonical signed type-2 transactions are supported');
    same(normalizedEnvelope(tx), canonicalEnvelope(intent.envelope), 'signed transaction envelope/recovered sender');
    return { hash: tx.hash, rawSha256: policy.digest(raw.toLowerCase()), from: tx.from };
}
function validateIntent(plan, operation) {
    const intent = operation.intent, index = operation.index;
    requireValue(Number.isInteger(index) && index >= 0 && index < 7 && intent && intent.planSha256 === plan.payloadSha256 && intent.senderPolicySha256 === policy.digest(plan.config.sender), 'Invalid operation intent');
    requireValue(Number.isSafeInteger(intent.startBlock) && intent.startBlock >= plan.config.block.number, 'Invalid intent starting block');
    const envelope = intent.envelope;
    requireValue(envelope && Object.keys(envelope).sort().join(',') === 'accessList,chainId,data,from,gasLimit,maxFeePerGas,maxPriorityFeePerGas,nonce,to,type,value', 'Exact transaction envelope required');
    if (index < 5) {
        same(envelope, plan.transactions[index].envelope, 'CREATE intent');
        same(intent.shared, { ...policy.creationIntents(plan)[index], startBlock: intent.startBlock }, 'shared CREATE intent');
    } else {
        const expected = plan.governanceCalls[index - 5];
        same({ from: envelope.from, to: envelope.to, data: envelope.data, chainId: envelope.chainId, value: envelope.value },
            { from: expected.from, to: expected.to, data: expected.data, chainId: 1, value: '0' }, 'new-graph governor CALL');
        requireValue(envelope.type === 2 && Number.isSafeInteger(envelope.nonce) && envelope.nonce >= 0 && Array.isArray(envelope.accessList) && envelope.accessList.length === 0, 'Unsupported governor envelope');
        for (const key of ['gasLimit', 'maxFeePerGas', 'maxPriorityFeePerGas']) requireValue(typeof envelope[key] === 'string' && /^(0|[1-9][0-9]*)$/.test(envelope[key]) && BigInt(envelope[key]) < 2n ** 256n, 'Invalid governor gas/fee quantity');
        requireValue(BigInt(envelope.gasLimit) >= 21000n && BigInt(envelope.gasLimit) <= policy.MAX_TRANSACTION_GAS && BigInt(envelope.maxFeePerGas) > 0n && BigInt(envelope.maxPriorityFeePerGas) <= BigInt(envelope.maxFeePerGas), 'Governor gas/fee bounds');
        same(intent.shared, { schema: 'governor-call-intent-v1', chainId: 1, creator: E.getAddress(envelope.from), nonce: envelope.nonce,
            to: envelope.to, value: '0', dataHash: E.keccak256(envelope.data), startBlock: intent.startBlock, gasLimit: envelope.gasLimit }, 'governor intent');
    }
    same(intent.envelopeSha256, policy.digest(envelope), 'full envelope hash');
    same(operation.intentSha256, policy.digest(intent), 'intent hash');
}
function loadSession(filename, plan, revision) {
    const target = ordinaryPath(filename), fd = fs.openSync(target, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    let text; try { requireValue(fs.fstatSync(fd).size <= 16 * 1024 * 1024, 'Session journal exceeds bound'); text = fs.readFileSync(fd, 'utf8'); } finally { fs.closeSync(fd); }
    requireValue(text.endsWith('\n'), 'Torn journal tail; preserve evidence and use manual recovery');
    const lines = text.trimEnd().split('\n'); requireValue(lines.length > 0 && lines.length <= 1000, 'Journal length outside bounds');
    let previous;
    for (const line of lines) {
        const row = JSON.parse(line), { payloadSha256, ...payload } = row;
        same(payloadSha256, policy.digest(payload), 'journal checksum');
        requireValue(row.schema === SCHEMA && row.provenance === 'new-receipt-bound-graph' && row.planSha256 === plan.payloadSha256 && row.journalPath === target, 'Wrong session source/plan/path');
        same(row.revision, revision, 'independent source revision');
        same(row.sequence, previous ? previous.sequence + 1 : 0, 'journal sequence');
        same(row.previousSha256, previous ? previous.payloadSha256 : null, 'journal chain');
        requireValue(['external-broadcast', 'raw-relay'].includes(row.mode) && Array.isArray(row.locks) && row.locks.length === ownerKeys(plan).length, 'Unsupported session/lock scope');
        same(row.locks.map(x => path.basename(x.path)), ownerKeys(plan), 'actor lock order');
        requireValue(row.locks.every(x => x.schema === 'creator-nonce-lock-v1' && x.chainId === 1 && x.journalPath === target && E.getAddress(x.creator).toLowerCase() === path.basename(x.path).slice(2)), 'Invalid actor lock identity');
        if (previous) for (const key of ['deploymentId', 'revision', 'planSha256', 'journalPath', 'mode', 'locks']) same(row[key], previous[key], `immutable session ${key}`);
        requireValue(Array.isArray(row.operations) && row.operations.length <= 7 && typeof row.complete === 'boolean', 'Invalid operation sequence');
        row.operations.forEach((operation, index) => {
            requireValue(operation.index === index && ['handed-off', 'signed', 'submission-attempted', 'receipt-observed', 'finalized', 'failed'].includes(operation.status), 'Invalid operation state');
            if (index < row.operations.length - 1) requireValue(operation.status === 'finalized', 'Only a contiguous finalized operation prefix may advance');
            validateIntent(plan, operation);
            if (operation.status !== 'handed-off') requireValue(/^0x[0-9a-f]{64}$/.test(operation.txHash || ''), 'Known transaction hash required');
            if (previous?.operations[index]) {
                const old = previous.operations[index]; same(operation.intent, old.intent, 'immutable durable intent');
                if (old.txHash) same(operation.txHash, old.txHash, 'immutable transaction hash');
                const next = { 'handed-off': ['handed-off', 'signed', 'receipt-observed', 'finalized', 'failed'], signed: ['signed', 'submission-attempted', 'receipt-observed', 'finalized', 'failed'],
                    'submission-attempted': ['submission-attempted', 'receipt-observed', 'finalized', 'failed'], 'receipt-observed': ['receipt-observed', 'finalized', 'failed'], finalized: ['finalized'], failed: ['failed'] };
                requireValue(next[old.status].includes(operation.status), 'Journal state regressed or tried to resubmit');
            }
        });
        if (previous) requireValue(row.operations.length >= previous.operations.length && row.operations.length <= previous.operations.length + 1 && (!previous.complete || row.complete), 'Journal operation history changed');
        requireValue(!row.complete || (row.operations.length === 7 && row.operations.every(x => x.status === 'finalized')), 'Premature session completion');
        if (row.complete) {
            const { payloadSha256: evidenceSha256, ...evidence } = row.authorityEvidence || {};
            same(evidenceSha256, policy.digest(evidence), 'completion evidence checksum');
            same(row.authorityEvidenceSha256, evidenceSha256, 'durable completion evidence');
            requireValue(evidence.schema === 'agialpha.mainnet.authority-evidence.v2' && evidence.graphAuthorityVerified === true && evidence.planSha256 === plan.payloadSha256, 'Invalid completion evidence');
            same(evidence.observedRevision, revision, 'completion source revision');
            if (previous?.complete) same(row.authorityEvidence, previous.authorityEvidence, 'immutable completion evidence');
        } else requireValue(!Object.hasOwn(row, 'authorityEvidence') && !Object.hasOwn(row, 'authorityEvidenceSha256'), 'Premature completion evidence');
        previous = row;
    }
    same(readJson(`${target}.head.json`), { schema: 'agialpha.session-head.v1', journalPath: target, sequence: previous.sequence, payloadSha256: previous.payloadSha256 }, 'durable journal head (missing tail or incomplete checkpoint)');
    return previous;
}
// Library callers own their independently observed revision/context; operational CLI always supplies
// the synchronous pinned-input boundary. No CLI flag can omit it.
async function guarded(plan, revision, filename, fn, completedCleanup = false, assertInputs = () => {}) {
    await policy.checkPlan(plan, undefined, revision);
    const target = ordinaryPath(filename), gate = `${target}.command-lock`, parent = path.dirname(target);
    const parentIdentity = fs.lstatSync(parent);
    let gateFd;
    try { gateFd = fs.openSync(gate, 'wx', 0o600); } catch (error) { if (error.code === 'EEXIST') requireValue(false, 'Session command lock exists; another process or crash requires explicit manual reconciliation'); throw error; }
    const gateIdentity = fs.fstatSync(gateFd);
    function assertGateIdentity() {
        const currentParent = fs.lstatSync(parent), currentGate = fs.lstatSync(gate);
        requireValue(currentParent.isDirectory() && !currentParent.isSymbolicLink() && fs.realpathSync(parent) === parent &&
            currentParent.dev === parentIdentity.dev && currentParent.ino === parentIdentity.ino && currentGate.isFile() && !currentGate.isSymbolicLink() &&
            currentGate.dev === gateIdentity.dev && currentGate.ino === gateIdentity.ino, 'Command gate or parent replaced; preserve original gate for manual recovery');
    }
    try {
        fs.writeFileSync(gateFd, JSON.stringify({ pid: process.pid, journalPath: target, token: crypto.randomUUID() }) + '\n'); fs.fsyncSync(gateFd); directorySync(path.dirname(gate));
        const state = loadSession(target, plan, revision);
        const snapshots = state.locks.map(lock => actorSnapshot(lock, completedCleanup && state.complete));
        function journalIdentity() { return [target, `${target}.head.json`].map(file => {
            const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
            try { const stat = fs.fstatSync(fd); requireValue(stat.isFile() && stat.size <= 16 * 1024 * 1024, 'Journal/head type or size changed');
                return [stat.dev, stat.ino, crypto.createHash('sha256').update(fs.readFileSync(fd)).digest('hex')];
            } finally { fs.closeSync(fd); }
        }); }
        let durable = state, durableIdentity = journalIdentity();
        function assertSession() {
            assertInputs(); assertGateIdentity(); assertActorSnapshots(state.locks, snapshots); ordinaryPath(target);
            same(journalIdentity(), durableIdentity, 'durable journal/head identity changed');
            same(loadSession(target, plan, revision), durable, 'durable session changed during command');
        }
        assertSession();
        return await fn(state, next => { assertSession(); durable = append(target, next, state); durableIdentity = journalIdentity(); return durable; }, assertSession);
    } finally { fs.closeSync(gateFd); assertGateIdentity(); fs.unlinkSync(gate); directorySync(parent); }
}
function progress(state) { const done = state.operations.filter(x => x.status === 'finalized'); return { creationHashes: done.slice(0, 5).map(x => x.txHash), governanceHashes: done.slice(5).map(x => x.txHash) }; }
async function phase(plan, revision, state, rpc) { const p = progress(state); return policy.preflight(plan, rpc, revision, p.creationHashes, plan.journal, p.governanceHashes); }
async function startSession({ plan, revision, directory, filename, mode, rpc, assertInputs = () => {} }) {
    await policy.checkPlan(plan, undefined, revision);
    requireValue(['external-broadcast', 'raw-relay'].includes(mode), 'Explicit external-broadcast or raw-relay mode required');
    const target = ordinaryPath(filename); requireValue(!fs.existsSync(target) && !fs.existsSync(`${target}.head.json`), 'Never overwrite an existing session or head');
    const locks = acquireActors(plan, directory, target), snapshots = locks.map(lock => actorSnapshot(lock));
    try {
        await policy.preflight(plan, rpc, revision);
        assertInputs(); assertActorSnapshots(locks, snapshots); ordinaryPath(target);
        return append(target, { schema: SCHEMA, provenance: 'new-receipt-bound-graph', deploymentId: crypto.randomUUID(), journalPath: target,
            planSha256: plan.payloadSha256, revision, mode, locks, operations: [], complete: false });
    } catch (error) {
        if (!fs.existsSync(target)) { assertActorSnapshots(locks, snapshots); for (const lock of locks.slice().reverse()) releaseActor(lock); }
        throw error;
    }
}
async function prepare({ plan, revision, filename, rpc, governorEnvelope, output, assertInputs = () => {} }) {
    if (output) assertOutsideCheckout(output);
    return guarded(plan, revision, filename, async (state, save) => {
        requireValue(!state.complete && state.operations.every(x => x.status === 'finalized'), 'Resolve the outstanding operation before another handoff');
        const report = await phase(plan, revision, state, rpc), index = state.operations.length;
        requireValue(report.nextOperation?.index === index && index < 7, 'Unexpected next operation');
        let envelope;
        if (index < 5) { requireValue(governorEnvelope === undefined, 'Governor envelope is not a CREATE override'); envelope = plan.transactions[index].envelope; }
        else {
            requireValue(governorEnvelope && Object.keys(governorEnvelope).sort().join(',') === 'accessList,gasLimit,maxFeePerGas,maxPriorityFeePerGas,nonce', 'Review an explicit governor nonce and fee envelope');
            const call = plan.governanceCalls[index - 5];
            envelope = { type: 2, chainId: 1, from: call.from, nonce: governorEnvelope.nonce, to: call.to, value: '0', data: call.data,
                gasLimit: governorEnvelope.gasLimit, maxFeePerGas: governorEnvelope.maxFeePerGas, maxPriorityFeePerGas: governorEnvelope.maxPriorityFeePerGas, accessList: governorEnvelope.accessList };
        }
        same(envelope.nonce, report.nextOperation.nonce, 'fresh actual-sender nonce');
        const startBlock = report.observedAtBlock.number;
        const shared = index < 5 ? { ...policy.creationIntents(plan)[index], startBlock } : { schema: 'governor-call-intent-v1', chainId: 1, creator: E.getAddress(envelope.from), nonce: envelope.nonce,
            to: envelope.to, value: '0', dataHash: E.keccak256(envelope.data), startBlock, gasLimit: envelope.gasLimit };
        const intent = { planSha256: plan.payloadSha256, senderPolicySha256: policy.digest(plan.config.sender), envelopeSha256: policy.digest(envelope), startBlock, envelope, shared };
        const operation = { index, status: 'handed-off', intent, intentSha256: policy.digest(intent) }; validateIntent(plan, operation);
        const observed = await rpc('eth_getBlockByNumber', [E.toQuantity(startBlock), false]);
        requireValue(observed.hash === report.observedAtBlock.hash && BigInt(envelope.gasLimit) <= BigInt(observed.gasLimit), 'Governor/creator gas exceeds current canonical block');
        const balance = BigInt(await rpc('eth_getBalance', [envelope.from, 'latest']));
        requireValue(balance >= BigInt(envelope.gasLimit) * BigInt(envelope.maxFeePerGas), 'Actual sender cannot cover the reviewed maximum gas cost; operator handles balances');
        const updated = save({ ...state, operations: [...state.operations, operation] }); // durable BEFORE packet export
        const packet = signingPacket(updated, operation);
        if (output) writeNew(output, packet);
        return { state: updated, packet };
    }, false, assertInputs);
}
function signingPacket(state, operation) {
    const envelope = operation.intent.envelope, { from, ...unsigned } = envelope;
    return { schema: 'agialpha.external-signing-handoff.v1', deploymentId: state.deploymentId, planSha256: state.planSha256,
        index: operation.index, intentSha256: operation.intentSha256, envelope, unsignedSerialized: E.Transaction.from(unsigned).unsignedSerialized,
        warning: 'Signing or external broadcast may occur after this handoff. Only an exact direct type-2 transaction is supported; never wrap, batch or use type4.' };
}
async function retrieveHandoff({ plan, revision, filename }) {
    await policy.checkPlan(plan, undefined, revision);
    const state = loadSession(filename, plan, revision), operation = state.operations.at(-1);
    requireValue(operation?.status === 'handed-off', 'Only an unresolved original handoff can be retrieved');
    return { state, packet: signingPacket(state, operation), journalMutated: false, externalTransactions: false };
}
async function importSigned({ plan, revision, filename, raw, rpc, assertInputs = () => {} }) {
    return guarded(plan, revision, filename, async (state, save) => {
        const operation = state.operations.at(-1); requireValue(operation?.status === 'handed-off', 'Only the outstanding handoff can accept a signature');
        const checked = validateSigned(raw, operation.intent);
        requireValue(typeof rpc === 'function', 'Fresh read-only phase check required after external signing');
        const report = await phase(plan, revision, state, rpc);
        requireValue(report.nextOperation?.index === operation.index && report.nextOperation.nonce === operation.intent.envelope.nonce, 'Actual sender nonce changed during external signing');
        const latest = await rpc('eth_getBlockByNumber', ['latest', false]);
        requireValue(latest.hash === report.observedAtBlock.hash && BigInt(operation.intent.envelope.gasLimit) <= BigInt(latest.gasLimit), 'Block/gas changed during external signing');
        requireValue(BigInt(await rpc('eth_getBalance', [operation.intent.envelope.from, latest.number])) >= BigInt(operation.intent.envelope.gasLimit) * BigInt(operation.intent.envelope.maxFeePerGas), 'Sender balance changed during external signing');
        const updated = { ...operation, status: 'signed', txHash: checked.hash, rawSha256: checked.rawSha256 };
        return save({ ...state, operations: [...state.operations.slice(0, -1), updated] });
    }, false, assertInputs);
}
function relayAcknowledgement(state) {
    const op = state.operations.at(-1); return policy.digest({ action: 'relay-exact-raw-once', deploymentId: state.deploymentId, planSha256: state.planSha256, index: op?.index, intentSha256: op?.intentSha256, transactionHash: op?.txHash });
}
async function relayOnce({ plan, revision, filename, raw, rpc, relay, acknowledgement, assertInputs = () => {} }) {
    return guarded(plan, revision, filename, async (state, save, assertSession) => {
        const operation = state.operations.at(-1);
        requireValue(state.mode === 'raw-relay' && operation?.status === 'signed', 'No relay for external mode or previously attempted/uncertain submission');
        same(acknowledgement, relayAcknowledgement(state), 'explicit one-shot relay acknowledgement');
        const checked = validateSigned(raw, operation.intent); same(checked.hash, operation.txHash, 'signed hash'); same(checked.rawSha256, operation.rawSha256, 'raw bytes hash');
        const report = await phase(plan, revision, state, rpc);
        for (const tag of ['latest', 'pending']) requireValue(BigInt(await rpc('eth_getTransactionCount', [operation.intent.envelope.from, tag])) === BigInt(operation.intent.envelope.nonce), 'Sender nonce drift before relay');
        const latest = await rpc('eth_getBlockByNumber', ['latest', false]);
        requireValue(latest.hash === report.observedAtBlock.hash && BigInt(operation.intent.envelope.gasLimit) <= BigInt(latest.gasLimit), 'Latest block/gas changed before relay');
        const balance = BigInt(await rpc('eth_getBalance', [operation.intent.envelope.from, latest.number]));
        requireValue(balance >= BigInt(operation.intent.envelope.gasLimit) * BigInt(operation.intent.envelope.maxFeePerGas), 'Insufficient reviewed relay gas balance');
        save({ ...state, operations: [...state.operations.slice(0, -1), { ...operation, status: 'submission-attempted' }] });
        // This callback receives only the validated bytes. Any error is ambiguous and cannot be retried.
        assertSession();
        const returned = await relay(raw);
        requireValue(typeof returned === 'string' && returned.toLowerCase() === operation.txHash, 'Relay returned an unexpected hash; submission is ambiguous');
        return { transactionHash: operation.txHash, submissionAttempted: true, receiptProven: false };
    }, false, assertInputs);
}
function rpcSignedBytes(tx) {
    requireValue(tx && BigInt(tx.type) === 2n && !tx.authorizationList && !tx.blobVersionedHashes, 'Unsupported recovered transaction type');
    return E.Transaction.from({ type: 2, chainId: BigInt(tx.chainId), nonce: Number(BigInt(tx.nonce)), to: tx.to, value: BigInt(tx.value), data: tx.input,
        gasLimit: BigInt(tx.gas), maxFeePerGas: BigInt(tx.maxFeePerGas), maxPriorityFeePerGas: BigInt(tx.maxPriorityFeePerGas), accessList: tx.accessList,
        signature: { r: tx.r, s: tx.s, yParity: Number(BigInt(tx.yParity ?? tx.v)) } }).serialized;
}
async function recoverOperation(plan, state, rpc, suppliedHash) {
    const op = state.operations.at(-1); requireValue(op && op.status !== 'finalized' && op.status !== 'failed', 'An unresolved operation is required');
    requireValue(BigInt(await rpc('eth_chainId', [])) === 1n, 'Wrong recovery chain');
    let transactionHash = op.txHash || suppliedHash;
    if (op.txHash && suppliedHash) same(suppliedHash, op.txHash, 'recovery hash');
    if (!transactionHash) {
        const head = await rpc('eth_getBlockByNumber', ['latest', false]);
        const end = Number(BigInt(head.number)); requireValue(end >= op.intent.startBlock && end - op.intent.startBlock < 512, 'Hashless recovery exceeds 512-block budget; supply separately reconciled exact transaction hash');
        for (let n = op.intent.startBlock; n <= end; ++n) {
            const b = await rpc('eth_getBlockByNumber', [E.toQuantity(n), true]);
            requireValue(b?.hash && Number(BigInt(b.number)) === n && Array.isArray(b.transactions), 'Incomplete canonical recovery block');
            for (const tx of b.transactions) {
                requireValue(tx && typeof tx === 'object', 'Full transactions required during recovery');
                if (tx.from?.toLowerCase() !== op.intent.envelope.from.toLowerCase() || BigInt(tx.nonce) !== BigInt(op.intent.envelope.nonce)) continue;
                const checked = validateSigned(rpcSignedBytes(tx), op.intent); same(checked.hash, tx.hash, 'recovered transaction hash');
                requireValue(!transactionHash || transactionHash === tx.hash, 'Conflicting sender nonce history'); transactionHash = tx.hash;
            }
            const again = await rpc('eth_getBlockByNumber', [E.toQuantity(n), false]); requireValue(again?.hash === b.hash, 'Recovery block reorg');
        }
        const again = await rpc('eth_getBlockByNumber', [head.number, false]); requireValue(again?.hash === head.hash, 'Recovery head reorg');
    }
    if (!transactionHash) return { resolved: false, reason: 'No canonical transaction observed; this does not prove no broadcast. Do not retry or reuse the nonce.' };
    requireValue(/^0x[0-9a-fA-F]{64}$/.test(transactionHash), 'Exact transaction hash required');
    const tx = await rpc('eth_getTransactionByHash', [transactionHash]), receipt = await rpc('eth_getTransactionReceipt', [transactionHash]);
    if (!tx) return { resolved: false, transactionHash, reason: 'Transaction not observed; keep the intent and actor locks unresolved.' };
    const checked = validateSigned(rpcSignedBytes(tx), op.intent); same(checked.hash, transactionHash, 'recovered hash');
    if (!receipt) return { resolved: false, transactionHash, reason: 'Exact transaction is pending or receipt unavailable; never resend automatically.' };
    same(receipt.transactionHash, transactionHash, 'receipt hash'); same(receipt.blockHash, tx.blockHash, 'receipt/transaction block'); same(receipt.blockNumber, tx.blockNumber, 'receipt block number');
    same(receipt.transactionIndex, tx.transactionIndex, 'receipt transaction index');
    const b = await rpc('eth_getBlockByNumber', [receipt.blockNumber, false]); requireValue(b?.hash === receipt.blockHash, 'Receipt is not canonical');
    const final = await rpc('eth_getBlockByNumber', ['finalized', false]);
    if (BigInt(receipt.blockNumber) > BigInt(final.number)) return { resolved: false, transactionHash, reason: 'Canonical receipt is not finalized; keep locks and do not advance.' };
    requireValue(receipt.status === '0x1', 'Canonical transaction failed; campaign is blocked and cannot skip/reuse this nonce');
    const pin = { number: Number(BigInt(final.number)), hash: final.hash };
    const proof = op.index < 5 ? await policy.receiptEvidence(plan, op.index, transactionHash, rpc, pin) : await policy.verifyGovernanceReceipt(plan, op.index - 5, transactionHash, rpc, pin);
    const next = { ...state, operations: [...state.operations.slice(0, -1), { ...op, status: 'finalized', txHash: transactionHash, receipt: proof }] };
    return { resolved: true, transactionHash, state: next, acceptanceBlock: pin };
}
async function recover({ plan, revision, filename, rpc, transactionHash }) {
    await policy.checkPlan(plan, undefined, revision);
    const state = loadSession(filename, plan, revision);
    const result = await recoverOperation(plan, state, rpc, transactionHash);
    return { ...result, externalTransactions: false, journalMutated: false };
}
async function reconcile({ plan, revision, filename, rpc, transactionHash, assertInputs = () => {} }) {
    return guarded(plan, revision, filename, async (state, save) => {
        const result = await recoverOperation(plan, state, rpc, transactionHash);
        requireValue(result.resolved, result.reason);
        await phase(plan, revision, result.state, rpc);
        return save(result.state);
    }, false, assertInputs);
}
async function finish({ plan, revision, filename, rpc, assertInputs = () => {} }) {
    return guarded(plan, revision, filename, async (state, save, assertSession) => {
        requireValue(state.operations.length === 7 && state.operations.every(x => x.status === 'finalized'), 'All seven exact finalized operations required');
        const p = progress(state), b = state.complete ? null : await rpc('eth_getBlockByNumber', ['finalized', false]);
        const acceptanceBlock = state.complete ? state.authorityEvidence.block : { number: Number(BigInt(b.number)), hash: b.hash };
        const evidence = await policy.verifyAuthority(plan, rpc, { ...p, acceptanceBlock }, revision);
        if (state.complete) same(evidence, state.authorityEvidence, 'reverified durable completion evidence');
        const completed = state.complete ? state : save({ ...state, complete: true, authorityEvidence: evidence, authorityEvidenceSha256: evidence.payloadSha256 });
        // Full evidence is durable before any release or CLI output. Retrying only finish may
        // clean up absent/owned locks; replacement locks and crash command gates remain blocked.
        assertSession();
        for (const lock of completed.locks.slice().reverse()) if (assertCompletedActor(lock)) releaseActor(lock);
        return { state: completed, evidence };
    }, true, assertInputs);
}
// This dedicated one-shot transport is never imported by the read-only transport.
function createRawRelay(url) {
    const parsed = new URL(url); requireValue(parsed.protocol === 'https:' && !parsed.username && !parsed.password && !parsed.hash, 'Explicit HTTPS relay URL without embedded credentials required');
    let used = false;
    return async raw => {
        requireValue(!used, 'Raw relay is one-shot; ambiguous submissions cannot retry'); used = true;
        requireValue(/^0x[0-9a-fA-F]+$/.test(raw) && raw.length <= 200000, 'Bounded raw transaction required');
        try {
            const response = await fetch(url, { method: 'POST', redirect: 'error', signal: AbortSignal.timeout(20000), headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_sendRawTransaction', params: [raw] }) });
            requireValue(response.ok, 'Relay HTTP failure');
            const reader = response.body?.getReader(); requireValue(reader, 'Relay response missing'); let size = 0; const chunks = [];
            try { while (true) { const { done, value } = await reader.read(); if (done) break; size += value.byteLength; requireValue(size <= 65536, 'Relay response too large'); chunks.push(value); } }
            finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
            const result = JSON.parse(Buffer.concat(chunks, size)); requireValue(result?.jsonrpc === '2.0' && result.id === 1 && !Object.hasOwn(result, 'error') && /^0x[0-9a-fA-F]{64}$/.test(result.result), 'Invalid relay result');
            return result.result;
        } catch { requireValue(false, 'Raw relay result ambiguous; reconcile the durable intent, never retry automatically. URL/provider details redacted.'); }
    };
}
function readRaw(filename) {
    const target = ordinaryPath(filename), fd = fs.openSync(target, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    try { requireValue(fs.fstatSync(fd).size <= 200002, 'Signed raw file exceeds bound'); return fs.readFileSync(fd, 'utf8').trim(); } finally { fs.closeSync(fd); }
}
async function main() {
    // One command input file keeps argument parsing narrow; exact schemas are selected per action.
    const [action, inputFile, output, extra] = process.argv.slice(2);
    const fields = { start: ['plan', 'journal', 'mode'], prepare: ['plan', 'journal', 'governorEnvelope'], import: ['plan', 'journal', 'signedRawFile'],
        relay: ['plan', 'journal', 'signedRawFile', 'acknowledgement'], recover: ['plan', 'journal', 'transactionHash'], reconcile: ['plan', 'journal', 'transactionHash'], finish: ['plan', 'journal'], status: ['plan', 'journal'], handoff: ['plan', 'journal'] };
    requireValue(fields[action] && inputFile && output && !extra, 'Usage: authority-session.js start|prepare|handoff|import|relay|recover|reconcile|finish|status COMMAND.json NEW_OUTPUT.json');
    const revision = require('./authority-revision').reviewedRevision();
    const boundary = require('./authority-input-boundary').createInputBoundary(revision), input = boundary.readJson(inputFile);
    same(Object.keys(input).sort(), fields[action].sort(), 'command fields');
    assertOutsideCheckout(output); assertOutsideCheckout(input.journal);
    boundary.pinDirectory(path.dirname(path.resolve(output))); boundary.pinDirectory(path.dirname(path.resolve(input.journal)));
    if (action === 'start') boundary.pinDirectory(process.env.DEPLOYMENT_LOCK_DIRECTORY);
    const plan = boundary.readJson(input.plan); await policy.checkPlan(plan, undefined, revision);
    requireValue(!fs.existsSync(output), 'Never overwrite command evidence');
    const needsRpc = !['status', 'handoff'].includes(action);
    const rpc = needsRpc ? createReadOnlyRpc(process.env.ALPHA_READ_ONLY_RPC_URL, scopeForPlan(plan)) : null;
    const args = { plan, revision, filename: input.journal, rpc, assertInputs: boundary.assertCurrent };
    let result;
    if (action === 'start') result = await startSession({ ...args, directory: process.env.DEPLOYMENT_LOCK_DIRECTORY, mode: input.mode });
    if (action === 'prepare') result = await prepare({ ...args, governorEnvelope: input.governorEnvelope ? boundary.readJson(input.governorEnvelope) : undefined });
    if (action === 'handoff') result = await retrieveHandoff(args);
    if (action === 'import') result = await importSigned({ ...args, raw: boundary.readRaw(input.signedRawFile) });
    if (action === 'relay') {
        requireValue(process.env.ALPHA_ENABLE_USER_RUN_RAW_RELAY === 'I_REVIEWED_THIS_EXACT_TRANSACTION', 'Explicit user-run raw relay switch required');
        result = await relayOnce({ ...args, raw: boundary.readRaw(input.signedRawFile), acknowledgement: input.acknowledgement, relay: createRawRelay(process.env.ALPHA_RAW_RELAY_RPC_URL) });
    }
    if (action === 'recover') result = await recover({ ...args, transactionHash: input.transactionHash || undefined });
    if (action === 'reconcile') result = await reconcile({ ...args, transactionHash: input.transactionHash || undefined });
    if (action === 'finish') result = await finish(args);
    if (action === 'status') {
        const state = loadSession(input.journal, plan, revision); let commandBlocked = false;
        try { fs.lstatSync(`${path.resolve(input.journal)}.command-lock`); commandBlocked = true; } catch (error) { if (error.code !== 'ENOENT') throw error; }
        result = { state, commandBlocked, relayAcknowledgement: !commandBlocked && state.operations.at(-1)?.status === 'signed' ? relayAcknowledgement(state) : null };
    }
    boundary.assertCurrent();
    writeNew(output, result);
    console.log(JSON.stringify({ output: path.resolve(output), action, activationAllowed: false, liveSigningPerformedByTool: false }));
}
module.exports = { SCHEMA, ownerKeys, acquireActors, releaseActor, loadSession, validateIntent, validateSigned, startSession, prepare,
    retrieveHandoff, importSigned, relayAcknowledgement, relayOnce, recover, reconcile, finish, readRaw };
if (require.main === module) main().catch(error => { console.error(error.publicMessage ? error.message : 'Session stopped. Preserve its journal and locks; source, input, runtime or submission needs reconciliation.'); process.exitCode = 1; });
