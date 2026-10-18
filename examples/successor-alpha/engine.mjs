// SPDX-License-Identifier: Apache-2.0

export const DEFAULT_LIMITS = Object.freeze({
    maxCsvBytes: 200000, maxRows: 1500, maxColumns: 32, maxCellChars: 4096,
    maxOutputPairs: 10000, maxOutputBytes: 2000000,
});

export const STRATEGIES = Object.freeze([
    Object.freeze({ id: 'nested_scan', label: 'Nested scan · current method' }),
    Object.freeze({ id: 'fixed_right_hash', label: 'Hash the right table · competitive baseline' }),
    Object.freeze({ id: 'smaller_side_hash', label: 'Hash the smaller table · candidate' }),
    Object.freeze({ id: 'sort_merge', label: 'Sort and merge · competitive baseline' }),
]);

const encoder = new TextEncoder();
const byteLength = value => encoder.encode(value).length;
const fail = message => { throw new Error(message); };
const ownKeys = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));

function limitsFor(overrides = {}) {
    if (!overrides || typeof overrides !== 'object' || Array.isArray(overrides)) fail('Limits must be an object.');
    if (Object.keys(overrides).some(key => !Object.hasOwn(DEFAULT_LIMITS, key))) fail('Unknown resource limit.');
    const limits = { ...DEFAULT_LIMITS, ...overrides };
    for (const [key, ceiling] of Object.entries(DEFAULT_LIMITS)) {
        if (!Number.isSafeInteger(limits[key]) || limits[key] < 1 || limits[key] > ceiling) {
            fail(`${key} must be an integer from 1 to ${ceiling}.`);
        }
    }
    return limits;
}

function freeze(value) {
    if (value && typeof value === 'object') {
        Object.freeze(value);
        for (const child of Object.values(value)) freeze(child);
    }
    return value;
}

export function parseCsv(text, overrides = {}) {
    const limits = limitsFor(overrides);
    if (typeof text !== 'string' || text.length > limits.maxCsvBytes || byteLength(text) > limits.maxCsvBytes) {
        fail(`Each CSV must contain at most ${limits.maxCsvBytes} UTF-8 bytes.`);
    }
    if (text.includes('\0')) fail('CSV cannot contain NUL characters.');
    if (text.startsWith('\uFEFF')) text = text.slice(1);
    if (!text.length) fail('CSV needs a header row.');
    const records = [];
    let record = [], field = '', quoted = false, closed = false, started = false;
    const fieldDone = () => {
        if (field.length > limits.maxCellChars) fail(`CSV cells exceed ${limits.maxCellChars} characters.`);
        record.push(field);
        if (record.length > limits.maxColumns) fail(`CSV exceeds ${limits.maxColumns} columns.`);
        field = ''; closed = false; started = false;
    };
    const recordDone = () => {
        fieldDone(); records.push(record); record = [];
        if (records.length > limits.maxRows + 1) fail(`CSV exceeds ${limits.maxRows} data rows.`);
    };
    for (let index = 0; index < text.length; index += 1) {
        const char = text[index];
        if (quoted) {
            if (char === '"') {
                if (text[index + 1] === '"') { field += '"'; index += 1; }
                else { quoted = false; closed = true; }
            } else field += char;
        } else if (char === ',') fieldDone();
        else if (char === '\r' || char === '\n') {
            if (char === '\r' && text[index + 1] === '\n') index += 1;
            recordDone();
        } else if (char === '"') {
            if (started || closed) fail('Quote inside an unquoted CSV cell.');
            quoted = true; started = true;
        } else {
            if (closed) fail('Unexpected text after a closing CSV quote.');
            field += char; started = true;
        }
        if (field.length > limits.maxCellChars) fail(`CSV cells exceed ${limits.maxCellChars} characters.`);
    }
    if (quoted) fail('Unclosed quoted CSV cell.');
    if (record.length || started || closed || field.length) recordDone();
    if (!records.length) fail('CSV needs a header row.');
    const [headers, ...rows] = records;
    if (headers.some(header => !header.trim()) || new Set(headers).size !== headers.length) {
        fail('CSV headers must be nonempty and unique.');
    }
    if (rows.some(row => row.length !== headers.length)) fail('Every CSV row must have the header column count.');
    return { headers, rows };
}

