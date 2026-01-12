// SPDX-License-Identifier: Apache-2.0
export function consilience(scores) {
  const vals = Object.values(scores);
  const avg = vals.reduce((sum, v) => sum + v, 0) / vals.length;
  const variance = vals.reduce((sum, v) => sum + (v - avg) ** 2, 0) / vals.length;
  return 1 - Math.sqrt(variance);
}
