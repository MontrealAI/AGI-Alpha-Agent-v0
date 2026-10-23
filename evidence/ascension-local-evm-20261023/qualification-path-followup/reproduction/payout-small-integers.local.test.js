// SPDX-License-Identifier: Apache-2.0
// Isolated supplemental local test; no production contract or existing test changed.
const { expect } = require("chai");
const { ethers, artifacts } = require("hardhat");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { fixture, evidence, spec, jump } = require("../../scripts/fixture");

const protocolPath = process.env.ASCENSION_SMALL_INTEGER_PROTOCOL;
const outputDirectory = process.env.ASCENSION_SMALL_INTEGER_OUTPUT;
if (!protocolPath || !outputDirectory) throw new Error("Explicit protocol and evidence paths are required");
const bytes = fs.readFileSync(protocolPath);
const protocolHash = crypto.createHash("sha256").update(bytes).digest("hex");
if (protocolHash !== "d72950970e93bec2d8cfd58323c2cb2ca1789e6ea018a44bc8604cb619b57a01") {
    throw new Error("Frozen small-integer protocol changed");
}
const protocol = JSON.parse(bytes);
const json = (value) => JSON.stringify(value, (_, item) => typeof item === "bigint" ? item.toString() : item, 2) + "\n";
const sha = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const blockNumber = async () => Number(BigInt(await ethers.provider.send("eth_blockNumber", [])));

async function observe(record, label, operation) {
    const before = await blockNumber();
    const entry = { label, beforeBlock: before, receipts: [] };
    record.operations.push(entry);
    try {
        entry.value = await operation();
        if (entry.value && typeof entry.value.wait === "function") {
            await entry.value.wait();
            entry.value = entry.value.hash;
        }
    } catch (error) {
        entry.error = { name: error.name, message: error.message, code: error.code ?? null };
    }
    entry.afterBlock = await blockNumber();
    for (let number = before + 1; number <= entry.afterBlock; number++) {
        const block = await ethers.provider.send("eth_getBlockByNumber", [ethers.toQuantity(number), false]);
        for (const hash of block.transactions) {
            entry.receipts.push(await ethers.provider.send("eth_getTransactionReceipt", [hash]));
        }
    }
    return entry;
}

async function success(record, label, operation) {
    const entry = await observe(record, label, operation);
    expect(entry.error, `${label} must succeed`).to.equal(undefined);
    expect(entry.receipts.length, `${label} must mine a transaction`).to.be.greaterThan(0);
    for (const receipt of entry.receipts) expect(BigInt(receipt.status)).to.equal(1n);
    return entry.value;
}

async function snapshot(f, id = null) {
    const addresses = {
        business: f.business.address,
        worker: f.agent.address,
        otherWorker: f.fastAgent.address,
        validator1: f.validator1.address,
        validator2: f.validator2.address,
        validator3: f.validator3.address,
        jobs: f.jobs.target,
        oracle: f.oracle.target,
        mark: f.mark.target,
    };
    const balances = {};
    for (const [name, address] of Object.entries(addresses)) balances[name] = await f.token.balanceOf(address);
    const result = {
        balances,
        supply: await f.token.totalSupply(),
        nextId: await f.jobs.nextId(),
        workerStake: await f.jobs.stake(f.agent.address),
        otherWorkerStake: await f.jobs.stake(f.fastAgent.address),
        workerLocked: await f.jobs.locked(f.agent.address),
        otherWorkerLocked: await f.jobs.locked(f.fastAgent.address),
    };
    if (id !== null) {
        const job = await f.jobs.jobs(id);
        result.job = {
            id, state: job.state, worker: job.worker, bounty: job.bounty, price: job.price,
            refund: job.refund, claimed: job.claimed, resultHash: job.resultHash,
            yes: job.yes, no: job.no,
        };
        result.hasBid = await f.jobs.hasBid(id, f.agent.address);
        result.votes = await Promise.all(f.validators.map((v) => f.jobs.votes(id, v.address)));
    }
    return result;
}

