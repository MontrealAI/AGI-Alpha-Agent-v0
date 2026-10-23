// Read all five deployed runtimes in a new disposable fixture, separate from tests.
// Calls the original fixture unchanged; never connects to a remote network.
const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');
const localRequire = createRequire(path.join(process.cwd(), 'package.json'));
const { ethers, network } = localRequire('hardhat');
const { fixture } = localRequire('./scripts/fixture');
const { requireDisposableLocalNetwork } = localRequire('./scripts/disposable');

async function main() {
  await requireDisposableLocalNetwork();
  const f = await fixture();
  const latest = await ethers.provider.getBlock('latest');
  const contracts = {};
  for (const [name, c] of Object.entries({AscensionAccess: f.access, NovaSeed: f.seed, AscensionRiskOracle: f.oracle, AscensionJobMarket: f.jobs, AscensionMark: f.mark})) {
    const address = await c.getAddress();
    const code = await ethers.provider.getCode(address);
    contracts[name] = {address, runtimeByteLength: (code.length - 2) / 2, runtimeKeccak256: ethers.keccak256(code), deploymentTransaction: c.deploymentTransaction().hash};
  }
  const tokenAddress = await f.token.getAddress();
  const tokenCode = await ethers.provider.getCode(tokenAddress);
  const data = {
    schema: 'discoverability.separate-local-fixture-observation.v1',
    qualification: 'Separate new disposable fixture AFTER the 36-test qualification; not the original receipts or the test receipts instance.',
    observedAtUtc: new Date().toISOString(),
    chainId: (await ethers.provider.getNetwork()).chainId.toString(),
    networkName: network.name,
    hardhatMetadata: await ethers.provider.send('hardhat_metadata', []),
    block: {number: latest.number, hash: latest.hash, timestamp: latest.timestamp},
    contracts,
    token: {address: tokenAddress, decimals: Number(await f.token.decimals()), runtimeKeccak256: ethers.keccak256(tokenCode), scope: 'MockAGI installed at configured identifier in local Hardhat only'},
    configuration: {
      ens: await f.access.ens(), wrapper: await f.access.wrapper(), accessOwner: await f.access.owner(),
      roots: {business: await f.access.roots(0), agent: await f.access.roots(1), validator: await f.access.roots(2)},
      seedAccess: await f.seed.access(), oracleAccess: await f.oracle.access(), oracleSeed: await f.oracle.seed(),
      minimumRiskStake: (await f.oracle.minimumStake()).toString(), riskQuorum: Number(await f.oracle.quorum()), maximumRiskBps: Number(await f.oracle.maximumRiskBps()),
      oracleMarketplace: await f.oracle.marketplace(), minimumMarketStake: (await f.jobs.minimumStake()).toString(),
      marketAccess: await f.jobs.access(), marketOracle: await f.jobs.oracle(), marketMark: await f.jobs.mark(),
      reviewWindowSeconds: Number(await f.jobs.REVIEW_WINDOW()), validatorBps: Number(await f.jobs.VALIDATOR_BPS()),
      markSeed: await f.mark.seed(), markAccess: await f.mark.access(), markOracle: await f.mark.oracle(), markJobs: await f.mark.jobs(),
    },
    realFunds: false, externalValidatorIndependence: false,
  };
  const target = path.join(__dirname, 'separate-fixture-observation.json');
  fs.writeFileSync(target, JSON.stringify(data, null, 2) + '\n', {flag: 'wx'});
  console.log(JSON.stringify({observationFile: path.basename(target), contracts: Object.keys(contracts), chainId: data.chainId}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