export function createJoinMission(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) fail('Mission inputs must be an object.');
    const allowed = ['leftCsv', 'rightCsv', 'leftKey', 'rightKey', 'limits'];
    if (Object.keys(input).some(key => !allowed.includes(key))) fail('Unknown mission input.');
    const limits = limitsFor(input.limits);
    const left = parseCsv(input.leftCsv, limits), right = parseCsv(input.rightCsv, limits);
    for (const [side, key] of [[left, input.leftKey], [right, input.rightKey]]) {
        if (typeof key !== 'string' || !side.headers.includes(key)) fail('Choose a key column present in each CSV.');
        side.key = key; side.keyIndex = side.headers.indexOf(key);
        if (side.rows.some(row => row[side.keyIndex] === '')) fail('Join keys must be nonempty exact strings.');
    }
    const frequencies = new Map();
    for (const row of right.rows) frequencies.set(row[right.keyIndex], (frequencies.get(row[right.keyIndex]) || 0) + 1);
    let outputPairs = 0;
    for (const row of left.rows) {
        outputPairs += frequencies.get(row[left.keyIndex]) || 0;
        if (outputPairs > limits.maxOutputPairs) fail(`Join exceeds ${limits.maxOutputPairs} output pairs.`);
    }
    return freeze({
        schemaVersion: 1, kind: 'catalog_join', left, right, limits,
        workload: { leftRows: left.rows.length, rightRows: right.rows.length,
            referenceComparisons: left.rows.length * right.rows.length, outputPairs },
    });
}

export function validateJoinMission(mission) {
    if (!ownKeys(mission, ['schemaVersion', 'kind', 'left', 'right', 'limits', 'workload'])
        || mission.schemaVersion !== 1 || mission.kind !== 'catalog_join') fail('Unsupported join mission.');
    if (!ownKeys(mission.limits, Object.keys(DEFAULT_LIMITS))) fail('Imported missions require all six resource limits.');
    const limits = limitsFor(mission.limits);
    for (const side of [mission.left, mission.right]) {
        if (!ownKeys(side, ['headers', 'rows', 'key', 'keyIndex']) || !Array.isArray(side.headers)
            || !side.headers.length || side.headers.length > limits.maxColumns
            || side.headers.some(header => typeof header !== 'string' || !header.trim()
                || header.length > limits.maxCellChars || header.includes('\0'))
            || new Set(side.headers).size !== side.headers.length || typeof side.key !== 'string'
            || !Number.isSafeInteger(side.keyIndex) || side.headers[side.keyIndex] !== side.key
            || !Array.isArray(side.rows) || side.rows.length > limits.maxRows) fail('Invalid mission table.');
        let bytes = side.headers.reduce((sum, header) => sum + byteLength(header), 0);
        if (bytes > limits.maxCsvBytes) fail('Mission table exceeds input budget.');
        for (const row of side.rows) {
            if (!Array.isArray(row) || row.length !== side.headers.length || row.some(cell => typeof cell !== 'string'
                || cell.length > limits.maxCellChars || cell.includes('\0')) || row[side.keyIndex] === '') {
                fail('Invalid mission row or empty key.');
            }
            bytes += row.reduce((sum, cell) => sum + byteLength(cell), 0);
            if (bytes > limits.maxCsvBytes) fail('Mission table exceeds input budget.');
        }
    }
    if (!ownKeys(mission.workload, ['leftRows', 'rightRows', 'referenceComparisons', 'outputPairs'])
        || mission.workload.leftRows !== mission.left.rows.length
        || mission.workload.rightRows !== mission.right.rows.length
        || mission.workload.referenceComparisons !== mission.left.rows.length * mission.right.rows.length
        || !Number.isSafeInteger(mission.workload.outputPairs) || mission.workload.outputPairs < 0
        || mission.workload.outputPairs > limits.maxOutputPairs) fail('Invalid mission workload.');
    const frequencies = new Map();
    for (const row of mission.right.rows) {
        const key = row[mission.right.keyIndex];
        frequencies.set(key, (frequencies.get(key) || 0) + 1);
    }
    let count = 0;
    for (const row of mission.left.rows) count += frequencies.get(row[mission.left.keyIndex]) || 0;
    if (count !== mission.workload.outputPairs || count > limits.maxOutputPairs) fail('Mission join count is invalid.');
    return true;
}

