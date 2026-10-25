// SPDX-License-Identifier: Apache-2.0
import * as alpha from './engine.mjs';

const PLAN = 'successor-join-program/v1';
const STUDY = 'successor-strategy-research/v1';
const RESOLUTION = 'successor-discrepancy-resolution/v1';
const fail = message => { throw Error(message); };
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const integer = (value, low, high) => Number.isSafeInteger(value) && !Object.is(value, -0) && value >= low && value <= high;

function canonical(value, state = { nodes: 0 }, depth = 0) {
    if (++state.nodes > 250000 || depth > 24) fail('Research data exceeds its structural budget.');
    if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
    if (typeof value === 'number' && Number.isSafeInteger(value) && !Object.is(value, -0)) return String(value);
    if (Array.isArray(value)) return '[' + value.map(item => canonical(item, state, depth + 1)).join(',') + ']';
    if (!value || typeof value !== 'object' || ![Object.prototype, null].includes(Object.getPrototypeOf(value))) {
        fail('Research data must contain only JSON values and safe integers.');
    }
    const keys = Object.keys(value).sort();
    return '{' + keys.map(key => JSON.stringify(key) + ':' + canonical(value[key], state, depth + 1)).join(',') + '}';
}

async function hash(value) {
    const bytes = new TextEncoder().encode(canonical(value));
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

function program({ buckets = 1, uniform = false, threshold = 0, side = 'smaller', blockRows = 64 } = {}) {
    return { schema: PLAN, guard: { op: uniform ? 'uniform_key' : 'none' },
        split: { op: 'stream_partition', buckets },
        leaf: { op: 'small_switch', maxProduct: threshold, small: { op: 'nested' },
            large: { op: 'block_hash', side, rows: blockRows } } };
}

export function validatePlan(plan) {
    if (!exact(plan, ['schema', 'guard', 'split', 'leaf']) || plan.schema !== PLAN
        || !exact(plan.guard, ['op']) || !['none', 'uniform_key'].includes(plan.guard.op)
        || !exact(plan.split, ['op', 'buckets']) || plan.split.op !== 'stream_partition'
        || ![1, 2, 4, 8].includes(plan.split.buckets)
        || !exact(plan.leaf, ['op', 'maxProduct', 'small', 'large']) || plan.leaf.op !== 'small_switch'
        || !integer(plan.leaf.maxProduct, 0, 2250000) || !exact(plan.leaf.small, ['op'])
        || plan.leaf.small.op !== 'nested' || !exact(plan.leaf.large, ['op', 'side', 'rows'])
        || plan.leaf.large.op !== 'block_hash' || !['left', 'right', 'smaller'].includes(plan.leaf.large.side)
        || !integer(plan.leaf.large.rows, 1, alpha.DEFAULT_LIMITS.maxRows)) fail('Invalid or unsupported join program.');
    return true;
}

function settings(options = {}) {
    const { maxAuxiliaryRows = 64, auxiliaryWeight = 0 } = options;
    if (!integer(maxAuxiliaryRows, 0, 4500) || !integer(auxiliaryWeight, 0, 1000000)) {
        fail('Use an auxiliary-row budget from 0 to 4500 and a whole objective weight from 0 to 1000000.');
    }
    return { maxAuxiliaryRows, auxiliaryWeight };
}

export function constructPlans(options = {}) {
    if (!exact(options, Object.keys(options)) || Object.keys(options).some(key => key !== 'maxAuxiliaryRows')) {
        fail('Unsupported construction options.');
    }
    const { maxAuxiliaryRows } = settings(options), blockRows = Math.max(1, Math.min(1500, maxAuxiliaryRows));
    const plans = [];
    for (const buckets of [1, 2, 4, 8]) for (const uniform of [false, true]) for (const threshold of [0, 16]) {
        plans.push(program({ buckets, uniform, threshold, blockRows }));
    }
    for (const side of ['left', 'right']) for (const uniform of [false, true]) {
        plans.push(program({ side, uniform, blockRows: Math.max(1, Math.floor(blockRows / 2)) }));
    }
    for (const plan of plans) validatePlan(plan);
    return plans;
}

export function executePlan(mission, plan) {
    alpha.validateJoinMission(mission); validatePlan(plan);
    const { left, right } = mission, pairs = [];
    const metrics = { keyComparisons: 0, comparedCharacters: 0, hashInsertions: 0, hashProbes: 0,
        hashedCharacters: 0, routingTests: 0, routingCharacters: 0, branchDecisions: 0,
        outputPairs: 0, peakAuxiliaryRows: 0, logicalOperations: 0 };
    const key = (side, index) => side.rows[index][side.keyIndex];
    const equal = (a, b) => {
        metrics.keyComparisons += 1;
        metrics.comparedCharacters += Math.max(a.length, b.length);
        return a === b;
    };
    const emit = (a, b) => {
        if (pairs.length >= mission.limits.maxOutputPairs) fail('Constructed plan exceeded the join output budget.');
        pairs.push([a, b]); metrics.outputPairs += 1;
    };
    let uniform = false;
    if (plan.guard.op === 'uniform_key') {
        metrics.branchDecisions += 1;
        uniform = left.rows.length > 0 && right.rows.length > 0;
        for (const side of [left, right]) {
            const first = side.rows.length ? key(side, 0) : '';
            for (let row = 0; uniform && row < side.rows.length; row += 1) uniform = equal(first, key(side, row));
        }
        if (uniform && equal(key(left, 0), key(right, 0))) {
            for (let a = 0; a < left.rows.length; a += 1) for (let b = 0; b < right.rows.length; b += 1) emit(a, b);
        }
    }
    const bucket = value => {
        let code = 2166136261;
        for (let index = 0; index < value.length; index += 1) {
            code = Math.imul(code ^ value.charCodeAt(index), 16777619) >>> 0;
            metrics.routingCharacters += 1;
        }
        return code % plan.split.buckets;
    };
    const leaf = (leftRows, rightRows, temporaryRows) => {
        const leftCount = leftRows ? leftRows.length : left.rows.length;
        const rightCount = rightRows ? rightRows.length : right.rows.length;
        const aIndex = index => leftRows ? leftRows[index] : index;
        const bIndex = index => rightRows ? rightRows[index] : index;
        metrics.peakAuxiliaryRows = Math.max(metrics.peakAuxiliaryRows, temporaryRows);
        metrics.branchDecisions += 1;
        if (leftCount * rightCount <= plan.leaf.maxProduct) {
            for (let a = 0; a < leftCount; a += 1) for (let b = 0; b < rightCount; b += 1) {
                if (equal(key(left, aIndex(a)), key(right, bIndex(b)))) emit(aIndex(a), bIndex(b));
            }
            return;
        }
        if (leftCount === 0 || rightCount === 0) return;
        const buildLeft = plan.leaf.large.side === 'left'
            || plan.leaf.large.side === 'smaller' && leftCount < rightCount;
        const build = buildLeft ? left : right, probe = buildLeft ? right : left;
        const buildCount = buildLeft ? leftCount : rightCount, probeCount = buildLeft ? rightCount : leftCount;
        const buildIndex = buildLeft ? aIndex : bIndex, probeIndex = buildLeft ? bIndex : aIndex;
        for (let start = 0; start < buildCount; start += plan.leaf.large.rows) {
            const end = Math.min(start + plan.leaf.large.rows, buildCount), index = new Map();
            metrics.peakAuxiliaryRows = Math.max(metrics.peakAuxiliaryRows, temporaryRows + end - start);
            for (let row = start; row < end; row += 1) {
                const value = key(build, buildIndex(row));
                metrics.hashInsertions += 1; metrics.hashedCharacters += value.length;
                if (!index.has(value)) index.set(value, []);
                index.get(value).push(buildIndex(row));
            }
            for (let row = 0; row < probeCount; row += 1) {
                const value = key(probe, probeIndex(row));
                metrics.hashProbes += 1; metrics.hashedCharacters += value.length;
                for (const match of index.get(value) || []) {
                    if (buildLeft) emit(match, probeIndex(row)); else emit(probeIndex(row), match);
                }
            }
        }
    };
    if (!uniform) {
        if (plan.split.buckets === 1) leaf(null, null, 0);
        else for (let partition = 0; partition < plan.split.buckets; partition += 1) {
            const leftRows = [], rightRows = [];
            for (const [side, indices] of [[left, leftRows], [right, rightRows]]) {
                for (let row = 0; row < side.rows.length; row += 1) {
                    metrics.routingTests += 1;
                    if (bucket(key(side, row)) === partition) indices.push(row);
                }
            }
            leaf(leftRows, rightRows, leftRows.length + rightRows.length);
        }
    }
    pairs.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    alpha.verifyJoinResult(mission, pairs);
    metrics.logicalOperations = Object.entries(metrics).reduce((sum, [name, count]) =>
        !['peakAuxiliaryRows', 'logicalOperations'].includes(name) ? sum + count : sum, 0);
    return { plan, pairs, metrics, correct: true };
}

const baselinePlans = budget => {
    const rows = Math.max(1, Math.min(1500, budget));
    return [
        { id: 'baseline_nested', label: 'Exact nested join', plan: program({ threshold: 2250000 }) },
        ...['left', 'right', 'smaller'].map(side => ({ id: `baseline_full_${side}`,
            label: `Full ${side}-side hash join`, plan: program({ side, blockRows: 1500 }) })),
        ...['left', 'right', 'smaller'].map(side => ({ id: `baseline_block_${side}`,
            label: `Bounded ${side}-side block hash join`, plan: program({ side, blockRows: rows }) })),
    ];
};

async function record(mission, plan, objective, id, label) {
    const execution = executePlan(mission, plan);
    return { id, label, plan, planHash: await hash(plan), pairsHash: await hash(execution.pairs), metrics: execution.metrics,
        correct: true, feasible: execution.metrics.peakAuxiliaryRows <= objective.maxAuxiliaryRows,
        objectiveValue: execution.metrics.logicalOperations + objective.auxiliaryWeight * execution.metrics.peakAuxiliaryRows };
}

const ranking = (a, b) => a.objectiveValue - b.objectiveValue || a.metrics.peakAuxiliaryRows - b.metrics.peakAuxiliaryRows
    || (a.planHash < b.planHash ? -1 : a.planHash > b.planHash ? 1 : 0);

function example(seed = 41, sameKey = false) {
    const leftCount = 65 + seed % 2, rightCount = 65 + (seed >>> 1) % 2;
    const leftId = `PUBLIC-LEFT-${seed}`, rightId = sameKey ? leftId : `PUBLIC-RIGHT-${seed}`;
    const left = ['sku,revision,note'], right = ['sku,revision,note'];
    for (let row = 0; row < leftCount; row += 1) left.push(`${leftId},r${seed % 3},Public edition ${seed}`);
    for (let row = 0; row < rightCount; row += 1) right.push(`${rightId},r${seed % 3},Public edition ${seed}`);
    return alpha.createJoinMission({ leftCsv: left.join('\n'), rightCsv: right.join('\n'), leftKey: 'sku', rightKey: 'sku' });
}

export function strategyExampleMission() { return example(); }

function confirmationMission(mission, seed) {
    if (mission.left.rows.length && mission.right.rows.length) {
        const firstLeft = mission.left.rows[0][mission.left.keyIndex], firstRight = mission.right.rows[0][mission.right.keyIndex];
        if (mission.left.rows.every(row => row[mission.left.keyIndex] === firstLeft)
            && mission.right.rows.every(row => row[mission.right.keyIndex] === firstRight)) {
            return example(seed, firstLeft === firstRight);
        }
    }
    return alpha.createSampleMission({ seed, leftRows: Math.max(1, Math.min(300, mission.left.rows.length)),
        rightRows: Math.max(1, Math.min(600, mission.right.rows.length)) });
}

export async function discoverStrategy(mission, options = {}) {
    alpha.validateJoinMission(mission);
    const allowed = ['sourceHash', 'maxAuxiliaryRows', 'auxiliaryWeight', 'signal', 'onProgress', 'confirmationSeed'];
    if (!options || typeof options !== 'object' || Array.isArray(options)
        || Object.keys(options).some(key => !allowed.includes(key)) || !/^[a-f0-9]{64}$/.test(options.sourceHash || '')
        || options.confirmationSeed !== undefined && !integer(options.confirmationSeed, 0, 0xffffffff)) {
        fail('Research requires an exact source hash and supported bounded options.');
    }
    const objective = settings(options), sourceHash = options.sourceHash, missionHash = await hash(mission);
    const checkpoint = async (stage, completed, total) => {
        if (options.signal?.aborted) fail('Strategy construction stopped; no candidate was retained.');
        options.onProgress?.({ stage, completed, total });
        await new Promise(resolve => setTimeout(resolve, 0));
        if (options.signal?.aborted) fail('Strategy construction stopped; no candidate was retained.');
    };
    const baselines = [], candidates = [];
    const declaredBaselines = baselinePlans(objective.maxAuxiliaryRows);
    const plans = constructPlans({ maxAuxiliaryRows: objective.maxAuxiliaryRows });
    for (let index = 0; index < declaredBaselines.length; index += 1) {
        await checkpoint('baselines', index, declaredBaselines.length);
        const baseline = declaredBaselines[index];
        baselines.push(await record(mission, baseline.plan, objective, baseline.id, baseline.label));
    }
    const incumbent = [...baselines].filter(item => item.feasible).sort(ranking)[0];
    for (let index = 0; index < plans.length; index += 1) {
        await checkpoint('construction', index, plans.length);
        candidates.push(await record(mission, plans[index], objective, `constructed_${String(index + 1).padStart(2, '0')}`,
            'Composition of declared exact join operators'));
    }
    const nominee = [...candidates].filter(item => item.feasible).sort(ranking)[0] || incumbent;
    const frozenData = { sourceHash, developmentMissionHash: missionHash, plan: nominee.plan, planHash: nominee.planHash,
        incumbentPlanHash: incumbent.planHash, objective };
    const frozen = { ...frozenData, commitment: await hash(frozenData) };
    await checkpoint('frozen', plans.length, plans.length);
    // Sampling happens after the local commitment. This local generator is public, not a protected evaluator.
    let seed = options.confirmationSeed ?? crypto.getRandomValues(new Uint32Array(1))[0];
    let fresh = confirmationMission(mission, seed), freshHash = await hash(fresh);
    for (let retry = 0; freshHash === missionHash && retry < 4; retry += 1) {
        seed = (seed + 1) >>> 0;
        fresh = confirmationMission(mission, seed); freshHash = await hash(fresh);
    }
    if (freshHash === missionHash) fail('Confirmation generator did not produce a distinct fresh input.');
    const candidate = await record(fresh, nominee.plan, objective, nominee.id, nominee.label);
    const freshBaselines = [];
    for (let index = 0; index < declaredBaselines.length; index += 1) {
        await checkpoint('confirmation', index, declaredBaselines.length);
        const baseline = declaredBaselines[index];
        freshBaselines.push(await record(fresh, baseline.plan, objective, baseline.id, baseline.label));
    }
    const confirmedIncumbent = freshBaselines.find(baseline => baseline.id === incumbent.id);
    const strongestFreshBaseline = [...freshBaselines].filter(item => item.feasible).sort(ranking)[0];
    const developmentImproved = nominee.feasible && nominee.objectiveValue < incumbent.objectiveValue;
    const passed = candidate.feasible && candidate.objectiveValue < strongestFreshBaseline.objectiveValue;
    const promoted = developmentImproved && passed;
    const retained = promoted ? nominee : incumbent;
    await checkpoint('complete', plans.length, plans.length);
    const ledger = (records, task) => ({ planExecutions: records.length,
        executionLogicalOperations: records.reduce((sum, item) => sum + item.metrics.logicalOperations, 0),
        independentReferenceComparisons: records.length * task.left.rows.length * task.right.rows.length,
        verifiedOutputPairs: records.reduce((sum, item) => sum + item.metrics.outputPairs, 0) });
    return { schema: STUDY, sourceHash, missionHash, objective, incumbent, baselines, candidates, frozen,
        confirmation: { seed, mission: fresh, missionHash: freshHash, publicSynthetic: true, protected: false,
            candidate, incumbent: confirmedIncumbent, baselines: freshBaselines, strongestBaseline: strongestFreshBaseline,
            passed, developmentImproved },
        evaluationLedger: { development: ledger([...baselines, ...candidates], mission),
            confirmation: ledger([candidate, ...freshBaselines], fresh),
            note: 'Separate execution and exhaustive-oracle counts; excludes enumeration, hashing commitments, '
                + 'serialization, sorting, report and export overhead. No net-benefit claim.' },
        decision: { state: promoted ? 'local_improvement' : 'held', promoted, retainedPlan: retained.plan,
            retainedPlanHash: retained.planHash,
            reason: promoted ? 'Strictly lower registered objective than every feasible declared baseline on development '
                + 'and a fresh local synthetic case.'
                : 'No strict improvement over the strongest feasible declared baseline on both cases; incumbent retained.' },
        qualification: 'local_engineering_only', independentlyQualified: false, protectedHoldout: false,
        externalAuthority: false, modelUsed: false, algorithmNoveltyClaim: false,
        scope: [
            'Programs combine reviewed uniform-key checks, streamed partitions, conditional nested joins, and bounded hash joins.',
            'Search is bounded enumeration of 20 programs in this declared grammar; it does not invent arbitrary operators or code.',
            'The incumbent is the strongest feasible member of the seven declared textbook baselines on this development input.',
            'The objective is logical operations plus the explicit auxiliary-row weight, subject to the explicit row-reference cap.',
            'Every string comparison is charged its maximum UTF-16 input length; hash operations are charged the full key length. '
                + 'These are reproducible proxies; JavaScript engines can short-circuit or reuse string hashes.',
            'Auxiliary rows count indexed and temporary partition row references, excluding shared inputs and returned output. '
                + 'They are not memory bytes or measured process peak memory.',
            'Canonical output sorting, independent oracle execution, search, report generation, and export are excluded from '
                + 'the per-plan objective; execution and oracle search counts are reported separately in evaluationLedger.',
            'Confirmation is a new generated public synthetic input after a local freeze, not a secret or independently administered holdout.',
            'The duplicate-heavy example deliberately uses a different repeated key in each catalog. A known uniform-key '
                + 'shortcut confirms the empty join; grouping retains every missing occurrence in two proposed corrective actions.',
            'No timing, economic return, model improvement, novel algorithm, general intelligence, or external execution claim is made.',
        ] };
}

export async function validateResearch(report, mission, options = {}) {
    if (!exact(options, ['sourceHash']) || !/^[a-f0-9]{64}$/.test(options.sourceHash || '')
        || !report || report.schema !== STUDY || report.sourceHash !== options.sourceHash
        || !report.objective || !report.confirmation) fail('Unsupported research record or source identity.');
    const serialized = canonical(report);
    if (new TextEncoder().encode(serialized).length > 8000000) fail('Research record exceeds 8 MB.');
    const recomputed = await discoverStrategy(mission, { sourceHash: options.sourceHash,
        maxAuxiliaryRows: report.objective.maxAuxiliaryRows, auxiliaryWeight: report.objective.auxiliaryWeight,
        confirmationSeed: report.confirmation.seed });
    if (canonical(recomputed) !== serialized) fail('Research record differs from complete deterministic recomputation.');
    return { valid: true, outputsAndObjectiveRecomputed: true, protectedHoldout: false,
        independentlyQualified: false, externalAuthority: false };
}

function resolutionCsv(actions, maximum) {
    const rows = [['action', 'exact_key', 'type', 'left_data_rows', 'right_data_rows', 'original_review_occurrences', 'next_step']];
    for (const action of actions) rows.push([action.id, action.key, action.type,
        action.leftRows.map(row => row + 1).join(';'), action.rightRows.map(row => row + 1).join(';'),
        action.occurrences.join(';'), action.nextStep]);
    let bytes = 0;
    return rows.map(row => {
        const line = row.map(value => {
            let cell = String(value);
            if (/^(?:\s*[=+\-@]|[\t\r\n])/.test(cell)) cell = `'${cell}`;
            return '"' + cell.replaceAll('"', '""') + '"';
        }).join(',') + '\r\n';
        bytes += new TextEncoder().encode(line).length;
        if (bytes > maximum) fail('Corrective-action CSV exceeds its output budget.');
        return line;
    }).join('');
}

export function resolveDiscrepancies(mission, result) {
    alpha.validateJoinMission(mission);
    if (result) alpha.verifyExperiment(mission, result);
    const experiment = result;
    const pairs = experiment ? experiment.strategies[0].pairs : alpha.executeJoin(mission, 'nested_scan').pairs;
    alpha.verifyJoinResult(mission, pairs);
    const groups = new Map(), matchedLeft = new Set(), matchedRight = new Set();
    const shared = mission.left.headers.flatMap((name, leftColumn) => {
        const rightColumn = mission.right.headers.indexOf(name);
        return leftColumn !== mission.left.keyIndex && rightColumn >= 0 && rightColumn !== mission.right.keyIndex
            ? [{ name, leftColumn, rightColumn }] : [];
    });
    const group = key => {
        if (!groups.has(key)) groups.set(key, { key, leftRows: new Set(), rightRows: new Set(),
            occurrences: [], conflicts: [], missingLeft: false, missingRight: false });
        return groups.get(key);
    };
    for (const [a, b] of pairs) {
        matchedLeft.add(a); matchedRight.add(b);
        const fields = shared.flatMap((field, index) =>
            mission.left.rows[a][field.leftColumn] !== mission.right.rows[b][field.rightColumn] ? [index] : []);
        if (fields.length) {
            const action = group(mission.left.rows[a][mission.left.keyIndex]);
            action.leftRows.add(a); action.rightRows.add(b); action.occurrences.push(`conflict:${a}:${b}`);
            action.conflicts.push({ leftIndex: a, rightIndex: b, fieldIndices: fields });
        }
    }
    for (const [side, matched, otherMissing, prefix] of [[mission.left, matchedLeft, 'missingRight', 'left'],
        [mission.right, matchedRight, 'missingLeft', 'right']]) {
        for (let row = 0; row < side.rows.length; row += 1) if (!matched.has(row)) {
            const action = group(side.rows[row][side.keyIndex]);
            action[otherMissing] = true;
            action[prefix === 'left' ? 'leftRows' : 'rightRows'].add(row);
            action.occurrences.push(`${prefix}:${row}`);
        }
    }
    const actions = [...groups.values()].sort((a, b) => a.key < b.key ? -1 : a.key > b.key ? 1 : 0).map((action, index) => ({
        id: `action-${String(index + 1).padStart(4, '0')}`, key: action.key,
        type: action.missingLeft ? 'missing_from_left' : action.missingRight ? 'missing_from_right' : 'review_shared_values',
        leftRows: [...action.leftRows].sort((a, b) => a - b), rightRows: [...action.rightRows].sort((a, b) => a - b),
        occurrences: action.occurrences, conflicts: action.conflicts,
        nextStep: action.missingLeft || action.missingRight
            ? 'Check whether this key belongs in the other catalog; retain every referenced occurrence before deciding.'
            : 'Review all referenced differences for this exact key and choose the authoritative values; do not auto-overwrite.',
    }));
    const expectedOccurrences = [];
    for (let row = 0; row < mission.left.rows.length; row += 1) {
        if (!matchedLeft.has(row)) expectedOccurrences.push(`left:${row}`);
    }
    for (let row = 0; row < mission.right.rows.length; row += 1) {
        if (!matchedRight.has(row)) expectedOccurrences.push(`right:${row}`);
    }
    for (const [leftIndex, rightIndex] of pairs) {
        if (shared.some(field => mission.left.rows[leftIndex][field.leftColumn]
            !== mission.right.rows[rightIndex][field.rightColumn])) expectedOccurrences.push(`conflict:${leftIndex}:${rightIndex}`);
    }
    const occurrences = actions.flatMap(action => action.occurrences), pairwiseReviewItems = expectedOccurrences.length;
    if (new Set(occurrences).size !== occurrences.length) fail('Corrective actions duplicated an original review occurrence.');
    if (canonical([...occurrences].sort()) !== canonical(expectedOccurrences.sort())) {
        fail('Corrective actions did not preserve every original review occurrence.');
    }
    const reducesItems = actions.length < pairwiseReviewItems;
    const report = { schema: RESOLUTION, actions, sharedFields: shared,
        burden: { pairwiseReviewItems, groupedActions: actions.length, groupingReduction: pairwiseReviewItems - actions.length,
            timeSavedClaim: false, sameTaskSuperiority: false },
        coverage: { originalOccurrences: pairwiseReviewItems, coveredOccurrences: occurrences.length,
            complete: true, missing: [], duplicates: [] },
        diagnosis: { originalGoal: 'Materialize matching row pairs and inspect each unmatched or conflicting occurrence.',
            proposedGoal: 'Decide which product keys need correction, retaining every source occurrence for review.',
            duplicateExceptionKeys: actions.filter(action => action.occurrences.length > 1).length,
            uniqueExceptionKeys: actions.length, groupingReducesDecisionItems: reducesItems },
        decision: { state: reducesItems ? 'offer_key_queue' : 'retain_original_review',
            recommendedContract: reducesItems ? 'per_key_corrective_actions' : 'original_occurrence_review',
            reason: reducesItems ? 'Several original exceptions concern the same exact key. A key-based queue reduces '
                + 'decision records under a changed output contract while preserving complete underlying evidence.'
                : 'No repeated exception key reduces the number of decision records; retain the original review contract.' },
        contract: { changed: true,
            original: 'One review item per unmatched source row or conflicting matched row pair.',
            reframed: 'One proposed corrective action per exact key, retaining every underlying original occurrence reference.',
            limitation: 'Grouping changes the unit of work. Fewer action records do not establish equal reviewer effort, '
                + 'correct resolution, time savings, or superiority on the original pairwise-output task.' },
        actionsCsv: resolutionCsv(actions, mission.limits.maxOutputBytes), externalAuthority: false,
        automaticallyResolved: false, qualification: 'local_engineering_only' };
    if (new TextEncoder().encode(canonical(report)).length > 8000000) fail('Corrective-action report exceeds 8 MB.');
    return report;
}

export function validateResolution(report, mission, result) {
    if (canonical(report) !== canonical(resolveDiscrepancies(mission, result))) {
        fail('Corrective-action report omits, duplicates, or changes source evidence.');
    }
    return { valid: true, completeCoverageRecomputed: true, automaticallyResolved: false, externalAuthority: false };
}
