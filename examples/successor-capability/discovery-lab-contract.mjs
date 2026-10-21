// SPDX-License-Identifier: Apache-2.0
// Shared bounded data language. Admission grants no execution authority.
export const MAX_INPUT_BYTES = 2_000_000;
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
    let nodes = 0, codeUnits = 0;
    const charge = count => {
        codeUnits += count;
        if (codeUnits > MAX_INPUT_BYTES) throw Error('Canonical JSON exceeds 2 MB');
    };
    const token = text => { charge(text.length); return text; };
    function encode(item, depth = 0) {
        if (++nodes > 100000 || depth > 32) throw Error('JSON complexity exceeds limit');
        if (Array.isArray(item) && item.length >= 100000) throw Error('JSON complexity exceeds limit');
        if (item === null || typeof item === 'boolean') return token(JSON.stringify(item));
        if (typeof item === 'string') {
            if (item.length > MAX_INPUT_BYTES - 2) throw Error('Canonical JSON exceeds 2 MB');
            if (scalar(item)) return token(JSON.stringify(item));
        }
        if (typeof item === 'number' && Number.isSafeInteger(item) && !Object.is(item, -0)) return token(String(item));
        let ownKeys;
        if (item && typeof item === 'object') {
            ownKeys = Reflect.ownKeys(item);
            const array = Array.isArray(item), width = ownKeys.length - (array ? 1 : 0);
            if (width > 100000 - nodes) throw Error('JSON complexity exceeds limit');
            // Bound width and the minimum serialized size before allocating descriptors.
            let minimum = 2 + Math.max(0, (array ? item.length : width) - 1);
            if (array) minimum += item.length;
            for (const key of ownKeys) {
                if (typeof key !== 'string') throw Error('Symbol data is unsupported');
                if (!array) minimum += key.length + 4; // Quotes, colon and at least one value byte.
                if (minimum > MAX_INPUT_BYTES - codeUnits) throw Error('Canonical JSON exceeds 2 MB');
            }
            for (const key of ownKeys) {
                const descriptor = Object.getOwnPropertyDescriptor(item, key);
                if (!descriptor || !Object.hasOwn(descriptor, 'value')) throw Error('Accessor data is unsupported');
                if (Array.isArray(item) && key === 'length') continue;
                if (!descriptor.enumerable) throw Error('Non-enumerable data is unsupported');
                if (Array.isArray(item) && (!/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= item.length)) {
                    throw Error('Extra array properties are unsupported');
                }
            }
        }
        if (Array.isArray(item)) {
            if (Object.getPrototypeOf(item) !== Array.prototype) throw Error('Non-standard arrays are unsupported');
            for (let i = 0; i < item.length; i++) if (!Object.hasOwn(item, i)) throw Error('Sparse arrays are not JSON');
            charge(2 + Math.max(0, item.length - 1));
            return '[' + item.map(v => encode(v, depth + 1)).join(',') + ']';
        }
        if (item && typeof item === 'object' && [Object.prototype, null].includes(Object.getPrototypeOf(item))) {
            const keys = ownKeys.sort();
            charge(2 + Math.max(0, keys.length - 1));
            return '{' + keys.map(key => {
                if (key.length > MAX_INPUT_BYTES - 3) throw Error('Canonical JSON exceeds 2 MB');
                if (!/^[\x20-\x7e]+$/.test(key)) throw Error('Object keys must be printable ASCII');
                return token(JSON.stringify(key) + ':') + encode(item[key], depth + 1);
            }).join(',') + '}';
        }
        throw Error('Unsupported JSON value; integers and Unicode scalars required');
    }
    const result = encode(value);
    if (result.length > MAX_INPUT_BYTES || new TextEncoder().encode(result).length > MAX_INPUT_BYTES) {
        throw Error('Canonical JSON exceeds 2 MB');
    }
    return result;
}
export const REQUEST_SCHEMA = 'successor-discovery-work-request/v1';
// Declared bounded admission work, not measured VM instructions or currency.
export const DISCOVERY_LAB_INSPECTION_CHECKS = 10000;
export const STAGES = Object.freeze(['learn', 'think', 'design', 'strategise', 'execute', 'evolve']);
export const RESOURCE_KEYS = Object.freeze([
    'acquisitions', 'search', 'checking', 'memoryBytes', 'storageBytes', 'workerCapacity', 'installations', 'elapsedMs'
]);
export const BINDING_KEYS = Object.freeze([
    'missionId', 'revision', 'purposeDigest', 'charterDigest', 'modelDigest', 'sourceDigest', 'evaluatorDigest'
]);
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const hash = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const nonnegative = value => Number.isSafeInteger(value) && value >= 0 && !Object.is(value, -0);
const identifier = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(value);
export async function payloadDigest(value) {
    const bytes = new TextEncoder().encode(canonical(value));
    return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))]
        .map(value => value.toString(16).padStart(2, '0')).join('');
}
export function validateResources(value) {
    canonical(value);
    if (!exact(value, RESOURCE_KEYS) || !RESOURCE_KEYS.every(key => nonnegative(value[key]))) {
        throw Error('Invalid Discovery Lab resource vector.');
    }
    return JSON.parse(canonical(value));
}
export function validateBindings(value) {
    canonical(value);
    if (!exact(value, BINDING_KEYS)
        || typeof value.missionId !== 'string'
        || !/^capability-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value.missionId)
        || !nonnegative(value.revision)
        || !BINDING_KEYS.slice(2).every(key => hash(value[key]))) {
        throw Error('Invalid Discovery Lab source or mission bindings.');
    }
    return JSON.parse(canonical(value));
}
export async function validateWorkRequest(input) {
    canonical(input);
    const keys = ['schema', ...BINDING_KEYS, 'stage', 'inputArtifacts', 'resourceLimits', 'executionMode',
        'commission', 'payloadDigest', 'payload'];
    if (!exact(input, keys) || input.schema !== REQUEST_SCHEMA) throw Error('Unsupported Discovery Lab request schema.');
    validateBindings(Object.fromEntries(BINDING_KEYS.map(key => [key, input[key]])));
    if (!STAGES.includes(input.stage) || !Array.isArray(input.inputArtifacts) || input.inputArtifacts.length > 6
        || !input.inputArtifacts.every(hash) || new Set(input.inputArtifacts).size !== input.inputArtifacts.length) {
        throw Error('Unsupported Discovery Lab stage or input artifacts.');
    }
    validateResources(input.resourceLimits);
    if (input.executionMode !== 'synthetic-local') throw Error('Discovery Lab execution mode is not provisioned.');
    const commission = input.commission;
    if (!exact(commission, ['id', 'branch', 'route', 'currency', 'capBaseUnits', 'status'])
        || !identifier(commission.id) || !identifier(commission.branch)
        || !['manager-usdc', 'jobs-agialpha'].includes(commission.route)
        || commission.currency !== (commission.route === 'manager-usdc' ? 'USDC6' : 'AGIALPHA18')
        || commission.capBaseUnits !== '0' || commission.status !== 'DRAFT_NOT_SUBMITTED') {
        throw Error('Discovery Lab commission route must be a single zero-cap draft.');
    }
    if (!input.payload || typeof input.payload !== 'object' || Array.isArray(input.payload)
        || !hash(input.payloadDigest) || input.payloadDigest !== await payloadDigest(input.payload)) {
        throw Error('Discovery Lab executable payload commitment mismatch.');
    }
    return JSON.parse(canonical(input));
}
export async function parseWorkRequest(text) {
    return validateWorkRequest(parseBounded(text));
}
/** Parse untrusted imports before they can allocate large or deeply nested objects. */
export function parseBounded(text) {
    if (typeof text !== 'string' || text.length > MAX_INPUT_BYTES
        || new TextEncoder().encode(text).length > MAX_INPUT_BYTES) throw Error('Import exceeds 2 MB');
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
