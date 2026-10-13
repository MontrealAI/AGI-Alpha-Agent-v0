// SPDX-License-Identifier: Apache-2.0
const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const { execFileSync } = require("child_process");
const { expect } = require("chai");
const hre = require("hardhat");
const { ethers } = hre;
const { TASK_COMPILE_SOLIDITY_CHECK_ERRORS } = require("hardhat/builtin-tasks/task-names");
const { ROOT, NAMES, loadRecord } = require("../scripts/mainnet-record");
const { makePlan, compiledContracts, canonical, reviewedRevision } = require("../scripts/mainnet");
const { SOLC_VERSION, pinnedCompiler } = require("../scripts/compiler-policy");
const { explorerCompiler, recordedPackage, plannedPackage, writePackage } = require("../scripts/verification-package");
const sha256 = data => crypto.createHash("sha256").update(data).digest("hex");
const clone = value => JSON.parse(JSON.stringify(value));

async function rejects(fn, text) {
    let error;
    try { await fn(); } catch (caught) { error = caught; }
    expect(error, text).to.be.instanceOf(Error);
    expect(error.message).to.include(text);
}

function configFixture() {
    const config = clone(require("../mainnet.example.json"));
    const account = index => ethers.getAddress(`0x${String(index).padStart(40, "0")}`);
    const hash = ethers.id("test fixture only");
    config.deployer = account(1); config.governor.address = account(2);
    config.governor.owners = [3, 4, 5].map(account); config.governor.codeHash = hash;
    config.block.hash = hash;
    for (const dependency of Object.values(config.dependencies)) dependency.codeHash = hash;
    for (const root of Object.keys(config.rootOwners)) config.rootOwners[root] = account(6);
    return config;
}

