// SPDX-License-Identifier: Apache-2.0
// Independent finite answer checker. No capability, constructor or producer import.
export function checkFutureOutput(charter, task, output, charge) {
    const rows = [];
    for (let state = 0; state < 2 ** charter.controls; state++) {
        charge('checking');
        const bits = Array.from({length: charter.controls}, (_, index) => Math.floor(state / 2 ** index) % 2);
        let value = 2 + bits.reduce((total, bit, index) => total + bit * [2, 2, 4, 6][index], 0);
        if (task.regime === 'coupled') value += 5 * bits[0] * bits[1] * bits[2];
        rows.push({mask: state, value});
    }
    let selected;
    if (task.kind === 'screen') selected = rows.filter(row => row.value >= task.parameter).map(row => row.mask);
    else if (task.kind === 'inverse') selected = rows.filter(row => row.value === task.parameter).map(row => row.mask);
    else {
        const eligible = rows.filter(row => row.mask.toString(2).replaceAll('0', '').length <= task.maxActiveControls);
        const optimum = Math.max(...eligible.map(row => row.value));
        selected = eligible.filter(row => row.value === optimum).map(row => row.mask);
    }
    for (const _row of rows) charge('checking');
    const accepted = output !== null && Array.isArray(output.rows) && Array.isArray(output.selected)
        && output.rows.length === rows.length && output.selected.length === selected.length
        && rows.every((row, index) => output.rows[index]?.mask === row.mask && output.rows[index]?.value === row.value)
        && selected.every((state, index) => output.selected[index] === state);
    return {accepted, reason: accepted ? 'Every finite output and task answer agrees with separately implemented semantics.'
        : 'The future output disagrees with the separately implemented current-regime semantics.',
    scope: 'Same-session independently implemented synthetic checker; no organizational reproduction.'};
}
