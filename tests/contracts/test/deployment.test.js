// SPDX-License-Identifier: Apache-2.0
const { expect } = require("chai");
const { ethers, network } = require("hardhat");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { deploymentPlan, deployLocal, verifyDeployment, verifyBuildSources, writeManifest } = require("../scripts/deployment");
const { verifyLegacyDisabled } = require("../scripts/check-deployment-config");

async function refusal(operation, message) {
    let error;
    try { await operation(); } catch (caught) { error = caught; }
    expect(error, "operation must reject").to.be.instanceOf(Error);
    expect(error.message).to.include(message);
}

describe("Local deployment operator workflow", function () {
    this.timeout(30000);
    beforeEach(async () => { await ethers.provider.send("hardhat_reset", []); });

    it("plans without provider writes and rejects token override drift", async () => {
        const before = await ethers.provider.getBlockNumber();
        const plan = deploymentPlan({});
        expect(plan.token.decimals).to.equal(18);
        expect(plan.chainId).to.equal("31337");
        expect(plan.sources["contracts/ascension/AscensionMark.sol"]).to.match(/^[0-9a-f]{64}$/);
        expect(await ethers.provider.getBlockNumber()).to.equal(before);
        expect(() => deploymentPlan({ AGIALPHA_ADDRESS: ethers.ZeroAddress })).to.throw("canonical $AGIALPHA");
        expect(() => deploymentPlan({ AGIALPHA_DECIMALS: "6" })).to.throw("canonical $AGIALPHA");
    });

    it("deploys, binds and verifies actual bytecode, ownership and empty state", async () => {
        const { contracts, manifest } = await deployLocal();
        expect(manifest.verified).to.equal(true);
        expect(manifest.productionAuthority).to.equal(false);
        expect(manifest.transactions).to.have.length(10);
        expect(manifest.instanceId).to.match(/^0x[0-9a-f]+$/i);
        expect(manifest.deployed.mark.runtimeCodeHash).to.equal(
            ethers.keccak256(await ethers.provider.getCode(contracts.mark.target)));
        expect(await verifyDeployment(contracts, manifest.governor)).to.equal(true);
        await refusal(() => verifyDeployment(contracts, ethers.ZeroAddress), "governance owner");
        await expect(contracts.oracle.bindMarketplace(contracts.jobs.target)).to.be.revertedWith("binding is one-time");
        await expect(contracts.jobs.bindMark(contracts.mark.target)).to.be.revertedWith("binding is one-time");
        const height = await ethers.provider.getBlockNumber();
        await refusal(() => deployLocal(), "existing chain state will not be reset");
        expect(await ethers.provider.getBlockNumber()).to.equal(height);
        await contracts.token.mint(manifest.governor, 1);
        await refusal(() => verifyDeployment(contracts, manifest.governor), "fresh token supply");
    });

    it("rejects URL-backed and forked networks before any deployment transaction", async () => {
        for (const [key, value] of [["url", "http://127.0.0.1:8545"], ["forking", { url: "http://127.0.0.1:8545" }]]) {
            const prior = network.config[key];
            try {
                network.config[key] = value;
                await refusal(() => deployLocal(), "in-process, unforked Hardhat");
            } finally {
                if (prior === undefined) delete network.config[key];
                else network.config[key] = prior;
            }
        }
        expect(await ethers.provider.getBlockNumber()).to.equal(0);
    });

    it("writes exclusive public evidence files without replacing earlier runs", () => {
        const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "ascension-deployment-"));
        try {
            const output = path.join(temporary, "receipt.json");
            writeManifest({ scope: "disposable-local-fixture" }, output);
            const prior = fs.readFileSync(output, "utf8");
            expect(() => writeManifest({ replaced: true }, output)).to.throw();
            expect(fs.readFileSync(output, "utf8")).to.equal(prior);
        } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
    });

    it("refuses stale compiler inputs instead of attributing old bytecode to changed source", () => {
        const build = { input: { sources: { "contracts/Example.sol": { content: "old source" } } } };
        expect(() => verifyBuildSources(build, () => "new source")).to.throw("Compiled source is stale");
        expect(verifyBuildSources(build, () => "old source")["contracts/Example.sol"]).to.match(/^[0-9a-f]{64}$/);
    });

    it("blocks the legacy route and catches attempts to re-enable its networks or deployment", async () => {
        const migration = require("../../../truffle/migrations/2_deploy_agijobs_v2");
        await verifyLegacyDisabled(require("../../../truffle/truffle-config"), migration);
        await refusal(() => verifyLegacyDisabled({ networks: { mainnet: {} } }, migration), "networks must remain disabled");
        await refusal(() => verifyLegacyDisabled({ networks: {} }, async deployer => deployer.deploy()), "before attempting");
        await refusal(() => verifyLegacyDisabled({ networks: {} }, async () => {}), "before attempting");
    });
});