describe("Strict compilation and exact explorer verification packages", function () {
    this.timeout(60000);
    it("uses the lockfile compiler and rejects every Solidity warning in the real compilation task", async () => {
        const compiler = pinnedCompiler();
        expect(compiler.version).to.equal(SOLC_VERSION);
        expect(compiler.longVersion).to.equal(require("solc").version());
        expect(compiler.isSolcJs).to.equal(true);
        expect(() => pinnedCompiler("0.8.24")).to.throw("Unsupported compiler profile");
        await hre.run(TASK_COMPILE_SOLIDITY_CHECK_ERRORS, { output: { errors: [] }, quiet: true });
        const warn = console.warn;
        try {
            console.warn = () => {};
            await rejects(() => hre.run(TASK_COMPILE_SOLIDITY_CHECK_ERRORS, {
                output: { errors: [{ severity: "warning", errorCode: "5574", formattedMessage: "Synthetic regression warning" }] },
                quiet: true,
            }), "1 warning(s)");
        } finally { console.warn = warn; }
    });

    it("exports the original input byte for byte and constructors matching all five recorded creation transactions", () => {
        const bundle = recordedPackage(), archive = loadRecord();
        const original = fs.readFileSync(path.join(ROOT, "compiler-input.json"), "utf8");
        expect(bundle.manifest.explorerSubmission).to.equal("not-performed");
        expect(bundle.manifest.chainId).to.equal(1);
        for (const [i, name] of NAMES.entries()) {
            const request = JSON.parse(bundle.files[`${name}/etherscan-request.json`]);
            expect(bundle.files[`${name}/standard-input.json`]).to.equal(original);
            expect(request.sourceCode).to.equal(original);
            expect(request.chainid).to.equal("1");
            expect(request.contractaddress).to.equal(archive.record.contracts[name].address);
            expect(request.compilerversion).to.equal("v0.8.24+commit.e11b9ed9");
            expect(request.contractname).to.equal(`${archive.compiled[name].sourceName}:${name}`);
            expect(request.constructorArguments).not.to.match(/^0x/);
            expect(ethers.keccak256(archive.compiled[name].bytecode + request.constructorArguments))
                .to.equal(archive.record.transactions[i].inputHash);
            expect(request).not.to.have.property("apikey");
        }
        for (const [filename, digest] of Object.entries(bundle.manifest.files))
            expect(sha256(bundle.files[filename]), filename).to.equal(digest);
    });

    it("never overwrites an existing export directory", () => {
        const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "ascension-verification-"));
        try {
            const destination = path.join(temporary, "package");
            const bundle = recordedPackage();
            expect(writePackage(bundle, destination)).to.equal(destination);
            expect(JSON.parse(fs.readFileSync(path.join(destination, "manifest.json")))).to.deep.equal(bundle.manifest);
            expect(() => writePackage(bundle, destination)).to.throw("Output already exists");
        } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
    });

    it("exports a reviewed new plan and rejects wrong-chain, changed-address, constructor or compiler profiles", async () => {
        const compiled = compiledContracts();
        const revision = { commit: "local-test", tree: "local-tree", lockSha256: "local-lock" };
        const plan = await makePlan(configFixture(), compiled, revision);
        const bundle = await plannedPackage(plan, compiled, revision);
        expect(bundle.manifest.profile.kind).to.equal("unsigned-plan");
        for (const [i, name] of NAMES.entries()) {
            const request = JSON.parse(bundle.files[`${name}/etherscan-request.json`]);
            expect(request.contractaddress).to.equal(plan.addresses[name]);
            expect(request.compilerversion).to.match(/^v0\.8\.37\+commit\.[a-f0-9]{8}$/);
            expect(JSON.parse(request.sourceCode).settings.evmVersion).to.equal("cancun");
            expect(compiled.records[name].bytecode + request.constructorArguments).to.equal(plan.transactions[i].data);
        }
        for (const mutate of [value => value.addresses.NovaSeed = value.config.deployer,
            value => value.transactions[0].constructorArguments[2] = value.config.deployer,
            value => Object.values(value.builds)[0].compiler = "0.8.24+commit.e11b9ed9"]) {
            const changed = clone(plan); mutate(changed);
            const { payloadSha256, ...payload } = changed;
            changed.payloadSha256 = sha256(canonical(payload));
            await rejects(() => plannedPackage(changed, compiled, revision), "differs from current compiled sources");
        }
        const wrongChain = clone(plan); wrongChain.config.chainId = 31337;
        const { payloadSha256, ...payload } = wrongChain;
        wrongChain.payloadSha256 = sha256(canonical(payload));
        await rejects(() => plannedPackage(wrongChain, compiled, revision), "Ethereum mainnet chainId 1 required");
        for (const field of ["commit", "tree", "lockSha256"]) {
            const changed = clone(plan); changed.revision[field] = "unreviewed";
            const { payloadSha256, ...payload } = changed;
            changed.payloadSha256 = sha256(canonical(payload));
            await rejects(() => plannedPackage(changed, compiled, revision), "exact clean source revision and dependency lock");
        }
    });

    it("requires a clean checkout and binds its exact commit, tree and lockfile", () => {
        const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "ascension-reviewed-checkout-"));
        const git = args => execFileSync("git", args, { cwd: temporary, stdio: "pipe" });
        try {
            const directory = path.join(temporary, "tests/contracts");
            fs.mkdirSync(directory, { recursive: true });
            const lock = path.join(directory, "package-lock.json");
            fs.writeFileSync(lock, "{}\n");
            git(["init"]); git(["add", "."]);
            const commit = message => git(["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", message]);
            commit("Initial fixture");
            const initial = reviewedRevision(temporary);
            expect(initial.lockSha256).to.equal(sha256("{}\n"));
            fs.writeFileSync(lock, "{\"changed\":true}\n");
            expect(() => reviewedRevision(temporary)).to.throw("clean reviewed checkout");
            git(["add", "."]); commit("Changed lock");
            const changed = reviewedRevision(temporary);
            for (const field of ["commit", "tree", "lockSha256"]) expect(changed[field]).not.to.equal(initial[field]);
            fs.writeFileSync(path.join(temporary, "unreviewed.txt"), "not reviewed\n");
            expect(() => reviewedRevision(temporary)).to.throw("clean reviewed checkout");
        } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
    });

    it("requires exact released compiler identities rather than guessing a compiler commit", () => {
        expect(explorerCompiler("0.8.24+commit.e11b9ed9.Emscripten.clang")).to.equal("v0.8.24+commit.e11b9ed9");
        for (const version of ["0.8.24", "latest", "0.8.24-nightly+commit.e11b9ed9"])
            expect(() => explorerCompiler(version)).to.throw("Exact release compiler version");
    });
});