export const validateMission = validateJoinMission;

const pairOrder = (a, b) => a[0] - b[0] || a[1] - b[1];
const clock = () => globalThis.performance?.now() ?? Date.now();

export function executeJoin(mission, strategyId) {
    validateJoinMission(mission);
    const definition = STRATEGIES.find(strategy => strategy.id === strategyId);
    if (!definition) fail('Unknown join strategy.');
    const start = clock(), pairs = [];
    const metrics = { keyComparisons: 0, hashInserts: 0, hashProbes: 0,
        indexedRows: 0, sortedRows: 0, outputPairs: 0, logicalOperations: 0, elapsedMicros: 0 };
    const { left, right } = mission;
    let buildSide = null;
    const add = (leftIndex, rightIndex) => {
        if (pairs.length >= mission.limits.maxOutputPairs) fail('Join output budget exhausted.');
        pairs.push([leftIndex, rightIndex]);
    };
    if (strategyId === 'nested_scan') {
        for (let leftIndex = 0; leftIndex < left.rows.length; leftIndex += 1) {
            for (let rightIndex = 0; rightIndex < right.rows.length; rightIndex += 1) {
                metrics.keyComparisons += 1;
                if (left.rows[leftIndex][left.keyIndex] === right.rows[rightIndex][right.keyIndex]) add(leftIndex, rightIndex);
            }
        }
    } else if (strategyId === 'fixed_right_hash' || strategyId === 'smaller_side_hash') {
        buildSide = strategyId === 'smaller_side_hash' && left.rows.length < right.rows.length ? 'left' : 'right';
        const build = buildSide === 'left' ? left : right, probe = buildSide === 'left' ? right : left;
        const index = new Map();
        for (let row = 0; row < build.rows.length; row += 1) {
            const key = build.rows[row][build.keyIndex];
            if (!index.has(key)) index.set(key, []);
            index.get(key).push(row); metrics.hashInserts += 1;
        }
        metrics.indexedRows = build.rows.length;
        for (let row = 0; row < probe.rows.length; row += 1) {
            metrics.hashProbes += 1;
            for (const matched of index.get(probe.rows[row][probe.keyIndex]) || []) {
                if (buildSide === 'left') add(matched, row); else add(row, matched);
            }
        }
    } else {
        const ordered = side => {
            let source = side.rows.map((row, rowIndex) => ({ key: row[side.keyIndex], rowIndex }));
            let target = new Array(source.length);
            for (let width = 1; width < source.length; width *= 2) {
                for (let startIndex = 0; startIndex < source.length; startIndex += width * 2) {
                    const middle = Math.min(startIndex + width, source.length);
                    const end = Math.min(startIndex + width * 2, source.length);
                    let first = startIndex, second = middle;
                    for (let out = startIndex; out < end; out += 1) {
                        if (first >= middle) target[out] = source[second++];
                        else if (second >= end) target[out] = source[first++];
                        else {
                            metrics.keyComparisons += 1;
                            target[out] = source[first].key <= source[second].key ? source[first++] : source[second++];
                        }
                    }
                }
                [source, target] = [target, source];
            }
            return source;
        };
        const first = ordered(left), second = ordered(right);
        metrics.sortedRows = first.length + second.length;
        let a = 0, b = 0;
        while (a < first.length && b < second.length) {
            metrics.keyComparisons += 1;
            if (first[a].key < second[b].key) { a += 1; continue; }
            if (first[a].key > second[b].key) { b += 1; continue; }
            let endA = a + 1, endB = b + 1;
            while (endA < first.length) {
                metrics.keyComparisons += 1;
                if (first[endA].key !== first[a].key) break;
                endA += 1;
            }
            while (endB < second.length) {
                metrics.keyComparisons += 1;
                if (second[endB].key !== second[b].key) break;
                endB += 1;
            }
            for (let i = a; i < endA; i += 1) for (let j = b; j < endB; j += 1) add(first[i].rowIndex, second[j].rowIndex);
            a = endA; b = endB;
        }
    }
    pairs.sort(pairOrder);
    metrics.outputPairs = pairs.length;
    metrics.logicalOperations = metrics.keyComparisons + metrics.hashInserts + metrics.hashProbes + metrics.outputPairs;
    metrics.elapsedMicros = Math.max(0, Math.round((clock() - start) * 1000));
    return { strategyId, label: definition.label, buildSide, pairs, metrics };
}

