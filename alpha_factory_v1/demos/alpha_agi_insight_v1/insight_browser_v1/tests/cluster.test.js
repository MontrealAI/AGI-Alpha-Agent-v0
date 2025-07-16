// SPDX-License-Identifier: Apache-2.0
import { detectColdZone } from '../src/utils/cluster.ts';

test('detect coldest cell', () => {
  const pts = [
    [0.1, 0.1],
    [0.15, 0.15],
    [0.9, 0.9]
  ];
  const cz = detectColdZone(pts, 2);
  // Only one point falls in cell 1,1 leaving 0,1 empty
  expect(cz.x).toBe(0);
  expect(cz.y).toBe(1);
});
