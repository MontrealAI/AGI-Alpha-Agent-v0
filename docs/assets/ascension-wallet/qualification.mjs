// SPDX-License-Identifier: Apache-2.0
// Qualification is admitted only by the source-reviewed build registry in client.mjs.
// This module checks that live state still matches that manifest; hashes are evidence
// references, not reviewer signatures. It cannot qualify an imported runtime profile.
import {ACTIONS, CONTRACTS, METHODS, SELECTORS, address, bytes32, callData, decode, isRecovery, uint} from './protocol.mjs';

const zero = '0x' + '0'.repeat(40);
const digest = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const hex = value => typeof value === 'string' && /^0x([0-9a-fA-F]{2})*$/.test(value) && value.length <= 20002;
const quantity = value => {
  if (typeof value !== 'string' || !/^0x(0|[1-9a-f][0-9a-f]*)$/.test(value)) throw Error('Noncanonical qualification quantity.');
  return BigInt(value);
};
const protocolChecks = {
  Access: ['owner','pendingOwner'],
  Oracle: ['owner','pendingOwner','minimumStake','quorum','maximumRiskBps'],
  Jobs: ['owner','pendingOwner','minimumStake','reviewWindow','validatorBps']
};
function validateRead(check) {
  if (!check || !hex(check.expected)) throw Error('Missing exact dependency observation.');
  if (check.kind === 'storage') { bytes32(check.slot); bytes32(check.expected); }
  else if (check.kind !== 'call' || !hex(check.data) || check.data.length < 10)
    throw Error('Only exact reviewed dependency calls or storage reads are supported.');
}
export function validateQualification(profile, stage, authorization = null, profileSHA256 = null) {
  if (!['canary','public'].includes(stage) || profile.schema !== 'agialpha.nova-qualified-profile.v1' ||
      profile.chainId !== 1 || profile.environment !== 'qualified-mainnet' || profile.mainnetQualification !== true)
    throw Error('Unsupported deployment qualification stage.');
  const required = ['evidenceSHA256','dependencyReviewSHA256','sourceVerificationSHA256','authorityReviewSHA256','approvalSHA256'];
  if (stage === 'public') required.push('canaryEvidenceSHA256','publicApprovalSHA256');
  if (required.some(key => !digest(profile.qualification?.[key])) || uint(profile.validUntil,64) === 0n)
    throw Error('Qualification evidence references and expiry must be source-pinned.');
  if (!Array.isArray(profile.recoveryActions) || profile.recoveryActions.some(action => !profile.allowedActions.includes(action) ||
      !(ACTIONS[action]?.risk === 'recovery' || ['approve','availability'].includes(action))))
    throw Error('Qualification requires an explicit bounded recovery action policy.');
  if (!Array.isArray(profile.continuationActions) || profile.continuationActions.some(action =>
      !profile.allowedActions.includes(action) || ACTIONS[action]?.risk !== 'obligation'))
    throw Error('Qualification requires an explicit existing-obligation policy.');
  for (const key of ['Access','Seed','Oracle','Jobs','Mark']) {
    if (Object.entries(CONTRACTS).some(([name,value]) => name !== 'Token' && address(value) === address(profile.contracts?.[key]?.address)))
      throw Error('Archived Mainnet suite cannot be qualified by a frontend profile.');
  }
  if (address(profile.contracts?.Token?.address) !== address(CONTRACTS.Token)) throw Error('Wrong canonical Mainnet token.');
  for (const [contract, methods] of Object.entries(protocolChecks)) {
    for (const method of methods) {
      const expected = profile.protocol?.[contract]?.[method];
      if (!hex(expected)) throw Error(`Missing pinned ${contract}.${method} authority or parameter.`);
      decode(METHODS[method].outputs,expected);
    }
  }
  if (!Array.isArray(profile.protocol?.Access?.roots) || profile.protocol.Access.roots.length !== 3)
    throw Error('All three namespace roots must be pinned.');
  profile.protocol.Access.roots.forEach(bytes32);
  if (!profile.dependencies || !profile.dependencies.Token || !profile.dependencies.ENS ||
      !Object.hasOwn(profile.dependencies,'Wrapper') || Object.keys(profile.dependencies).some(k => !['Token','ENS','Wrapper'].includes(k)))
    throw Error('Token, ENS and optional Wrapper dependencies must be explicitly reviewed.');
  for (const [name, dependency] of Object.entries(profile.dependencies)) {
    if (name === 'Wrapper' && dependency === null) continue;
    address(dependency.address);
    if (!digest(dependency.sha256) || !digest(dependency.authority?.evidenceSHA256))
      throw Error('Dependency runtime and authority evidence must be pinned.');
    if (dependency.authority.model === 'immutable') {
      if (!Array.isArray(dependency.authority.checks) || dependency.authority.checks.length !== 0)
        throw Error('Immutable authority declarations cannot contain ambiguous checks.');
    } else if (dependency.authority.model !== 'governed' || !Array.isArray(dependency.authority.checks) ||
        dependency.authority.checks.length === 0 || dependency.authority.checks.length > 32)
      throw Error('Governed dependency requires exact live authority observations.');
    dependency.authority.checks.forEach(validateRead);
    if (dependency.proxy === null) continue;
    const proxy = dependency.proxy;
    if (!proxy || !digest(proxy.implementationSHA256)) throw Error('Declare the reviewed proxy structure explicitly.');
    if (dependency.authority.model !== 'governed') throw Error('A proxy requires live reviewed authority observations.');
    address(proxy.implementation); validateRead(proxy.pointer);
    if (proxy.pointer.expected.toLowerCase() !== '0x' + address(proxy.implementation).slice(2).padStart(64,'0'))
      throw Error('Proxy pointer must resolve exactly to its pinned implementation.');
  }
  if (address(profile.dependencies.Token.address) !== address(profile.contracts.Token.address))
    throw Error('Dependency token identity differs from the protocol token.');
  if (stage === 'canary') {
    if (!authorization || authorization.profileSHA256 !== profileSHA256 || !digest(authorization.approvalSHA256) ||
        uint(authorization.validUntil,64) === 0n || !Array.isArray(authorization.intents) ||
        !authorization.intents.length || authorization.intents.length > 128)
      throw Error('Canary requires an explicit bounded list of exact transaction intents.');
    const nonceKeys = new Set();
    for (const intent of authorization.intents) {
      if (!Object.hasOwn(ACTIONS,intent.action) || !profile.allowedActions.includes(intent.action) ||
          address(intent.to) !== address(profile.contracts[ACTIONS[intent.action].contract].address) ||
          !hex(intent.data) || !intent.data.startsWith(SELECTORS[ACTIONS[intent.action].method]) ||
          intent.value !== '0x0') throw Error('Invalid exact canary intent.');
      address(intent.from); quantity(intent.nonce);
      if (quantity(intent.maxGas) <= 0n || quantity(intent.maxGas) > 30000000n) throw Error('Invalid canary gas ceiling.');
      const nonceKey = address(intent.from) + ':' + intent.nonce;
      if (nonceKeys.has(nonceKey)) throw Error('Canary sender nonce may authorize only one exact intent.');
      nonceKeys.add(nonceKey);
    }
  }
}
function authorizationCurrent(profile, blockTime) {
  return uint(profile.validUntil,64) > BigInt(blockTime) && uint(profile.validUntil,64) > BigInt(Math.floor(Date.now()/1000));
}
export function authorizeQualifiedIntent(profile, stage, action, tx, blockTime, args, authorization = null) {
  if (!['canary','public'].includes(stage)) return;
  if (!profile.allowedActions.includes(action)) throw Error('Operation is outside the qualified policy.');
  if (tx.data.toLowerCase() !== callData(ACTIONS[action].method,args).toLowerCase() || tx.value !== '0x0' ||
      address(tx.to) !== address(profile.contracts[ACTIONS[action].contract].address)) throw Error('Qualified intent arguments changed.');
  if ((profile.recoveryActions.includes(action) && isRecovery(action,args)) || profile.continuationActions.includes(action)) return;
  if (!authorizationCurrent(profile,blockTime)) throw Error('New-exposure authorization expired; reviewed recovery remains available.');
  if (stage === 'public') return;
  if (!authorization || !authorizationCurrent(authorization,blockTime)) throw Error('Exact canary run authorization expired.');
  const intent = authorization.intents.find(item => item.action === action && address(item.from) === address(tx.from) &&
    address(item.to) === address(tx.to) && item.data.toLowerCase() === tx.data.toLowerCase() && item.value === tx.value && item.nonce === tx.nonce);
  if (!intent || (tx.gas && quantity(tx.gas) > quantity(intent.maxGas)))
    throw Error('Transaction is outside the exact sender, nonce, calldata, value or gas scope of this canary.');
}
export async function verifyQualification(client, block, epoch, hashRuntime) {
  const profile = client.profile;
  for (const [contract, methods] of Object.entries(protocolChecks)) {
    for (const method of methods) {
      const response = await client.read('eth_call',[{to:client.contracts[contract],data:callData(method)},block.number],epoch);
      if (response.toLowerCase() !== profile.protocol[contract][method].toLowerCase())
        throw Error(`${contract}.${method}: live authority or economic parameter changed.`);
    }
  }
  for (let role=0;role<3;role++) {
    if ((await client.call('Access','roots',[String(role)],block.number,epoch))[0] !== profile.protocol.Access.roots[role].toLowerCase())
      throw Error('Namespace root differs from the reviewed deployment.');
  }
  const ens = (await client.call('Access','ens',[],block.number,epoch))[0];
  const wrapper = (await client.call('Access','wrapper',[],block.number,epoch))[0];
  if (ens !== address(profile.dependencies.ENS.address) ||
      wrapper !== (profile.dependencies.Wrapper === null ? zero : address(profile.dependencies.Wrapper.address)))
    throw Error('ENS or Wrapper dependency binding changed.');
  for (const dependency of Object.values(profile.dependencies)) {
    if (!dependency) continue;
    if (await hashRuntime(await client.read('eth_getCode',[dependency.address,block.number],epoch)) !== dependency.sha256)
      throw Error('External dependency runtime differs from the reviewed profile.');
    const checks = [...dependency.authority.checks];
    if (dependency.proxy) {
      const proxy = dependency.proxy;
      if (await hashRuntime(await client.read('eth_getCode',[proxy.implementation,block.number],epoch)) !== proxy.implementationSHA256)
        throw Error('Proxy implementation runtime changed.');
      checks.push(proxy.pointer);
    }
    for (const check of checks) {
      const actual = check.kind === 'storage'
        ? await client.read('eth_getStorageAt',[dependency.address,check.slot,block.number],epoch)
        : await client.read('eth_call',[{to:dependency.address,data:check.data},block.number],epoch);
      if (typeof actual !== 'string' || actual.toLowerCase() !== check.expected.toLowerCase())
        throw Error('External dependency implementation or authority observation changed.');
    }
  }
  return {authorizationCurrent:authorizationCurrent(profile,block.timestamp) &&
    (client.stage !== 'canary' || authorizationCurrent(client.authorization,block.timestamp))};
}