function independentReference(mission) {
    const expected = [];
    for (let i = 0; i < mission.left.rows.length; i += 1) {
        const key = mission.left.rows[i][mission.left.keyIndex];
        for (let j = 0; j < mission.right.rows.length; j += 1) {
            if (key === mission.right.rows[j][mission.right.keyIndex]) expected.push([i, j]);
        }
    }
    if (expected.length !== mission.workload.outputPairs) fail('Mission output count differs from independent enumeration.');
    return expected;
}

export function verifyJoinResult(mission, pairs) {
    validateJoinMission(mission);
    if (!Array.isArray(pairs) || pairs.length > mission.limits.maxOutputPairs) fail('Invalid join output.');
    const expected = independentReference(mission);
    if (pairs.length !== expected.length || pairs.some((pair, index) => !Array.isArray(pair) || pair.length !== 2
        || pair[0] !== expected[index][0] || pair[1] !== expected[index][1])) fail('Join output failed independent exact verification.');
    return true;
}

function reconcile(mission, pairs) {
    const { left, right } = mission;
    const sharedFields = left.headers.flatMap((name, leftColumn) => {
        const rightColumn = right.headers.indexOf(name);
        return leftColumn !== left.keyIndex && rightColumn >= 0 && rightColumn !== right.keyIndex
            ? [{ name, leftColumn, rightColumn }] : [];
    });
    const matchedLeft = new Set(), matchedRight = new Set(), conflicts = [];
    for (const [leftIndex, rightIndex] of pairs) {
        matchedLeft.add(leftIndex); matchedRight.add(rightIndex);
        const fieldIndices = sharedFields.flatMap((field, index) =>
            left.rows[leftIndex][field.leftColumn] !== right.rows[rightIndex][field.rightColumn] ? [index] : []);
        if (fieldIndices.length) conflicts.push({ leftIndex, rightIndex, fieldIndices });
    }
    return { matchedPairs: pairs.length, matchedLeftRows: matchedLeft.size, matchedRightRows: matchedRight.size,
        unmatchedLeft: left.rows.flatMap((_, index) => matchedLeft.has(index) ? [] : [index]),
        unmatchedRight: right.rows.flatMap((_, index) => matchedRight.has(index) ? [] : [index]), sharedFields, conflicts };
}

export async function runJoinExperiment(mission, options = {}) {
    validateJoinMission(mission);
    if (!options || typeof options !== 'object' || Array.isArray(options)
        || Object.keys(options).some(key => !['checkpoint', 'signal', 'onProgress'].includes(key))) fail('Invalid experiment options.');
    const checkpoint = async () => {
        if (options.signal?.aborted) fail('Experiment stopped. No result was admitted.');
        if (options.checkpoint) await options.checkpoint();
        if (options.signal?.aborted) fail('Experiment stopped. No result was admitted.');
    };
    await checkpoint();
    const expected = independentReference(mission), strategies = [];
    for (const definition of STRATEGIES) {
        await checkpoint();
        options.onProgress?.({ strategyId: definition.id, completed: strategies.length, total: STRATEGIES.length });
        const result = executeJoin(mission, definition.id);
        if (result.pairs.length !== expected.length || result.pairs.some((pair, index) =>
            pair[0] !== expected[index][0] || pair[1] !== expected[index][1])) fail('A strategy failed independent exact verification.');
        strategies.push({ ...result, verified: true });
    }
    await checkpoint();
    return experimentResult(mission, strategies, expected);
}

