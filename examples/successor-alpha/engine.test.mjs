// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import {
    DEFAULT_LIMITS, STRATEGIES, parseCsv, createJoinMission, validateJoinMission, validateMission, verifyExperiment, executeJoin,
    verifyJoinResult, runJoinExperiment, exportJoinedCsv, exportReconciliationCsv, buildArtifacts, createSampleMission,
} from './engine.mjs';

const mission = () => createJoinMission({
    leftCsv: 'sku,title,revision\r\na,"A, one",1\r\na,A two,2\r\nb,B,1\r\nleft,L,1\r\n',
    rightCsv: 'id,title,revision\r\na,"A, one",1\r\na,A two,3\r\nb,B,1\r\nright,R,1\r\n',
    leftKey: 'sku', rightKey: 'id',
});

test('CSV accepts BOM, escaped quotes, quoted newlines and CRLF', () => {
    assert.deepEqual(parseCsv('\uFEFFkey,text\r\na,"one\r\ntwo, ""three"""\r\n'), {
        headers: ['key', 'text'], rows: [['a', 'one\r\ntwo, "three"']],
    });
});

test('CSV rejects ambiguous quotes, widths, empty and duplicate headers', () => {
    for (const text of ['', 'a,a\n1,2', 'a,\n1,2', 'a,b\n1', 'a\n"x', 'a\nx"y', 'a\n"x"junk']) {
        assert.throws(() => parseCsv(text));
    }
});

test('CSV preserves final empty cells and header-only tables', () => {
    assert.deepEqual(parseCsv('a,b\nx,'), { headers: ['a', 'b'], rows: [['x', '']] });
    assert.deepEqual(parseCsv('a,b\n'), { headers: ['a', 'b'], rows: [] });
});

test('limits cap bytes, rows, columns, and cell sizes', () => {
    assert.throws(() => parseCsv('key\néé', { maxCsvBytes: 7 }));
    assert.throws(() => parseCsv('key\na\nb', { maxRows: 1 }));
    assert.throws(() => parseCsv('a,b\nx,y', { maxColumns: 1 }));
    assert.throws(() => parseCsv('key\nabcd', { maxCellChars: 3 }));
    assert.throws(() => parseCsv('key\na', { maxRows: 1501 }));
    assert.throws(() => parseCsv('key\na', { unknown: 1 }));
});

test('mission requires valid key columns and nonempty exact keys', () => {
    assert.throws(() => createJoinMission({ leftCsv: 'id\n""', rightCsv: 'id\na', leftKey: 'id', rightKey: 'id' }));
    assert.throws(() => createJoinMission({ leftCsv: 'id\na', rightCsv: 'id\na', leftKey: 'missing', rightKey: 'id' }));
    assert.throws(() => createJoinMission({ leftCsv: 'id\na', rightCsv: 'id\na', leftKey: 'id', rightKey: 'id', execute: 'bad' }));
});

test('every algorithm preserves duplicate-key multiplicity and canonical order', () => {
    const input = mission(), expected = [[0, 0], [0, 1], [1, 0], [1, 1], [2, 2]];
    for (const { id } of STRATEGIES) {
        const result = executeJoin(input, id);
        assert.deepEqual(result.pairs, expected);
        assert.equal(verifyJoinResult(input, result.pairs), true);
        assert.equal(result.metrics.outputPairs, 5);
        assert.ok(Number.isSafeInteger(result.metrics.elapsedMicros));
    }
});

test('headers and key values such as __proto__ are ordinary strings', () => {
    const input = createJoinMission({ leftCsv: '__proto__,value\nconstructor,a', rightCsv: 'key,value\nconstructor,b',
        leftKey: '__proto__', rightKey: 'key' });
    assert.deepEqual(executeJoin(input, 'smaller_side_hash').pairs, [[0, 0]]);
    assert.equal(Object.prototype.polluted, undefined);
});

test('empty tables and no-match cases produce complete empty joins', () => {
    for (const leftCsv of ['id\n', 'id\na']) {
        const input = createJoinMission({ leftCsv, rightCsv: 'id\nb', leftKey: 'id', rightKey: 'id' });
        for (const { id } of STRATEGIES) assert.deepEqual(executeJoin(input, id).pairs, []);
    }
});

