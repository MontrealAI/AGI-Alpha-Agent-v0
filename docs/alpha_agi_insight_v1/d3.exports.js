// SPDX-License-Identifier: Apache-2.0
const d3 = window.d3;
if (!d3) {
  throw new Error('d3 global not found');
}
export const select = d3.select;
export const selectAll = d3.selectAll;
export default d3;
