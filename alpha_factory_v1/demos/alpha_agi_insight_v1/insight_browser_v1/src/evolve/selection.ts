// SPDX-License-Identifier: Apache-2.0
export function selectPopulation<T>(candidates: T[], front: T[], requested: number): T[] {
  if (!Number.isFinite(requested) || requested < 1) throw new Error('Population size must be positive');
  const limit = Math.min(10000, Math.floor(requested));
  const elites = [...new Set(front)].slice(0, limit);
  const selected = new Set(elites);
  for (const candidate of candidates) {
    if (selected.size >= limit) break;
    selected.add(candidate);
  }
  return [...selected];
}
