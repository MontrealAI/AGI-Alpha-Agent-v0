// SPDX-License-Identifier: Apache-2.0
import { AbiCoder, keccak256, id, concat, toUtf8Bytes } from './vendor/ethers-6.17.0.mjs';
import { canonicalJSON } from '../ascension/crypto.mjs';
import { units, uint } from '../ascension-wallet/protocol.mjs';
const coder = AbiCoder.defaultAbiCoder();
const keys = ['goal', 'successMetric', 'bounty', 'duration', 'priceWeight'];
export function validateSpec(spec) {
  if (!spec || Object.keys(spec).sort().join() !== [...keys].sort().join()) throw Error('Use the five FusionPlan job fields.');
  for (const key of keys.slice(0, 2)) {
    if (typeof spec[key] !== 'string' || !spec[key].length || toUtf8Bytes(spec[key]).length > 512)
      throw Error('Goal and acceptance criteria each require 1–512 UTF-8 bytes.');
  }
  if (typeof spec.bounty !== 'string' || uint(spec.bounty, 96) < 100n) throw Error('Bounty must be at least 100 base units and fit uint96.');
  if (!Number.isInteger(spec.duration) || spec.duration < 1 || spec.duration > 90 * 86400)
    throw Error('Delivery duration must be 1–7,776,000 whole seconds.');
  if (!Number.isInteger(spec.priceWeight) || spec.priceWeight < 0 || spec.priceWeight > 10000)
    throw Error('Price preference must be 0–10,000 basis points.');
  return { ...spec };
}
export function jobFromEditor({ goal, successMetric, bounty, duration, priceWeight }) {
  return validateSpec({ goal, successMetric, bounty: units(bounty).toString(),
    duration: Number(uint(String(duration), 32)), priceWeight: Number(uint(String(priceWeight), 16)) });
}
export function leaf(index, spec) {
  validateSpec(spec);
  return keccak256(keccak256(coder.encode(['uint32','bytes32','bytes32','uint96','uint32','uint16'],
    [index, id(spec.goal), id(spec.successMetric), spec.bounty, spec.duration, spec.priceWeight])));
}
export const pair = (a, b) => keccak256(concat([a, b].sort()));
export function compilePlan(source) {
  if (!Array.isArray(source) || !source.length || source.length > 128) throw Error('A plan requires 1–128 jobs.');
  const specs = source.map(validateSpec), levels = [specs.map((s, i) => leaf(i, s))];
  while (levels.at(-1).length > 1) {
    const previous = levels.at(-1), next = [];
    for (let i = 0; i < previous.length; i += 2) next.push(i + 1 < previous.length ? pair(previous[i], previous[i + 1]) : previous[i]);
    levels.push(next);
  }
  const result = { schema:'agialpha.ascension.fusion-plan.v1', token:'AGIALPHA', decimals:18,
    planRoot:levels.at(-1)[0], totalBounty:specs.reduce((s, x) => s + BigInt(x.bounty), 0n).toString(),
    jobs:specs.map((spec, index) => {
      const proof = []; let position = index;
      for (const level of levels.slice(0, -1)) {
        if ((position ^ 1) < level.length) proof.push(level[position ^ 1]);
        position = Math.floor(position / 2);
      }
      return { index, spec, leaf:levels[0][index], proof };
    }) };
  canonicalJSON(result);
  return result;
}
export function verifyPlan(plan) {
  if (!Array.isArray(plan?.jobs)) throw Error('Missing executable FusionPlan.');
  const rebuilt = compilePlan(plan.jobs.map(j => j.spec));
  if (canonicalJSON(plan) !== canonicalJSON(rebuilt)) throw Error('Plan root, proofs, ordering or totals have changed.');
  return rebuilt;
}
