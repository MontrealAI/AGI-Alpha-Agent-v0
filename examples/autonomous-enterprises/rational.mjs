// SPDX-License-Identifier: Apache-2.0
export const MAX_RATIONAL_DIGITS = 128;
const need = (condition, message) => { if (!condition) throw Error(message); };
function gcd(a, b) { a = a < 0n ? -a : a; while (b) [a, b] = [b, a % b]; return a; }
export function ratio(n, d = 1n) {
    need(typeof n === 'bigint' && typeof d === 'bigint' && d !== 0n, 'Invalid rational operands.');
    if (d < 0n) { n = -n; d = -d; }
    const divisor = gcd(n, d); n /= divisor; d /= divisor;
    need(n.toString().length <= MAX_RATIONAL_DIGITS && d.toString().length <= MAX_RATIONAL_DIGITS,
        'Rational bit-growth limit exceeded.');
    return [n, d];
}
export function parse(value) {
    if (typeof value === 'number') {
        need(Number.isSafeInteger(value) && !Object.is(value, -0), 'Only exact safe integer numbers are admitted.');
        return [BigInt(value), 1n];
    }
    need(typeof value === 'string' && value.length <= 2 * MAX_RATIONAL_DIGITS + 1
        && /^-?(0|[1-9][0-9]*)(\/[1-9][0-9]*)?$/.test(value), 'Invalid rational encoding.');
    const parts = value.split('/'); const result = ratio(BigInt(parts[0]), BigInt(parts[1] || '1'));
    need(encode(result) === value, 'Rationals must use reduced canonical encoding.');
    return result;
}
export function encode(a) { return a[1] === 1n ? String(a[0]) : `${a[0]}/${a[1]}`; }
export const add = (a, b) => ratio(a[0] * b[1] + b[0] * a[1], a[1] * b[1]);
export const subtract = (a, b) => ratio(a[0] * b[1] - b[0] * a[1], a[1] * b[1]);
export const multiply = (a, b) => ratio(a[0] * b[0], a[1] * b[1]);
export const divide = (a, b) => ratio(a[0] * b[1], a[1] * b[0]);
export const negate = a => [-a[0], a[1]];
export const equal = (a, b) => a[0] === b[0] && a[1] === b[1];
export const zero = () => [0n, 1n];
