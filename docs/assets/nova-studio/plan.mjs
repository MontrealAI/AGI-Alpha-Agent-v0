// SPDX-License-Identifier: Apache-2.0
import {AbiCoder, keccak256, toUtf8Bytes, concat} from './vendor/ethers-6.17.0.min.mjs';
import {units, tokens} from '../ascension-wallet/protocol.mjs';
import {canonicalJSON} from '../ascension/crypto.mjs';

export const PLAN_SCHEMA = 'agialpha.ascension.fusion-plan.v1';
const coder = AbiCoder.defaultAbiCoder();
const fields = ['goal', 'successMetric', 'bounty', 'duration', 'priceWeight'];
export const toBaseUnits = text => units(text).toString();
export const formatTokens = value => tokens(value);

function specification(value) {
  if (!value || Object.getPrototypeOf(value) !== Object.prototype || Object.keys(value).length !== fields.length ||
      !fields.every(field => Object.hasOwn(value, field))) throw Error('A job requires exactly goal, successMetric, bounty, duration and priceWeight.');
  for (const key of ['goal', 'successMetric']) {
    if (typeof value[key] !== 'string' || !value[key].length || toUtf8Bytes(value[key]).length > 512)
      throw Error('Each goal and acceptance criterion must contain 1–512 UTF-8 bytes.');
  }
  if (typeof value.bounty !== 'string' || !/^[1-9][0-9]{0,28}$/.test(value.bounty) ||
      BigInt(value.bounty) < 100n || BigInt(value.bounty) >= 2n ** 96n)
    throw Error('Bounty must be 100 through uint96 maximum in exact $AGIALPHA base units.');
  if (!Number.isInteger(value.duration) || value.duration < 1 || value.duration > 90 * 86400)
    throw Error('Delivery duration must be 1–7776000 whole seconds (at most 90 days).');
  if (!Number.isInteger(value.priceWeight) || value.priceWeight < 0 || value.priceWeight > 10000)
    throw Error('Price preference must be a whole number from 0 through 10000.');
  return Object.fromEntries(fields.map(field => [field, value[field]]));
}

export function leaf(index, value) {
  if (!Number.isInteger(index) || index < 0 || index >= 2 ** 32) throw Error('Job index must fit uint32.');
  const spec = specification(value);
  return keccak256(keccak256(coder.encode(
    ['uint32', 'bytes32', 'bytes32', 'uint96', 'uint32', 'uint16'],
    [index, keccak256(toUtf8Bytes(spec.goal)), keccak256(toUtf8Bytes(spec.successMetric)),
      spec.bounty, spec.duration, spec.priceWeight],
  )));
}

const pair = (left, right) => keccak256(concat([left, right].sort()));
export function compilePlan(source) {
  if (!Array.isArray(source) || source.length < 1 || source.length > 128)
    throw Error('A FusionPlan requires 1–128 ordered job specifications.');
  const specs = source.map(specification), levels = [specs.map((spec, index) => leaf(index, spec))];
  while (levels.at(-1).length > 1) {
    const previous = levels.at(-1), next = [];
    for (let index = 0; index < previous.length; index += 2)
      next.push(index + 1 < previous.length ? pair(previous[index], previous[index + 1]) : previous[index]);
    levels.push(next);
  }
  const result = {
    schema: PLAN_SCHEMA, token: 'AGIALPHA', decimals: 18, planRoot: levels.at(-1)[0],
    totalBounty: specs.reduce((sum, spec) => sum + BigInt(spec.bounty), 0n).toString(),
    jobs: specs.map((spec, index) => {
      const proof = [];
      let position = index;
      for (const level of levels.slice(0, -1)) {
        if ((position ^ 1) < level.length) proof.push(level[position ^ 1]);
        position = Math.floor(position / 2);
      }
      return {index, spec, leaf: levels[0][index], proof};
    }),
  };
  canonicalJSON(result);
  return result;
}

export function verifyPlan(plan) {
  if (!plan || !Array.isArray(plan.jobs)) throw Error('Invalid FusionPlan structure.');
  const rebuilt = compilePlan(plan.jobs.map(job => job?.spec));
  if (canonicalJSON(rebuilt) !== canonicalJSON(plan))
    throw Error('FusionPlan commitment, proofs, order or metadata do not match.');
  return rebuilt;
}

export function verifyProof(index, spec, proof, root) {
  if (!Array.isArray(proof) || proof.length > 7 || !/^0x[0-9a-f]{64}$/.test(root)) return false;
  let hash = leaf(index, spec);
  for (const sibling of proof) {
    if (!/^0x[0-9a-f]{64}$/.test(sibling)) return false;
    hash = pair(hash, sibling);
  }
  return hash === root;
}
