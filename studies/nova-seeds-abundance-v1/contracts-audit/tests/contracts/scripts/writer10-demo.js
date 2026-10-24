// SPDX-License-Identifier: Apache-2.0
const fs = require("fs");
const path = require("path");
const assert = require("assert/strict");
const { performance } = require("perf_hooks");
const { ethers, network } = require("hardhat");
const { fixture, units, now, jump } = require("./fixture");
const { compilePlan } = require("./plan");
const { SignedRegistry, verifyRegistry, sha256 } = require("./writer10-registry");

async function main() {
    if (!process.env.NOVA_LEDGER_PATH) throw Error("NOVA_LEDGER_PATH must identify public or synthetic evidence bytes");
    const input = fs.readFileSync(process.env.NOVA_LEDGER_PATH);
    if (input.length > 20 * 1024 * 1024) throw Error("Evidence file exceeds bounded 20 MiB input");
    JSON.parse(input.toString("utf8"));
    const resultHash = ethers.keccak256(input), resultSha256 = sha256(input);
    const started = performance.now(), cpuStarted = process.cpuUsage();
    const f = await fixture();
    const txs = [], checks = [];
    async function record(label, promise) {
        const tx = await promise, receipt = await tx.wait();
        const events = [];
        for (const log of receipt.logs) {
            for (const c of [f.access, f.seed, f.oracle, f.jobs, f.mark, f.token]) {
                try {
                    const event = c.interface.parseLog(log);
                    if (event) { events.push({address: log.address, name: event.name, args: event.args.toArray().map(x => typeof x === "bigint" ? x.toString() : x)}); break; }
                } catch (_) {}
            }
        }
        txs.push({label, hash: receipt.hash, blockNumber: receipt.blockNumber, gasUsed: receipt.gasUsed.toString(), status: receipt.status, events});
        return receipt;
    }
    async function reject(label, action, reason) {
        let rejected = false, observed = "no rejection";
        try { const value = await action(); if (value && typeof value.wait === "function") await value.wait(); } catch (error) {
            observed = error.message;
            const data = error.data?.data || error.data;
            if (typeof data === "string" && data.startsWith("0x08c379a0")) observed += " " + ethers.AbiCoder.defaultAbiCoder().decode(["string"], "0x" + data.slice(10))[0];
            rejected = observed.includes(reason);
        }
        assert(rejected, `${label}: expected rejection containing ${reason}; observed ${observed}`);
        checks.push({label, passed: true, expected: reason});
    }
    const specs = [
        {goal: "Allocate synthetic calibration-constrained instrument work", successMetric: "Public ledger replay verifies validity, service output and resource accounting", bounty: units("100").toString(), duration: 86400, priceWeight: 6000},
        {goal: "Independently replay disclosed resource ledger", successMetric: "Exact input digest, plan and replay outcomes match the delivered bytes", bounty: units("100").toString(), duration: 86400, priceWeight: 6000}
    ];
    const plan = compilePlan(specs);
    const capsuleHash = ethers.id("Writer 10 public disclosure: no encrypted or confidential input in this local run");
    await record("seal", f.seed.connect(f.business).seal(capsuleHash, plan.planRoot, specs.length, "urn:nova-seeds:writer10:synthetic-evidence", 0, resultHash));
    const id = await f.seed.nextId();
    assert.equal(await f.seed.ownerOf(id), f.business.address);
    assert.equal((await f.seed.genomes(id)).evidenceHash, resultHash);
    await reject("zero_jobs", () => f.seed.connect(f.business).seal(capsuleHash, plan.planRoot, 0, "urn:nova-seeds:test", 0, resultHash), "job bound");
    await reject("129_jobs", () => f.seed.connect(f.business).seal(capsuleHash, plan.planRoot, 129, "urn:nova-seeds:test", 0, resultHash), "job bound");
    await record("open_review", f.oracle.connect(f.business).openReview(id));
    await record("attest_1", f.oracle.connect(f.validator1).attest(id, 1000, true, resultHash));
    assert.equal(await f.oracle.green(id), false);
    await reject("duplicate_attestation", () => f.oracle.connect(f.validator1).attest(id, 1000, true, resultHash), "duplicate vote");
    await record("attest_2", f.oracle.connect(f.validator2).attest(id, 1000, true, resultHash));
    assert.equal(await f.oracle.green(id), true);
    await record("open_funding", f.mark.connect(f.business).open(id, units("2"), units("0.1"), 100, units("200"), (await now()) + 86400, 14 * 86400));
    await record("fund_local", f.mark.connect(f.funder).buy(id, 60, units("297")));
    const nftOwnerBefore = await f.seed.ownerOf(id), nftCountBefore = await f.seed.nextId();
    await record("bloom", f.mark.connect(f.business).bloom(id));
    assert.equal(await f.seed.ownerOf(id), nftOwnerBefore);
    assert.equal(await f.seed.nextId(), nftCountBefore);
    checks.push({label: "bloom_keeps_same_nft", passed: true});
    await reject("buy_after_bloom", () => f.mark.connect(f.funder).buy(id, 1, units("100")), "funding closed");
    await reject("sell_after_bloom", () => f.mark.connect(f.funder).sell(id, 1, 0), "not redeemable");
    const supplyBefore = await f.token.totalSupply();
    for (const item of plan.jobs) {
        await reject(`altered_metric_${item.index}`, () => f.mark.connect(f.business).route(id, item.index, {...item.spec, successMetric: "trust me"}, item.proof, 60, f.committee), "FusionPlan proof");
        await record(`route_${item.index}`, f.mark.connect(f.business).route(id, item.index, item.spec, item.proof, 60, f.committee));
        const jobId = await f.jobs.nextId();
        await reject(`duplicate_route_${item.index}`, () => f.mark.connect(f.business).route(id, item.index, item.spec, item.proof, 60, f.committee), "FusionPlan proof");
        assert.equal(await f.jobs.hashSpec(item.index, item.spec), item.leaf);
        await record(`bid_${item.index}`, f.jobs.connect(f.agent).bid(jobId, units("80"), 3600));
        await jump((await f.jobs.jobs(jobId)).auctionEnd);
        await record(`award_${item.index}`, f.jobs.award(jobId));
        await record(`submit_${item.index}`, f.jobs.connect(f.agent).submit(jobId, resultHash, "urn:nova-seeds:writer10:exact-input-bytes"));
        await reject(`wrong_artifact_${item.index}`, () => f.jobs.connect(f.validator1).validate(jobId, ethers.id("wrong bytes"), true, resultHash), "artifact binding");
        await record(`validate_1_${item.index}`, f.jobs.connect(f.validator1).validate(jobId, resultHash, true, resultHash));
        await record(`validate_2_${item.index}`, f.jobs.connect(f.validator2).validate(jobId, resultHash, true, resultHash));
        assert.equal((await f.jobs.jobs(jobId)).state, 4n);
        await record(`collect_${item.index}`, f.mark.collect(jobId));
        await reject(`duplicate_collect_${item.index}`, () => f.mark.collect(jobId), "not collectible");
    }
    await record("close", f.mark.close(id));
    const beforeReclaim = await f.token.balanceOf(f.funder.address);
    await record("reclaim", f.mark.connect(f.funder).reclaim(id));
    const returned = (await f.token.balanceOf(f.funder.address)) - beforeReclaim;
    assert.equal(returned, units("137"));
    assert.equal(supplyBefore - await f.token.totalSupply(), units("1.6"));
    assert.equal(await f.token.balanceOf(f.mark.target), 0n);
    await record("fresh_successor", f.seed.connect(f.business).seal(capsuleHash, plan.planRoot, specs.length, "urn:nova-seeds:writer10:successor", id, resultHash));
    const successor = await f.seed.nextId();
    assert.equal(await f.oracle.green(successor), false);
    checks.push({label: "successor_requires_fresh_review", passed: true});
    await f.green(successor);
    const fundingEnd = (await now()) + 120;
    await record("deadline_open", f.mark.connect(f.business).open(successor, units("2"), 0, 100, units("100"), fundingEnd, 14 * 86400));
    await record("deadline_fund_local", f.mark.connect(f.funder).buy(successor, 50, units("100")));
    await jump(fundingEnd);
    await reject("bloom_at_funding_deadline", () => f.mark.connect(f.business).bloom(successor), "not funded");
    const registryStart = performance.now();
    const registry = new SignedRegistry();
    const authority = {owner: f.business.address, role: "business", mission: "writer10-synthetic-replay", now: 0, until: 1000};
    const rid = registry.seal({owner: f.business.address, capsuleHash, planRoot: plan.planRoot, evidenceHash: resultHash, parent: 0, jobs: specs.length, metadataURI: "urn:nova-seeds:writer10:synthetic-evidence", authority});
    registry.approve(rid, f.business.address, authority);
    for (const item of plan.jobs) {
        registry.route(rid, item.index, item.spec, item.proof, f.business.address, 1);
        registry.deliver(rid, item.index, resultHash, resultSha256);
        await reject(`offchain_duplicate_route_${item.index}`, () => registry.route(rid, item.index, item.spec, item.proof, f.business.address, 1), "FusionPlan proof");
    }
    const registryMs = performance.now() - registryStart;
    assert(verifyRegistry(registry.events, registry.publicKey));
    const altered = structuredClone(registry.events); altered[0].payload += " ";
    assert.equal(verifyRegistry(altered, registry.publicKey), false);
    const omitted = registry.events.filter((_, i) => i !== 1);
    assert.equal(verifyRegistry(omitted, registry.publicKey), false);
    const prefixAccepted = verifyRegistry(registry.events.slice(0, -1), registry.publicKey);
    assert.equal(prefixAccepted, true);
    checks.push({label: "offchain_tamper_rejected", passed: true}, {label: "offchain_middle_omission_rejected", passed: true}, {label: "unflattering_truncated_prefix_accepted_without_pinned_terminal_checkpoint", passed: true, limitation: true});
    const verifyStart = performance.now();
    for (let i = 0; i < 1000; i++) assert(verifyRegistry(registry.events, registry.publicKey));
    const verify1000Ms = performance.now() - verifyStart;
    let chainGas = 0n, chainTransactions = 0;
    for (let i = 1, end = await ethers.provider.getBlockNumber(); i <= end; i++) {
        const block = await ethers.provider.getBlock(i);
        for (const hash of block.transactions) {
            const r = await ethers.provider.getTransactionReceipt(hash); chainGas += r.gasUsed; chainTransactions++;
        }
    }
    const cpu = process.cpuUsage(cpuStarted);
    const output = {schema: "nova-seeds.writer10.contract-evidence.v1", environment: {scope: "isolated local unforked EVM; simulated tokens and ENS; no live financial action", chainId: (await ethers.provider.getNetwork()).chainId.toString(), network: network.name, node: process.version, solc: require("solc").version(), sourceCommit: "197147ffd22c5ae13113162afffaf3ce9c10aa2e", deployedSourceCompared: "c0fc5217e364a39a4cd123d17a8317c06b80f820"}, input: {filename: path.basename(process.env.NOVA_LEDGER_PATH), bytes: input.length, keccak256: resultHash, sha256: resultSha256}, plan, seed: id.toString(), successor: successor.toString(), checks, transactions: txs, costs: {wallMs: performance.now() - started, cpuUserMs: cpu.user / 1000, cpuSystemMs: cpu.system / 1000, localChainTotalGasIncludingFixturesAndNegativeCases: chainGas.toString(), localChainTransactionCount: chainTransactions, trackedLifecycleGas: txs.reduce((s,t) => s + BigInt(t.gasUsed), 0n).toString(), gasPriceCurrencyConversion: null, liveMoneySpent: 0, humanEffortAndCommercialDemand: "not measured"}, localAccounting: {fundingTokens: "297", twoJobsGrossTokens: "160", burnTokens: "1.6", workerNetTokens: "150.48", reviewersNetTokens: "7.92", principalReturnedTokens: returned.toString(), scaleDecimals: 18}, offchainRegistry: {scope: "equivalent evidence/lineage/route-once interface, not decentralized custody or escrow; same external productive workload bytes", trust: "central operator with independently pinned Ed25519 key; signed prefixes can be withheld; no consensus guarantee", publicKey: registry.publicKey, records: registry.events, sourceBindingMatches: true, registryConstructionMs: registryMs, verify1000Ms, recordBytes: Buffer.byteLength(JSON.stringify(registry.events)), validPrefixAcceptedWithoutPinnedTerminalCheckpoint: prefixAccepted, keyPersistence: "private key generated in memory only and not written"}};
    const out = process.env.NOVA_CONTRACT_OUTPUT || path.join(__dirname, "../evidence/writer10-contract-results.json");
    fs.mkdirSync(path.dirname(out), {recursive: true});
    fs.writeFileSync(out, JSON.stringify(output, null, 2) + "\n");
    console.log(JSON.stringify({out, checks: checks.length, localChainTransactions: chainTransactions, chainGas: chainGas.toString(), sameEvidenceDigest: true}));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
