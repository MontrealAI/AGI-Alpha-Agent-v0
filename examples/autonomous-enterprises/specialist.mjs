// SPDX-License-Identifier: Apache-2.0
// A fixed conventional fast implementation; its authoring and institutional proof costs are unmeasured.
import * as q from './rational.mjs';
import {copy, need} from './protocol.mjs';
export function applySpecialist(kind, inputsInput) {
    const inputs = copy(inputsInput), n = inputs[0]?.length;
    need([2, 4, 8, 16, 32].includes(n) && inputs.length === (kind === 'xor-convolution' ? 2 : 1)
        && inputs.every(row => Array.isArray(row) && row.length === n), 'Specialist input scope mismatch.');
    let arithmetic = 0;
    function walsh(input) {
        const result = input.slice();
        for (let half = 1; half < n; half *= 2) {
            for (let start = 0; start < n; start += 2 * half) for (let j = 0; j < half; j++) {
                const a = result[start + j], b = result[start + half + j];
                result[start + j] = q.add(a, b); result[start + half + j] = q.subtract(a, b); arithmetic += 2;
            }
        }
        return result;
    }
    const rationalInputs = inputs.map(row => row.map(q.parse));
    let output;
    if (kind === 'walsh') output = walsh(rationalInputs[0]);
    else if (kind === 'xor-convolution') {
        const left = walsh(rationalInputs[0]), right = walsh(rationalInputs[1]);
        const products = left.map((value, i) => { arithmetic++; return q.multiply(value, right[i]); });
        output = walsh(products).map(value => { arithmetic++; return q.divide(value, q.parse(n)); });
    } else {
        need(kind === 'inverse', 'Unsupported specialist interface.');
        let total = rationalInputs[0][0];
        for (let i = 1; i < n; i++) { total = q.add(total, rationalInputs[0][i]); arithmetic++; }
        const offset = q.divide(total, q.parse(2 * n * n)); arithmetic++;
        output = rationalInputs[0].map(value => { arithmetic += 2; return q.subtract(q.divide(value, q.parse(n)), offset); });
    }
    return {output: output.map(q.encode), arithmetic};
}
