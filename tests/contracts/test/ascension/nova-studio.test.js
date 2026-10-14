// SPDX-License-Identifier: Apache-2.0
const assert = require("node:assert/strict");
const { ethers, network } = require("hardhat");
const { createHash } = require("crypto");
const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { pathToFileURL } = require("url");
const { novaFixture } = require("../../scripts/nova-fixture");
const { spec, units, evidence, now, jump } = require("../../scripts/fixture");
const { requireDisposableLocalNetwork } = require("../../scripts/disposable");

const root = path.resolve(__dirname, "../../../..");
const python = process.env.ALPHA_PYTHON || "python3";
const passphrase = "local integration recovery phrase; never a wallet key";
function rawCID(bytes) {
    const input = Buffer.concat([Buffer.from([1, 0x55, 0x12, 0x20]), createHash("sha256").update(bytes).digest()]);
    const alphabet = "abcdefghijklmnopqrstuvwxyz234567";
    let accumulator = 0, bits = 0, result = "b";
    for (const byte of input) {
        accumulator = (accumulator << 8) | byte; bits += 8;
        while (bits >= 5) { bits -= 5; result += alphabet[(accumulator >>> bits) & 31]; }
    }
    if (bits) result += alphabet[(accumulator << (5 - bits)) & 31];
    return result;
}

async function localBuild(f) {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), "nova-current-source-"));
    const assets = path.join(directory, "assets");
    fs.mkdirSync(assets);
    for (const name of ["ascension", "ascension-wallet", "nova-studio"])
        fs.cpSync(path.join(root, "docs/assets", name), path.join(assets, name), { recursive: true });
    const sourceProfile = path.join(directory, "input-profile.json");
    fs.writeFileSync(sourceProfile, JSON.stringify(f.profile));
    execFileSync(python, [path.join(root, "scripts/build_mark_wallet.py"), "--root", root,
        "--local-profile", sourceProfile, "--local-output", path.join(assets, "ascension-wallet")],
    { cwd: root, encoding: "utf8", timeout: 30000 });
    const profile = JSON.parse(fs.readFileSync(path.join(assets, "ascension-wallet/profile.json"), "utf8"));
    const load = module => import(pathToFileURL(path.join(assets, module)));
    return {
        directory, profile, wallet: await load("ascension-wallet/client.mjs"),
        workflow: await load("nova-studio/workflow.mjs"), packages: await load("nova-studio/package.mjs"),
        storage: await load("nova-studio/storage.mjs"), plan: await load("nova-studio/plan.mjs"),
        protocol: await load("ascension-wallet/protocol.mjs"),
    };
}

