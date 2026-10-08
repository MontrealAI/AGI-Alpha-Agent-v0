// SPDX-License-Identifier: Apache-2.0
const { expect } = require("chai");
const { ethers, network } = require("hardhat");
const { spawn } = require("child_process");
const readline = require("readline");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { fixture, spec, jump } = require("../../scripts/fixture");
const { requireDisposableLocalNetwork } = require("../../scripts/disposable");
const root = path.resolve(__dirname, "../../../..");
const python = process.env.ALPHA_PYTHON || "python3";
const script = `
import json,sys
from pathlib import Path
from datetime import datetime,timezone
from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor.ascension import MarketContext,MarketReader,seal_terms,bind_assignment,bind_delivery,import_settlement
from alpha_factory_v1.core.runtime.successor.protocol import JobContract,ExecutionAuthorization
source=json.loads(sys.stdin.readline())
def rpc(method,params):
    print(json.dumps({"rpc":method,"params":params}),flush=True)
    response=json.loads(sys.stdin.readline())
    if "error" in response: raise ValueError(response["error"])
    return response["result"]
journal=Journal(source["home"]) if Path(source["home"]).exists() else Journal.initialize(source["home"])
reader=MarketReader(MarketContext.model_validate(source["context"]),rpc)
if source["operation"]=="seal":
    contract=JobContract(job_id="evaluation-report",institution_id="institution",mission_id="bounded-mission",family="verification",worker=None,acceptance_owner="local-customer",goal=source["spec"]["goal"],release_digest="a"*64,environment_digest="b"*64,valid_until="2099-01-01T00:00:00Z",outputs={"report":"evaluation"},resources={"calls":1})
    result=seal_terms(journal,contract,source["spec"],reader,plan=source.get("plan"),index=source.get("index"))
elif source["operation"]=="bind":
    auth=ExecutionAuthorization(authorization_id="local-authorization",acting_identity=source["worker"].lower(),job_terms_digest=source["seal"]["body"]["job_terms_digest"],release_digest="a"*64,environment_digest="b"*64,capabilities=["evaluate"],reservation_id="bounded-reservation",expires_at=datetime.fromtimestamp(source["due"],timezone.utc).isoformat().replace("+00:00","Z"))
    binding=bind_assignment(journal,source["seal"],reader,market_job_id=source["job"],posting_tx=source["posting"],assignment_tx=source["assignment"],execution_authorization=auth.model_dump(mode="json"))
    artifact=source["artifact"].encode()
    result={"binding":binding,"delivery":bind_delivery(journal,binding,artifact,candidate_verdict="FAIL")}
else:
    result=import_settlement(journal,source["binding"],source["delivery"],source["artifact"].encode(),reader,settlement_tx=source["settlement"])
print(json.dumps({"result":result}),flush=True)
`;

function nativeRPC(input) {
    return new Promise((resolve, reject) => {
        const child = spawn(python, ["-u", "-c", script], {
            cwd: root, env: { ...process.env, PYTHONPATH: root, NO_DISCLAIMER: "1" },
            stdio: ["pipe", "pipe", "pipe"],
        });
        let result, stderr = "", failure;
        const timer = setTimeout(() => { child.kill(); reject(Error("Native RPC bridge timeout")); }, 60000);
        child.stdin.write(JSON.stringify(input) + "\n");
        child.stderr.on("data", data => { stderr += data; });
        const lines = readline.createInterface({ input: child.stdout });
        lines.on("line", async line => {
            try {
                const message = JSON.parse(line);
                if (message.rpc) {
                    if (!new Set(["eth_call", "eth_chainId", "eth_getCode", "eth_getBlockByNumber", "eth_getTransactionReceipt", "eth_getLogs"]).has(message.rpc))
                        throw Error("Native adapter attempted a mutating RPC");
                    child.stdin.write(JSON.stringify({ result: await ethers.provider.send(message.rpc, message.params) }) + "\n");
                } else result = message.result;
            } catch (error) {
                failure = error;
                child.stdin.write(JSON.stringify({ error: String(error) }) + "\n");
            }
        });
        child.on("error", error => { clearTimeout(timer); reject(error); });
        child.on("exit", code => {
            clearTimeout(timer);
            if (failure || code !== 0 || result === undefined) reject(failure || Error(stderr));
            else resolve(result);
        });
    });
}

