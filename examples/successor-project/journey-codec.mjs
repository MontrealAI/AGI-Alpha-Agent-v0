// SPDX-License-Identifier: Apache-2.0
/** Strict outer journey codec; native record readers retain their own smaller limits. */
export const VERSION = 'alpha-guided-json/v1';
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join('|') === [...keys].sort().join('|');
const integer = (value, low, high) => Number.isSafeInteger(value) && value >= low && value <= high;
function scalar(value) {
    if (typeof value !== 'string') return false;
    for (let i = 0; i < value.length; i++) {
        const c = value.charCodeAt(i);
        if (c >= 0xd800 && c <= 0xdbff) {
            const next = value.charCodeAt(++i);
            if (!(next >= 0xdc00 && next <= 0xdfff)) return false;
        } else if (c >= 0xdc00 && c <= 0xdfff) return false;
    }
    return true;
}
export function canonical(value) {
    let nodes = 0;
    function encode(item, depth = 0) {
        if (++nodes > 100000 || depth > 32) throw Error('JSON complexity exceeds limit');
        if (item === null || typeof item === 'boolean') return JSON.stringify(item);
        if (typeof item === 'string' && scalar(item)) return JSON.stringify(item);
        if (typeof item === 'number' && Number.isSafeInteger(item) && !Object.is(item, -0)) return String(item);
        if (Array.isArray(item)) {
            for (let i = 0; i < item.length; i++) if (!Object.hasOwn(item, i)) throw Error('Sparse arrays are not JSON');
            return '[' + item.map(v => encode(v, depth + 1)).join(',') + ']';
        }
        if (item && typeof item === 'object' && [Object.prototype, null].includes(Object.getPrototypeOf(item))) {
            return '{' + Object.keys(item).sort().map(key => {
                if (!/^[\x20-\x7e]+$/.test(key)) throw Error('Object keys must be printable ASCII');
                return JSON.stringify(key) + ':' + encode(item[key], depth + 1);
            }).join(',') + '}';
        }
        throw Error('Unsupported JSON value; integers and Unicode scalars required');
    }
    const result = encode(value);
    if (new TextEncoder().encode(result).length > 16000000) throw Error('Canonical JSON exceeds 16 MB');
    return result;
}
export async function digest(domain, value) {
    if (!/^[a-z][a-z0-9-]{0,63}$/.test(domain)) throw Error('Invalid digest domain');
    const bytes = new TextEncoder().encode('successor-omega/v1:' + domain + '\0' + canonical(value));
    return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), n => n.toString(16).padStart(2, '0')).join('');
}
/** Parse untrusted imports before they can allocate large or deeply nested objects. */
export function parseJourney(text) {
    if (typeof text !== 'string' || new TextEncoder().encode(text).length > 16_000_000) throw Error('Import exceeds 16 MB');
    let pos = 0, nodes = 0;
    const ws = () => { while (/[\x20\t\n\r]/.test(text[pos] || '\u0000')) pos++; };
    const string = () => {
        const start = pos++;
        while (pos < text.length) {
            if (text[pos] === '\\') { pos += 2; continue; }
            if (text[pos++] === '"') {
                const value = JSON.parse(text.slice(start, pos));
                if (!scalar(value)) throw Error('Malformed Unicode');
                return value;
            }
        }
        throw Error('Unterminated string');
    };
    function read(depth = 0) {
        if (++nodes > 100000 || depth > 32) throw Error('Import complexity exceeds limit');
        ws();
        if (text[pos] === '"') return string();
        if (text[pos] === '[' || text[pos] === '{') {
            const object = text[pos++] === '{', end = object ? '}' : ']';
            const value = object ? Object.create(null) : [];
            ws(); if (text[pos] === end) { pos++; return value; }
            while (true) {
                ws();
                if (object) {
                    if (text[pos] !== '"') throw Error('Expected object key');
                    const key = string(); ws();
                    if (Object.hasOwn(value, key)) throw Error('Duplicate JSON key');
                    if (text[pos++] !== ':') throw Error('Expected colon');
                    value[key] = read(depth + 1);
                } else value.push(read(depth + 1));
                ws(); const next = text[pos++];
                if (next === end) break;
                if (next !== ',') throw Error('Expected comma');
            }
            return value;
        }
        for (const [token, value] of [['true', true], ['false', false], ['null', null]]) {
            if (text.startsWith(token, pos)) { pos += token.length; return value; }
        }
        const match = /^-?(?:0|[1-9]\d*)(?![\d.eE+-])/.exec(text.slice(pos));
        if (!match) throw Error('Expected integer JSON value');
        pos += match[0].length; const value = Number(match[0]);
        if (!Number.isSafeInteger(value) || Object.is(value, -0)) throw Error('Unsafe integer');
        return value;
    }
    const value = read(); ws();
    if (pos !== text.length) throw Error('Trailing JSON content');
    canonical(value);
    return value;
}
