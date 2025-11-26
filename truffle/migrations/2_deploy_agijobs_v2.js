const Deployer = artifacts.require('Deployer');
const path = require('path');
const { AGIALPHA_ADDRESS, AGIALPHA_DECIMALS } = require(path.join(__dirname, '../../token.config'));

module.exports = async function (deployer) {
  const governance = process.env.GOVERNANCE_ADDRESS;
  if (!governance) {
    throw new Error('GOVERNANCE_ADDRESS env var is required');
  }

  const agiAddress = process.env.AGIALPHA_ADDRESS || AGIALPHA_ADDRESS;
  const agiDecimals = Number(process.env.AGIALPHA_DECIMALS || AGIALPHA_DECIMALS);
  if (!web3.utils.isAddress(agiAddress)) {
    throw new Error('AGIALPHA_ADDRESS must be a valid address');
  }
  if (agiDecimals !== 18) {
    throw new Error('AGIALPHA_DECIMALS must be 18');
  }

  await deployer.deploy(Deployer);
  const instance = await Deployer.deployed();

  const ids = {
    ens: '0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e',
    nameWrapper: '0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401',
    clubRootNode: web3.utils.namehash('club.agi.eth'),
    agentRootNode: web3.utils.namehash('agent.agi.eth'),
    validatorMerkleRoot: '0x0000000000000000000000000000000000000000000000000000000000000000',
    agentMerkleRoot: '0x0000000000000000000000000000000000000000000000000000000000000000',
  };

  console.log('Using AGIALPHA token', agiAddress, `(${agiDecimals} decimals)`);

  const receipt = await instance.deployDefaults(ids, governance);
  console.log('AGIJobs v2 deployed via Deployer at', instance.address);
  console.log('tx hash:', receipt.tx);
};