function retainEvidence(name, data) {
    if (!process.env.SUCCESSOR_EVM_EVIDENCE_DIR) return;
    const directory = path.resolve(process.env.SUCCESSOR_EVM_EVIDENCE_DIR);
    fs.mkdirSync(directory, { recursive: true });
    fs.writeFileSync(path.join(directory, name + ".json"), JSON.stringify({
        evidence_scope: "disposable-local-fixture", execution: "actual in-process Hardhat and Python adapter",
        external_verifier_independence: false, production_authority: false, ...data,
    }, null, 2) + "\n", { flag: "wx" });
}

async function context(f, seed) {
    return {
        schema_version: 1, chain_id: (await ethers.provider.getNetwork()).chainId.toString(),
        market: f.jobs.target.toLowerCase(), market_code_hash: ethers.keccak256(await ethers.provider.getCode(f.jobs.target)),
        token_code_hash: ethers.keccak256(await ethers.provider.getCode(f.token.target)),
        protocol: "agialpha.ascension.v1", scope: "disposable-local-fixture", confirmations: 1,
        mark: f.mark.target.toLowerCase(), mark_code_hash: ethers.keccak256(await ethers.provider.getCode(f.mark.target)),
        seed: f.seed.target.toLowerCase(), seed_code_hash: ethers.keccak256(await ethers.provider.getCode(f.seed.target)), seed_id: seed.toString(),
    };
}

async function assigned(f, planIndex, plan, id, base, artifact) {
    const seal = await nativeRPC({ ...base, operation: "seal", spec, plan, index: planIndex });
    expect(seal.body.plan_binding.indexed_leaf).to.equal(await f.jobs.hashSpec(planIndex, spec));
    expect(seal.body.market_spec_hash).to.equal(await f.jobs.hashSpec(0, spec));
    const posting = await (await f.mark.connect(f.business).route(id, planIndex, spec, plan.jobs[planIndex].proof, 60, f.committee)).wait();
    const job = await f.jobs.nextId();
    await f.jobs.connect(f.agent).bid(job, ethers.parseEther("80"), 3600);
    await jump((await f.jobs.jobs(job)).auctionEnd);
    const assignment = await (await f.jobs.award(job)).wait();
    const bound = await nativeRPC({ ...base, operation: "bind", seal, job: job.toString(), worker: f.agent.address, due: Number((await f.jobs.jobs(job)).due), posting: posting.hash, assignment: assignment.hash, artifact });
    const resultHash = ethers.keccak256(ethers.toUtf8Bytes(artifact));
    expect(bound.delivery.body.artifact_keccak256).to.equal(resultHash);
    await f.deliver(job, resultHash);
    return { seal, job, bound, resultHash };
}

