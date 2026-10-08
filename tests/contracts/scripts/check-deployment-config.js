// SPDX-License-Identifier: Apache-2.0
// Dependency-free operator gate: no Hardhat import, provider, or wallet access.
const { deploymentPlan } = require("./deployment");

async function verifyLegacyDisabled(config, migration) {
    if (!config || !config.networks || Object.keys(config.networks).length !== 0)
        throw Error("Legacy Truffle networks must remain disabled");
    let attempted = false;
    let refusal;
    try {
        await migration({ deploy: () => { attempted = true; throw Error("Unexpected legacy deployment attempt"); } });
    } catch (error) { refusal = error; }
    if (attempted || !refusal || !String(refusal.message).startsWith("Legacy Truffle migration is unsupported:"))
        throw Error("Legacy Truffle migration must refuse before attempting a deployment");
}

async function main() {
    await verifyLegacyDisabled(require("../../../truffle/truffle-config"),
        require("../../../truffle/migrations/2_deploy_agijobs_v2"));
    const plan = deploymentPlan();
    if (plan.chainId !== "31337" || plan.network !== "hardhat" || plan.externalTransactions !== false || !plan.token.mock)
        throw Error("Hardhat deployment must remain a disposable local fixture");
    process.stdout.write(JSON.stringify({ token: plan.token, legacyDisabled: true, chainId: plan.chainId }) + "\n");
}

module.exports = { verifyLegacyDisabled };
if (require.main === module) main().catch(error => { console.error(error.message); process.exitCode = 1; });
