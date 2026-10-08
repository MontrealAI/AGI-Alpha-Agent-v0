// SPDX-License-Identifier: Apache-2.0
const { ethers } = require("hardhat");
const { requireDisposableLocalNetwork } = require("./disposable");
const { installToken } = require("../test/utils/token");
const { compilePlan } = require("./plan");
const units = ethers.parseEther;
const evidence = ethers.id(
    "public local acceptance fixture; not an independent real-world review",
);
const spec = {
    goal: "Choose an energy resilience pilot portfolio from supplied public planning assumptions.",
    successMetric:
        "Replay the supplied allocation and verify every budget, risk and objective calculation.",
    bounty: units("100").toString(),
    duration: 86400,
    priceWeight: 6000,
};
async function now() {
    return (await ethers.provider.getBlock("latest")).timestamp;
}
async function jump(timestamp) {
    await ethers.provider.send("evm_setNextBlockTimestamp", [
        Number(timestamp),
    ]);
    await ethers.provider.send("evm_mine");
}
async function fixture() {
    await requireDisposableLocalNetwork();
    await ethers.provider.send("hardhat_reset", []);
    const [
        governor,
        business,
        agent,
        fastAgent,
        validator1,
        validator2,
        validator3,
        funder,
        outsider,
        funder2,
    ] = await ethers.getSigners();
    const token = await installToken();
    async function deploy(name, ...args) {
        const contract = await (
            await ethers.getContractFactory(name)
        ).deploy(...args);
        await contract.waitForDeployment();
        return contract;
    }
    const ens = await deploy("MockAscensionENS"),
        wrapper = await deploy("MockAscensionWrapper");
    const access = await deploy(
        "AscensionAccess",
        ens.target,
        wrapper.target,
        governor.address,
    );
    const seed = await deploy("NovaSeed", access.target);
    const oracle = await deploy(
        "AscensionRiskOracle",
        access.target,
        seed.target,
        units("10"),
        2,
        2000,
        governor.address,
    );
    const jobs = await deploy(
        "AscensionJobMarket",
        access.target,
        oracle.target,
        units("10"),
        governor.address,
    );
    const mark = await deploy(
        "AscensionMark",
        seed.target,
        access.target,
        oracle.target,
        jobs.target,
    );
    await oracle.bindMarketplace(jobs.target);
    await jobs.bindMark(mark.target);
    async function register(account, role, label) {
        const node = await access.child(await access.roots(role), label);
        await ens.setOwner(node, account.address);
        await access.connect(account).register(role, label);
        return node;
    }
    for (const account of [
        business,
        agent,
        fastAgent,
        validator1,
        validator2,
        validator3,
        funder,
        funder2,
    ]) {
        await access.setAdmission(
            account.address,
            evidence,
            (await now()) + 180 * 86400,
        );
        await token.mint(account.address, units("10000"));
        for (const target of [oracle, jobs, mark])
            await token
                .connect(account)
                .approve(target.target, ethers.MaxUint256);
    }
    await register(business, 0, "resilience");
    await register(agent, 1, "researcher");
    await register(fastAgent, 1, "fast-researcher");
    for (const [i, v] of [validator1, validator2, validator3].entries()) {
        await register(v, 2, `reviewer${i + 1}`);
        await oracle.connect(v).deposit(units("100"));
        await oracle
            .connect(v)
            .setJobAvailability(
                business.address,
                (await now()) + 120 * 86400,
                32,
            );
    }
    for (const a of [agent, fastAgent])
        await jobs.connect(a).deposit(units("1000"));
    const validators = [validator1, validator2, validator3];
    const committee = validators.map((v) => v.address);
    async function createSeed(
        specs = [spec],
        parent = 0,
        capsuleHash = evidence,
    ) {
        const plan = compilePlan(specs);
        await seed
            .connect(business)
            .seal(
                capsuleHash,
                plan.planRoot,
                specs.length,
                "ipfs://local-fixture-metadata",
                parent,
                evidence,
            );
        return { id: await seed.nextId(), plan };
    }
    async function green(id) {
        await oracle.connect(business).openReview(id);
        for (const v of validators.slice(0, 2))
            await oracle.connect(v).attest(id, 1000, true, evidence);
    }
    async function campaign(specs = [spec]) {
        const data = await createSeed(specs);
        await green(data.id);
        await mark
            .connect(business)
            .open(
                data.id,
                units("2"),
                units("0.1"),
                100,
                units("100"),
                (await now()) + 86400,
                14 * 86400,
            );
        await mark.connect(funder).buy(data.id, 40, units("158"));
        await mark.connect(business).bloom(data.id);
        return data;
    }
    async function post(s = spec) {
        await jobs.connect(business).post(s, 60, committee);
        return await jobs.nextId();
    }
    async function assign(id, price = "80", duration = 3600, worker = agent) {
        await jobs.connect(worker).bid(id, units(price), duration);
        await jump((await jobs.jobs(id)).auctionEnd);
        await jobs.award(id);
    }
    async function deliver(id, hash = evidence, worker = agent) {
        await jobs
            .connect(worker)
            .submit(id, hash, "ipfs://local-fixture-result");
    }
    async function approve(id, hash = evidence) {
        for (const v of validators.slice(0, 2))
            await jobs.connect(v).validate(id, hash, true, evidence);
    }
    return {
        governor,
        business,
        agent,
        fastAgent,
        validators,
        validator1,
        validator2,
        validator3,
        funder,
        funder2,
        outsider,
        token,
        ens,
        wrapper,
        access,
        seed,
        oracle,
        jobs,
        mark,
        register,
        createSeed,
        green,
        campaign,
        post,
        assign,
        deliver,
        approve,
        committee,
    };
}
module.exports = { fixture, units, evidence, spec, now, jump };
