// SPDX-License-Identifier: Apache-2.0
const fs = require("fs");
const path = require("path");
const os = require("os");
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { ROOT, NAMES, loadRecord, verifyRecord, expectedBindings } = require("../scripts/mainnet-record");
const { readOnlyRpc } = require("../scripts/mainnet");
const { fixture, evidence } = require("../scripts/fixture");
async function rejects(fn, text) {
    let error;
    try { await fn(); } catch (caught) { error = caught; }
    expect(error, text).to.be.instanceOf(Error);
    expect(error.message).to.include(text);
}
function fixtureRpc(bundle) {
    const { record, compiled, expected } = bundle;
    const bindings = expectedBindings(record);
    const codes = JSON.parse(fs.readFileSync(path.join(ROOT, "runtime-code.json")));
    return async (method, args) => {
        if (method === "eth_chainId") return "0x1";
        if (method === "eth_getBlockByNumber") {
            const number = args[0] === "finalized" ? record.finalizedBlock.number : Number(BigInt(args[0]));
            const hash = number === record.finalizedBlock.number ? record.finalizedBlock.hash :
                record.transactions.find(row => row.blockNumber === number)?.blockHash;
            return { number: ethers.toQuantity(number), hash };
        }
        if (method === "eth_getTransactionByHash" || method === "eth_getTransactionReceipt") {
            const i = record.transactions.findIndex(row => row.hash === args[0]), row = record.transactions[i];
            if (!row) return null;
            const base = { from: row.from, to: row.to, blockHash: row.blockHash, blockNumber: ethers.toQuantity(row.blockNumber) };
            if (method === "eth_getTransactionReceipt") return { ...base, transactionHash: row.hash,
                status: "0x1", contractAddress: row.contractAddress, gasUsed: ethers.toQuantity(row.gasUsed),
                effectiveGasPrice: ethers.toQuantity(row.effectiveGasPrice) };
            return { ...base, hash: row.hash, input: expected[i].data, nonce: ethers.toQuantity(row.nonce),
                chainId: "0x1", value: "0x0", type: ethers.toQuantity(row.type), gas: ethers.toQuantity(row.gasLimit),
                maxFeePerGas: ethers.toQuantity(row.maxFeePerGas), maxPriorityFeePerGas: ethers.toQuantity(row.maxPriorityFeePerGas) };
        }
        const address = method === "eth_call" ? args[0].to : args[0];
        const name = NAMES.find(name => record.contracts[name].address === address);
        if (method === "eth_getCode") return codes[name];
        if (method === "eth_call") {
            const abi = new ethers.Interface(compiled[name].abi), fn = abi.getFunction(args[0].data.slice(0, 10));
            const value = fn.name === "roots" ? ethers.namehash(
                ["alpha.agi.eth", "alpha.agent.agi.eth", "alpha.club.agi.eth"][Number(abi.decodeFunctionData(fn, args[0].data)[0])]
            ) : bindings[name][fn.name];
            return abi.encodeFunctionResult(fn, [value]);
        }
        throw Error(`Unexpected fixture request ${method}`);
    };
}
describe("Recorded Ethereum deployment (offline and read-only)", function () {
    this.timeout(60000);
    it("binds the eleven recorded transactions to exact archived bytecode, sources and gas accounting", () => {
        const bundle = loadRecord();
        expect(bundle.record.transactions).to.have.length(11);
        expect(bundle.record.compiler.version).to.equal("0.8.24+commit.e11b9ed9");
        expect(bundle.record.operationalStatus.newerSettlementHardeningIncluded).to.equal(false);
    });
    it("refuses a modified deployment manifest or compiler input", () => {
        const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "ascension-record-"));
        try {
            fs.cpSync(ROOT, temporary, { recursive: true });
            const file = path.join(temporary, "manifest.json"), content = fs.readFileSync(file);
            fs.appendFileSync(file, " ");
            expect(() => loadRecord(temporary)).to.throw("manifest SHA-256");
            fs.writeFileSync(file, content);
            fs.appendFileSync(path.join(temporary, "compiler-input.json"), " ");
            expect(() => loadRecord(temporary)).to.throw("file compiler-input.json");
        } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
    });
    it("verifies complete finalized receipts and owners without claiming participant commissioning", async () => {
        const bundle = loadRecord(), rpc = fixtureRpc(bundle), methods = [];
        const report = await verifyRecord(bundle, (method, args) => { methods.push(method); return rpc(method, args); });
        expect(report.governanceComplete).to.equal(true);
        expect(report.readyForPublicFunding).to.equal(false);
        expect(report.participantCommissioning).to.equal("not-assessed");
        expect(report.receipts).to.have.length(11);
        expect(methods.every(method => ["eth_chainId", "eth_getBlockByNumber", "eth_getTransactionByHash",
            "eth_getTransactionReceipt", "eth_getCode", "eth_call"].includes(method))).to.equal(true);
    });
    it("rejects wrong chain, non-finality, changed bytecode/ownership and missing or altered receipts", async () => {
        const bundle = loadRecord(), base = fixtureRpc(bundle);
        const cases = [
            ["eth_chainId", () => "0xaa36a7", "chain ID"],
            ["eth_getBlockByNumber", args => args[0] === "finalized" ? { number: "0x1" } : base("eth_getBlockByNumber", args), "not finalized"],
            ["eth_getCode", () => "0x6000", "complete runtime"],
            ["eth_getTransactionReceipt", () => null, "Missing or failed receipt"],
            ["eth_getTransactionReceipt", async args => ({ ...await base("eth_getTransactionReceipt", args), status: "0x0" }), "failed receipt"],
            ["eth_getTransactionByHash", async args => ({ ...await base("eth_getTransactionByHash", args), input: "0x00" }), "transaction input"],
            ["eth_getTransactionByHash", async args => ({ ...await base("eth_getTransactionByHash", args), chainId: "0xaa36a7" }), "transaction chain"],
            ["eth_call", async args => args[0].data === ethers.id("owner()").slice(0, 10) ?
                ethers.AbiCoder.defaultAbiCoder().encode(["address"], [bundle.record.deployer]) : base("eth_call", args), ".owner"],
        ];
        for (const [target, replacement, message] of cases)
            await rejects(() => verifyRecord(bundle, (method, args) => method === target ? replacement(args) : base(method, args)), message);
    });
    it("blocks wallet, send and development mutation methods before transport", async () => {
        const rpc = readOnlyRpc("https://example.invalid/private-key-placeholder");
        for (const method of ["eth_sendRawTransaction", "eth_sendTransaction", "eth_sign", "personal_sign", "hardhat_setCode", "hardhat_impersonateAccount"])
            await rejects(() => rpc(method, []), "Read-only RPC method required");
    });
    it("documents the deployed snapshot's revoked-rejection behavior on an isolated EVM", async () => {
        const contractArtifacts = loadRecord().compiled;
        const f = await fixture({ contractArtifacts });
        const id = await f.post();
        await f.assign(id); await f.deliver(id);
        const before = await f.jobs.stake(f.agent.address);
        await f.jobs.connect(f.validator1).validate(id, evidence, false, evidence);
        await f.access.setAdmission(f.validator1.address, ethers.ZeroHash, 0);
        await f.jobs.connect(f.validator2).validate(id, evidence, false, evidence);
        expect(await f.jobs.stake(f.agent.address)).to.be.lessThan(before);
        expect(await f.jobs.terminal(id)).to.equal(true);
        // Current-source settlement.test.js requires rejection and timeout recovery instead.
    });
});
