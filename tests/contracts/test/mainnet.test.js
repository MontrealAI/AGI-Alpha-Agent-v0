// SPDX-License-Identifier: Apache-2.0
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { AGIALPHA_ADDRESS } = require("../../../token.config");
const { validateConfig, compiledContracts, makePlan, checkPlan, inspectChain, verifyLive, readOnlyRpc, ENS, WRAPPER, roots } = require("../scripts/mainnet");
const { installToken } = require("./utils/token");
const clone = value => JSON.parse(JSON.stringify(value));
async function rejects(fn, text) {
    let error;
    try { await fn(); } catch (caught) { error = caught; }
    expect(error, text).to.be.instanceOf(Error);
    expect(error.message).to.include(text);
}
function fixtureConfig() {
    const hash = ethers.id("reviewed test fixture; not mainnet evidence");
    const account = number => ethers.getAddress(`0x${number.toString(16).padStart(40, "0")}`);
    return { schema: "agialpha.mainnet.config.v1", chainId: 1, deployer: account(1), nonce: 0,
        block: { number: 100, hash },
        governor: { address: account(2), codeHash: ethers.keccak256("0x6000"), owners: [account(3), account(4), account(5)], threshold: 2 },
        dependencies: Object.fromEntries(Object.entries({ token: AGIALPHA_ADDRESS, ens: ENS, wrapper: WRAPPER }).map(([key, address]) => [key, { address, codeHash: ethers.keccak256("0x6000") }])),
        rootOwners: Object.fromEntries(roots.map(root => [root, account(6)])),
        parameters: { minimumValidatorStake: ethers.parseEther("10").toString(), minimumAgentStake: ethers.parseEther("10").toString(), quorum: 2, maximumRiskBps: 2000 } };
}
function rpcFixture(c) {
    return async (method, params) => {
        if (method === "eth_chainId") return "0x1";
        if (method === "eth_getBlockByNumber") return { number: "0x64", hash: c.block.hash, timestamp: "0x100" };
        if (method === "eth_getCode") return params[0] === c.deployer ? "0x" : "0x6000";
        if (method === "eth_getTransactionCount") return ethers.toQuantity(c.nonce);
        if (method === "eth_call") {
            const data = params[0].data, coder = ethers.AbiCoder.defaultAbiCoder();
            if (data.startsWith(ethers.id("decimals()").slice(0, 10))) return coder.encode(["uint8"], [18]);
            if (data.startsWith(ethers.id("getOwners()").slice(0, 10))) return coder.encode(["address[]"], [c.governor.owners]);
            if (data.startsWith(ethers.id("getThreshold()").slice(0, 10))) return coder.encode(["uint256"], [c.governor.threshold]);
            if (data.startsWith(ethers.id("owner(bytes32)").slice(0, 10))) return coder.encode(["address"], [c.rootOwners[roots[0]]]);
        }
        throw Error(`Unexpected read ${method}`);
    };
}
describe("Mainnet preparation (unsigned and read-only)", function () {
    this.timeout(60000);
    it("rejects wrong chain, placeholder hashes, noncanonical token and unsafe governance", () => {
        const cases = [c => c.chainId = 31337, c => c.dependencies.token.address = c.deployer,
            c => c.governor.threshold = 1, c => c.nonce = -1, c => c.nonce = 0.5,
            c => c.governor.owners[1] = c.governor.owners[0], c => c.parameters.minimumAgentStake = "1e18",
            c => c.block.hash = ethers.ZeroHash, c => c.governor.address = c.deployer];
        for (const change of cases) { const c = fixtureConfig(); change(c); expect(() => validateConfig(c)).to.throw(); }
    });
    it("checks pinned dependencies, governance, roots and nonce without mutation methods", async () => {
        const c = fixtureConfig(), base = rpcFixture(c), methods = [];
        const report = await inspectChain(c, async (method, args) => { methods.push(method); return base(method, args); });
        expect(report.preflightPassed).to.equal(true);
        expect(report.readyToBroadcast).to.equal(false);
        expect(methods.every(method => method.startsWith("eth_get") || ["eth_chainId", "eth_call"].includes(method))).to.equal(true);
        const cases = [
            ["eth_chainId", () => "0xaa36a7", "Wrong chain"],
            ["eth_getCode", () => "0x6001", "code hash mismatch"],
            ["eth_getTransactionCount", () => "0x1", "nonce changed"],
            ["eth_getBlockByNumber", () => ({ number: "0x64", hash: ethers.id("reorg") }), "block hash mismatch"],
        ];
        for (const [target, replacement, text] of cases)
            await rejects(() => inspectChain(c, (method, args) => method === target ? replacement(args) : base(method, args)), text);
        await rejects(() => inspectChain(c, (method, args) => method === "eth_getBlockByNumber" && args[0] === "finalized" ?
            { number: "0x63", hash: c.block.hash } : base(method, args)), "must be finalized");
        const invalidOwners = clone(c); invalidOwners.governor.owners[0] = c.deployer;
        await rejects(() => inspectChain(invalidOwners, base), "owners/threshold mismatch");
        const invalidRoots = clone(c); invalidRoots.rootOwners[roots[1]] = c.deployer;
        await rejects(() => inspectChain(invalidRoots, base), "root owner mismatch");
        const wrongDecimals = async (method, args) => method === "eth_call" && args[0].to === AGIALPHA_ADDRESS ?
            ethers.AbiCoder.defaultAbiCoder().encode(["uint8"], [6]) : base(method, args);
        await rejects(() => inspectChain(c, wrongDecimals), "decimals");
    });
    it("refuses signing methods before transport and redacts RPC errors", async () => {
        expect(() => readOnlyRpc("http://rpc.example")).to.throw("HTTPS");
        expect(() => readOnlyRpc("https://secret:password@rpc.example")).to.throw("credentials");
        const rpc = readOnlyRpc("https://rpc.example/private-secret");
        await rejects(() => rpc("eth_sendRawTransaction", ["0x"]), "Read-only");
        const previous = global.fetch;
        try {
            global.fetch = async () => { throw Error("private-secret"); };
            await rejects(() => rpc("eth_chainId", []), "URL and provider errors are redacted");
        } finally { global.fetch = previous; }
    });
    it("executes the exact prepared constructor data and governance bindings on an isolated EVM", async () => {
        await ethers.provider.send("hardhat_reset", []);
        const [deployer, governor] = await ethers.getSigners();
        await installToken();
        for (const [name, destination] of [["MockAscensionENS", ENS], ["MockAscensionWrapper", WRAPPER]]) {
            const contract = await (await ethers.getContractFactory(name)).deploy();
            await ethers.provider.send("hardhat_setCode", [destination, await ethers.provider.getCode(contract.target)]);
        }
        const config = fixtureConfig();
        config.deployer = deployer.address; config.governor.address = governor.address;
        config.nonce = await ethers.provider.getTransactionCount(deployer.address);
        const plan = await makePlan(config, compiledContracts(), { commit: "local-test" });
        checkPlan(plan);
        const modified = clone(plan); modified.transactions[0].data = "0x00";
        expect(() => checkPlan(modified)).to.throw("checksum");
        expect(plan.transactions).to.have.length(5);
        expect(plan.governanceCalls).to.have.length(2);
        for (const tx of plan.transactions) {
            const receipt = await (await deployer.sendTransaction({ data: tx.data, nonce: tx.nonce })).wait();
            expect(receipt.contractAddress).to.equal(tx.expectedAddress);
        }
        for (const tx of plan.governanceCalls) await (await governor.sendTransaction({ to: tx.to, data: tx.data })).wait();
        const jobs = await ethers.getContractAt("AscensionJobMarket", plan.addresses.AscensionJobMarket);
        expect(await jobs.owner()).to.equal(governor.address);
        expect(await jobs.mark()).to.equal(plan.addresses.AscensionMark);
        const base = rpcFixture(config);
        // The chain/config adapter is a test fixture; actual runtime and binding reads use the EVM.
        const adapter = async (method, args) => {
            if (method === "eth_getTransactionCount") return ethers.toQuantity(config.nonce + 5);
            if (method === "eth_getCode" && Object.values(plan.addresses).includes(args[0])) return ethers.provider.getCode(args[0]);
            if (method === "eth_call" && Object.values(plan.addresses).includes(args[0].to)) return ethers.provider.call(args[0]);
            return base(method, args);
        };
        const verified = await verifyLive(plan, adapter);
        expect(verified.deploymentVerified).to.equal(true);
        expect(verified.readyForPublicFunding).to.equal(false);
        await ethers.provider.send("hardhat_setCode", [jobs.target, "0x6000"]);
        await rejects(() => verifyLive(plan, adapter), "Runtime bytecode mismatch");
    });
});