describe("Supplemental Alpha source small-integer payout boundaries (local simulated funds)", function () {
    this.timeout(60000);
    before(function () {
        const production = path.resolve(__dirname, "../../../../contracts/ascension/AscensionJobMarket.sol");
        const mirror = path.resolve(__dirname, "../../contracts/ascension/AscensionJobMarket.sol");
        expect(sha(production)).to.equal(protocol.source.sha256);
        expect(sha(mirror)).to.equal(protocol.source.sha256);
        fs.mkdirSync(outputDirectory, { recursive: true });
    });
    for (const vector of protocol.cases) {
        it(`p=${vector.p}: ${vector.expectedContractOutcome}`, async function () {
            const record = {
                schema: "ascension-small-integer-case/v1",
                startedAt: new Date().toISOString(),
                protocolSha256: protocolHash,
                testSha256: sha(__filename),
                vector,
                scope: protocol.scope,
                operations: [],
            };
            try {
                const p = BigInt(vector.p);
                const each = p / 40n;
                const gross = p - 2n * each;
                const arithmetic = {
                    workerGross: gross,
                    eachValidatorGross: each,
                    workerNet: gross - gross / 100n,
                    eachQualifyingValidatorNet: each - each / 100n,
                    totalBurn: gross / 100n + 2n * (each / 100n),
                };
                record.arithmetic = arithmetic;
                expect(arithmetic.workerNet).to.equal(BigInt(vector.workerNet));
                expect(arithmetic.eachQualifyingValidatorNet).to.equal(BigInt(vector.eachQualifyingValidatorNet));
                expect(arithmetic.totalBurn).to.equal(BigInt(vector.totalBurn));
                const f = await fixture();
                const network = await ethers.provider.getNetwork();
                expect(network.chainId).to.equal(31337n);
                const artifact = await artifacts.readArtifact("AscensionJobMarket");
                expect(artifact.sourceName).to.equal("contracts/ascension/AscensionJobMarket.sol");
                record.localChain = {
                    chainId: network.chainId,
                    metadata: await ethers.provider.send("hardhat_metadata", []),
                    actualJobsAddress: f.jobs.target,
                    actualJobsRuntimeKeccak256: ethers.keccak256(await ethers.provider.getCode(f.jobs.target)),
                    artifactSourceName: artifact.sourceName,
                    sourceSha256: protocol.source.sha256,
                    actors: {
                        business: f.business.address, worker: f.agent.address,
                        validators: f.validators.map((v) => v.address),
                    },
                };
                const smallSpec = { ...spec, bounty: vector.p };
                if (p < 100n) {
                    record.actualOutcome = "post-and-bid-rejected";
                    record.noPayoutOccurred = true;
                    const beforePost = await snapshot(f);
                    const rejectedPost = await observe(record, "post-below-minimum", () =>
                        f.jobs.connect(f.business).post(smallSpec, 60, f.committee, { gasLimit: 2000000 }));
                    expect(rejectedPost.error?.message).to.include("job bounds");
                    const afterPost = await snapshot(f);
                    expect(afterPost).to.deep.equal(beforePost);
                    record.rejectedPostState = { before: beforePost, after: afterPost };
                    const id = await success(record, "post-valid-minimum-for-bid-rejection", () =>
                        f.post({ ...spec, bounty: "100" }));
                    const beforeBid = await snapshot(f, id);
                    const rejectedBid = await observe(record, "bid-below-minimum", () =>
                        f.jobs.connect(f.agent).bid(id, p, 3600, { gasLimit: 2000000 }));
                    expect(rejectedBid.error?.message).to.include("bid bounds");
                    const afterBid = await snapshot(f, id);
                    expect(afterBid).to.deep.equal(beforeBid);
                    record.rejectedBidState = { before: beforeBid, after: afterBid };
                    for (const rejected of [rejectedPost, rejectedBid]) {
                        for (const receipt of rejected.receipts) expect(BigInt(receipt.status)).to.equal(0n);
                    }
                } else {
                    record.actualOutcome = "paid";
                    const initial = await snapshot(f);
                    const id = await success(record, "post", () => f.post(smallSpec));
                    await success(record, "bid", () => f.jobs.connect(f.agent).bid(id, p, 3600));
                    await jump((await f.jobs.jobs(id)).auctionEnd);
                    await success(record, "award", () => f.jobs.award(id));
                    await success(record, "deliver", () => f.deliver(id));
                    const beforePay = await snapshot(f, id);
                    await success(record, "approve-two-distinct-local-validators", () => f.approve(id));
                    const afterPay = await snapshot(f, id);
                    const delta = {};
                    for (const key of ["worker", "validator1", "validator2", "validator3"]) {
                        delta[key] = afterPay.balances[key] - beforePay.balances[key];
                    }
                    delta.burn = beforePay.supply - afterPay.supply;
                    delta.marketReduction = beforePay.balances.jobs - afterPay.balances.jobs;
                    expect(delta.worker).to.equal(BigInt(vector.workerNet));
                    expect(delta.validator1).to.equal(BigInt(vector.eachQualifyingValidatorNet));
                    expect(delta.validator2).to.equal(BigInt(vector.eachQualifyingValidatorNet));
                    expect(delta.validator3).to.equal(0n);
                    expect(delta.burn).to.equal(BigInt(vector.totalBurn));
                    expect(delta.marketReduction).to.equal(p);
                    expect(delta.worker + delta.validator1 + delta.validator2 + delta.validator3 + delta.burn).to.equal(p);
                    expect(initial.balances.business - afterPay.balances.business).to.equal(p);
                    expect(beforePay.balances.business).to.equal(afterPay.balances.business);
                    expect(afterPay.balances.jobs).to.equal(initial.balances.jobs);
                    expect(afterPay.balances.validator3).to.equal(initial.balances.validator3);
                    expect(afterPay.workerStake).to.equal(initial.workerStake);
                    expect(afterPay.workerLocked).to.equal(0n);
                    expect(afterPay.job.state).to.equal(4n);
                    expect(afterPay.job.refund).to.equal(0n);
                    expect(afterPay.job.price).to.equal(p);
                    expect(afterPay.votes).to.deep.equal([1n, 1n, 0n]);
                    const payouts = [];
                    for (const operation of record.operations) {
                        for (const receipt of operation.receipts) {
                            for (const log of receipt.logs) {
                                if (log.address.toLowerCase() !== f.jobs.target.toLowerCase()) continue;
                                const parsed = f.jobs.interface.parseLog(log);
                                if (parsed?.name === "Payout") payouts.push({
                                    transactionHash: receipt.transactionHash,
                                    blockHash: receipt.blockHash,
                                    blockNumber: receipt.blockNumber,
                                    logIndex: log.logIndex,
                                    id: parsed.args[0], recipient: parsed.args[1],
                                    gross: parsed.args[2], burn: parsed.args[3],
                                });
                            }
                        }
                    }
                    expect(payouts.length).to.equal(3);
                    for (const [recipient, recipientGross] of [
                        [f.agent.address, gross], [f.validator1.address, each], [f.validator2.address, each],
                    ]) {
                        const events = payouts.filter((entry) => entry.recipient === recipient);
                        expect(events.length).to.equal(1);
                        expect(events[0].id).to.equal(id);
                        expect(events[0].gross).to.equal(recipientGross);
                        expect(events[0].burn).to.equal(recipientGross / 100n);
                    }
                    record.payoutEvents = payouts;
                    record.balancesAndState = { initial, beforePay, afterPay, delta };
                }
                record.passed = true;
            } catch (error) {
                record.passed = false;
                record.failure = { name: error.name, message: error.message, stack: error.stack };
                throw error;
            } finally {
                record.finishedAt = new Date().toISOString();
                fs.writeFileSync(path.join(outputDirectory, `p-${vector.p}.json`), json(record), { flag: "wx" });
            }
        });
    }
});
