// Synthetic local PTY harness only. Never use a real private key with this fixture.
const terminal = require('../scripts/creator-terminal');
const E = require('ethers');
(async () => {
    await terminal.confirmPublicPlan({ planSha256: 'a'.repeat(64), chainId: 1, creator: '0x19E7E376E7C213B7E7e7e46cc70A5dD086DAff2A', governor: '0xd76AD27a1Bcf8652e7e46BE603FA742FD1c10A99', scope: 'Disposable PTY test; no relay/provider' });
    const signer = await terminal.promptCreator('0x19E7E376E7C213B7E7e7e46cc70A5dD086DAff2A');
    try {
        const raw = await signer.signExact({ type: 2, chainId: 1, from: signer.address, nonce: 0, to: null, value: '0', data: '0x60006000f3', gasLimit: '100000', maxFeePerGas: '1000000000', maxPriorityFeePerGas: '1', accessList: [] });
        process.stdout.write(`TERMINAL_OK ${E.Transaction.from(raw).hash}\n`);
    } finally { signer.close(); }
})().catch(() => { process.stderr.write('TERMINAL_STOPPED\n'); process.exitCode = 1; });