function experimentResult(mission, strategies, expected) {
    const candidate = strategies.find(result => result.strategyId === 'smaller_side_hash');
    const comparisons = strategies.filter(result => result !== candidate).map(result => ({
        strategyId: result.strategyId,
        logicalOperationsSaved: result.metrics.logicalOperations - candidate.metrics.logicalOperations,
        indexedRowsSaved: result.metrics.indexedRows - candidate.metrics.indexedRows,
        auxiliaryRowsSaved: result.metrics.indexedRows + 2 * result.metrics.sortedRows - candidate.metrics.indexedRows,
        observedMicrosSaved: result.metrics.elapsedMicros - candidate.metrics.elapsedMicros,
    }));
    return {
        schemaVersion: 1, missionKind: 'catalog_join', candidateStrategyId: 'smaller_side_hash',
        incumbentStrategyId: 'nested_scan', strategies, reconciliation: reconcile(mission, expected),
        assessment: { state: 'local_demonstration', independentReview: 'pending', externalAuthority: false,
            superiorityClaim: false, novelAlgorithm: false, localCorrectness: true, comparisons,
            explanation: 'All four methods returned the same complete join. Smaller-side hashing is a known heuristic. '
                + 'Operation and auxiliary-row counts describe this workload; timings are single local observations. '
                + 'Independent confirmation and economic benefit remain unestablished.' },
        measurementNotes: [
            'Keys are exact, case-sensitive strings; no trimming or numeric conversion. Duplicate keys preserve every matching row pair.',
            'A conflict means unequal exact text in a shared non-key column, not evidence that either catalog is wrong.',
            'Logical operations count key comparisons, indexed-row insertions, hash probes, and emitted pairs. '
                + 'They omit string length, hashing internals, allocation, canonical output sorting, verification, and export costs.',
            'indexedRows/sortedRows count indexed row references or sorted records, not bytes or measured peak memory. '
                + 'Merge sorting also uses a scratch array of the same total row count.',
            'One bounded execution per method; no statistical timing claim, cost saving, model discovery, or external certification.',
            'CSV exports prefix formula-like cells with an apostrophe for spreadsheet safety; exact JSON preserves original strings.',
        ],
    };
}

function sameData(left, right) {
    if (left === right) return true;
    if (Array.isArray(left) || Array.isArray(right)) return Array.isArray(left) && Array.isArray(right)
        && left.length === right.length && left.every((value, index) => sameData(value, right[index]));
    if (left && right && typeof left === 'object' && typeof right === 'object') {
        const keys = Object.keys(left);
        return keys.length === Object.keys(right).length && keys.every(key => Object.hasOwn(right, key) && sameData(left[key], right[key]));
    }
    return false;
}

export function verifyExperiment(mission, result) {
    validateJoinMission(mission);
    if (!result || typeof result !== 'object' || !Array.isArray(result.strategies)
        || result.strategies.length !== STRATEGIES.length) fail('Invalid experiment report.');
    const expected = independentReference(mission), checked = [];
    for (let index = 0; index < STRATEGIES.length; index += 1) {
        const actual = result.strategies[index];
        if (!actual || actual.strategyId !== STRATEGIES[index].id || !actual.metrics
            || !Number.isSafeInteger(actual.metrics.elapsedMicros) || actual.metrics.elapsedMicros < 0) {
            fail('Invalid strategy record or historical timing.');
        }
        const recomputed = executeJoin(mission, STRATEGIES[index].id);
        recomputed.metrics.elapsedMicros = actual.metrics.elapsedMicros;
        const verified = { ...recomputed, verified: true };
        if (!sameData(verified, actual) || recomputed.pairs.length !== expected.length
            || recomputed.pairs.some((pair, row) => pair[0] !== expected[row][0] || pair[1] !== expected[row][1])) {
            fail('Experiment record differs from deterministic recomputation.');
        }
        checked.push(verified);
    }
    if (!sameData(experimentResult(mission, checked, expected), result)) {
        fail('Experiment assessment or reconciliation differs from deterministic recomputation.');
    }
    return { valid: true, correctnessRecomputed: true, operationCountsRecomputed: true,
        historicalTimingsVerified: false, externalIndependence: false };
}

