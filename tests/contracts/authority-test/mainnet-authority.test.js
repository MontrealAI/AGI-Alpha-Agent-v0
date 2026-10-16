// SPDX-License-Identifier: Apache-2.0
// Disposable local functional/consensus-path tests, not mainnet/fork/custody evidence.
const { expect } = require("chai");
const fs = require("fs");
const path = require("path");
const { ethers, network } = require("hardhat");
const policy = require("../scripts/mainnet-authority");
const legacy = require("../scripts/mainnet");
const { installToken } = require("../test/utils/token");
const { requireDisposableLocalNetwork } = require("../scripts/disposable");
const { AGIALPHA_ADDRESS: TOKEN } = require("../../../token.config");
const { ENS, WRAPPER, roots } = legacy;
const clone = v => JSON.parse(JSON.stringify(v));
const revision = { commit: "bd1728f067e3fd1e94d81a19142733d308de1e43", tree: "19e498dd8d082a397555ed2006269512422444fb", lockSha256: "070e3c6652f4939fabe14788a0c80b38ed3d6e2ad792cebad4a5bbf842308667" };
const selectedGovernor = "0xd76AD27a1Bcf8652e7e46BE603FA742FD1c10A99";
const address = n => ethers.getAddress(`0x${n.toString(16).padStart(40, "0")}`);
const fixtureHash = ethers.id("SYNTHETIC TEST FIXTURE; NOT A QUALIFICATION OR APPROVAL");
function config(deployer = address(101), governor = selectedGovernor) {
    return { schema: "agialpha.mainnet.config.v2", chainId: 1, deployer, nonce: 7, block: { number: 100, hash: fixtureHash },
        governor: { kind: "ledger-eoa", address: governor, addressAcknowledgement: governor },
        dependencies: Object.fromEntries(Object.entries({ token: TOKEN, ens: ENS, wrapper: WRAPPER }).map(([k, a]) => [k, { address: a, codeHash: ethers.keccak256("0x6000") }])),
        rootOwners: Object.fromEntries(roots.map(n => [n, address(106)])), parameters: { minimumValidatorStake: "10000000000000000000", minimumAgentStake: "10000000000000000000", quorum: 2, maximumRiskBps: 2000 },
        sender: { mode: policy.EMPTY }, envelope: { gasLimit: "8000000", maxFeePerGas: "10000000000", maxPriorityFeePerGas: "1000000000", accessList: [] } };
}
function journal(c) { return { schema: "ethereum.cross-project-nonce-journal.v1", journalId: "offline-synthetic-test", revision: 1, chainId: 1, sender: c.deployer, scope: ["alpha", "jobs", "manager"], block: c.block,
    latestNonce: c.nonce, pendingNonce: c.nonce, allocations: [{ project: "alpha", startNonce: c.nonce, count: 5 }, { project: "jobs", startNonce: c.nonce + 5, count: 1 }, { project: "manager", startNonce: c.nonce + 6, count: 1 }] }; }
