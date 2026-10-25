// SPDX-License-Identifier: Apache-2.0
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { requireDisposableLocalNetwork } = require("../../scripts/disposable");
const { installToken } = require("../utils/token");
const APPROVED_GOVERNOR = "0xd76AD27a1Bcf8652e7e46BE603FA742FD1c10A99";

describe("Fresh Ascension constructor authority", function () {
    this.timeout(60000);
    beforeEach(async () => {
        await requireDisposableLocalNetwork();
        await ethers.provider.send("hardhat_reset", []);
    });

    async function graph(governorAddress) {
        const [creator, governor, outsider] = await ethers.getSigners();
        await installToken();
        const selected = governorAddress || governor.address;
        const receipts = {};
        async function deploy(name, ...args) {
            const contract = await (await ethers.getContractFactory(name, creator)).deploy(...args);
            receipts[name] = await contract.deploymentTransaction().wait();
            return contract;
        }
        const ens = await deploy("MockAscensionENS"), wrapper = await deploy("MockAscensionWrapper");
        const access = await deploy("AscensionAccess", ens.target, wrapper.target, selected);
        const seed = await deploy("NovaSeed", access.target);
        const oracle = await deploy("AscensionRiskOracle", access.target, seed.target, 10n, 2, 2000, selected);
        const jobs = await deploy("AscensionJobMarket", access.target, oracle.target, 10n, selected);
        const mark = await deploy("AscensionMark", seed.target, access.target, oracle.target, jobs.target);
        return { creator, governor, outsider, access, seed, oracle, jobs, mark, receipts, selected, ens, wrapper };
    }

    it("installs the approved address directly with no creator ownership event or pending handover", async () => {
        const f = await graph(APPROVED_GOVERNOR);
        for (const [name, contract] of [["AscensionAccess", f.access], ["AscensionRiskOracle", f.oracle], ["AscensionJobMarket", f.jobs]]) {
            expect(await contract.owner()).to.equal(APPROVED_GOVERNOR);
            expect(await contract.pendingOwner()).to.equal(ethers.ZeroAddress);
            const ownership = f.receipts[name].logs.map(log => {
                try { return contract.interface.parseLog(log); } catch { return null; }
            }).filter(event => event?.name === "OwnershipTransferred");
            expect(ownership).to.have.length(1);
            expect(ownership[0].args.previousOwner).to.equal(ethers.ZeroAddress);
            expect(ownership[0].args.newOwner).to.equal(APPROVED_GOVERNOR);
        }
        expect(await f.access.admitted(f.creator.address)).to.equal(false);
        expect(await f.access.eligible(f.creator.address, 0)).to.equal(false);
        expect(await f.seed.nextId()).to.equal(0);
        expect(await f.jobs.nextId()).to.equal(0);
        expect(await f.oracle.marketplace()).to.equal(ethers.ZeroAddress);
        expect(await f.jobs.mark()).to.equal(ethers.ZeroAddress);
    });

    it("rejects zero governance in every authority-bearing constructor", async () => {
        const f = await graph();
        for (const [name, args] of [
            ["AscensionAccess", [f.ens.target, f.wrapper.target, ethers.ZeroAddress]],
            ["AscensionRiskOracle", [f.access.target, f.seed.target, 10n, 2, 2000, ethers.ZeroAddress]],
            ["AscensionJobMarket", [f.access.target, f.oracle.target, 10n, ethers.ZeroAddress]],
        ]) {
            const factory = await ethers.getContractFactory(name, f.creator);
            await expect(factory.deploy(...args)).to.be.revertedWithCustomError(factory, "OwnableInvalidOwner")
                .withArgs(ethers.ZeroAddress);
        }
    });

    it("rejects creator and unrelated accounts before and after the two separately governed bindings", async () => {
        const f = await graph();
        for (const actor of [f.creator, f.outsider]) {
            for (const contract of [f.access, f.oracle, f.jobs]) {
                await expect(contract.connect(actor).transferOwnership(actor.address))
                    .to.be.revertedWithCustomError(contract, "OwnableUnauthorizedAccount").withArgs(actor.address);
                await expect(contract.connect(actor).renounceOwnership())
                    .to.be.revertedWithCustomError(contract, "OwnableUnauthorizedAccount").withArgs(actor.address);
                await expect(contract.connect(actor).acceptOwnership())
                    .to.be.revertedWithCustomError(contract, "OwnableUnauthorizedAccount").withArgs(actor.address);
            }
            await expect(f.access.connect(actor).setAdmission(actor.address, ethers.id("local evidence"), 0))
                .to.be.revertedWithCustomError(f.access, "OwnableUnauthorizedAccount").withArgs(actor.address);
            await expect(f.oracle.connect(actor).bindMarketplace(f.jobs.target))
                .to.be.revertedWithCustomError(f.oracle, "OwnableUnauthorizedAccount").withArgs(actor.address);
            await expect(f.jobs.connect(actor).bindMark(f.mark.target))
                .to.be.revertedWithCustomError(f.jobs, "OwnableUnauthorizedAccount").withArgs(actor.address);
        }
        await f.oracle.connect(f.governor).bindMarketplace(f.jobs.target);
        expect(await f.oracle.marketplace()).to.equal(f.jobs.target);
        expect(await f.jobs.mark()).to.equal(ethers.ZeroAddress);
        await f.jobs.connect(f.governor).bindMark(f.mark.target);
        for (const actor of [f.creator, f.outsider]) {
            await expect(f.oracle.connect(actor).bindMarketplace(f.jobs.target))
                .to.be.revertedWithCustomError(f.oracle, "OwnableUnauthorizedAccount").withArgs(actor.address);
            await expect(f.jobs.connect(actor).bindMark(f.mark.target))
                .to.be.revertedWithCustomError(f.jobs, "OwnableUnauthorizedAccount").withArgs(actor.address);
        }
        expect(await f.jobs.mark()).to.equal(f.mark.target);
        for (const contract of [f.access, f.oracle, f.jobs]) {
            expect(await contract.owner()).to.equal(f.governor.address);
            expect(await contract.pendingOwner()).to.equal(ethers.ZeroAddress);
        }
    });

    it("uses normal EVM code and initcode limits rather than unlimited fixture settings", async () => {
        const [creator] = await ethers.getSigners();
        const oversizedRuntime = "0x616001600e6000396160016000f3" + "00".repeat(24577);
        let runtimeError;
        try { await creator.sendTransaction({ data: oversizedRuntime, gasLimit: 16000000 }); }
        catch (error) { runtimeError = error; }
        expect(runtimeError).to.be.instanceOf(Error);
        expect(runtimeError.message).to.match(/code is too large|EIP-170|code size/i);
        let initcodeError;
        try { await creator.sendTransaction({ data: "0x" + "00".repeat(49153), gasLimit: 16000000 }); }
        catch (error) { initcodeError = error; }
        expect(initcodeError).to.be.instanceOf(Error);
        expect(initcodeError.message).to.match(/initcode|EIP-3860|49152/i);
    });
});