test('keys do not trim, lowercase, or coerce numeric text', () => {
    const input = createJoinMission({ leftCsv: 'id\n01\nA\n a\n0', rightCsv: 'id\n1\na\n a\n0', leftKey: 'id', rightKey: 'id' });
    for (const { id } of STRATEGIES) assert.deepEqual(executeJoin(input, id).pairs, [[2, 2], [3, 3]]);
});

test('output explosion is rejected before algorithms run', () => {
    assert.throws(() => createJoinMission({ leftCsv: 'id\na\na', rightCsv: 'id\na\na', leftKey: 'id', rightKey: 'id',
        limits: { maxOutputPairs: 3 } }), /output pairs/);
});

test('independent check rejects a missing, duplicate, reordered, or fabricated pair', () => {
    const input = mission(), correct = executeJoin(input, 'smaller_side_hash').pairs;
    for (const pairs of [correct.slice(1), [...correct, [0, 0]], correct.toReversed(), [[99, 0]]]) {
        assert.throws(() => verifyJoinResult(input, pairs));
    }
});

test('mission is frozen and validation rejects an altered workload or table', () => {
    const input = mission();
    assert.throws(() => input.left.rows.push(['x']));
    const copy = structuredClone(input); copy.left.rows[0][0] = '';
    assert.throws(() => validateJoinMission(copy));
    const changed = structuredClone(input); changed.workload.referenceComparisons = 1;
    assert.throws(() => validateJoinMission(changed));
    assert.throws(() => executeJoin(input, 'generated_code'));
    const forgedCount = structuredClone(input); forgedCount.workload.outputPairs = 1;
    assert.throws(() => validateMission(forgedCount));
});

test('import inspection recomputes complete results and rejects forged measurements or authority', async () => {
    const input = mission(), result = await runJoinExperiment(input);
    assert.equal(verifyExperiment(input, result).correctnessRecomputed, true);
    assert.equal(verifyExperiment(input, result).historicalTimingsVerified, false);
    const reordered = Object.fromEntries(Object.entries(structuredClone(result)).reverse());
    assert.equal(verifyExperiment(input, reordered).valid, true);
    const sortedKeys = value => Array.isArray(value) ? value.map(sortedKeys) : value && typeof value === 'object'
        ? Object.fromEntries(Object.keys(value).sort().map(key => [key, sortedKeys(value[key])])) : value;
    const canonicalCopy = sortedKeys(result);
    assert.equal(buildArtifacts(input, canonicalCopy).joinedCsv, buildArtifacts(input, result).joinedCsv);
    for (const mutate of [
        copy => { copy.strategies[0].metrics.logicalOperations += 1; },
        copy => { copy.strategies[1].metrics.indexedRows += 1; },
        copy => { copy.reconciliation.unmatchedRight = []; },
        copy => { copy.assessment.externalAuthority = true; },
        copy => { copy.assessment.comparisons[0].logicalOperationsSaved += 1; },
        copy => { copy.strategies[0].metrics.elapsedMicros = -1; },
    ]) {
        const copy = structuredClone(result); mutate(copy);
        assert.throws(() => verifyExperiment(input, copy));
    }
});

test('smaller-side hashing reduces stored row references on a right-heavy catalog', () => {
    const input = createSampleMission({ leftRows: 8, rightRows: 31 });
    const candidate = executeJoin(input, 'smaller_side_hash'), fixed = executeJoin(input, 'fixed_right_hash');
    assert.equal(candidate.buildSide, 'left'); assert.equal(candidate.metrics.indexedRows, 8);
    assert.equal(fixed.metrics.indexedRows, 31);
    assert.equal(candidate.metrics.logicalOperations, fixed.metrics.logicalOperations);
    assert.deepEqual(candidate.pairs, fixed.pairs);
});

test('experiment includes all credible comparisons and holds independent admission', async () => {
    const result = await runJoinExperiment(mission());
    assert.equal(result.strategies.length, 4);
    assert.ok(result.strategies.every(strategy => strategy.verified));
    assert.equal(result.assessment.state, 'local_demonstration');
    assert.equal(result.assessment.independentReview, 'pending');
    assert.equal(result.assessment.superiorityClaim, false);
    assert.equal(result.assessment.externalAuthority, false);
    assert.equal(result.assessment.comparisons.length, 3);
    assert.deepEqual(result.reconciliation.unmatchedLeft, [3]);
    assert.deepEqual(result.reconciliation.unmatchedRight, [3]);
    assert.equal(result.reconciliation.conflicts.length, 3);
});

