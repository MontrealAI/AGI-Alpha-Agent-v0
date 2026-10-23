const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const project = process.cwd();
const lockBytes = fs.readFileSync('package-lock.json');
const lock = JSON.parse(lockBytes);
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
assert.equal(process.version, 'v22.17.1');
assert.equal(sha256(lockBytes), '070e3c6652f4939fabe14788a0c80b38ed3d6e2ad792cebad4a5bbf842308667');
const packageNames = ['hardhat', 'solc', 'ethers', '@openzeppelin/contracts',
  '@nomicfoundation/hardhat-ethers', '@nomicfoundation/hardhat-chai-matchers',
  '@nomicfoundation/edr', 'chai', 'keccak'];
const versions = {};
const installedScripts = {};
for (const name of packageNames) {
  const info = JSON.parse(fs.readFileSync(path.join(project, 'node_modules', name, 'package.json')));
  assert.equal(info.version, lock.packages['node_modules/' + name].version, name + ' differs from lock');
  versions[name] = info.version;
  if (lock.packages['node_modules/' + name].hasInstallScript) installedScripts[name] = info.scripts;
}
// Resolve from the copied contract project's own node_modules, never a global install.
const localRequire = require('node:module').createRequire(path.join(project, 'package.json'));
const compiler = localRequire('solc');
assert.match(compiler.version(), /^0\.8\.37\+commit\./);
const edr = localRequire('@nomicfoundation/edr');
const keccak = localRequire('keccak');
assert.equal(keccak('keccak256').update(Buffer.alloc(0)).digest('hex'),
  'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470');
const hardhatEntry = fs.realpathSync('node_modules/.bin/hardhat');
assert.ok(hardhatEntry.startsWith(path.join(project, 'node_modules') + path.sep));
process.stdout.write(JSON.stringify({
  node: process.version, v8: process.versions.v8, platform: process.platform, arch: process.arch,
  lockfileSha256: sha256(lockBytes), versions, compilerLongVersion: compiler.version(),
  compilerPath: localRequire.resolve('solc/soljson.js'), hardhatEntry,
  edrNativeModuleLoaded: Boolean(edr), keccakEmptyVectorPassed: true,
  npmLifecycleScriptsExecuted: false, suppressedInstalledScripts: installedScripts,
  evmStarted: false, externalProviderInvoked: false,
}, null, 2) + '\n');
