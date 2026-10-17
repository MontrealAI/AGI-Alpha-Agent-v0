// SPDX-License-Identifier: Apache-2.0
// User-run Ubuntu Hardhat entry point. Real keys must never be supplied to an assistant.
const fs = require('fs');
const path = require('path');
const E = require('ethers');
const policy = require('./mainnet-authority');
const session = require('./authority-session');
const terminal = require('./creator-terminal');
const { createReadOnlyRpc, scopeForPlan } = require('./authority-rpc');
const { assertOutsideCheckout } = require('./authority-paths');
const { writeNew } = require('./authority-cli');
const need = (ok, message) => { if (!ok) throw Error(message); };
function creatorReview(plan) {
    const maximumFee = plan.transactions.reduce((sum, t) => sum + BigInt(t.envelope.gasLimit) * BigInt(t.envelope.maxFeePerGas), 0n);
    return { schema: 'agialpha.creator-terminal-review.v1', planSha256: plan.payloadSha256, revision: plan.revision,
        chainId: plan.config.chainId, creator: plan.config.deployer, governor: plan.config.governor,
        senderPolicy: plan.config.sender, ...(plan.config.sender.mode === policy.CONVENTIONAL ? { assurance: 'Conventional transaction correctness only. No wallet qualification, delegate target safety, no-invocation or custody assurance.' } : {}), dependencies: plan.config.dependencies, rootOwners: plan.config.rootOwners,
        parameters: plan.config.parameters, addresses: plan.addresses, transactions: plan.transactions,
        maximumTotalCreationFeeWei: maximumFee.toString(), maximumTotalCreationFeeETH: E.formatEther(maximumFee),
        creatorOperations: 5, governorOperationsSignedHere: 0,
        notice: 'Only these five fresh direct type-2 CREATEs. No governor binding, old deployment, transfer, admission or activation. The key stays in this process during bounded finality waits. JavaScript cannot guarantee secure memory erasure.' };
}
function rpcSupervisor(endpoint, plan) {
    const started = Date.now(); let requests = 0, bytes = 0;
    return async fn => {
        need(Date.now() - started < 3 * 60 * 60 * 1000 && requests < 10000 && bytes < 128 * 1024 * 1024, 'Creator read budget exhausted');
        const rpc = createReadOnlyRpc(endpoint, scopeForPlan(plan), { limits: {
            requests: Math.min(2000, 10000 - requests), totalBytes: Math.min(100 * 1024 * 1024, 128 * 1024 * 1024 - bytes) } });
        try { return await fn(rpc); } finally { const s = rpc.stats(); requests += s.requests; bytes += s.totalBytes; }
    };
}
function creationPrefix(state) {
    need(!state.complete && state.mode === 'raw-relay' && state.operations.length <= 5, 'Creator-only session boundary exceeded');
    const finished = state.operations.filter(op => op.status === 'finalized');
    need(finished.every((op, index) => op.index === index && index < 5), 'Contiguous creator prefix required');
    return finished.map(op => op.txHash);
}
async function runCreator({ plan, revision, filename, directory, withRpc, assertInputs, confirm, obtainSigner, relay, sleep,
    exists = fs.existsSync, coordinator = session, checkPlan = policy.checkPlan, preflight = policy.preflight, onProgress = () => {} }) {
    await checkPlan(plan, undefined, revision); assertInputs();
    const common = { plan, revision, filename, assertInputs };
    let state = exists(filename) ? coordinator.loadSession(filename, plan, revision) : null, recovery = null;
    if (state) {
        creationPrefix(state);
        if (state.operations.at(-1)?.status !== 'finalized' && state.operations.length) {
            recovery = await withRpc(rpc => coordinator.recover({ ...common, rpc })); assertInputs();
            if (!recovery.resolved) return { status: 'needs-reconciliation', reason: recovery.reason, transactionHash: recovery.transactionHash || null, keyRequested: false, activationAllowed: false };
        }
    }
    const observed = recovery?.state || state;
    const hashes = observed ? creationPrefix(observed) : [];
    await withRpc(rpc => preflight(plan, rpc, revision, hashes, plan.journal, [])); assertInputs();
    if (hashes.length < 5 || recovery) { await confirm(creatorReview(plan)); assertInputs(); }
    if (!state) state = await withRpc(rpc => coordinator.startSession({ ...common, directory, mode: 'raw-relay', rpc }));
    else if (recovery) state = await withRpc(rpc => coordinator.reconcile({ ...common, rpc }));
    assertInputs();
    let signer;
    try {
        if (creationPrefix(state).length < 5) { signer = await obtainSigner(plan.config.deployer); need(E.getAddress(signer.address) === plan.config.deployer, 'Creator key/address mismatch'); assertInputs(); }
        while (creationPrefix(state).length < 5) {
            const index = state.operations.length;
            need(index < 5, 'Never sign governor calls with the creator');
            const prepared = await withRpc(rpc => coordinator.prepare({ ...common, rpc })); assertInputs();
            need(prepared.packet.index === index && prepared.packet.envelope.to === null && prepared.packet.envelope.from === plan.config.deployer, 'Unexpected creator envelope');
            policy.validateEnvelope(plan.transactions[index].envelope, prepared.packet.envelope);
            let raw = await signer.signExact(prepared.packet.envelope);
            try {
                assertInputs();
                const signed = await withRpc(rpc => coordinator.importSigned({ ...common, raw, rpc })); assertInputs();
                await withRpc(rpc => relay({ ...common, raw, rpc, acknowledgement: coordinator.relayAcknowledgement(signed) }));
            } finally { raw = null; }
            onProgress({ index, status: 'submission-attempted', transactionHash: coordinator.loadSession(filename, plan, revision).operations.at(-1).txHash });
            let resolved = false;
            for (let attempt = 0; attempt < 120; attempt++) {
                const result = await withRpc(rpc => coordinator.recover({ ...common, rpc })); assertInputs();
                if (result.resolved) { state = await withRpc(rpc => coordinator.reconcile({ ...common, rpc })); resolved = true; break; }
                if (attempt < 119) await sleep(15000);
            }
            need(resolved, 'Finality wait exhausted; preserve journal and reconcile without resending');
            assertInputs(); onProgress({ index, status: 'finalized', transactionHash: state.operations[index].txHash });
        }
        const creationHashes = creationPrefix(state);
        const report = await withRpc(rpc => preflight(plan, rpc, revision, creationHashes, plan.journal, [])); assertInputs();
        return { schema: 'agialpha.creation-complete-checkpoint.v1', status: 'awaiting-governor-bindings', planSha256: plan.payloadSha256,
            revision, creator: plan.config.deployer, governor: plan.config.governor.address, addresses: plan.addresses,
            creationHashes, governanceHashes: [], creationEvidence: state.operations.map(op => op.receipt), preflight: report,
            finalAuthorityVerified: false, actorLocksRetained: true, activationAllowed: false,
            next: 'Independently verify this public checkpoint on Mac, then authorize the two exact Ledger governor bindings. Preserve the original path-bound journal and locks; do not copy it as a portable signing authority.' };
    } finally { signer?.close(); }
}
async function main() {
    terminal.assertTerminalEnvironment();
    const hre = require('hardhat');
    need(hre.network.name === 'mainnet' && hre.network.config.chainId === 1 && hre.network.config.accounts.length === 0, 'Explicit creator Hardhat configuration required');
    need(process.argv.length === 2 && process.env.ALPHA_CREATOR_COMMAND, 'Use the public ALPHA_CREATOR_COMMAND file path; no key arguments');
    const revision = require('./authority-revision').reviewedRevision();
    const boundary = require('./authority-input-boundary').createInputBoundary(revision), input = boundary.readJson(process.env.ALPHA_CREATOR_COMMAND);
    need(Object.keys(input).sort().join(',') === 'journal,output,plan', 'Exact public creator command fields required');
    const plan = boundary.readJson(input.plan);
    const transportTrust = terminal.observeCaPolicy();
    if (transportTrust) { boundary.readJson(transportTrust.policyFile); boundary.pinDirectory(path.dirname(transportTrust.certificate)); }
    const assertInputs = () => { boundary.assertCurrent(); terminal.assertTerminalEnvironment(); need(policy.digest(terminal.observeCaPolicy()) === policy.digest(transportTrust), 'Transport trust changed'); };
    for (const file of [input.journal, input.output]) { assertOutsideCheckout(file); boundary.pinDirectory(path.dirname(path.resolve(file))); }
    boundary.pinDirectory(process.env.DEPLOYMENT_LOCK_DIRECTORY);
    need(!fs.existsSync(input.output), 'Choose a fresh checkpoint output');
    need(process.env.ALPHA_RAW_RELAY_RPC_URL, 'Explicit bounded relay endpoint required');
    const relayUrl = new URL(process.env.ALPHA_RAW_RELAY_RPC_URL);
    need(relayUrl.protocol === 'https:' && !relayUrl.username && !relayUrl.password && !relayUrl.hash, 'Explicit HTTPS relay endpoint required');
    const result = await runCreator({ plan, revision, filename: input.journal, directory: process.env.DEPLOYMENT_LOCK_DIRECTORY,
        withRpc: rpcSupervisor(process.env.ALPHA_READ_ONLY_RPC_URL, plan), assertInputs,
        confirm: review => terminal.confirmPublicPlan({ ...review, transportTrust }), obtainSigner: terminal.promptCreator,
        relay: args => session.relayUserSignedOnce({ ...args, endpoint: process.env.ALPHA_RAW_RELAY_RPC_URL }),
        sleep: ms => new Promise(resolve => setTimeout(resolve, ms)), onProgress: value => process.stdout.write(JSON.stringify(value) + '\n') });
    assertInputs(); writeNew(input.output, result);
    process.stdout.write(JSON.stringify({ status: result.status, output: path.resolve(input.output), activationAllowed: false }) + '\n');
}
module.exports = { creatorReview, rpcSupervisor, creationPrefix, runCreator };
if (require.main === module) main().catch(() => { console.error('Creator stopped. No key, signed bytes or provider details are logged. Preserve journal and locks; reconcile any outstanding transaction before another attempt.'); process.exitCode = 1; });