test('experiment stops between strategies and never returns an admitted partial result', async () => {
    const controller = new AbortController(); let checkpoints = 0;
    await assert.rejects(runJoinExperiment(mission(), {
        signal: controller.signal,
        checkpoint: async () => { checkpoints += 1; if (checkpoints === 3) controller.abort(); },
    }), /stopped/);
});

test('exports useful joined, missing, and conflict artifacts with lossless JSON', async () => {
    const input = mission(), result = await runJoinExperiment(input), files = buildArtifacts(input, result);
    const joined = parseCsv(files.joinedCsv);
    assert.equal(joined.rows.length, 5);
    assert.deepEqual(joined.headers, ['left.sku', 'left.title', 'left.revision', 'right.id', 'right.title', 'right.revision']);
    assert.equal(parseCsv(files.unmatchedLeftCsv).rows[0][0], 'left');
    assert.equal(parseCsv(files.unmatchedRightCsv).rows[0][0], 'right');
    assert.equal(parseCsv(files.conflictsCsv).rows.length, 5);
    assert.deepEqual(JSON.parse(files.exactJson).mission, input);
});

test('CSV exports escape formula-like values while JSON source remains exact', async () => {
    const input = createJoinMission({ leftCsv: 'id,title\na,=2+2', rightCsv: 'id,title\na,@sum(A1)', leftKey: 'id', rightKey: 'id' });
    const result = await runJoinExperiment(input), files = buildArtifacts(input, result);
    assert.ok(files.joinedCsv.includes("'=2+2"));
    assert.ok(files.joinedCsv.includes("'@sum(A1)"));
    assert.equal(JSON.parse(files.exactJson).mission.left.rows[0][1], '=2+2');
});

test('artifact export refuses injected pairs and changed reconciliation', async () => {
    const input = mission(), result = await runJoinExperiment(input);
    assert.throws(() => exportJoinedCsv(input, [[0, 99]]));
    const changed = structuredClone(result.reconciliation); changed.unmatchedLeft = [];
    assert.throws(() => exportReconciliationCsv(input, changed));
});

test('export byte ceiling is enforced before a large artifact is returned', async () => {
    const input = createJoinMission({ leftCsv: 'id,v\na,xxxxxxxx', rightCsv: 'id,v\na,yyyyyyyy', leftKey: 'id', rightKey: 'id',
        limits: { maxOutputBytes: 12 } });
    const result = await runJoinExperiment(input);
    assert.throws(() => exportJoinedCsv(input, result.strategies[0].pairs), /artifact exceeds/);
});

test('seeded sample mission is deterministic and retains declared bounds', () => {
    assert.deepEqual(createSampleMission({ seed: 7 }), createSampleMission({ seed: 7 }));
    assert.notDeepEqual(createSampleMission({ seed: 7 }), createSampleMission({ seed: 8 }));
    assert.equal(createSampleMission().limits.maxRows, DEFAULT_LIMITS.maxRows);
    assert.throws(() => createSampleMission({ leftRows: 0 }));
    assert.throws(() => createSampleMission({ seed: -1 }));
});

test('algorithm equality holds over varied seeded, duplicate, and Unicode tables', async () => {
    for (let seed = 0; seed < 12; seed += 1) {
        const left = ['id,value'], right = ['id,value'];
        for (let row = 0; row < 17; row += 1) left.push(`${['é', 'a', '中', '01'][(row + seed) % 4]},L${row}`);
        for (let row = 0; row < 11; row += 1) right.push(`${['é', 'a', '中', '01'][(row * 3 + seed) % 4]},R${row}`);
        const input = createJoinMission({ leftCsv: left.join('\n'), rightCsv: right.join('\n'), leftKey: 'id', rightKey: 'id' });
        const result = await runJoinExperiment(input);
        assert.ok(result.strategies.every(strategy => strategy.verified));
    }
});
