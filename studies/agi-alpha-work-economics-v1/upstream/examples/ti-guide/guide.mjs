// SPDX-License-Identifier: Apache-2.0
import * as alpha from '../successor-alpha/engine.mjs';
import * as research from '../successor-alpha/research.mjs';

export const SAMPLE = Object.freeze({
    leftCsv: 'item,name,price\nMUG,Stoneware mug,12\nMUG,Stoneware mug,14\nTEA,Green tea,8\nTEA,Green tea,9\nBOWL,Blue bowl,18\nLAMP,Desk lamp,35\n',
    rightCsv: 'item,name,price\nMUG,Stoneware mug,13\nTEA,Green tea,10\nBOWL,Blue bowl,18\nVASE,Glass vase,22\n',
    leftKey: 'item', rightKey: 'item',
});
export const LIMITATIONS = Object.freeze({
    localOnly: true, authority: 'none', automaticallyResolved: false,
    timeSavedMeasured: false, accuracyImprovementMeasured: false,
    supportedTask: 'Exact string identifiers; compare shared non-identifier column names. No fuzzy matching or automatic correction.',
    sourceRows: 'Data rows are numbered from 1 after the header. Quoted multiline cells are one data row.',
    duplicates: 'Duplicate identifiers retain every matching pair; they are never silently deduplicated.',
    csvSafety: 'CSV cells starting with formula characters receive a leading apostrophe. Workspace retains exact originals.',
});
const fail = message => { throw Error(message); };
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
export function canonical(value) {
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    if (value && typeof value === 'object') return '{' + Object.keys(value).sort()
        .map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
    return JSON.stringify(value);
}
export function preview(csv) { return alpha.parseCsv(csv); }
export function safeCsv(rows) {
    let bytes = 0;
    return rows.map(row => {
        const line = row.map(value => {
            let cell = String(value ?? '');
            if (/^(?:\s*[=+\-@]|[\t\r\n])/.test(cell)) cell = "'" + cell;
            return '"' + cell.replaceAll('"', '""') + '"';
        }).join(',') + '\r\n';
        bytes += new TextEncoder().encode(line).length;
        if (bytes > 2000000) fail('The download exceeds 2 MB. Use smaller lists.');
        return line;
    }).join('');
}
async function digest(text) {
    const bytes = new TextEncoder().encode(text);
    const value = await crypto.subtle.digest('SHA-256', bytes);
    return { sha256: [...new Uint8Array(value)].map(x => x.toString(16).padStart(2, '0')).join(''), bytes: bytes.length };
}
export async function compute(input, progress = () => {}) {
    if (!exact(input, ['leftCsv', 'rightCsv', 'leftKey', 'rightKey'])) fail('Unsupported list settings.');
    input = { ...input };
    progress('parse');
    const mission = alpha.createJoinMission(input);
    const leftIdentity = await digest(input.leftCsv), rightIdentity = await digest(input.rightCsv);
    progress('compare');
    const resolution = research.resolveDiscrepancies(mission);
    progress('preserve');
    const differences = [];
    let differenceBytes = 0;
    const keep = difference => {
        differenceBytes += new TextEncoder().encode(JSON.stringify(difference)).length;
        if (differenceBytes > 1500000) fail('Full difference evidence exceeds 1.5 MB. Use smaller lists; nothing was truncated.');
        differences.push(difference);
    };
    for (const action of resolution.actions) {
        for (const occurrence of action.occurrences) {
            const [kind, a, b] = occurrence.split(':'), row = Number(a);
            if (kind === 'conflict') {
                const conflict = action.conflicts.find(x => x.leftIndex === row && x.rightIndex === Number(b));
                for (const f of conflict.fieldIndices) {
                    const field = resolution.sharedFields[f];
                    keep({ id: occurrence + ':' + f, occurrence, action: action.id, key: action.key,
                        kind, leftRow: row + 1, rightRow: Number(b) + 1, field: field.name,
                        leftValue: mission.left.rows[row][field.leftColumn],
                        rightValue: mission.right.rows[Number(b)][field.rightColumn] });
                }
            } else {
                const side = kind === 'left' ? mission.left : mission.right;
                keep({ id: occurrence, occurrence, action: action.id, key: action.key,
                    kind: kind === 'left' ? 'missing_from_right' : 'missing_from_left',
                    leftRow: kind === 'left' ? row + 1 : '', rightRow: kind === 'right' ? row + 1 : '', field: '',
                    leftValue: kind === 'left' ? JSON.stringify(side.rows[row]) : '',
                    rightValue: kind === 'right' ? JSON.stringify(side.rows[row]) : '' });
            }
        }
    }
    const refs = new Set(differences.map(x => x.occurrence));
    if (refs.size !== resolution.coverage.originalOccurrences
        || resolution.actions.some(x => x.occurrences.some(ref => !refs.has(ref)))) fail('Evidence coverage failed.');
    const duplicateInfo = side => {
        const counts = new Map();
        for (const row of side.rows) { const k = row[side.keyIndex]; counts.set(k, (counts.get(k) || 0) + 1); }
        return { keys: [...counts.values()].filter(x => x > 1).length,
            extraRows: [...counts.values()].reduce((n, x) => n + x - 1, 0) };
    };
    const missing = differences.filter(x => x.kind !== 'conflict');
    const result = { schema: 'ti-catalogue-result/v1', leftIdentity, rightIdentity, resolution, differences,
        metrics: { leftRows: mission.left.rows.length, rightRows: mission.right.rows.length,
            matchedPairs: mission.workload.outputPairs, unmatchedRows: missing.length,
            unmatchedKeys: new Set(missing.map(x => x.key)).size,
            conflictingPairs: resolution.actions.reduce((n, x) => n + x.conflicts.length, 0),
            fieldDifferences: differences.filter(x => x.kind === 'conflict').length,
            actionGroups: resolution.actions.length, evidenceReferences: refs.size,
            leftDuplicates: duplicateInfo(mission.left), rightDuplicates: duplicateInfo(mission.right),
            comparedColumns: resolution.sharedFields.map(x => x.name),
            unsharedLeft: mission.left.headers.filter((x, i) => i !== mission.left.keyIndex && !resolution.sharedFields.some(f => f.name === x)),
            unsharedRight: mission.right.headers.filter((x, i) => i !== mission.right.keyIndex && !resolution.sharedFields.some(f => f.name === x)) },
        limitations: LIMITATIONS };
    if (new TextEncoder().encode(JSON.stringify(result)).length > 6000000) fail('The result exceeds 6 MB. Use smaller lists.');
    fullDifferencesCsv(result);
    progress('complete');
    return result;
}
export function fullDifferencesCsv(result) {
    const fields = ['id', 'occurrence', 'action', 'key', 'kind', 'leftRow', 'rightRow', 'field', 'leftValue', 'rightValue'];
    return safeCsv([fields, ...result.differences.map(x => fields.map(f => x[f]))]);
}
export function actionPlanCsv(result) { return result.resolution.actionsCsv; }
export function makeWorkspace(input, result, { approach, sourceHash, runId, createdAt, language }) {
    if (!['grouped', 'original'].includes(approach) || !['en', 'fr'].includes(language)) fail('Unsupported workspace choice.');
    return { schema: 'ti-catalogue-workspace/v1', sourceHash, runId, createdAt, language, approach, input, result,
        limitations: LIMITATIONS, authority: 'none' };
}
export async function restoreWorkspace(raw, sourceHash, progress) {
    if (typeof raw !== 'string' || raw.length > 8000000 || new TextEncoder().encode(raw).length > 8000000) {
        fail('Workspaces must be no larger than 8 MB.');
    }
    const saved = JSON.parse(raw);
    if (!exact(saved, ['schema', 'sourceHash', 'runId', 'createdAt', 'language', 'approach', 'input', 'result', 'limitations', 'authority'])
        || saved.schema !== 'ti-catalogue-workspace/v1' || saved.sourceHash !== sourceHash
        || saved.authority !== 'none' || !['grouped', 'original'].includes(saved.approach)
        || !['en', 'fr'].includes(saved.language) || typeof saved.runId !== 'string' || saved.runId.length > 80
        || typeof saved.createdAt !== 'string' || !Number.isFinite(Date.parse(saved.createdAt))) fail('Unsupported workspace or method version. Reopen its original saved HTML.');
    const result = await compute(saved.input, progress);
    if (canonical(result) !== canonical(saved.result) || canonical(saved.limitations) !== canonical(LIMITATIONS)) {
        fail('The saved results differ from recomputation. No result or authority was restored.');
    }
    return saved;
}
