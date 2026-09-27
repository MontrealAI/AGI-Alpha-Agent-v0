// SPDX-License-Identifier: Apache-2.0
const { ethers } = require("ethers");
const fs = require("fs");

function leaf(index, spec) {
    return ethers.keccak256(
        ethers.keccak256(
            ethers.AbiCoder.defaultAbiCoder().encode(
                ["uint32", "bytes32", "bytes32", "uint96", "uint32", "uint16"],
                [
                    index,
                    ethers.id(spec.goal),
                    ethers.id(spec.successMetric),
                    spec.bounty,
                    spec.duration,
                    spec.priceWeight,
                ],
            ),
        ),
    );
}
function pair(a, b) {
    return ethers.keccak256(ethers.concat([a, b].sort()));
}
function compilePlan(specs) {
    if (!Array.isArray(specs) || !specs.length || specs.length > 128)
        throw Error("1–128 job specifications required");
    for (const s of specs) {
        if (
            typeof s.goal !== "string" ||
            !s.goal.length ||
            Buffer.byteLength(s.goal) > 512 ||
            typeof s.successMetric !== "string" ||
            !s.successMetric.length ||
            Buffer.byteLength(s.successMetric) > 512 ||
            typeof s.bounty !== "string" ||
            !/^[1-9][0-9]*$/.test(s.bounty) ||
            BigInt(s.bounty) < 100n ||
            BigInt(s.bounty) >= 2n ** 96n ||
            !Number.isInteger(s.duration) ||
            s.duration < 1 ||
            s.duration > 90 * 86400 ||
            !Number.isInteger(s.priceWeight) ||
            s.priceWeight < 0 ||
            s.priceWeight > 10000
        )
            throw Error("Invalid job specification");
    }
    const levels = [specs.map((s, i) => leaf(i, s))];
    while (levels.at(-1).length > 1) {
        const previous = levels.at(-1),
            next = [];
        for (let i = 0; i < previous.length; i += 2)
            next.push(
                i + 1 < previous.length
                    ? pair(previous[i], previous[i + 1])
                    : previous[i],
            );
        levels.push(next);
    }
    return {
        schema: "agialpha.ascension.fusion-plan.v1",
        token: "AGIALPHA",
        decimals: 18,
        planRoot: levels.at(-1)[0],
        totalBounty: specs
            .reduce((sum, s) => sum + BigInt(s.bounty), 0n)
            .toString(),
        jobs: specs.map((spec, index) => {
            const proof = [];
            let position = index;
            for (const level of levels.slice(0, -1)) {
                if ((position ^ 1) < level.length)
                    proof.push(level[position ^ 1]);
                position = Math.floor(position / 2);
            }
            return { index, spec, leaf: levels[0][index], proof };
        }),
    };
}
module.exports = { compilePlan, leaf };
if (require.main === module) {
    if (process.argv.length !== 3)
        throw Error("Usage: node scripts/plan.js /absolute/path/jobs.json");
    const source = fs.readFileSync(process.argv[2], "utf8");
    if (Buffer.byteLength(source) > 250000) throw Error("Plan exceeds 250 KB");
    process.stdout.write(
        JSON.stringify(compilePlan(JSON.parse(source)), null, 2) + "\n",
    );
}
