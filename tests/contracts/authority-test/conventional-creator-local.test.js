// SPDX-License-Identifier: Apache-2.0
// Fixed disposable key and unforked Osaka only. No public RPC, physical wallet or real finality.
const { expect } = require('chai');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { ethers, network } = require('hardhat');
const policy = require('../scripts/mainnet-authority');
const session = require('../scripts/authority-session');
const creator = require('../scripts/deploy-mainnet-creator');
const terminal = require('../scripts/creator-terminal');
const legacy = require('../scripts/mainnet');
const { installToken } = require('../test/utils/token');
const { requireDisposableLocalNetwork } = require('../scripts/disposable');
const { AGIALPHA_ADDRESS } = require('../../../token.config');
describe('Conventional creator wrapper (disposable EVM)', function () {
    this.timeout(120000);
    for (const marker of [false, true]) it(`creates five and resumes with conventional ${marker ? 'marker' : 'empty'} origin`, async () => {
        await requireDisposableLocalNetwork(); expect(network.config.chainId).to.equal(1); expect(network.config.hardfork).to.equal('osaka');
        await network.provider.send('hardhat_reset');
        const evidence = process.env.ALPHA_CONVENTIONAL_TEST_OUTPUT + (marker ? '-marker' : '-empty');
        expect(evidence).to.be.a('string'); expect(fs.existsSync(evidence)).to.equal(false);
        fs.mkdirSync(evidence, { recursive: false, mode: 0o700 });
        const locks = path.join(evidence, 'locks'); fs.mkdirSync(locks, { mode: 0o700 });
        const filename = path.join(evidence, 'session.jsonl');
        const wallet = new ethers.Wallet('0x' + '11'.repeat(32)), governor = '0xd76AD27a1Bcf8652e7e46BE603FA742FD1c10A99';
        await network.provider.send('hardhat_setBalance', [wallet.address, ethers.toQuantity(ethers.parseEther('100'))]);
        const markerCode = '0xef0100' + legacy.ENS.slice(2).toLowerCase();
        if (marker) await network.provider.send('hardhat_setCode', [wallet.address, markerCode]);
        await installToken();
        for (const [name, destination] of [['MockAscensionENS', legacy.ENS], ['MockAscensionWrapper', legacy.WRAPPER]]) {
            const fixture = await (await ethers.getContractFactory(name)).deploy();
            await network.provider.send('hardhat_setCode', [destination, await ethers.provider.getCode(fixture.target)]);
        }
        const ens = await ethers.getContractAt('MockAscensionENS', legacy.ENS);
        for (const name of legacy.roots) await (await ens.setOwner(ethers.namehash(name), governor)).wait();
        const start = await ethers.provider.getBlock('latest');
        const config = { schema: 'agialpha.mainnet.config.v2', chainId: 1, deployer: wallet.address, nonce: 0,
            block: { number: start.number, hash: start.hash }, governor: { kind: 'ledger-eoa', address: governor, addressAcknowledgement: governor },
            dependencies: {}, rootOwners: Object.fromEntries(legacy.roots.map(name => [name, governor])),
            parameters: { minimumValidatorStake: '10000000000000000000', minimumAgentStake: '10000000000000000000', quorum: 2, maximumRiskBps: 2000 },
            sender: { mode: policy.CONVENTIONAL }, envelope: { gasLimit: '8000000', maxFeePerGas: '10000000000', maxPriorityFeePerGas: '1000000000', accessList: [] } };
        for (const [name, address] of Object.entries({ token: AGIALPHA_ADDRESS, ens: legacy.ENS, wrapper: legacy.WRAPPER })) config.dependencies[name] = { address, codeHash: ethers.keccak256(await ethers.provider.getCode(address)) };
        const revision = { commit: '38064bec3423218f87c6b81760ac6768b3e7d4e5', tree: '4fe59cb9b8c7e65ea087fd27b0e2abed6bf34c68', lockSha256: '070e3c6652f4939fabe14788a0c80b38ed3d6e2ad792cebad4a5bbf842308667' };
        const journal = { schema: 'ethereum.cross-project-nonce-journal.v1', journalId: 'disposable-creator-wrapper', revision: 1, chainId: 1,
            sender: wallet.address, scope: ['alpha', 'jobs', 'manager'], block: config.block, latestNonce: 0, pendingNonce: 0,
            allocations: [{ project: 'alpha', startNonce: 0, count: 5 }, { project: 'jobs', startNonce: 5, count: 1 }, { project: 'manager', startNonce: 6, count: 1 }] };
        const plan = await policy.makePlan(config, policy.compiledContracts(), revision, journal);
        const rpc = (method, params) => network.provider.send(method, method === 'eth_getBlockByNumber' && params[0] === 'finalized' ? ['latest', false] : params);
        const sourceFiles = ['creator-terminal.js', 'deploy-mainnet-creator.js', 'authority-session.js'].map(name => path.join(__dirname, '../scripts', name));
        const digest = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'), pins = sourceFiles.map(digest);
        const assertInputs = () => { sourceFiles.forEach((file, index) => expect(digest(file)).to.equal(pins[index])); if (fs.existsSync(filename)) expect(fs.statSync(filename).size).to.be.lessThan(4 * 1024 * 1024); };
        let prompts = 0, closes = 0, relayCount = 0, interrupt = true;
        const args = { plan, revision, filename, directory: locks, assertInputs, withRpc: fn => fn(rpc),
            confirm: async review => { expect(review.governor.address).to.equal(governor); expect(review.creatorOperations).to.equal(5); },
            obtainSigner: async address => { prompts++; const signer = terminal.signerFromBytes(Buffer.from('0x' + '11'.repeat(32)), address); return { address: signer.address, signExact: signer.signExact, close() { closes++; signer.close(); } }; },
            relay: options => session.relayOnce({ ...options, relay: async raw => { relayCount++; return network.provider.send('eth_sendRawTransaction', [raw]); } }),
            sleep: async () => { throw Error('Disposable automine should not wait'); },
            onProgress: progress => { if (interrupt && progress.index === 1 && progress.status === 'finalized') throw Error('Synthetic interruption after two finalized creations'); } };
        let stopped; try { await creator.runCreator(args); } catch (error) { stopped = error; }
        expect(stopped?.message).to.equal('Synthetic interruption after two finalized creations');
        const prefix = session.loadSession(filename, plan, revision).operations;
        expect(prefix.length).to.equal(2); expect(prefix.every(op => op.status === 'finalized')).to.equal(true);
        interrupt = false;
        const result = await creator.runCreator(args), state = session.loadSession(filename, plan, revision);
        expect(result.status).to.equal('awaiting-governor-bindings'); expect(result.creationHashes.length).to.equal(5); expect(result.governanceHashes).to.deep.equal([]);
        expect(state.operations.slice(0, 2)).to.deep.equal(prefix); expect(state.operations.length).to.equal(5); expect(state.complete).to.equal(false);
        expect(relayCount).to.equal(5); expect(prompts).to.equal(2); expect(closes).to.equal(2); expect(await ethers.provider.getTransactionCount(wallet.address)).to.equal(5);
        for (const name of policy.OWNED) { const contract = await ethers.getContractAt(name, plan.addresses[name]); expect(await contract.owner()).to.equal(governor); expect(await contract.pendingOwner()).to.equal(ethers.ZeroAddress); }
        expect(await (await ethers.getContractAt('AscensionRiskOracle', plan.addresses.AscensionRiskOracle)).marketplace()).to.equal(ethers.ZeroAddress);
        expect(await (await ethers.getContractAt('AscensionJobMarket', plan.addresses.AscensionJobMarket)).mark()).to.equal(ethers.ZeroAddress);
        expect(result.actorLocksRetained).to.equal(true); expect(state.locks.every(lock => fs.existsSync(lock.path))).to.equal(true);
        if (marker) expect(await ethers.provider.getCode(wallet.address)).to.equal(markerCode);
        fs.writeFileSync(path.join(evidence, 'public-result.json'), JSON.stringify({ ...result, testScope: 'Disposable synthetic key and dependencies; latest-as-finalized; no clean-Git CLI or real-provider qualification', relayCount, prompts, closes }, null, 2), { flag: 'wx', mode: 0o600 });
    });
});
