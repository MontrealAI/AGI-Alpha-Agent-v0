// SPDX-License-Identifier: Apache-2.0
// Deterministic specialist control. This is not a recruited human expert.
import { LIMITS, invariant, optionalMeter } from './protocol.mjs';
import { buildRepresentation, bindQuery } from './representation.mjs';
import { flatReduce } from './normalizer.mjs';

export function directReduce(mission, { meter, strategy = 'kahn-v1' } = {}) {
  meter = optionalMeter(meter);
  if (mission.kind === 'flat-reduction') return { representation: null, rows: flatReduce(mission.rows, { meter }) };
  const representation = buildRepresentation(mission.graph, { meter, strategy });
  const { index, seeds, targets } = bindQuery(representation, { seeds: mission.seeds, targets: mission.targets }, { meter });
  const values = representation.nodes.map(() => 0n);
  if (mission.kind === 'bom-demand') {
    for (const seed of seeds) { meter.tick('specialist-seed'); values[index.get(seed.node)] += BigInt(seed.amount); }
    for (const node of representation.order) { meter.tick('specialist-node'); for (const edge of representation.adjacency[index.get(node)]) { meter.tick('specialist-edge'); values[edge.to] += values[index.get(node)] * BigInt(edge.weight); invariant(values[edge.to].toString().length <= LIMITS.integerDigits, 'INTEGER_DIGIT_LIMIT', 'Specialist magnitude ceiling reached.'); } }
  } else {
    const queue = []; const seen = new Set();
    for (const seed of seeds) { meter.tick('specialist-seed'); if (seed.amount > 0 && !seen.has(seed.node)) { seen.add(seed.node); queue.push(seed.node); } }
    for (let cursor = 0; cursor < queue.length; cursor++) { meter.tick('specialist-node'); const node = queue[cursor]; values[index.get(node)] = 1n; for (const edge of representation.adjacency[index.get(node)]) { meter.tick('specialist-edge'); const child = representation.nodes[edge.to]; if (!seen.has(child)) { seen.add(child); queue.push(child); } } }
  }
  return { representation, rows: targets.map(group => { meter.tick('specialist-output'); return { group, amount: values[index.get(group)].toString() }; }) };
}
