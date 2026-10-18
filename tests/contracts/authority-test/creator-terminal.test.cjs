// Disposable synthetic keys only; no provider or real terminal is used here.
const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const E = require('ethers');
const terminal = require('../scripts/creator-terminal');
const core = require('../scripts/deploy-mainnet-creator');
const session = require('../scripts/authority-session');
const secret = '0x' + '11'.repeat(32), wallet = new E.Wallet(secret), governor = new E.Wallet('0x' + '22'.repeat(32)).address;
function channel() {
    const input = new EventEmitter(); let paused = true;
    Object.assign(input, { fd: 73, isTTY: true, isRaw: false, readableEncoding: null, readableFlowing: null, isPaused: () => paused, setRawMode(value) { this.isRaw = value; }, pause() { paused = true; this.readableFlowing = false; }, resume() { paused = false; this.readableFlowing = true; } });
    const text = [], output = Object.assign(new EventEmitter(), { fd: 74, isTTY: true, write(value, callback) { text.push(value); callback?.(); } }), signals = new EventEmitter();
    return { input, output, signals, text };
}
test('hidden input never echoes synthetic key and restores terminal state', async () => {
    const c = channel(), pending = terminal.readTerminalLine({ ...c, prompt: 'Hidden: ', hidden: true, maximum: 66 });
    c.input.emit('data', Buffer.from(secret)); c.input.emit('data', Buffer.from('\r'));
    const bytes = await pending; assert.equal(bytes.toString(), secret); bytes.fill(0);
    assert.equal(c.text.join(''), 'Hidden: \n'); assert.equal(c.input.isRaw, false); assert.equal(c.input.isPaused(), true);
    assert.equal(c.input.listenerCount('data'), 0); assert.equal(c.signals.listenerCount('SIGTERM'), 0);
});
for (const [name, data] of [['Ctrl-C', '\x03'], ['Ctrl-Z', '\x1a'], ['escape', '\x1b[A'], ['overflow', 'x'.repeat(67)], ['pasted second line', secret + '\nextra']]) {
    test(`rejects ${name} without leaking input`, async () => {
        const c = channel(), pending = terminal.readTerminalLine({ ...c, prompt: 'Hidden: ', hidden: true, maximum: 66 });
        c.input.emit('data', Buffer.from(data)); await assert.rejects(pending, /input rejected/);
        assert.equal(c.input.isRaw, false); assert.equal(c.text.join(''), 'Hidden: \n');
    });
}
for (const signal of ['SIGINT', 'SIGTERM', 'SIGHUP', 'SIGQUIT']) test(`restores terminal on ${signal}`, async () => {
    const c = channel(), pending = terminal.readTerminalLine({ ...c, prompt: 'Hidden: ', hidden: true, maximum: 66 });
    c.signals.emit(signal); await assert.rejects(pending, /interrupted/); assert.equal(c.input.isRaw, false);
});
test('rejects redirected or already-raw terminal', async () => {
    for (const mutate of [c => c.input.isTTY = false, c => c.output.isTTY = false, c => c.input.isRaw = true]) {
        const c = channel(); mutate(c); await assert.rejects(terminal.readTerminalLine({ ...c, prompt: '', hidden: true, maximum: 66 })); assert.equal(c.text.length, 0);
    }
});
test('public raw confirmation releases its reader before the shared hidden-key helper', async t => {
    const tty = require('node:tty'), prior = [tty.ReadStream, tty.WriteStream];
    tty.ReadStream = EventEmitter; tty.WriteStream = EventEmitter;
    t.after(() => { [tty.ReadStream, tty.WriteStream] = prior; }); t.mock.method(tty, 'isatty', fd => [73, 74].includes(fd));
    const c = channel(), answer = terminal.readTerminalLine({ ...c, prompt: 'Confirm: ', hidden: false, maximum: 80 });
    c.input.emit('data', Buffer.from('DEPLOY public-hash\r')); (await answer).fill(0);
    assert.equal(c.input.readableFlowing, false); assert.equal(c.input.listenerCount('data'), 0);
    const pending = require('../scripts/ephemeral-key.cjs').promptPrivateKey(c);
    c.input.emit('data', Buffer.from(secret + '\r')); assert.equal(await pending, secret);
    assert.equal(c.text.join('').includes(secret), false); assert.equal(c.input.isRaw, false);
});
test('rejects secret environment, loaders and debuggers; permits exact Hardhat preload', () => {
    for (const env of [{ PRIVATE_KEY: secret }, { DEPLOYER_PRIVATE_KEY: secret }, { MNEMONIC: 'synthetic' }, { NODE_OPTIONS: '--inspect' }, { NODE_PATH: '/fake' }, { NODE_EXTRA_CA_CERTS: '/fake' }, { DEBUG: '*' }]) assert.throws(() => terminal.assertTerminalEnvironment(env, []));
    for (const args of [['--inspect'], ['--eval', 'bad'], ['--import=bad'], ['--require', __filename], ['-e', 'bad']]) assert.throws(() => terminal.assertTerminalEnvironment({}, args));
    terminal.assertTerminalEnvironment({}, ['--require', require.resolve('hardhat/register'), '--max-old-space-size=256']);
});
function envelope(nonce = 0) { return { type: 2, chainId: 1, from: wallet.address, nonce, to: null, value: '0', data: '0x60006000f3', gasLimit: '100000', maxFeePerGas: '1000000000', maxPriorityFeePerGas: '1', accessList: [] }; }
test('ephemeral capability signs exact CREATE, checks sender, clears supplied buffer and closes', async () => {
    const bytes = Buffer.from(secret), signer = terminal.signerFromBytes(bytes, wallet.address); assert(bytes.every(x => x === 0));
    const raw = await signer.signExact(envelope()); assert.equal(E.Transaction.from(raw).from, wallet.address);
    session.validateSigned(raw, { envelope: envelope() });
    for (const change of [{ to: governor }, { type: 4 }, { chainId: 2 }, { value: '1' }, { from: governor }, { accessList: [{ address: governor, storageKeys: [] }] }]) await assert.rejects(signer.signExact({ ...envelope(), ...change }));
    signer.close(); await assert.rejects(signer.signExact(envelope())); assert.deepEqual(Object.keys(signer).sort(), ['address', 'close', 'signExact']);
});
test('bad scalar, missing prefix and wrong address are sanitized and input buffer cleared', () => {
    for (const value of ['0x' + '00'.repeat(32), '11'.repeat(32), '0x' + 'ff'.repeat(32), secret]) {
        const bytes = Buffer.from(value); assert.throws(() => terminal.signerFromBytes(bytes, governor), error => !error.message.includes(value)); assert(bytes.every(x => x === 0));
    }
});
function fixture(prefix = 0) {
    const plan = { payloadSha256: 'a'.repeat(64), revision: { commit: 'b'.repeat(40) }, config: { chainId: 1, deployer: wallet.address, governor: { address: governor }, sender: { mode: 'eoa' } }, journal: {}, addresses: {}, transactions: Array.from({ length: 5 }, (_, i) => ({ name: `Contract${i}`, envelope: envelope(i) })) };
    let state = prefix ? { complete: false, mode: 'raw-relay', operations: Array.from({ length: prefix }, (_, index) => ({ index, status: 'finalized', txHash: E.id(`done${index}`), receipt: {} })) } : null;
    const effects = [], signedRaw = [], snapshots = [], flags = { failPreflight: false, drift: false, ambiguous: false, pending: false, rejectConfirmation: false, confirmations: 0, keyPrompts: 0, closed: 0 };
    const copy = value => JSON.parse(JSON.stringify(value));
    function save(value) { state = copy(value); snapshots.push(copy(value)); return copy(state); }
    const coordinator = {
        loadSession() { return copy(state); },
        async startSession() { effects.push('start'); return save({ complete: false, mode: 'raw-relay', operations: [] }); },
        async prepare() { const index = state.operations.length, intent = { envelope: plan.transactions[index].envelope }; save({ ...state, operations: [...state.operations, { index, status: 'handed-off', intent }] }); return { packet: { index, envelope: intent.envelope } }; },
        async importSigned({ raw }) { const op = state.operations.at(-1); const checked = session.validateSigned(raw, op.intent); return save({ ...state, operations: [...state.operations.slice(0, -1), { ...op, status: 'signed', txHash: checked.hash, rawSha256: checked.rawSha256 }] }); },
        relayAcknowledgement: session.relayAcknowledgement,
        async recover() { if (flags.pending) return { resolved: false, reason: 'Pending uncertainty' }; const next = copy(state); next.operations.at(-1).status = 'finalized'; next.operations.at(-1).receipt = { canonical: true }; return { resolved: true, state: next }; },
        async reconcile() { effects.push('reconcile'); const recovered = await this.recover(); return save(recovered.state); }
    };
    const args = { plan, revision: plan.revision, filename: '/synthetic/session', directory: '/synthetic/locks', exists: () => state !== null, coordinator,
        checkPlan: async () => {}, withRpc: async fn => fn(async () => {}), assertInputs: () => { if (flags.drift) throw Error('drift'); },
        preflight: async () => { if (flags.failPreflight) throw Error('preflight'); return { verified: true }; },
        confirm: async review => { flags.confirmations++; assert.equal(review.maximumTotalCreationFeeWei, '500000000000000'); assert.equal(effects.length, 0); if (flags.rejectConfirmation) throw Error('cancel'); },
        obtainSigner: async address => { flags.keyPrompts++; const inner = terminal.signerFromBytes(Buffer.from(secret), address); return { address: inner.address, signExact: inner.signExact, close() { flags.closed++; inner.close(); } }; },
        relay: async ({ raw }) => { effects.push('attempt'); state.operations.at(-1).status = 'submission-attempted'; signedRaw.push(raw); if (flags.ambiguous) throw Error('ambiguous'); },
        sleep: async () => {} };
    return { args, flags, effects, signedRaw, snapshots, state: () => copy(state), replace: value => { state = copy(value); } };
}
test('fresh confirmed synthetic campaign signs exactly five creations and stops before governor', async () => {
    const f = fixture(), result = await core.runCreator(f.args); assert.equal(f.flags.confirmations, 1); assert.equal(f.flags.keyPrompts, 1); assert.equal(f.flags.closed, 1);
    assert.equal(f.signedRaw.length, 5); assert.equal(result.status, 'awaiting-governor-bindings'); assert.equal(result.finalAuthorityVerified, false); assert.equal(result.actorLocksRetained, true);
    assert.deepEqual(f.signedRaw.map(x => E.Transaction.from(x).nonce), [0, 1, 2, 3, 4]); assert.equal(f.state().complete, false);
    assert(!JSON.stringify(f.snapshots).includes(secret)); for (const raw of f.signedRaw) assert(!JSON.stringify(f.snapshots).includes(raw));
});
for (const count of [1, 2, 3, 4, 5]) test(`resumes immutable finalized prefix ${count} without replay`, async () => {
    const f = fixture(count), before = f.state(), result = await core.runCreator(f.args);
    assert.equal(f.signedRaw.length, 5 - count); assert.deepEqual(f.state().operations.slice(0, count), before.operations); assert.equal(f.flags.keyPrompts, count === 5 ? 0 : 1); assert.equal(result.creationHashes.length, 5);
});
test('preflight refusal and declined confirmation have no key prompt or durable effect', async () => {
    for (const flag of ['failPreflight', 'rejectConfirmation']) { const f = fixture(); f.flags[flag] = true; await assert.rejects(core.runCreator(f.args)); assert.equal(f.flags.keyPrompts, 0); assert.deepEqual(f.effects, []); }
});
test('ambiguous send keeps outstanding state and stops before a second signature', async () => {
    const f = fixture(); f.flags.ambiguous = true; await assert.rejects(core.runCreator(f.args)); assert.equal(f.signedRaw.length, 1); assert.equal(f.state().operations[0].status, 'submission-attempted'); assert.equal(f.flags.closed, 1);
    f.flags.pending = true; const result = await core.runCreator(f.args); assert.equal(result.status, 'needs-reconciliation'); assert.equal(f.flags.keyPrompts, 1); assert.equal(f.signedRaw.length, 1);
});
test('source drift after key prompt prevents first signature and closes key capability', async () => {
    const f = fixture(); const acquire = f.args.obtainSigner; f.args.obtainSigner = async address => { const signer = await acquire(address); f.flags.drift = true; return signer; };
    await assert.rejects(core.runCreator(f.args), /drift/); assert.equal(f.signedRaw.length, 0); assert.equal(f.flags.closed, 1);
});
test('rejects governor-phase or noncontiguous journals before prompting', async () => {
    for (const mutate of [s => s.complete = true, s => s.mode = 'external-broadcast', s => s.operations[0].index = 1, s => s.operations.push({ index: 5, status: 'finalized' })]) {
        const f = fixture(5), state = f.state(); mutate(state); f.replace(state); await assert.rejects(core.runCreator(f.args)); assert.equal(f.flags.keyPrompts, 0);
    }
});
test('legacy relay factory remains private', () => { assert.equal(session.createRawRelay, undefined); assert.equal(typeof session.relayUserSignedOnce, 'function'); });
