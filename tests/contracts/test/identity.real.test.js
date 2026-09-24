// SPDX-License-Identifier: Apache-2.0
const { expect } = require('chai');
const { ethers } = require('hardhat');
describe('Shipped identity verification (no permissive test stub)', function () {
  it('accepts the actual Merkle member and rejects a different claimant or name', async function () {
    const [member, stranger] = await ethers.getSigners();
    const harness = await (await ethers.getContractFactory('IdentityHarness')).deploy();
    const node = ethers.keccak256(ethers.toUtf8Bytes('agent-root'));
    const subnode = ethers.solidityPackedKeccak256(['bytes32','bytes32'], [node, ethers.keccak256(ethers.toUtf8Bytes('alice'))]);
    const root = ethers.solidityPackedKeccak256(['bytes32','address'], [subnode, member.address]);
    expect(await harness.verify.staticCall(member.address, 'alice', [], node, root)).to.equal(true);
    expect(await harness.verify.staticCall(stranger.address, 'alice', [], node, root)).to.equal(false);
    expect(await harness.verify.staticCall(member.address, 'bob', [], node, root)).to.equal(false);
  });
  it('rejects an unconfigured root', async function () {
    const [member] = await ethers.getSigners();
    const harness = await (await ethers.getContractFactory('IdentityHarness')).deploy();
    expect(await harness.verify.staticCall(member.address, 'alice', [], ethers.ZeroHash, ethers.ZeroHash)).to.equal(false);
  });
});