async function prepareProject(build, specs = [spec]) {
    const pkg = await build.packages.preparePackage({
        genome: { schema: "agialpha.novaseed.genome.v1", title: "Current-source browser integration", goal: spec.goal },
        plan: build.plan.compilePlan(specs), passphrase,
        evidence: { source: "Local synthetic acceptance fixture; not an independent real-world review", goal: spec.goal },
        profile: build.profile,
    });
    const files = new Map(), requests = [];
    const fetchImpl = async (input, options = {}) => {
        const url = String(input); requests.push({ url, method: options.method || "GET" });
        if (url === "https://uploads.pinata.cloud/v3/files" && options.method === "POST") {
            const file = options.body.get("file"), bytes = Buffer.from(await file.arrayBuffer()), cid = rawCID(bytes);
            files.set(cid, bytes);
            return new Response(JSON.stringify({ data: { cid } }), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        const cid = new URL(url).pathname.split("/").at(-1);
        const bytes = files.get(cid);
        return new Response(bytes || "Missing artifact", { status: bytes ? 200 : 404, headers: { "Content-Type": "application/json" } });
    };
    const adapter = new build.storage.PinataStorage({ token: "local-fixture-only", fetchImpl });
    const publication = await build.storage.publishPackage(pkg, {
        adapter, name: "Nova exact-source acceptance", description: "Public synthetic fixture evidence", disclosureAccepted: true,
    });
    const kit = await build.packages.createRecoveryKit(pkg, { publication, disclosureAccepted: true });
    assert.equal(requests.filter(request => request.method === "POST").length, 3);
    assert.equal(JSON.stringify(kit).includes(passphrase), false);
    return { pkg, publication, kit, adapter, files, requests };
}

function nativeDelivery(directory, plan) {
    const code = `
import json,sys
from pathlib import Path
from alpha_factory_v1.core.runtime.ascension import delivery,verify_delivery
from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.models import Mission
from alpha_factory_v1.core.runtime.store import Journal,digest
plan=json.load(sys.stdin)
mission=Mission.model_validate({"goal":plan["jobs"][0]["spec"]["goal"],"work":{"kind":"allocation","budget":10,"items":[{"id":"one","cost":3,"value":8},{"id":"two","cost":7,"value":10}]}})
journal=Journal.initialize(Path(sys.argv[1])/"native-state")
engine=Engine(journal)
record=engine.execute(journal.submit(mission)["id"])
assert record["state"]=="review" and record["result"]["value"]==18
engine.review(record["id"],record["revision"],digest(record["result"]),True,"Local synthetic fixture review recomputed both items; not an independent real-world reviewer.")
data=delivery(journal,plan,0,record["id"])
verified=verify_delivery(data,journal.public,plan["planRoot"])
print(json.dumps({"text":data.decode("utf-8"),"publicKey":journal.public,"verified":verified}))
`;
    return JSON.parse(execFileSync(python, ["-c", code, directory], {
        cwd: root, env: { ...process.env, PYTHONPATH: root, NO_DISCLAIMER: "1" },
        input: JSON.stringify(plan), encoding: "utf8", timeout: 30000, stdio: ["pipe", "pipe", "pipe"],
    }));
}

describe("Nova Studio: production workflow on a real disposable current-source EVM", function () {
    this.timeout(180000);
    let f, build, project, actors;
    beforeEach(async () => {
        f = await novaFixture(); build = await localBuild(f); project = await prepareProject(build); actors = new Map();
    });
    afterEach(() => { if (build?.directory) fs.rmSync(build.directory, { recursive: true, force: true }); });

    async function actor(name, seedId = null, jobId = null) {
        if (!actors.has(name)) {
            const provider = f.provider(name), client = new build.wallet.MarkClient(build.profile);
            client.select(provider); await client.connect();
            const flow = new build.workflow.NovaWorkflow(client);
            await flow.setPackage(project.pkg, { publication: project.publication, adapter: project.adapter,
                recoveryExported: true, parent: "0" });
            actors.set(name, { provider, client, flow });
        }
        const result = actors.get(name);
        if (seedId !== null) await result.flow.refresh(String(seedId), jobId === null ? null : String(jobId));
        return result;
    }
    async function send(name, action, values = {}, seedId = null, jobId = null) {
        const a = await actor(name, seedId, jobId);
        const preview = await a.flow.prepare(action, values);
        assert.equal(preview.transaction.value, "0x0");
        const hash = await a.flow.confirm(true);
        await a.flow.reconcile(hash);
        assert.equal(a.client.pending.status, "finalized");
        return { ...a, hash, preview };
    }
    async function mint() {
        const sent = await send("business", "mint");
        const receipt = await ethers.provider.getTransactionReceipt(sent.hash);
        const event = receipt.logs.filter(log => log.address.toLowerCase() === f.seed.target.toLowerCase())
            .map(log => { try { return f.seed.interface.parseLog(log); } catch { return null; } })
            .find(log => log?.name === "SeedSealed");
        assert.ok(event); const id = event.args.seedId;
        assert.equal(sent.preview.transaction.to.toLowerCase(), f.seed.target.toLowerCase());
        const genome = await f.seed.genomes(id);
        assert.equal(genome.capsuleHash, project.pkg.commitments.capsuleHash);
        assert.equal(genome.planRoot, project.pkg.plan.planRoot);
        assert.equal(genome.jobs, BigInt(project.pkg.plan.jobs.length));
        assert.equal(genome.evidenceHash, project.pkg.commitments.evidenceHash);
        assert.equal(await f.seed.tokenURI(id), project.publication.metadataURI);
        assert.equal(sent.flow.state.seedId, String(id));
        assert.equal(sent.flow.state.observation.phase, "none");
        assert.equal(sent.flow.state.runtime.status, "not-connected");
        return id;
    }
    async function green(id) {
        await send("business", "request-review", {}, id);
        for (const name of ["validator1", "validator2"])
            await send(name, "risk-approve", { riskBps: "1000", approved: true, evidenceHash: evidence }, id);
        assert.equal(await f.oracle.green(id), true);
    }
    async function fund(id) {
        await send("business", "campaign", {
            base: "2", slope: "0.1", maxLots: "100", target: "100",
            fundingEnd: String(await now() + 86400), duration: String(14 * 86400),
        }, id);
        await f.token.connect(f.funder).approve(f.mark.target, 0);
        await send("funder", "approve", { spender: "Mark", amount: "158" }, id);
        assert.equal(await f.token.allowance(f.funder.address, f.mark.target), units("158"));
        await send("funder", "fund", { lots: "40", maxCost: "158" }, id);
        assert.equal(await f.token.allowance(f.funder.address, f.mark.target), 0n);
        assert.equal((await f.mark.campaigns(id)).reserve, units("158"));
    }
    async function route(index = 0) {
        const id = await mint(); await green(id); await fund(id);
        await send("business", "activate", {}, id);
        assert.equal((await f.mark.campaigns(id)).phase, 2n);
        const sent = await send("business", "route", { index, auctionSeconds: "60", reviewers: f.committee }, id);
        const receipt = await ethers.provider.getTransactionReceipt(sent.hash);
        const event = receipt.logs.filter(log => log.address.toLowerCase() === f.mark.target.toLowerCase())
            .map(log => { try { return f.mark.interface.parseLog(log); } catch { return null; } })
            .find(log => log?.name === "MissionRouted");
        assert.ok(event); const jobId = event.args.jobId;
        assert.equal(event.args.index, BigInt(index));
        assert.equal(await f.mark.jobSeed(jobId), id);
        assert.equal((await f.jobs.jobs(jobId)).client, f.mark.target);
        assert.equal((await f.jobs.jobs(jobId)).business, f.business.address);
        assert.equal((await f.mark.campaigns(id)).reserve, units("58"));
        assert.equal(sent.flow.state.route.jobId, String(jobId));
        assert.equal(sent.flow.state.observation.job.stage, "posted");
        assert.equal(sent.flow.state.runtime.status, "not-connected");
        return { id, jobId };
    }
    async function award(id, jobId) {
        await send("agent", "bid", [String(jobId), "80", "3600"], id, jobId);
        await jump((await f.jobs.jobs(jobId)).auctionEnd);
        await send("business", "award", [String(jobId)], id, jobId);
        assert.equal((await f.jobs.jobs(jobId)).worker, f.agent.address);
    }
    async function exit(id, jobId, expected) {
        await send("business", "collect", [String(jobId)], id, jobId);
        await send("business", "close", [String(id)], id, jobId);
        const before = await f.token.balanceOf(f.funder.address);
        await send("funder", "reclaim", [String(id)], id, jobId);
        assert.equal(await f.token.balanceOf(f.funder.address) - before, units(expected));
        assert.equal((await f.mark.campaigns(id)).reserve, 0n);
        assert.equal(await f.mark.lots(id, f.funder.address), 0n);
    }

    it("mints with zero token allowance, verifies IDs and settles every accepted payout and exit", async () => {
        for (const target of [f.mark, f.jobs, f.oracle]) await f.token.connect(f.business).approve(target.target, 0);
        const { id, jobId } = await route();
        await assert.rejects((await actor("business", id)).flow.prepare("route", {
            index: 0, auctionSeconds: "60", reviewers: f.committee,
        }));
        await award(id, jobId);
        const native = nativeDelivery(build.directory, project.pkg.plan), agent = await actor("agent", id, jobId);
        const business = await actor("business", id, jobId);
        await agent.flow.openRouteReceipt(business.flow.state.route.hash);
        const timestamp = native.text.match(/"time_ns":([0-9]+)/);
        assert.ok(timestamp && BigInt(timestamp[1]) > BigInt(Number.MAX_SAFE_INTEGER));
        await assert.rejects(agent.flow.importDelivery(native.text, { trustedPublicKey: "00".repeat(32) }), /signer|trusted/i);
        const rounded = JSON.stringify(JSON.parse(native.text));
        assert.notEqual(rounded, native.text);
        await assert.rejects(agent.flow.importDelivery(rounded, { trustedPublicKey: native.publicKey }), /signature|format/i);
        const delivery = await agent.flow.importDelivery(native.text, { trustedPublicKey: native.publicKey });
        const resultHash = ethers.keccak256(ethers.toUtf8Bytes(native.text));
        assert.equal(delivery.resultHash, resultHash); assert.equal(native.verified.resultHash, resultHash);
        assert.equal(delivery.signatureVerified, true); assert.equal(delivery.connected, false);
        await send("agent", "submit", [String(jobId), resultHash, `ipfs://${rawCID(Buffer.from(native.text))}`], id, jobId);
        const supply = await f.token.totalSupply(), worker = await f.token.balanceOf(f.agent.address);
        for (const name of ["validator1", "validator2"])
            await send(name, "validate", [String(jobId), resultHash, "true", evidence], id, jobId);
        assert.equal((await f.jobs.jobs(jobId)).state, 4n);
        assert.equal(supply - await f.token.totalSupply(), units("0.8"));
        assert.equal(await f.token.balanceOf(f.agent.address) - worker, units("75.24"));
        assert.equal(await f.jobs.locked(f.agent.address), 0n);
        await exit(id, jobId, "78");
        assert.equal(await f.token.balanceOf(f.mark.target), 0n);
        for (const name of ["validator1", "validator2", "validator3"])
            assert.equal(await f.oracle.activeJobs(f[name].address), 0n);
    });

    for (const outcome of ["rejected", "delivery-timeout", "missing-review"]) {
        it(`reconciles ${outcome} accounting and the actual permitted MARK recovery`, async () => {
            const { id, jobId } = await route(); await award(id, jobId);
            const stake = await f.jobs.stake(f.agent.address), supply = await f.token.totalSupply();
            if (outcome !== "delivery-timeout")
                await send("agent", "submit", [String(jobId), evidence, "ipfs://bafkreilocalresultfixture"], id, jobId);
            if (outcome === "rejected") {
                for (const name of ["validator1", "validator2"])
                    await send(name, "validate", [String(jobId), evidence, "false", evidence], id, jobId);
            } else {
                const job = await f.jobs.jobs(jobId);
                await jump((outcome === "delivery-timeout" ? job.due : job.reviewEnd) + 1n);
                await send("business", "timeout", [String(jobId)], id, jobId);
            }
            const slash = outcome !== "missing-review";
            assert.equal((await f.jobs.jobs(jobId)).state, slash ? 5n : 6n);
            assert.equal(stake - await f.jobs.stake(f.agent.address), slash ? units("10") : 0n);
            assert.equal(supply - await f.token.totalSupply(), slash ? units("0.1") : 0n);
            await exit(id, jobId, slash ? "167.9" : "158");
        });
    }

    it("preserves an actual broadcast with a lost wallet response across a fresh client and portable kit", async () => {
        const a = await actor("business");
        a.provider.mode = "lose-response";
        await a.flow.prepare("mint", {});
        await assert.rejects(a.flow.confirm(true), /unknown/i);
        assert.equal(a.client.pending.status, "submission-unknown");
        assert.equal(await f.seed.nextId(), 1n);
        await f.createSeed();
        assert.equal(await f.seed.nextId(), 2n);
        await assert.rejects(a.flow.prepare("mint", {}), /outstanding|pending|reconcile/i);
        const kit = await build.packages.createRecoveryKit(project.pkg, {
            publication: project.publication, journal: a.client.journal(), disclosureAccepted: true,
        });
        const restored = await build.packages.restoreRecoveryKit(JSON.stringify(kit), { passphrase });
        const client = new build.wallet.MarkClient(build.profile);
        client.select(a.provider); await client.connect();
        const flow = new build.workflow.NovaWorkflow(client);
        await flow.setPackage(restored.package, { publication: restored.publication, adapter: project.adapter,
            recoveryExported: true, parent: "0" });
        client.restore(restored.journal);
        await flow.reconcile(a.provider.lastHash);
        assert.equal(client.pending.status, "finalized");
        assert.equal(flow.state.seedId, "1");
        assert.equal(a.provider.sends.length, 1);
        assert.equal(await f.seed.nextId(), 2n);
        assert.equal(JSON.stringify(kit).includes(passphrase), false);
    });

    it("approval interruption resumes without inventing funding or spending twice", async () => {
        const id = await mint(); await green(id);
        await send("business", "campaign", { base: "2", slope: "0.1", maxLots: "100", target: "100",
            fundingEnd: String(await now() + 86400), duration: String(14 * 86400) }, id);
        await f.token.connect(f.funder).approve(f.mark.target, 0);
        const a = await send("funder", "approve", { spender: "Mark", amount: "158" }, id);
        a.provider.mode = "reject";
        await a.flow.prepare("fund", { lots: "40", maxCost: "158" });
        await assert.rejects(a.flow.confirm(true), /reject/i);
        assert.equal((await f.mark.campaigns(id)).reserve, 0n);
        assert.equal(await f.token.allowance(f.funder.address, f.mark.target), units("158"));
        a.provider.mode = "normal";
        await send("funder", "fund", { lots: "40", maxCost: "158" }, id);
        assert.equal((await f.mark.campaigns(id)).reserve, units("158"));
        assert.equal(await f.token.allowance(f.funder.address, f.mark.target), 0n);
    });

    it("allows funding exits after real admission revocation and review expiry", async () => {
        const id = await mint(); await green(id); await fund(id);
        await f.access.setAdmission(f.funder.address, ethers.ZeroHash, 0);
        await jump((await f.oracle.rounds(id)).until + 1n);
        assert.equal(await f.oracle.green(id), false);
        const before = await f.token.balanceOf(f.funder.address);
        await send("funder", "sell", [String(id), "40", "158"], id);
        assert.equal(await f.token.balanceOf(f.funder.address) - before, units("158"));
        assert.equal(await f.mark.lots(id, f.funder.address), 0n);
        await send("business", "close", [String(id)], id);
    });

    it("detects an actual disappearing receipt after a local reorganization and keeps the resend barrier", async () => {
        await requireDisposableLocalNetwork();
        const snapshot = await network.provider.request({ method: "evm_snapshot", params: [] });
        const a = await actor("business");
        await a.flow.prepare("mint", {});
        const hash = await a.flow.confirm(true); await a.flow.reconcile(hash);
        assert.equal(a.client.pending.status, "finalized");
        await network.provider.request({ method: "evm_revert", params: [snapshot] });
        const result = await a.flow.reconcile(hash);
        assert.equal(result.status, "pending-or-replaced");
        await assert.rejects(a.flow.prepare("mint", {}), /outstanding|pending|reconcile/i);
        assert.notEqual(a.flow.state.steps.find(step => step.id === "mint").status, "done");
        assert.equal(a.flow.state.runtime.status, "not-connected");
        assert.equal(a.provider.sends.length, 1);
    });

    it("never authorizes a foreign job under the selected project's review and recovery context", async () => {
        const { id, jobId } = await route(), foreign = await f.post();
        const a = await actor("agent", id, jobId), sent = a.provider.sends.length;
        await assert.rejects(a.flow.prepare("bid", [String(foreign), "80", "3600"]), /job|context|project|selected/i);
        assert.equal(a.provider.sends.length, sent);
        assert.equal(await f.jobs.bidCount(foreign), 0n);
    });

    it("binds an odd-tree nonzero routed index even when separate jobs have identical specifications", async () => {
        project = await prepareProject(build, [{ ...spec }, { ...spec }, { ...spec }]);
        const { id, jobId } = await route(2), a = await actor("business", id, jobId);
        const work = a.flow.workPackage(2);
        assert.equal(work.planIndex, 2);
        assert.equal(work.seedId, String(id)); assert.equal(work.jobId, String(jobId));
        assert.equal(work.leaf, project.pkg.plan.jobs[2].leaf);
        assert.equal(work.marketSpecHash, project.pkg.plan.jobs[0].leaf);
        assert.equal(work.runtime.status, "not-connected");
        assert.throws(() => a.flow.workPackage(0), /receipt|index|route|MissionRouted/i);
        assert.equal(await f.mark.posted(id, 2), true);
        assert.equal(await f.mark.posted(id, 0), false);
    });

    it("requires semantic mint reconciliation after missing logs and ignores a foreign emitter", async () => {
        const a = await actor("business");
        await a.flow.prepare("mint", {}); const hash = await a.flow.confirm(true);
        const request = a.provider.request.bind(a.provider);
        let hide = true;
        a.provider.request = async args => {
            const result = await request(args);
            if (args.method !== "eth_getTransactionReceipt" || !result) return result;
            const receipt = structuredClone(result);
            const event = receipt.logs.find(log => log.topics[0] === build.protocol.EVENTS.SeedSealed.topic);
            const foreign = { ...event, address: f.oracle.target };
            receipt.logs = [foreign, ...receipt.logs.filter(log => !hide || log !== event)];
            return receipt;
        };
        await assert.rejects(a.flow.reconcile(hash), /SeedSealed|matching event/i);
        assert.equal(build.wallet.unresolved(a.client.pending), true);
        const saved = JSON.parse(JSON.stringify(a.client.journal()));
        const restored = new build.wallet.MarkClient(build.profile); restored.restore(saved);
        assert.equal(build.wallet.unresolved(restored.pending), true);
        await assert.rejects(a.flow.prepare("mint", {}), /outstanding|pending|reconcile/i);
        hide = false;
        await a.flow.reconcile(hash);
        assert.equal(a.flow.state.seedId, "1");
        assert.equal(a.provider.sends.length, 1);
        assert.equal(await f.seed.nextId(), 1n);
    });

    it("invalidates a prepared mint after a real provider/account change without any wallet send", async () => {
        const a = await actor("business"); await a.flow.prepare("mint", {});
        const changed = f.provider("outsider"); a.client.select(changed); await a.client.connect();
        await assert.rejects(a.flow.confirm(true), /Prepare|confirm|changed/i);
        assert.equal(a.provider.sends.length, 0); assert.equal(changed.sends.length, 0);
        assert.equal(await f.seed.nextId(), 0n);
        const wrongProfile = structuredClone(build.profile); wrongProfile.contracts.Seed.address = f.outsider.address;
        assert.throws(() => new build.wallet.MarkClient(wrongProfile), /profile|deployment|qualification/i);
    });

    it("reconciles an actual same-nonce cancellation without reporting the original mint as completed", async () => {
        await requireDisposableLocalNetwork();
        const a = await actor("business"); await a.flow.prepare("mint", {});
        await network.provider.request({ method: "evm_setAutomine", params: [false] });
        try {
            const originalHash = await a.flow.confirm(true);
            const original = await network.provider.request({ method: "eth_getTransactionByHash", params: [originalHash] });
            const replacement = {
                from: f.business.address, to: f.business.address, nonce: original.nonce, gas: "0x5208", value: "0x0", data: "0x",
                maxFeePerGas: ethers.toQuantity(BigInt(original.maxFeePerGas) * 2n + 1n),
                maxPriorityFeePerGas: ethers.toQuantity(BigInt(original.maxPriorityFeePerGas) * 2n + 1n),
            };
            const hash = await network.provider.request({ method: "eth_sendTransaction", params: [replacement] });
            await network.provider.request({ method: "evm_mine", params: [] });
            const reconciled = await a.flow.reconcile(hash);
            assert.equal(reconciled.status, "cancelled");
            assert.equal(await f.seed.nextId(), 0n);
            assert.equal(a.flow.state.seedId, null);
            assert.equal(a.provider.sends.length, 1);
        } finally {
            await network.provider.request({ method: "evm_setAutomine", params: [true] });
        }
    });
});
