// SPDX-License-Identifier: Apache-2.0
// The operator runs this on their own terminal. Never supply a real key to an assistant.
const E = require('ethers');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { promptPrivateKey } = require('./ephemeral-key.cjs');
function fail() { return Error('Creator terminal input rejected or interrupted; no input is echoed.'); }
function observeCaPolicy(env = process.env) {
    const extra = env.NODE_EXTRA_CA_CERTS, declaration = env.ALPHA_CREATOR_CA_POLICY;
    if (extra === undefined && declaration === undefined) return null;
    try {
        const read = (name, maximum) => {
            if (typeof name !== 'string' || !path.isAbsolute(name) || path.normalize(name) !== name || fs.realpathSync(name) !== name) throw fail();
            const fd = fs.openSync(name, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
            try { const stat = fs.fstatSync(fd); if (!stat.isFile() || stat.size > maximum) throw fail(); return fs.readFileSync(fd); }
            finally { fs.closeSync(fd); }
        };
        const policy = JSON.parse(read(declaration, 4096));
        if (Object.keys(policy).sort().join(',') !== 'certificate,schema,sha256' || policy.schema !== 'agialpha.creator-ca-policy.v1' ||
            policy.certificate !== extra || !/^[a-f0-9]{64}$/.test(policy.sha256)) throw fail();
        const bytes = read(extra, 1024 * 1024);
        if (crypto.createHash('sha256').update(bytes).digest('hex') !== policy.sha256 || bytes.includes('PRIVATE KEY')) throw fail();
        // One explicitly reviewed extra CA, not a wildcard bundle or a TLS-disable switch.
        if (!/^-----BEGIN CERTIFICATE-----[\s\S]+-----END CERTIFICATE-----\s*$/.test(bytes.toString('ascii')) ||
            (bytes.toString('ascii').match(/-----BEGIN CERTIFICATE-----/g) || []).length !== 1 || !new crypto.X509Certificate(bytes).ca) throw fail();
        return Object.freeze({ policyFile: declaration, certificate: extra, sha256: policy.sha256 });
    } catch { throw fail(); }
}
function assertTerminalEnvironment(env = process.env, args = process.execArgv) {
    if (Object.keys(env).some(k => /(?:PRIVATE_KEY|MNEMONIC|SEED_PHRASE)/i.test(k)) ||
        ['NODE_OPTIONS', 'NODE_PATH', 'NODE_TLS_REJECT_UNAUTHORIZED', 'DEBUG'].some(k => env[k]) ||
        args.some(a => /^--(?:inspect|debug|eval|print|import)(?:[=-]|$)/.test(a))) throw fail();
    observeCaPolicy(env);
    for (let i = 0; i < args.length; i++) {
        if (/^--max-old-space-size=[0-9]+$/.test(args[i])) continue;
        if (args[i] === '--require' && args[i + 1]) {
            let resolved; try { resolved = require.resolve(args[++i]); } catch { throw fail(); }
            if (resolved === require.resolve('hardhat/register')) continue;
        }
        throw fail();
    }
}
function readTerminalLine({ input, output, signals, prompt, hidden, maximum }) {
    if (!input?.isTTY || !output?.isTTY || typeof input.setRawMode !== 'function' || input.isRaw ||
        input.readableFlowing === true || input.readableEncoding != null || input.listenerCount('data') || input.listenerCount('readable')) return Promise.reject(fail());
    return new Promise((resolve, reject) => {
        const bytes = Buffer.alloc(maximum); let length = 0, ended = false;
        const timer = setTimeout(() => done(fail()), 180000);
        function done(error) {
            if (ended) return; ended = true;
            clearTimeout(timer);
            input.removeListener('data', data); input.removeListener('end', interrupted); input.removeListener('error', interrupted);
            for (const name of ['SIGINT', 'SIGTERM', 'SIGHUP', 'SIGQUIT']) signals.removeListener(name, interrupted);
            try { input.setRawMode(false); input.pause(); output.write('\n'); }
            catch { error = fail(); }
            const result = error ? null : Buffer.from(bytes.subarray(0, length)); bytes.fill(0);
            if (error) reject(fail()); else resolve(result);
        }
        function interrupted() { done(fail()); }
        function data(chunk) {
            // No pasted multi-line commands, control sequences, or trailing bytes after Enter.
            for (let i = 0; i < chunk.length && !ended; i++) {
                const b = chunk[i];
                if (b === 13 || b === 10) { if (i !== chunk.length - 1) return done(fail()); return done(); }
                if (b === 8 || b === 127) { if (length) { bytes[--length] = 0; if (!hidden) output.write('\b \b'); } continue; }
                if (b < 32 || b > 126 || length >= maximum) return done(fail());
                bytes[length++] = b; if (!hidden) output.write(String.fromCharCode(b));
            }
        }
        try {
            output.write(prompt); input.setRawMode(true);
            input.on('data', data); input.once('end', interrupted); input.once('error', interrupted);
            for (const name of ['SIGINT', 'SIGTERM', 'SIGHUP', 'SIGQUIT']) signals.once(name, interrupted);
            input.resume();
        } catch { done(fail()); }
    });
}
function realTerminal() { return { input: process.stdin, output: process.stdout, signals: process }; }
async function confirmPublicPlan(review) {
    assertTerminalEnvironment();
    if (!process.stdin.isTTY || !process.stdout.isTTY) throw fail();
    process.stdout.write(JSON.stringify(review, null, 2) + '\n');
    const expected = `DEPLOY ${review.planSha256}`;
    const answer = await readTerminalLine({ ...realTerminal(), prompt: `Type ${expected} to approve these five creations only: `, hidden: false, maximum: 80 });
    try { if (answer.toString('ascii') !== expected) throw fail(); } finally { answer.fill(0); }
}
function signerFromBytes(bytes, expectedAddress) {
    let wallet;
    try {
        const text = bytes.toString('ascii');
        if (!/^0x[0-9a-fA-F]{64}$/.test(text)) throw fail();
        wallet = new E.Wallet(text);
        if (wallet.address !== E.getAddress(expectedAddress)) throw fail();
    } catch { wallet = null; throw fail(); }
    finally { bytes.fill(0); }
    const address = wallet.address;
    return Object.freeze({ address,
        async signExact(envelope) {
            if (!wallet || envelope.type !== 2 || envelope.chainId !== 1 || envelope.to !== null ||
                envelope.value !== '0' || E.getAddress(envelope.from) !== address ||
                !Array.isArray(envelope.accessList) || envelope.accessList.length || envelope.authorizationList) throw fail();
            try { const { from, ...unsigned } = envelope; return await wallet.signTransaction(unsigned); } catch { throw fail(); }
        },
        close() { wallet = null; } });
}
async function promptCreator(expectedAddress) {
    assertTerminalEnvironment();
    let key;
    try { key = await promptPrivateKey(); return signerFromBytes(Buffer.from(key, 'ascii'), expectedAddress); }
    finally { key = null; } // Dropping references is not a secure-erasure guarantee.
}
module.exports = { observeCaPolicy, assertTerminalEnvironment, readTerminalLine, confirmPublicPlan, promptCreator, signerFromBytes };
