// SPDX-License-Identifier: Apache-2.0
import type { Individual } from '../state/serializer';

export function paretoFront(pop: Individual[]): Individual[] {
  if (pop.length === 0) return [];

  // Sort by logic (desc) then feasible (desc) and scan once.
  const sorted = [...pop].sort(
    (a, b) => b.logic - a.logic || b.feasible - a.feasible,
  );

  const front: Individual[] = [];
  let bestFeasible = -Infinity;
  for (const p of sorted) {
    if (p.feasible >= bestFeasible) {
      front.push(p);
      bestFeasible = p.feasible;
    }
  }

  return front;
}
