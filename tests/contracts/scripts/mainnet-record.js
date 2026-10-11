// SPDX-License-Identifier: Apache-2.0
// Read-only verification of the recorded deployment, independently of newer builds.
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const ethers = require("ethers");
const { readOnlyRpc, ENS, WRAPPER, roots } = require("./mainnet");
const { writeManifest } = require("./deployment");
const ROOT = path.resolve(__dirname, "../../../deployments/ethereum-mainnet/2026-10-11");
const RECORD_SHA256 = "829e61c887ea6127e93570d994a4bf12b88763104b69beed1a7076a634cf6246";
const NAMES = ["AscensionAccess", "NovaSeed", "AscensionRiskOracle", "AscensionJobMarket", "AscensionMark"];
const TOKEN = "0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA";
const sha256 = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
function requireValue(ok, message) {
    if (!ok) { const error = Error(message); error.publicMessage = true; throw error; }
}
function same(actual, expected, label) {
    requireValue(String(actual).toLowerCase() === String(expected).toLowerCase(), `Recorded deployment mismatch: ${label}`);
}
function constructorArguments(record) {
    const a = Object.fromEntries(NAMES.map(name => [name, record.contracts[name].address]));
    const p = record.parameters;
    return [[ENS, WRAPPER, record.governor], [a.AscensionAccess],
        [a.AscensionAccess, a.NovaSeed, p.minimumValidatorStake, p.quorum, p.maximumRiskBps, record.deployer],
        [a.AscensionAccess, a.AscensionRiskOracle, p.minimumAgentStake, record.deployer],
        [a.NovaSeed, a.AscensionAccess, a.AscensionRiskOracle, a.AscensionJobMarket]];
}
function expectedTransactions(record, compiled) {
    const args = constructorArguments(record);
    const rows = NAMES.map((name, i) => ({ from: record.deployer, to: null, nonce: record.startingNonce + i,
        data: ethers.concat([compiled[name].bytecode, new ethers.Interface(compiled[name].abi).encodeDeploy(args[i])]) }));
    for (const [name, method, values] of [
        ["AscensionRiskOracle", "bindMarketplace", [record.contracts.AscensionJobMarket.address]],
        ["AscensionJobMarket", "bindMark", [record.contracts.AscensionMark.address]],
        ["AscensionRiskOracle", "transferOwnership", [record.governor]],
        ["AscensionJobMarket", "transferOwnership", [record.governor]],
        ["AscensionRiskOracle", "acceptOwnership", []],
        ["AscensionJobMarket", "acceptOwnership", []],
    ]) {
        rows.push({ from: rows.length < 9 ? record.deployer : record.governor,
            to: record.contracts[name].address, nonce: record.transactions[rows.length].nonce,
            data: new ethers.Interface(compiled[name].abi).encodeFunctionData(method, values) });
    }
    return rows;
}
function loadRecord(directory = ROOT) {
    const bytes = fs.readFileSync(path.join(directory, "manifest.json"));
    same(sha256(bytes), RECORD_SHA256, "manifest SHA-256");
    const record = JSON.parse(bytes);
    requireValue(record.schema === "agialpha.ethereum-mainnet.deployment-record.v1" && record.chainId === 1,
        "Expected the registered Ethereum mainnet record");
    for (const [name, digest] of Object.entries(record.files)) {
        requireValue(!path.isAbsolute(name) && !name.split(/[\\/]/).includes(".."), "Unsafe evidence path");
        const file = path.join(directory, name);
        requireValue(fs.lstatSync(file).isFile() && !fs.lstatSync(file).isSymbolicLink(), "Evidence must be a regular file");
        same(sha256(fs.readFileSync(file)), digest, `file ${name}`);
    }
    const compiled = JSON.parse(fs.readFileSync(path.join(directory, "compiled-contracts.json")));
    const input = JSON.parse(fs.readFileSync(path.join(directory, "compiler-input.json")));
    requireValue(input.settings.optimizer.enabled && input.settings.optimizer.runs === 200 &&
        input.settings.viaIR === true && input.settings.evmVersion === "paris", "Archived compiler settings differ");
    for (const [name, source] of Object.entries(input.sources)) if (name.startsWith("project/contracts/")) {
        requireValue(source.content === fs.readFileSync(path.join(directory, "sources", name.slice(8)), "utf8"),
            `Archived compiler source differs: ${name}`);
    }
    requireValue(record.transactions.length === 11, "Expected nine deployment and two acceptance transactions");
    const expected = expectedTransactions(record, compiled);
    for (const [i, row] of record.transactions.entries()) {
        same(row.inputHash, ethers.keccak256(expected[i].data), `transaction ${i + 1} input`);
        same(row.from, expected[i].from, `transaction ${i + 1} sender`);
        same(row.to, expected[i].to, `transaction ${i + 1} destination`);
        same(row.value, "0", `transaction ${i + 1} value`);
        same(row.chainId, 1, `transaction ${i + 1} chain`);
        if (i < 9) same(row.nonce, record.startingNonce + i, `transaction ${i + 1} nonce`);
        if (i < 5) same(record.contracts[NAMES[i]].address,
            ethers.getCreateAddress({ from: record.deployer, nonce: row.nonce }), `CREATE ${NAMES[i]}`);
    }
    const total = record.transactions.reduce((cost, row) => cost + BigInt(row.gasUsed) * BigInt(row.effectiveGasPrice), 0n);
    same(record.gasCostETH, ethers.formatEther(total), "total recorded gas cost");
    return { record, compiled, expected };
}
function expectedBindings(record) {
    const a = Object.fromEntries(NAMES.map(name => [name, record.contracts[name].address]));
    const p = record.parameters, ownership = { owner: record.governor, pendingOwner: ethers.ZeroAddress };
    return {
        AscensionAccess: { ...ownership, ens: ENS, wrapper: WRAPPER },
        NovaSeed: { access: a.AscensionAccess },
        AscensionRiskOracle: { ...ownership, access: a.AscensionAccess, seed: a.NovaSeed, token: TOKEN,
            marketplace: a.AscensionJobMarket, minimumStake: p.minimumValidatorStake,
            quorum: p.quorum, maximumRiskBps: p.maximumRiskBps },
        AscensionJobMarket: { ...ownership, access: a.AscensionAccess, oracle: a.AscensionRiskOracle,
            token: TOKEN, mark: a.AscensionMark, minimumStake: p.minimumAgentStake },
        AscensionMark: { seed: a.NovaSeed, access: a.AscensionAccess, oracle: a.AscensionRiskOracle,
            jobs: a.AscensionJobMarket, token: TOKEN },
    };
}
async function verifyRecord(bundle, rpc) {
    const { record, compiled, expected } = bundle;
    same(BigInt(await rpc("eth_chainId", [])), 1n, "chain ID");
    const block = await rpc("eth_getBlockByNumber", ["finalized", false]);
    requireValue(block && BigInt(block.number) >= BigInt(record.finalizedBlock.number), "Recorded deployment is not finalized");
    const tag = block.number, blockNumber = Number(BigInt(tag));
    const anchor = await rpc("eth_getBlockByNumber", [ethers.toQuantity(record.finalizedBlock.number), false]);
    same(anchor?.hash, record.finalizedBlock.hash, "recorded finalized history");
    const receipts = [];
    for (const [i, row] of record.transactions.entries()) {
        const tx = await rpc("eth_getTransactionByHash", [row.hash]);
        const receipt = await rpc("eth_getTransactionReceipt", [row.hash]);
        requireValue(tx && receipt && receipt.status === "0x1", `Missing or failed receipt: step ${i + 1}`);
        requireValue(BigInt(receipt.blockNumber) <= BigInt(tag), `Unfinalized receipt: step ${i + 1}`);
        same(tx.hash, row.hash, "transaction hash"); same(receipt.transactionHash, row.hash, "receipt hash");
        same(tx.from, expected[i].from, "transaction sender"); same(tx.to, expected[i].to, "transaction destination");
        same(tx.input, expected[i].data, "transaction input"); same(BigInt(tx.nonce), BigInt(row.nonce), "nonce");
        same(BigInt(tx.chainId), 1n, "transaction chain"); same(BigInt(tx.value), 0n, "ETH value");
        same(BigInt(tx.type), BigInt(row.type), "transaction type");
        same(BigInt(tx.gas), BigInt(row.gasLimit), "transaction gas limit");
        same(BigInt(tx.maxFeePerGas), BigInt(row.maxFeePerGas), "transaction maximum fee");
        same(BigInt(tx.maxPriorityFeePerGas), BigInt(row.maxPriorityFeePerGas), "transaction priority fee");
        same(tx.blockHash, row.blockHash, "transaction block"); same(receipt.blockHash, row.blockHash, "receipt block");
        same(receipt.contractAddress, row.contractAddress, "created address");
        same(receipt.from, row.from, "receipt sender"); same(receipt.to, row.to, "receipt destination");
        same(BigInt(receipt.blockNumber), BigInt(row.blockNumber), "receipt block number");
        same(BigInt(receipt.gasUsed), BigInt(row.gasUsed), "receipt gas used");
        same(BigInt(receipt.effectiveGasPrice), BigInt(row.effectiveGasPrice), "receipt gas price");
        same((await rpc("eth_getBlockByNumber", [receipt.blockNumber, false]))?.hash, row.blockHash, "canonical receipt");
        receipts.push({ hash: row.hash, label: row.label, blockNumber: row.blockNumber, finalized: true });
    }
    const bindings = expectedBindings(record), observed = {};
    for (const name of NAMES) {
        const contract = record.contracts[name], abi = new ethers.Interface(compiled[name].abi);
        const code = await rpc("eth_getCode", [contract.address, tag]);
        requireValue(code !== "0x", `Missing contract: ${name}`);
        same(ethers.keccak256(code), contract.runtimeCodeHash, `complete runtime ${name}`);
        const getters = {};
        for (const [getter, value] of Object.entries(bindings[name])) {
            const result = await rpc("eth_call", [{ to: contract.address, data: abi.encodeFunctionData(getter) }, tag]);
            getters[getter] = String(abi.decodeFunctionResult(getter, result)[0]);
            same(getters[getter], value, `${name}.${getter}`);
        }
        if (name === "AscensionAccess") for (const [i, root] of roots.entries()) {
            const data = await rpc("eth_call", [{ to: contract.address, data: abi.encodeFunctionData("roots", [i]) }, tag]);
            same(abi.decodeFunctionResult("roots", data)[0], ethers.namehash(root), `ENS role ${i}`);
        }
        observed[name] = { ...contract, getters };
    }
    same((await rpc("eth_getBlockByNumber", [tag, false]))?.hash, block.hash, "finalized block changed during verification");
    return { schema: "agialpha.ethereum-mainnet.record-verification.v1", chainId: 1,
        checkedAt: new Date().toISOString(), block: { number: blockNumber, hash: block.hash },
        manifestSha256: RECORD_SHA256, deploymentTransactionsConfirmed: true, bindingsVerified: true,
        governanceComplete: true, pendingGovernanceActions: [], observed, receipts, externalTransactions: false,
        participantCommissioning: "not-assessed", readyForPublicFunding: false,
        sourceProfile: record.profile, newerSettlementHardeningIncluded: false,
        next: "Read docs/agent/MAINNET_DEPLOYMENT.md before admissions or funding; current source differs from deployed code." };
}
async function main() {
    const [mode, output, extra] = process.argv.slice(2);
    requireValue(!extra && ((mode === "check" && !output) || (mode === "verify" && output)),
        "Usage: mainnet:record-check OR mainnet:record-verify -- /absolute/path/new-report.json");
    const bundle = loadRecord();
    if (mode === "check") {
        console.log(JSON.stringify({ recordIntegrity: true, chainId: 1, transactions: 11,
            manifestSha256: RECORD_SHA256, sourceProfile: bundle.record.profile, externalTransactions: false }));
        return;
    }
    requireValue(!fs.existsSync(output), "Output already exists; choose a new report filename");
    const report = await verifyRecord(bundle, readOnlyRpc(process.env.MAINNET_RPC_URL || ""));
    writeManifest(report, output);
    console.log(JSON.stringify({ output: path.resolve(output), governanceComplete: true,
        finalizedBlock: report.block.number, externalTransactions: false, readyForPublicFunding: false }));
}
module.exports = { ROOT, RECORD_SHA256, NAMES, loadRecord, verifyRecord, expectedBindings, expectedTransactions };
if (require.main === module) main().catch(error => {
    console.error(error.publicMessage ? error.message : "Read-only verification failed. Check the HTTPS RPC, registered evidence and new output path. Provider details are hidden.");
    process.exitCode = 1;
});