function delegated(c, target = address(201), code = "0x600060006000f000") {
    c.sender = { mode: policy.DELEGATED, delegationCode: `0xef0100${target.slice(2).toLowerCase()}`, target, targetCodeHash: ethers.keccak256(code),
        stateChecks: [{ to: target, data: "0x12345678", resultHash: ethers.keccak256("0x") }],
        qualification: { consensusEvidenceSha256: fixtureHash.slice(2), forkEvidenceSha256: fixtureHash.slice(2), delegateReviewSha256: fixtureHash.slice(2) } };
    return c;
}
async function rejects(fn, text) { let error; try { await fn(); } catch (e) { error = e; } expect(error, text).to.be.instanceOf(Error); if (text) expect(error.message).to.include(text); }
let compiled;
function mockRpc(c) {
    return async (method, args) => {
        if (method === "eth_chainId") return "0x1";
        if (method === "eth_getBlockByNumber") return { number: ethers.toQuantity(c.block.number), hash: c.block.hash, timestamp: "0x100", gasLimit: "0x1c9c380" };
        if (method === "eth_getCode") {
            if (args[0].toLowerCase() === c.governor.address.toLowerCase()) return "0x";
            if (args[0].toLowerCase() === c.deployer.toLowerCase()) return c.sender.delegationCode || "0x";
            if (c.sender.target && args[0].toLowerCase() === c.sender.target.toLowerCase()) return "0x600060006000f000";
            if (Object.values(c.dependencies).some(d => d.address.toLowerCase() === args[0].toLowerCase())) return "0x6000";
            return "0x";
        }
        if (method === "eth_getTransactionCount") return ethers.toQuantity(args[0].toLowerCase() === c.deployer.toLowerCase() ? c.nonce : 0);
        if (method === "eth_call") {
            const { to, data } = args[0], coder = ethers.AbiCoder.defaultAbiCoder();
            if (to === c.sender.target) return "0x";
            if (data.startsWith(ethers.id("decimals()").slice(0, 10))) return coder.encode(["uint8"], [18]);
            if (data.startsWith(ethers.id("owner(bytes32)").slice(0, 10))) return coder.encode(["address"], [c.rootOwners[roots[0]]]);
        }
        throw Error(`Unexpected mock read ${method}`);
    };
}
async function localFixture(mode) {
    await requireDisposableLocalNetwork();
    expect(network.config.chainId).to.equal(1); expect(network.config.hardfork).to.equal("osaka");
    await ethers.provider.send("hardhat_reset", []);
    const [sponsor, governor] = await ethers.getSigners();
    const creator = ethers.Wallet.createRandom().connect(ethers.provider);
    await ethers.provider.send("hardhat_setBalance", [creator.address, ethers.toQuantity(ethers.parseEther("100"))]);
    await installToken();
    for (const [name, to] of [["MockAscensionENS", ENS], ["MockAscensionWrapper", WRAPPER]]) {
        const deployed = await (await ethers.getContractFactory(name)).deploy();
        await ethers.provider.send("hardhat_setCode", [to, await ethers.provider.getCode(deployed.target)]);
    }
    const ens = await ethers.getContractAt("MockAscensionENS", ENS);
    for (const n of roots) await (await ens.setOwner(ethers.namehash(n), governor.address)).wait();
    const c = config(creator.address, governor.address);
    if (mode === policy.DELEGATED) {
        const target = address(201), delegateCode = "0x600060006000f000";
        await ethers.provider.send("hardhat_setCode", [target, delegateCode]);
        const authorization = await creator.authorize({ address: target, chainId: 1, nonce: 0 });
        const setCode = await sponsor.sendTransaction({ type: 4, to: sponsor.address, value: 0, authorizationList: [authorization] });
        const receipt = await setCode.wait(); expect(receipt.status).to.equal(1); expect(setCode.type).to.equal(4);
        delegated(c, target, delegateCode);
        expect(await ethers.provider.getCode(creator.address)).to.equal(c.sender.delegationCode);
    }
    c.nonce = Number(BigInt(await ethers.provider.send("eth_getTransactionCount", [creator.address, "latest"])));
    for (const dep of Object.values(c.dependencies)) dep.codeHash = ethers.keccak256(await ethers.provider.getCode(dep.address));
    c.rootOwners = Object.fromEntries(roots.map(n => [n, governor.address]));
    const b = await ethers.provider.send("eth_getBlockByNumber", ["latest", false]); c.block = { number: Number(BigInt(b.number)), hash: b.hash };
    const j = journal(c), plan = await policy.makePlan(c, compiled, revision, j), creationHashes = [], governanceHashes = [];
    // Only finality is synthetic here. Every transaction, signature, receipt, code and getter is from the in-process EVM.
    const rpc = (m, a) => ethers.provider.send(m, m === "eth_getBlockByNumber" && a[0] === "finalized" ? ["latest", false] : a);
    async function create(i) {
        const { from, ...envelope } = plan.transactions[i].envelope;
        const signed = await creator.signTransaction(envelope); // disposable random local key only
        expect(ethers.Transaction.from(signed).from).to.equal(creator.address);
        const sent = await ethers.provider.broadcastTransaction(signed); const receipt = await sent.wait();
        expect(receipt.contractAddress).to.equal(plan.transactions[i].expectedAddress); creationHashes.push(sent.hash);
        return sent;
    }
    async function bind() { for (const tx of plan.governanceCalls) { const sent = await governor.sendTransaction({ type: 2, to: tx.to, data: tx.data, value: 0, accessList: [] }); await sent.wait(); governanceHashes.push(sent.hash); } }
    async function evidence() { const b = await rpc("eth_getBlockByNumber", ["latest", false]); return { creationHashes, governanceHashes, acceptanceBlock: { number: Number(BigInt(b.number)), hash: b.hash } }; }
    return { c, j, plan, creator, governor, sponsor, rpc, create, bind, evidence, creationHashes, governanceHashes };
}
describe("Candidate v2 direct-CREATE and authority policy (offline)", function () {
    this.timeout(120000);
    before(() => { compiled = policy.compiledContracts(); });
    it("binds arbitrary separate creators to the exact selected governor without rewriting v1", async () => {
        const seen = new Set();
        for (const creator of [address(101), address(102), "0x6c8B8897Fb6b08B4070387233B89b3E9A94eD00E"]) for (const mode of [policy.EMPTY, policy.DELEGATED]) {
            const c = config(creator); if (mode === policy.DELEGATED) delegated(c);
            const p = await policy.makePlan(c, compiled, revision, journal(c)); await policy.checkPlan(p, compiled, revision);
            expect(p.readyToBroadcast).to.equal(false);
            for (const tx of p.transactions) {
                expect(tx.envelope.type).to.equal(2); expect(tx.envelope.to).to.equal(null);
                if (policy.OWNED.includes(tx.name)) expect(tx.constructorArguments.at(-1)).to.equal(selectedGovernor);
            }
            expect(p.governanceCalls.every(call => call.from === selectedGovernor && call.operation === 0)).to.equal(true);
            const boundary = policy.signingBoundary(p);
            expect(boundary.executorIntegrated).to.equal(false);
            expect(boundary.lock.key).to.equal(`1-${creator.toLowerCase()}`);
            expect(boundary.lock.keys).to.deep.equal([`1-${creator.toLowerCase()}`, `1-${selectedGovernor.toLowerCase()}`].sort());
            expect(boundary.intents.map(x => x.nonce)).to.deep.equal(p.transactions.map(x => x.envelope.nonce));
            for (const [i, intent] of boundary.intents.entries()) {
                expect(intent.schema).to.equal("creation-intent-v1"); expect(intent.dataHash).to.equal(ethers.keccak256(p.transactions[i].envelope.data));
            }
            seen.add(p.addresses.AscensionAccess);
        }
        expect(seen.size).to.equal(3);
        const old = config(); delete old.sender; delete old.envelope; old.schema = "agialpha.mainnet.config.v1";
        expect(() => legacy.validateConfig(old)).to.throw("historical governor");
        old.governor.address = legacy.HISTORICAL_LEDGER_GOVERNOR; old.governor.addressAcknowledgement = old.governor.address;
        expect(legacy.validateConfig(old)).to.equal(old);
    });
    it("rejects missing acknowledgement, creator=governor and unsupported/malformed sender profiles", () => {
        for (const mutate of [c => c.governor.addressAcknowledgement = legacy.HISTORICAL_LEDGER_GOVERNOR, c => c.governor.addressAcknowledgement = selectedGovernor.toLowerCase(),
            c => c.deployer = c.governor.address, c => c.sender.mode = "factory", c => c.sender.mode = "type4", c => c.sender.mode = "smart-wallet", c => c.sender.mode = "batch",
            c => delete c.sender.mode, c => c.envelope.accessList.push({ address: address(1), storageKeys: [] }), c => c.envelope.maxPriorityFeePerGas = "99999999999999"]) {
            const c = config(); mutate(c); expect(() => policy.validateConfig(c)).to.throw();
        }
        for (const mutate of [c => c.sender.delegationCode += "00", c => c.sender.delegationCode = "0x6000", c => c.sender.target = address(3),
            c => c.sender.targetCodeHash = ethers.ZeroHash, c => c.sender.stateChecks = [], c => c.sender.qualification.forkEvidenceSha256 = null,
            c => c.sender.qualification.delegateReviewSha256 = "0".repeat(64)]) { const c = delegated(config()); mutate(c); expect(() => policy.validateConfig(c)).to.throw(); }
    });
    it("enforces Osaka EIP-7825 in the planner and actual local transaction admission", async () => {
        const c = config(); c.envelope.gasLimit = policy.MAX_TRANSACTION_GAS.toString(); expect(policy.validateConfig(c)).to.equal(c);
        c.envelope.gasLimit = (policy.MAX_TRANSACTION_GAS + 1n).toString(); expect(() => policy.validateConfig(c)).to.throw("gas cap");
        await requireDisposableLocalNetwork();
        expect(network.config.hardfork).to.equal("osaka");
        expect(network.config.blockGasLimit).to.equal(30000000);
        expect(network.config.blockGasLimit).not.to.equal(0x1fffffffffffff); // no coverage gas-cap bypass
        const [signer] = await ethers.getSigners();
        await rejects(() => signer.sendTransaction({ type: 2, to: signer.address, value: 0, gasLimit: policy.MAX_TRANSACTION_GAS + 1n }), "gas cap");
        await (await signer.sendTransaction({ type: 2, to: signer.address, value: 0, gasLimit: policy.MAX_TRANSACTION_GAS })).wait();
    });
    it("requires one coordinated nonoverlapping Alpha/Jobs/Manager nonce journal", () => {
        const c = config();
        for (const mutate of [j => j.scope.pop(), j => j.sender = address(7), j => j.pendingNonce++, j => j.allocations[1].startNonce = c.nonce + 4,
            j => j.allocations[0].count = 4, j => j.allocations.push({ ...j.allocations[0] }), j => j.block = { ...j.block, hash: ethers.id("other") }]) {
            const j = clone(journal(c)); mutate(j); expect(() => policy.validateJournal(c, j)).to.throw();
        }
    });
    it("rejects every unsupported envelope substitution including zero-address to and extra authorization", async () => {
        const c = config(), p = await policy.makePlan(c, compiled, revision, journal(c)), expected = p.transactions[0].envelope;
        for (const mutate of [t => t.type = 4, t => t.to = c.deployer, t => t.to = ethers.ZeroAddress, t => t.to = address(201), t => delete t.to,
            t => t.chainId = 31337, t => t.from = address(9), t => t.nonce++, t => t.value = "1", t => t.data += "00", t => t.gasLimit = "9999999",
            t => t.maxFeePerGas = "1", t => t.accessList = [{ address: address(5), storageKeys: [] }], t => t.authorizationList = [], t => t.factory = address(7)]) {
            const tx = clone(expected); mutate(tx); expect(() => policy.validateEnvelope(expected, tx)).to.throw();
        }
        for (const mutate of [x => x.transactions[0].constructorArguments[2] = c.deployer, x => x.contracts.AscensionAccess.runtime += "00", x => x.governanceCalls[0].from = c.deployer,
            x => x.revision.lockSha256 = "f".repeat(64), x => x.builds[Object.keys(x.builds)[0]].input.settings.optimizer.runs++]) {
            const altered = clone(p); mutate(altered); const { payloadSha256, ...payload } = altered; await rejects(() => policy.checkPlan(policy.seal(payload), compiled, revision), "Plan/source/constructor");
        }
    });
    it("requires an independently observed revision instead of a self-declared plan source label", async () => {
        const c = config(), plan = await policy.makePlan(c, compiled, revision, journal(c));
        let reads = 0;
        const noRpc = async () => { ++reads; throw Error("Source rejection must precede every RPC read"); };
        await rejects(() => policy.checkPlan(plan, compiled), "independently observed");
        await rejects(() => policy.preflight(plan, noRpc), "independently observed");
        await rejects(() => policy.verifyAuthority(plan, noRpc, {}), "independently observed");
        for (const mutate of [r => r.commit = "a".repeat(40), r => r.tree = "b".repeat(40), r => r.lockSha256 = "c".repeat(64),
            r => { r.commit = "a".repeat(40); r.tree = "b".repeat(40); }]) {
            const altered = clone(plan); mutate(altered.revision);
            const { payloadSha256, ...payload } = altered, resealed = policy.seal(payload);
            await rejects(() => policy.checkPlan(resealed, compiled, revision), "independently observed revision differs");
            await rejects(() => policy.preflight(resealed, noRpc, revision), "independently observed revision differs");
            await rejects(() => policy.verifyAuthority(resealed, noRpc, {}, revision), "independently observed revision differs");
        }
        expect(reads).to.equal(0);
        await policy.checkPlan(plan, compiled, revision);
        expect((await policy.preflight(plan, mockRpc(c), revision)).observedRevision).to.deep.equal(revision);
    });
    it("protects previous deployments from stale-nonce plans and substituted binding targets or arguments", async () => {
        const archive = require("../scripts/mainnet-record").loadRecord().record;
        expect(policy.HISTORICAL_GRAPH).to.deep.equal(Object.values(archive.contracts).map(c => ethers.getAddress(c.address)));
        for (const mode of [policy.EMPTY, policy.DELEGATED]) {
            const oldNonce = config(archive.deployer); oldNonce.nonce = archive.startingNonce;
            if (mode === policy.DELEGATED) delegated(oldNonce);
            await rejects(() => policy.makePlan(oldNonce, compiled, revision, journal(oldNonce)), "Previously deployed graph is protected");
        }
        const c = config(), plan = await policy.makePlan(c, compiled, revision, journal(c));
        expect(plan.governanceCalls.every(call => Object.values(plan.addresses).includes(call.to) && Object.values(plan.addresses).includes(call.argument))).to.equal(true);
        expect([...Object.values(plan.addresses), ...plan.governanceCalls.map(call => call.to)].some(a => policy.HISTORICAL_GRAPH.includes(a))).to.equal(false);
        for (const change of [
            p => p.governanceCalls[0].to = archive.contracts.AscensionRiskOracle.address,
            p => p.governanceCalls[1].argument = archive.contracts.AscensionMark.address,
            p => p.governanceCalls[0].data = new ethers.Interface(compiled.records.AscensionRiskOracle.abi).encodeFunctionData("bindMarketplace", [archive.contracts.AscensionJobMarket.address]),
            p => p.addresses.AscensionAccess = archive.contracts.AscensionAccess.address,
            p => p.governanceCalls.push({ ...p.governanceCalls[0], to: archive.contracts.AscensionRiskOracle.address })
        ]) {
            const altered = clone(plan); change(altered); const { payloadSha256, ...payload } = altered;
            await rejects(() => policy.checkPlan(policy.seal(payload), compiled, revision), "Plan/source/constructor");
        }
    });
    it("detects pinned/latest sender, governor, target, authority, nonce, address and journal drift", async () => {
        const c = delegated(config()), p = await policy.makePlan(c, compiled, revision, journal(c)), base = mockRpc(c);
        expect((await policy.preflight(p, base, revision)).readyToBroadcast).to.equal(false);
        const changes = [
            (m, a) => m === "eth_chainId" ? "0x2" : undefined,
            (m, a) => m === "eth_getBlockByNumber" ? { number: "0x64", hash: c.block.hash, timestamp: "0x100", gasLimit: "0x186a0" } : undefined,
            (m, a) => m === "eth_getCode" && a[0] === c.deployer ? "0x" : undefined,
            (m, a) => m === "eth_getCode" && a[0] === c.sender.target ? "0x6000" : undefined,
            (m, a) => m === "eth_getCode" && a[0] === c.governor.address ? "0xef0100" + address(201).slice(2) : undefined,
            (m, a) => m === "eth_call" && a[0].to === c.sender.target ? "0x01" : undefined,
            (m, a) => m === "eth_getTransactionCount" && a[0] === c.deployer && a[1] === "pending" ? "0x8" : undefined,
            (m, a) => m === "eth_getCode" && a[0] === p.transactions[0].expectedAddress ? "0x6000" : undefined,
            (m, a) => m === "eth_getTransactionCount" && a[0] === p.transactions[0].expectedAddress ? "0x1" : undefined,
            (m, a) => m === "eth_getBlockByNumber" && a[0] === "0x64" ? { number: "0x64", hash: ethers.id("reorg"), timestamp: "0x100" } : undefined
        ];
        for (const change of changes) await rejects(() => policy.preflight(p, async (m, a) => change(m, a) ?? base(m, a), revision));
        const j = clone(p.journal); j.revision++; await rejects(() => policy.preflight(p, base, revision, [], j), "Journal changed");
        const empty = config(), ep = await policy.makePlan(empty, compiled, revision, journal(empty));
        await rejects(() => policy.preflight(ep, (m, a) => m === "eth_getCode" && a[0] === empty.deployer ? c.sender.delegationCode : mockRpc(empty)(m, a), revision), "Empty-code mode");
    });
    for (const mode of [policy.EMPTY, policy.DELEGATED]) it(`executes serialized ${mode} creations, resumable receipt checks and governor-only bindings`, async () => {
        const f = await localFixture(mode); expect((await policy.preflight(f.plan, f.rpc, revision)).nextIndex).to.equal(0);
        for (let i = 0; i < 5; ++i) {
            await f.create(i);
            const progress = await policy.preflight(f.plan, f.rpc, revision, f.creationHashes); expect(progress.nextIndex).to.equal(i + 1); expect(progress.nextNonce).to.equal(f.c.nonce + i + 1);
            const name = policy.NAMES[i];
            if (policy.OWNED.includes(name)) {
                const contract = await ethers.getContractAt(name, f.plan.addresses[name]); expect(await contract.owner()).to.equal(f.governor.address); expect(await contract.pendingOwner()).to.equal(ethers.ZeroAddress);
                for (const [method, args] of [["transferOwnership", [f.creator.address]], ["renounceOwnership", []], ["acceptOwnership", []]]) await expect(contract.connect(f.creator)[method](...args)).to.be.reverted;
            }
        }
        await rejects(() => policy.preflight(f.plan, f.rpc, revision, []), "nonce drift");
        await rejects(() => policy.preflight(f.plan, f.rpc, revision, [f.creationHashes[1]]));
        const access = await ethers.getContractAt("AscensionAccess", f.plan.addresses.AscensionAccess), oracle = await ethers.getContractAt("AscensionRiskOracle", f.plan.addresses.AscensionRiskOracle), market = await ethers.getContractAt("AscensionJobMarket", f.plan.addresses.AscensionJobMarket);
        await expect(access.connect(f.creator).setAdmission(f.creator.address, fixtureHash, 0)).to.be.reverted;
        await expect(oracle.connect(f.creator).bindMarketplace(market.target)).to.be.reverted;
        await expect(market.connect(f.creator).bindMark(f.plan.addresses.AscensionMark)).to.be.reverted;
        await f.bind();
        const verified = await policy.verifyAuthority(f.plan, f.rpc, await f.evidence(), revision); expect(verified.graphAuthorityVerified).to.equal(true); expect(verified.activationAllowed).to.equal(false);
        const bundle = await require("../scripts/authority-verification-package").receiptProvenPackage(f.plan, f.rpc, await f.evidence(), revision, compiled);
        expect(bundle.manifest.addressStatus).to.equal("receipt-proven");
        for (const [i, name] of policy.NAMES.entries()) expect(bundle.manifest.contracts[name].creationEvidence.transactionHash).to.equal(f.creationHashes[i]);
        if (process.env.ALPHA_AUTHORITY_EVIDENCE_DIRECTORY) {
            const output = { schema: "agialpha.offline-functional-evidence.v1", recordedAt: new Date().toISOString(),
                runtime: process.version, hardhat: require("hardhat/package.json").version, edr: JSON.parse(fs.readFileSync(path.join(path.dirname(require.resolve("@nomicfoundation/edr")), "package.json"))).version,
                chain: "Disposable unforked in-process chainId1, explicit Osaka; not Ethereum mainnet", finality: "Synthetic latest-as-finalized fixture", dependencies: "Local mock AGIALPHA/ENS/Wrapper",
                senderMode: mode, creator: f.creator.address, governor: f.governor.address, delegation: f.c.sender, sourceAnchor: revision,
                planSha256: f.plan.payloadSha256, verified, providerBackedFork: false, realWalletSigning: false, actual7702DelegateQualification: false,
                limits: ["Functional engine/path evidence only; no custody, real dependency behavior, independent review or production acceptance claim"] };
            fs.writeFileSync(path.join(process.env.ALPHA_AUTHORITY_EVIDENCE_DIRECTORY, `${mode}.json`), JSON.stringify(output, null, 2) + "\n", { flag: "wx" });
        }
        for (const name of policy.OWNED) {
            const contract = await ethers.getContractAt(name, f.plan.addresses[name]);
            for (const [method, args] of [["transferOwnership", [f.creator.address]], ["renounceOwnership", []], ["acceptOwnership", []]]) await expect(contract.connect(f.creator)[method](...args)).to.be.reverted;
        }
        await expect(oracle.connect(f.creator).bindMarketplace(market.target)).to.be.reverted;
        await expect(market.connect(f.creator).bindMark(f.plan.addresses.AscensionMark)).to.be.reverted;
        const snapshot = await ethers.provider.send("evm_snapshot", []);
        const seed = await ethers.getContractAt("NovaSeed", f.plan.addresses.NovaSeed);
        await (await seed.connect(f.sponsor).setApprovalForAll(f.creator.address, true)).wait();
        await rejects(async () => policy.verifyAuthority(f.plan, f.rpc, await f.evidence(), revision), "Unexpected authority/participant/approval events");
        await ethers.provider.send("evm_revert", [snapshot]);
        // Current creator state is no longer a historical creation invariant after the handover.
        await ethers.provider.send("hardhat_setCode", [f.creator.address, "0x6000"]);
        await ethers.provider.send("hardhat_setNonce", [f.creator.address, ethers.toQuantity(f.c.nonce + 20)]);
        expect((await policy.verifyAuthority(f.plan, f.rpc, await f.evidence(), revision)).graphAuthorityVerified).to.equal(true);
        await expect(oracle.connect(f.governor).bindMarketplace(market.target)).to.be.revertedWith("binding is one-time");
        await expect(market.connect(f.governor).bindMark(f.plan.addresses.AscensionMark)).to.be.revertedWith("binding is one-time");
        const latest = await ethers.provider.getBlock("latest");
        await (await access.connect(f.governor).setAdmission(f.creator.address, fixtureHash, latest.timestamp + 1000)).wait();
        await rejects(async () => policy.verifyAuthority(f.plan, f.rpc, await f.evidence(), revision), "creator admission");
    });
    it("detects a delegated account CREATE-induced nonce race and stops a partial run", async () => {
        const f = await localFixture(policy.DELEGATED); await f.create(0);
        await (await f.sponsor.sendTransaction({ to: f.creator.address, data: "0x12345678", gasLimit: 500000 })).wait();
        expect(BigInt(await f.rpc("eth_getTransactionCount", [f.creator.address, "latest"]))).to.equal(BigInt(f.c.nonce + 2));
        await rejects(() => policy.preflight(f.plan, f.rpc, revision, f.creationHashes), "nonce drift");
    });
    it("rejects nonce consumption by an unrelated competing transaction without retrying CREATE", async () => {
        const f = await localFixture(policy.EMPTY);
        const sent = await f.creator.sendTransaction({ type: 2, to: f.sponsor.address, value: 0, nonce: f.c.nonce }); await sent.wait();
        await rejects(() => policy.preflight(f.plan, f.rpc, revision), "nonce drift");
        await rejects(() => policy.preflight(f.plan, f.rpc, revision, [sent.hash]), "direct type-2 CREATE");
    });
    it("rejects failed/replaced/wrong-source/noncanonical creation evidence and tampered runtime", async () => {
        const f = await localFixture(policy.EMPTY); await f.create(0);
        const pin = (await f.evidence()).acceptanceBlock;
        const tamper = [
            ["eth_getTransactionReceipt", x => ({ ...x, status: "0x0" })],
            ["eth_getTransactionReceipt", x => ({ ...x, contractAddress: address(7) })],
            ["eth_getTransactionReceipt", x => ({ ...x, blockHash: ethers.id("wrong block") })],
            ["eth_getTransactionByHash", x => ({ ...x, input: x.input + "00" })],
            ["eth_getTransactionByHash", x => ({ ...x, from: address(7) })],
            ["eth_getTransactionByHash", x => ({ ...x, r: fixtureHash })],
            ["eth_getTransactionByHash", x => ({ ...x, type: "0x4", authorizationList: [] })]
        ];
        for (const [method, mutate] of tamper) await rejects(() => policy.receiptEvidence(f.plan, 0, f.creationHashes[0], async (m, a) => { const x = await f.rpc(m, a); return m === method ? mutate(x) : x; }, pin));
        await ethers.provider.send("hardhat_setCode", [f.plan.addresses.AscensionAccess, "0x6000"]);
        await rejects(() => policy.preflight(f.plan, f.rpc, revision, f.creationHashes), "exact runtime/immutables");
    });
    for (const [mode, submission] of [[policy.EMPTY, "raw-relay"], [policy.DELEGATED, "external-broadcast"]])
    it(`coordinates all seven ${mode} operations with ${submission} recovery and both actor locks`, async () => {
        const session = require("../scripts/authority-session"), os = require("os");
        const f = await localFixture(mode), temp = fs.mkdtempSync(path.join(os.tmpdir(), "alpha-session-")), filename = path.join(temp, "progress.jsonl");
        const governor = ethers.HDNodeWallet.fromPhrase("test test test test test test test test test test test junk", undefined, "m/44'/60'/0'/0/1");
        expect(governor.address).to.equal(f.governor.address); // public disposable Hardhat fixture only
        const args = { plan: f.plan, revision, filename, rpc: f.rpc };
        try {
            let state = await session.startSession({ ...args, directory: temp, mode: submission });
            expect(state.operations).to.have.length(0);
            const partialPlan = { config: config(address(998), f.governor.address) };
            const child = require("child_process").spawnSync(process.execPath, ["-e", `const s=require(${JSON.stringify(require.resolve("../scripts/authority-session"))});try{s.acquireActors(JSON.parse(process.argv[1]),process.argv[2],process.argv[3]);process.exit(3)}catch(e){if(!e.message.includes('Actor lock exists'))throw e;process.exit(0)}`, JSON.stringify(partialPlan), temp, path.join(temp, "other.jsonl")], { encoding: "utf8" });
            expect(child.status, child.stderr).to.equal(0); // independent process, different creator, shared governor
            let relays = 0;
            for (let index = 0; index < 7; ++index) {
                const governorEnvelope = index < 5 ? undefined : { nonce: Number(BigInt(await f.rpc("eth_getTransactionCount", [f.governor.address, "pending"]))),
                    gasLimit: "1000000", maxFeePerGas: "10000000000", maxPriorityFeePerGas: "1000000000", accessList: [] };
                const handed = await session.prepare({ ...args, governorEnvelope });
                expect(handed.state.operations[index].status).to.equal("handed-off");
                await rejects(() => session.prepare({ ...args, governorEnvelope }), "Resolve the outstanding");
                const { from, ...envelope } = handed.packet.envelope, signer = index < 5 ? f.creator : governor;
                const raw = await signer.signTransaction(envelope);
                if (index === 0) {
                    const wrong = await signer.signTransaction({ ...envelope, maxFeePerGas: "10000000001" });
                    await rejects(() => session.importSigned({ ...args, raw: wrong }), "signed transaction envelope");
                    expect((await session.recover(args)).resolved).to.equal(false);
                }
                if (index === 1) await (await ethers.provider.broadcastTransaction(raw)).wait(); // hashless external handoff recovery
                else {
                    state = await session.importSigned({ ...args, raw });
                    if (submission === "raw-relay") {
                        const relay = async bytes => { relays++; const sent = await ethers.provider.broadcastTransaction(bytes); await sent.wait(); if (index === 0) throw Error("synthetic lost response"); return sent.hash; };
                        await rejects(() => session.relayOnce({ ...args, raw, relay, acknowledgement: "wrong" }), "acknowledgement");
                        if (index === 0) await rejects(() => session.relayOnce({ ...args, raw, relay, acknowledgement: session.relayAcknowledgement(state) }), "synthetic lost response");
                        else await session.relayOnce({ ...args, raw, relay, acknowledgement: session.relayAcknowledgement(state) });
                        await rejects(() => session.relayOnce({ ...args, raw, relay, acknowledgement: session.relayAcknowledgement(state) }), "previously attempted");
                    } else {
                        await rejects(() => session.relayOnce({ ...args, raw, relay: () => { throw Error("Forbidden external relay"); }, acknowledgement: session.relayAcknowledgement(state) }), "external mode");
                        await (await ethers.provider.broadcastTransaction(raw)).wait();
                    }
                }
                const before = fs.readFileSync(filename, "utf8"), recovered = await session.recover(args);
                expect(recovered.resolved).to.equal(true); expect(fs.readFileSync(filename, "utf8")).to.equal(before);
                state = await session.reconcile(args);
                expect(state.operations).to.have.length(index + 1); expect(state.operations.every(x => x.status === "finalized")).to.equal(true);
                const creations = state.operations.slice(0, 5).map(x => x.txHash), bindings = state.operations.slice(5).map(x => x.txHash);
                const report = await policy.preflight(f.plan, f.rpc, revision, creations, f.j, bindings);
                expect(report.bindings.length).to.equal(Math.max(0, index - 4));
                if (index === 5) expect(policy.expectedState(f.plan, 1).AscensionJobMarket.mark).to.equal(ethers.ZeroAddress);
            }
            expect(relays).to.equal(submission === "raw-relay" ? 6 : 0);
            if (submission === "raw-relay") {
                const unlink = fs.unlinkSync, secondOwner = path.join(state.locks[0].path, "owner.json");
                fs.unlinkSync = file => { if (file === secondOwner) throw Error("synthetic second-lock release failure"); return unlink(file); };
                try { await rejects(() => session.finish(args), "synthetic second-lock"); } finally { fs.unlinkSync = unlink; }
                const durable = session.loadSession(filename, f.plan, revision);
                expect(durable.complete).to.equal(true); expect(durable.authorityEvidence.graphAuthorityVerified).to.equal(true);
                expect(fs.existsSync(state.locks[1].path)).to.equal(false); expect(fs.existsSync(state.locks[0].path)).to.equal(true);
                // A new owner of the already-released path is never mistaken for ours.
                fs.mkdirSync(state.locks[1].path); fs.writeFileSync(path.join(state.locks[1].path, "owner.json"), JSON.stringify({ ...state.locks[1], token: "replacement-owner" }));
                await rejects(() => session.finish(args), "actor lock ownership");
                fs.rmSync(state.locks[1].path, { recursive: true }); // disposable fixture cleanup only
                let changedGate = false; const completionGate = filename + ".command-lock", savedGate = completionGate + ".saved";
                await rejects(() => session.finish({ ...args, rpc: async (method, params) => {
                    const result = await f.rpc(method, params);
                    if (!changedGate) { fs.renameSync(completionGate, savedGate); fs.writeFileSync(completionGate, "replacement completion gate"); changedGate = true; }
                    return result;
                } }), "Command gate or parent replaced");
                expect(fs.readFileSync(completionGate, "utf8")).to.equal("replacement completion gate");
                expect(fs.existsSync(savedGate)).to.equal(true); expect(fs.existsSync(state.locks[0].path)).to.equal(true);
                fs.unlinkSync(completionGate); fs.unlinkSync(savedGate); // explicit disposable cleanup, never automatic recovery
            }
            const completed = await session.finish(args); expect(completed.evidence.graphAuthorityVerified).to.equal(true); expect(completed.evidence.activationAllowed).to.equal(false);
            expect(completed.state.complete).to.equal(true); expect(completed.state.locks.every(lock => !fs.existsSync(lock.path))).to.equal(true);
            expect(session.loadSession(filename, f.plan, revision).complete).to.equal(true);
            const output = path.join(temp, "finish-evidence.json"), io = require("../scripts/authority-cli");
            fs.writeFileSync(output, "existing output must remain");
            expect(() => io.writeNew(output, completed)).to.throw(); expect(fs.readFileSync(output, "utf8")).to.equal("existing output must remain");
            const retry = await session.finish(args); expect(retry.evidence).to.deep.equal(completed.evidence);
            expect(retry.state.sequence).to.equal(completed.state.sequence); // no second completion or signature
            io.writeNew(path.join(temp, "recovered-finish-evidence.json"), retry);
            await rejects(() => session.prepare(args)); // missing locks never permit an ordinary command
        } finally { fs.rmSync(temp, { recursive: true, force: true }); }
    });
    it("retains crashed command locks and rejects torn journals, stale ownership, source drift and raw substitutions", async () => {
        const session = require("../scripts/authority-session"), os = require("os");
        const f = await localFixture(policy.EMPTY), temp = fs.mkdtempSync(path.join(os.tmpdir(), "alpha-crash-")), filename = path.join(temp, "progress.jsonl");
        const args = { plan: f.plan, revision, filename, rpc: f.rpc };
        try {
            const state = await session.startSession({ ...args, directory: temp, mode: "raw-relay" });
            const gate = filename + ".command-lock"; fs.writeFileSync(gate, "synthetic crashed process");
            await rejects(() => session.prepare(args), "command lock exists"); expect(fs.existsSync(gate)).to.equal(true); fs.unlinkSync(gate); // explicit test cleanup only
            const original = fs.readFileSync(filename, "utf8"); fs.appendFileSync(filename, "{");
            expect(() => session.loadSession(filename, f.plan, revision)).to.throw("Torn journal"); fs.writeFileSync(filename, original);
            const ownerFile = path.join(state.locks[0].path, "owner.json"), owner = fs.readFileSync(ownerFile, "utf8");
            fs.writeFileSync(ownerFile, JSON.stringify({ ...state.locks[0], token: "different" }));
            await rejects(() => session.prepare(args), "actor lock ownership"); expect(() => session.releaseActor(state.locks[0])).to.throw("actor lock ownership"); fs.writeFileSync(ownerFile, owner);
            await rejects(() => session.prepare({ ...args, revision: { ...revision, tree: "a".repeat(40) } }), "independently observed");
            // A replacement parent may contain another process's gate. Never unlink it during failure cleanup.
            const moved = temp + "-displaced"; let swapped = false;
            await rejects(() => session.prepare({ ...args, rpc: async (method, params) => {
                const result = await f.rpc(method, params);
                if (!swapped) { fs.renameSync(temp, moved); fs.mkdirSync(temp); fs.writeFileSync(gate, "replacement gate must remain"); swapped = true; }
                return result;
            } }), "Command gate or parent replaced");
            expect(fs.readFileSync(gate, "utf8")).to.equal("replacement gate must remain");
            expect(fs.existsSync(path.join(moved, path.basename(gate)))).to.equal(true);
            fs.rmSync(temp, { recursive: true, force: true }); fs.renameSync(moved, temp); fs.unlinkSync(gate); // explicit disposable recovery only
            const beforeMutation = fs.readFileSync(filename), savedJournal = filename + ".saved"; let changedJournal = false;
            await rejects(() => session.prepare({ ...args, rpc: async (method, params) => {
                const result = await f.rpc(method, params);
                if (!changedJournal) { fs.renameSync(filename, savedJournal); fs.writeFileSync(filename, beforeMutation); changedJournal = true; }
                return result;
            } }), "journal/head identity changed");
            expect(fs.readFileSync(filename).equals(beforeMutation)).to.equal(true); expect(fs.existsSync(savedJournal)).to.equal(true);
            fs.unlinkSync(filename); fs.renameSync(savedJournal, filename); changedJournal = false;
            await rejects(() => session.prepare({ ...args, rpc: async (method, params) => {
                const result = await f.rpc(method, params);
                if (!changedJournal) { fs.appendFileSync(filename, "{}\n"); changedJournal = true; }
                return result;
            } }));
            expect(fs.readFileSync(filename, "utf8")).to.equal(beforeMutation.toString() + "{}\n"); fs.writeFileSync(filename, beforeMutation);
            const handed = await session.prepare(args), intent = handed.state.operations[0].intent, { from, ...envelope } = intent.envelope;
            const fullJournal = fs.readFileSync(filename, "utf8"), headFile = filename + ".head.json", fullHead = fs.readFileSync(headFile, "utf8");
            fs.writeFileSync(filename, fullJournal.split("\n").slice(0, -2).join("\n") + "\n");
            expect(() => session.loadSession(filename, f.plan, revision)).to.throw("durable journal head"); fs.writeFileSync(filename, fullJournal);
            fs.writeFileSync(headFile, JSON.stringify({ ...JSON.parse(fullHead), sequence: 999 }));
            expect(() => session.loadSession(filename, f.plan, revision)).to.throw("durable journal head"); fs.writeFileSync(headFile, fullHead);
            fs.unlinkSync(headFile); expect(() => session.loadSession(filename, f.plan, revision)).to.throw(); fs.writeFileSync(headFile, fullHead);
            for (const change of [x => x.chainId = 31337, x => x.nonce++, x => x.to = f.creator.address, x => x.value = "1", x => x.data += "00", x => x.gasLimit = "9000000",
                x => x.maxPriorityFeePerGas = "2", x => x.accessList = [{ address: f.creator.address, storageKeys: [] }]]) {
                const altered = { ...envelope }; change(altered); const raw = await f.creator.signTransaction(altered);
                expect(() => session.validateSigned(raw, intent)).to.throw("signed transaction envelope");
            }
            const wrong = await ethers.Wallet.createRandom().signTransaction(envelope); expect(() => session.validateSigned(wrong, intent)).to.throw("recovered sender");
            const exact = await f.creator.signTransaction(envelope);
            let lateImportDrift = false;
            await rejects(() => session.importSigned({ ...args, raw: exact,
                rpc: async (method, params) => { const result = await f.rpc(method, params); lateImportDrift = true; return result; },
                assertInputs: () => { if (lateImportDrift) throw Error("synthetic late input drift"); } }), "late input drift");
            expect(session.loadSession(filename, f.plan, revision).operations[0].status).to.equal("handed-off");
            await rejects(() => session.importSigned({ ...args, raw: exact, rpc: undefined }), "Fresh read-only phase");
            await rejects(() => session.importSigned({ ...args, raw: exact, rpc: (m, a) => m === "eth_getCode" && a[0] === f.creator.address ? "0x6000" : f.rpc(m, a) }), "Empty-code mode");
            expect(session.loadSession(filename, f.plan, revision).operations[0].status).to.equal("handed-off");
            const rename = fs.renameSync;
            fs.renameSync = (from, to) => { if (to === headFile) throw Error("synthetic interrupted head publication"); return rename(from, to); };
            try { await rejects(() => session.importSigned({ ...args, raw: exact }), "interrupted head"); } finally { fs.renameSync = rename; }
            expect(() => session.loadSession(filename, f.plan, revision)).to.throw("durable journal head");
            await rejects(() => session.prepare(args), "durable journal head");
            expect(state.locks.every(lock => fs.existsSync(lock.path))).to.equal(true);
        } finally { fs.rmSync(temp, { recursive: true, force: true }); }
    });

    it("keeps pending, failed, conflicting and reorg recovery blocked without another relay", async () => {
        const session = require("../scripts/authority-session"), os = require("os");
        let f = await localFixture(policy.EMPTY); const temp = fs.mkdtempSync(path.join(os.tmpdir(), "alpha-recovery-"));
        try {
            const filename = path.join(temp, "pending.jsonl"), args = { plan: f.plan, revision, filename, rpc: f.rpc };
            await session.startSession({ ...args, directory: temp, mode: "raw-relay" });
            const handed = await session.prepare(args), { from, ...envelope } = handed.packet.envelope, raw = await f.creator.signTransaction(envelope);
            const signed = await session.importSigned({ ...args, raw }); let relays = 0;
            let lateRelayDrift = false;
            await rejects(() => session.relayOnce({ ...args, raw, acknowledgement: session.relayAcknowledgement(signed),
                rpc: async (method, params) => { const result = await f.rpc(method, params); lateRelayDrift = true; return result; },
                assertInputs: () => { if (lateRelayDrift) throw Error("synthetic late input drift"); }, relay: () => { relays++; } }), "late input drift");
            expect(relays).to.equal(0); expect(session.loadSession(filename, f.plan, revision).operations[0].status).to.equal("signed");
            await session.relayOnce({ ...args, raw, acknowledgement: session.relayAcknowledgement(signed), relay: async () => { relays++; return ethers.Transaction.from(raw).hash; } });
            expect((await session.recover(args)).resolved).to.equal(false); // transport returned hash, transaction never observed
            await ethers.provider.send("evm_setAutomine", [false]);
            await ethers.provider.broadcastTransaction(raw);
            expect((await session.recover(args)).resolved).to.equal(false); // exact pending transaction, no receipt
            await rejects(() => session.relayOnce({ ...args, raw, acknowledgement: session.relayAcknowledgement(signed), relay: () => { relays++; } }), "previously attempted");
            await ethers.provider.send("evm_mine", []); await ethers.provider.send("evm_setAutomine", [true]);
            for (const [method, mutate, message] of [
                ["eth_getTransactionReceipt", x => ({ ...x, status: "0x0" }), "failed"],
                ["eth_getBlockByNumber", x => ({ ...x, hash: ethers.id("reorg") }), "not canonical"],
                ["eth_getTransactionByHash", x => ({ ...x, input: x.input + "00" }), "signed transaction"]
            ]) await rejects(() => session.recover({ ...args, rpc: async (m, a) => { const x = await f.rpc(m, a); return m === method ? mutate(x) : x; } }), message);
            expect(relays).to.equal(1); expect((await session.recover(args)).resolved).to.equal(true);
            await session.reconcile(args);
            // A different campaign demonstrates a conflicting canonical sender nonce, not a resumable CREATE.
            f = await localFixture(policy.EMPTY);
            const conflict = { plan: f.plan, revision, filename: path.join(temp, "conflict.jsonl"), rpc: f.rpc };
            const otherLocks = path.join(temp, "other-locks"); fs.mkdirSync(otherLocks);
            await session.startSession({ ...conflict, directory: otherLocks, mode: "external-broadcast" }); await session.prepare(conflict);
            await (await f.creator.sendTransaction({ type: 2, to: f.sponsor.address, nonce: f.c.nonce, value: 0 })).wait();
            await rejects(() => session.recover(conflict), "signed transaction envelope");
            expect(session.loadSession(conflict.filename, f.plan, revision).operations[0].status).to.equal("handed-off");
        } finally { await ethers.provider.send("evm_setAutomine", [true]); fs.rmSync(temp, { recursive: true, force: true }); }
    });
    it("rejects every mutable checkout path and symlink alias before creating evidence or actor locks", async () => {
        const paths = require("../scripts/authority-paths"), io = require("../scripts/authority-cli"), exporter = require("../scripts/authority-verification-package"), session = require("../scripts/authority-session");
        const temp = fs.mkdtempSync(path.join(require("os").tmpdir(), "alpha-outside-checkout-")), inside = path.join(paths.SOURCE_ROOT, "tests/contracts/.authority-path-negative");
        const c = config(), plan = await policy.makePlan(c, compiled, revision, journal(c)); let calls = 0;
        try {
            fs.symlinkSync(paths.SOURCE_ROOT, path.join(temp, "checkout-alias"), "dir");
            for (const target of [paths.SOURCE_ROOT, inside, path.relative(process.cwd(), inside), path.join(paths.SOURCE_ROOT, "tests/contracts/node_modules/ignored-evidence.json"), path.join(temp, "checkout-alias", "new-evidence.json")]) {
                expect(() => paths.assertOutsideCheckout(target)).to.throw("outside the reviewed checkout");
                expect(() => io.writeNew(target, {})).to.throw("outside the reviewed checkout");
                expect(() => exporter.writePackage({ files: { "manifest.json": "{}" } }, target)).to.throw("outside the reviewed checkout");
            }
            expect(paths.assertOutsideCheckout(paths.SOURCE_ROOT + "-different-directory/output.json")).to.equal(paths.SOURCE_ROOT + "-different-directory/output.json");
            expect(() => session.acquireActors(plan, paths.SOURCE_ROOT, path.join(temp, "progress.jsonl"))).to.throw("outside the reviewed checkout");
            expect(() => session.acquireActors(plan, temp, inside)).to.throw("outside the reviewed checkout");
            await rejects(() => session.startSession({ plan, revision, filename: inside, directory: temp, mode: "external-broadcast", rpc: () => { calls++; } }), "outside the reviewed checkout");
            await rejects(() => session.prepare({ plan, revision, filename: path.join(temp, "progress.jsonl"), output: inside, rpc: () => { calls++; } }), "outside the reviewed checkout");
            expect(calls).to.equal(0); expect(fs.existsSync(inside)).to.equal(false);
            expect(fs.readdirSync(temp)).to.deep.equal(["checkout-alias"]);
        } finally { fs.rmSync(temp, { recursive: true, force: true }); }
    });
    it("persists handoff uncertainty before output failure and never silently repeats packet preparation", async () => {
        const session = require("../scripts/authority-session"), os = require("os");
        const f = await localFixture(policy.EMPTY), temp = fs.mkdtempSync(path.join(os.tmpdir(), "alpha-handoff-")), filename = path.join(temp, "progress.jsonl");
        const args = { plan: f.plan, revision, filename, rpc: f.rpc };
        try {
            const copied = temp + "-copied-locks"; let replacedLocks = false;
            await rejects(() => session.startSession({ ...args, directory: temp, mode: "external-broadcast", rpc: async (method, params) => {
                const result = await f.rpc(method, params);
                if (!replacedLocks) { fs.renameSync(temp, copied); fs.cpSync(copied, temp, { recursive: true }); replacedLocks = true; }
                return result;
            } }), "actor lease identity changed");
            expect(fs.readdirSync(temp)).to.have.length(2); expect(fs.readdirSync(copied)).to.have.length(2);
            fs.rmSync(temp, { recursive: true, force: true }); fs.renameSync(copied, temp);
            for (const key of fs.readdirSync(temp)) session.releaseActor(JSON.parse(fs.readFileSync(path.join(temp, key, "owner.json")))); // explicit disposable recovery
            let drift = false;
            const late = { ...args, rpc: async (method, params) => { const result = await f.rpc(method, params); drift = true; return result; },
                assertInputs: () => { if (drift) throw Error("synthetic late input drift"); } };
            await rejects(() => session.startSession({ ...late, directory: temp, mode: "external-broadcast" }), "late input drift");
            expect(fs.existsSync(filename)).to.equal(false); expect(fs.readdirSync(temp)).to.deep.equal([]);
            await session.startSession({ ...args, directory: temp, mode: "external-broadcast" });
            drift = false;
            await rejects(() => session.prepare(late), "late input drift");
            expect(session.loadSession(filename, f.plan, revision).operations).to.have.length(0);
            const output = path.join(temp, "existing.json"); fs.writeFileSync(output, "do not overwrite");
            await rejects(() => session.prepare({ ...args, output }), "EEXIST");
            expect(fs.readFileSync(output, "utf8")).to.equal("do not overwrite");
            const state = session.loadSession(filename, f.plan, revision); expect(state.operations[0].status).to.equal("handed-off");
            expect(state.locks.every(x => fs.existsSync(x.path))).to.equal(true);
            await rejects(() => session.prepare(args), "Resolve the outstanding");
            const before = fs.readFileSync(filename, "utf8"), retrieved = await session.retrieveHandoff(args), op = state.operations[0];
            expect(retrieved.journalMutated).to.equal(false); expect(fs.readFileSync(filename, "utf8")).to.equal(before);
            expect(retrieved.packet.deploymentId).to.equal(state.deploymentId); expect(retrieved.packet.index).to.equal(0);
            expect(retrieved.packet.intentSha256).to.equal(op.intentSha256); expect(retrieved.packet.envelope).to.deep.equal(op.intent.envelope);
            const { from, ...unsigned } = op.intent.envelope;
            expect(retrieved.packet.unsignedSerialized).to.equal(ethers.Transaction.from(unsigned).unsignedSerialized);
            require("../scripts/authority-cli").writeNew(path.join(temp, "recovered-handoff.json"), retrieved);
        } finally { fs.rmSync(temp, { recursive: true, force: true }); }
    });

});
