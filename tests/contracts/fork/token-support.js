// SPDX-License-Identifier: Apache-2.0
const { ethers, network } = require("hardhat");
const { AGIALPHA_ADDRESS } = require("../../../token.config");
let baseline;
async function requireOwnedFork() {
    if (network.name !== "hardhat" || network.config.url || network.config.chainId !== 31337)
        throw Error("Not a private in-process fork");
    const metadata = await ethers.provider.send("hardhat_metadata", []);
    const fork = metadata?.forkedNetwork;
    if (!metadata?.instanceId || fork?.chainId !== 1 || fork.forkBlockNumber !== Number(process.env.ALPHA_FORK_BLOCK) ||
        fork.forkBlockHash?.toLowerCase() !== process.env.ALPHA_FORK_BLOCK_HASH)
        throw Error("Pinned mainnet fork identity differs");
}
async function seedForkToken(accounts) {
    await requireOwnedFork();
    const token = new ethers.Contract(AGIALPHA_ADDRESS, [
        "function balanceOf(address) view returns(uint256)", "function totalSupply() view returns(uint256)",
        "function decimals() view returns(uint8)", "function approve(address,uint256) returns(bool)",
        "function transfer(address,uint256) returns(bool)", "function burn(uint256)"
    ], accounts[0]);
    const code = await ethers.provider.getCode(AGIALPHA_ADDRESS);
    if (code === "0x" || await token.decimals() !== 18n) throw Error("Actual forked token unavailable");
    const originalSupply = await token.totalSupply();
    let delta = 0n;
    for (const account of accounts) {
        const previous = await token.balanceOf(account.address);
        const target = ethers.parseEther("10000"); delta += target - previous;
        const slot = ethers.keccak256(ethers.AbiCoder.defaultAbiCoder().encode(["address", "uint256"], [account.address, 0]));
        await ethers.provider.send("hardhat_setStorageAt", [AGIALPHA_ADDRESS, slot, ethers.toBeHex(target, 32)]);
        if (await token.balanceOf(account.address) !== target) throw Error("Token balance layout differs; stop instead of replacing code");
    }
    await ethers.provider.send("hardhat_setStorageAt", [AGIALPHA_ADDRESS, ethers.toBeHex(2, 32), ethers.toBeHex(originalSupply + delta, 32)]);
    if (await token.totalSupply() !== originalSupply + delta || await ethers.provider.getCode(AGIALPHA_ADDRESS) !== code)
        throw Error("Fork supply or unchanged token code check failed");
    baseline = { token: AGIALPHA_ADDRESS, codeHash: ethers.keccak256(code), originalSupply: originalSupply.toString(), syntheticSupplyDelta: delta.toString() };
    return token;
}
module.exports = { requireOwnedFork, seedForkToken, tokenBaseline: () => baseline };