describe("SUCCESSOR: exact Ascension adapter and honest local settlement", function () {
    this.timeout(180000);
    it("refuses fixture/reset authority for URL-backed or forked providers regardless of chain ID", async () => {
        for (const change of [{ url: "http://127.0.0.1:8545" }, { forking: { url: "http://127.0.0.1:8545" } }]) {
            const key = Object.keys(change)[0], original = network.config[key];
            try {
                network.config[key] = change[key];
                let refusal;
                try { await requireDisposableLocalNetwork(); } catch (error) { refusal = String(error); }
                expect(refusal).to.include("in-process, unforked Hardhat");
            } finally {
                if (original === undefined) delete network.config[key];
                else network.config[key] = original;
            }
        }
    });
    it("accepts and pays a correct FAIL report at nonzero plan index without admitting the candidate", async () => {
        await requireDisposableLocalNetwork();
        const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "successor-ascension-"));
        try {
            const f = await fixture();
            const { id, plan } = await f.campaign([spec, spec]);
            const base = { home: path.join(temporary, "state"), context: await context(f, id) };
            const evaluationInput = [7, 11], expected = 18;
            const candidateResult = evaluationInput[0] - evaluationInput[1];
            const artifact = JSON.stringify({
                candidateVerdict: candidateResult === expected ? "PASS" : "FAIL",
                evaluationInput, expected, candidateResult, correctnessFailures: Number(candidateResult !== expected),
                scope: "actual bounded arithmetic evaluation; local-fixture settlement",
            });
            const { seal, job, bound, resultHash } = await assigned(f, 1, plan, id, base, artifact);
            expect(seal.body.plan_binding.indexed_leaf).not.to.equal(seal.body.market_spec_hash);
            const before = await f.token.totalSupply();
            await f.jobs.connect(f.validators[0]).validate(job, resultHash, true, ethers.id("local reviewer accepted correct negative evaluation"));
            const settled = await (await f.jobs.connect(f.validators[1]).validate(job, resultHash, true, ethers.id("second local review accepted exact FAIL report"))).wait();
            const request = { ...base, ...bound, operation: "import", artifact, settlement: settled.hash };
            const receipt = await nativeRPC(request);
            expect(receipt.job_acceptance).to.equal("accepted");
            expect(receipt.candidate_verdict).to.equal("FAIL");
            expect(receipt.settlement_status).to.equal("paid");
            expect(receipt.institutional_admission).to.equal("not_granted");
            expect(receipt.authority_status).to.equal("not_granted");
            expect(receipt.memory_admission).to.equal("not_granted");
            expect(receipt.customer_realized_value).to.equal(null);
            expect(receipt.reviews).to.have.length(2);
            expect(before - await f.token.totalSupply()).to.equal(ethers.parseEther("0.8"));
            expect(await nativeRPC(request)).to.deep.equal(receipt);
            retainEvidence("accepted-negative-evaluation", { context: base.context, seal, ...bound, artifact, settlement: receipt });
            let mismatch;
            try { await nativeRPC({ ...request, artifact: artifact + " " }); } catch (error) { mismatch = String(error); }
            expect(mismatch).to.include("artifact size mismatch");
        } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
    });

    it("returns bounty and unlocks a delivered report when review quorum is missing", async () => {
        await requireDisposableLocalNetwork();
        const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "successor-no-quorum-"));
        try {
            const f = await fixture();
            const { id, plan } = await f.campaign([spec]);
            const base = { home: path.join(temporary, "state"), context: await context(f, id) };
            const artifact = JSON.stringify({ candidateVerdict: "FAIL", correctReport: true, scope: "local-fixture" });
            const { seal, job, bound } = await assigned(f, 0, plan, id, base, artifact);
            const stakeBefore = await f.jobs.stake(f.agent.address);
            await jump((await f.jobs.jobs(job)).reviewEnd + 1n);
            const settled = await (await f.jobs.timeout(job)).wait();
            const receipt = await nativeRPC({ ...base, ...bound, operation: "import", artifact, settlement: settled.hash });
            expect(receipt.job_acceptance).to.equal("unresolved_no_quorum");
            expect(receipt.settlement_status).to.equal("refunded");
            expect(receipt.refund_base_units).to.equal(spec.bounty);
            expect(receipt.payouts).to.deep.equal([]);
            retainEvidence("missing-review-quorum", { context: base.context, seal, ...bound, artifact, settlement: receipt });
            expect(await f.jobs.stake(f.agent.address)).to.equal(stakeBefore);
            expect(await f.jobs.locked(f.agent.address)).to.equal(0);
        } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
    });
});
