// SPDX-License-Identifier: Apache-2.0
const { network, ethers } = require("hardhat");

async function requireDisposableLocalNetwork() {
    // Hardhat's in-process provider is created by this test process. A network
    // URL, fork, or advertised chain ID alone never authorizes fixture writes.
    if (network.name !== "hardhat" || network.config.url || network.config.forking)
        throw Error("Fixture mutation requires a newly created in-process, unforked Hardhat network");
    const metadata = await ethers.provider.send("hardhat_metadata", []);
    if (!metadata || typeof metadata.instanceId !== "string" || metadata.forkedNetwork)
        throw Error("Cannot verify a disposable in-process Hardhat instance");
}
module.exports = { requireDisposableLocalNetwork };