function csvText(rows, limits, spreadsheetSafe = true) {
    const lines = [];
    let bytes = 0;
    for (const row of rows) {
        const line = row.map(value => {
            let cell = String(value);
            if (spreadsheetSafe && /^(?:\s*[=+\-@]|[\t\r\n])/.test(cell)) cell = `'${cell}`;
            return /[",\r\n]/.test(cell) ? `"${cell.replaceAll('"', '""')}"` : cell;
        }).join(',') + '\r\n';
        bytes += byteLength(line);
        if (bytes > limits.maxOutputBytes) fail(`CSV artifact exceeds ${limits.maxOutputBytes} bytes.`);
        lines.push(line);
    }
    return lines.join('');
}

export function exportJoinedCsv(mission, pairs) {
    verifyJoinResult(mission, pairs);
    const headers = [...mission.left.headers.map(header => `left.${header}`), ...mission.right.headers.map(header => `right.${header}`)];
    function* rows() {
        yield headers;
        for (const [a, b] of pairs) yield [...mission.left.rows[a], ...mission.right.rows[b]];
    }
    return csvText(rows(), mission.limits);
}

export function exportReconciliationCsv(mission, reconciliation, type = 'conflicts') {
    validateJoinMission(mission);
    const actual = reconcile(mission, independentReference(mission));
    if (!sameData(actual, reconciliation)) fail('Reconciliation differs from independent source checking.');
    if (type === 'unmatched_left' || type === 'unmatched_right') {
        const side = type === 'unmatched_left' ? mission.left : mission.right;
        const indices = type === 'unmatched_left' ? actual.unmatchedLeft : actual.unmatchedRight;
        return csvText([side.headers, ...indices.map(index => side.rows[index])], mission.limits);
    }
    if (type !== 'conflicts') fail('Unknown reconciliation artifact.');
    function* rows() {
        yield ['key', 'left_data_row', 'right_data_row', 'field', 'left_value', 'right_value'];
        for (const conflict of actual.conflicts) for (const index of conflict.fieldIndices) {
            const field = actual.sharedFields[index];
            yield [mission.left.rows[conflict.leftIndex][mission.left.keyIndex], conflict.leftIndex + 1,
                conflict.rightIndex + 1, field.name, mission.left.rows[conflict.leftIndex][field.leftColumn],
                mission.right.rows[conflict.rightIndex][field.rightColumn]];
        }
    }
    return csvText(rows(), mission.limits);
}

export function buildArtifacts(mission, result) {
    verifyExperiment(mission, result);
    const candidate = result.strategies.find(strategy => strategy.strategyId === 'smaller_side_hash');
    if (!candidate) fail('Candidate result is missing.');
    const joinedCsv = exportJoinedCsv(mission, candidate.pairs);
    const unmatchedLeftCsv = exportReconciliationCsv(mission, result.reconciliation, 'unmatched_left');
    const unmatchedRightCsv = exportReconciliationCsv(mission, result.reconciliation, 'unmatched_right');
    const conflictsCsv = exportReconciliationCsv(mission, result.reconciliation, 'conflicts');
    const exactJson = JSON.stringify({ schemaVersion: 1, mission, result }, null, 2) + '\n';
    if (byteLength(exactJson) > mission.limits.maxOutputBytes * 4) fail('Exact JSON artifact exceeds its 8 MB ceiling.');
    return { joinedCsv, unmatchedLeftCsv, unmatchedRightCsv, conflictsCsv, exactJson };
}

export function createSampleMission(options = {}) {
    if (!options || typeof options !== 'object' || Array.isArray(options)
        || Object.keys(options).some(key => !['seed', 'leftRows', 'rightRows'].includes(key))) fail('Invalid sample options.');
    const { seed = 41, leftRows = 120, rightRows = 360 } = options;
    if (!Number.isSafeInteger(seed) || seed < 0 || seed > 0xffffffff || !Number.isSafeInteger(leftRows)
        || !Number.isSafeInteger(rightRows) || leftRows < 1 || rightRows < 1
        || leftRows > DEFAULT_LIMITS.maxRows || rightRows > DEFAULT_LIMITS.maxRows) fail('Invalid sample seed or row count.');
    let state = seed >>> 0;
    const random = () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state; };
    const left = [['sku', 'title', 'revision']];
    for (let index = 0; index < leftRows; index += 1) left.push([`OPEN-${String(index).padStart(5, '0')}`, `Public catalog item ${index}`, `r${random() % 4}`]);
    const right = [['sku', 'title', 'revision', 'license']];
    for (let index = 0; index < rightRows; index += 1) {
        const key = index < Math.min(leftRows, rightRows) ? index : leftRows + index;
        const source = left[key + 1];
        right.push([`OPEN-${String(key).padStart(5, '0')}`, `Public catalog item ${key}`,
            source && index % 7 !== 0 ? source[2] : `r${random() % 4}`, 'CC0 synthetic']);
    }
    const leftCsv = csvText(left, DEFAULT_LIMITS, false), rightCsv = csvText(right, DEFAULT_LIMITS, false);
    return createJoinMission({ leftCsv, rightCsv, leftKey: 'sku', rightKey: 'sku' });
}
