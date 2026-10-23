// SPDX-License-Identifier: Apache-2.0
import { optionalMeter, deepFreeze } from './protocol.mjs';
import { bindQuery } from './representation.mjs';

export const ALGEBRA = 'boolean-or-and';
export function booleanReduce(representation, query, { meter } = {}) {
  meter = optionalMeter(meter);
  const bound = bindQuery(representation, query, { meter });
  const values = representation.nodes.map(() => false);
  for (const seed of bound.seeds) { meter.tick('boolean-seed-or'); values[bound.index.get(seed.node)] ||= seed.amount > 0; }
  for (const node of representation.order) { meter.tick('boolean-node'); const source = bound.index.get(node); for (const edge of representation.adjacency[source]) { meter.tick('boolean-or'); values[edge.to] ||= values[source]; } }
  return deepFreeze(bound.targets.map(group => { meter.tick('boolean-output'); return { group, amount: values[bound.index.get(group)] ? '1' : '0' }; }));
}
