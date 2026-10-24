// SPDX-License-Identifier: Apache-2.0
import { LIMITS, invariant, optionalMeter, deepFreeze } from './protocol.mjs';
import { bindQuery } from './representation.mjs';

export const ALGEBRA = 'nonnegative-integer-sum-product';
export function weightedReduce(representation, query, { meter } = {}) {
  meter = optionalMeter(meter);
  const bound = bindQuery(representation, query, { meter });
  const values = representation.nodes.map(() => 0n);
  for (const seed of bound.seeds) { meter.tick('weighted-seed-add'); values[bound.index.get(seed.node)] += BigInt(seed.amount); }
  for (const node of representation.order) {
    meter.tick('weighted-node'); const source = bound.index.get(node);
    for (const edge of representation.adjacency[source]) { meter.tick('weighted-multiply-add'); const next = values[edge.to] + values[source] * BigInt(edge.weight); invariant(next.toString().length <= LIMITS.integerDigits, 'INTEGER_DIGIT_LIMIT', 'Exact arithmetic magnitude ceiling reached.'); values[edge.to] = next; }
  }
  return deepFreeze(bound.targets.map(group => { meter.tick('weighted-output'); return { group, amount: values[bound.index.get(group)].toString() }; }));
}
