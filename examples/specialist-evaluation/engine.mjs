// SPDX-License-Identifier: Apache-2.0
/** Local contract preparation and reported-evidence checks. Never a proof issuer. */
import {canonical, digest, parseBounded} from '../../docs/assets/successor/engine.mjs';

export const SCHEMA = 'specialist-evaluation-contract/v1';
export const ROLES = ['candidate', 'incumbent', 'alternative'];
export const DIMENSIONS = ['quality', 'cost', 'time', 'safety', 'robustness', 'human', 'proof'];
const HASH = /^[a-f0-9]{64}$/;
const ID = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$/;
const MAX = 1_000_000_000_000;
function fail(condition, code) { if (!condition) throw Error(`EVALUATION_${code}`); }
function keys(value, expected) {
    fail(value && typeof value === 'object' && !Array.isArray(value)
        && Object.keys(value).sort().join('|') === [...expected].sort().join('|'), 'SCHEMA');
}
function label(value, max = 1000) { fail(typeof value === 'string' && value.trim() && value.length <= max, 'TEXT'); }
function id(value) { fail(typeof value === 'string' && ID.test(value), 'ID'); }
function hash(value) { fail(typeof value === 'string' && HASH.test(value), 'HASH'); }
function integer(value, low = 0, high = MAX) { fail(Number.isSafeInteger(value) && !Object.is(value, -0) && value >= low && value <= high, 'INTEGER'); }
function list(value, min, max) { fail(Array.isArray(value) && value.length >= min && value.length <= max, 'LIST'); }
function unique(rows, key) { fail(new Set(rows.map(row => row[key])).size === rows.length, 'DUPLICATE'); }
function clone(value) { return parseBounded(canonical(value)); }
function freeze(value) {
    if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
    return value;
}
function time(value) {
    fail(typeof value === 'string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(value)
        && Number.isFinite(Date.parse(value)) && new Date(value).toISOString() === value, 'TIME');
}
function participant(row) {
    keys(row, ['id', 'sourceHash', 'configurationHash', 'toolsHash', 'knowledgeHash', 'interfacesHash']);
    id(row.id);
    for (const key of ['sourceHash', 'configurationHash', 'toolsHash', 'knowledgeHash', 'interfacesHash']) hash(row[key]);
}
/** Domain-separated commitments to supplied exact JSON/UTF-8 strings; not source authenticity checks. */
export async function bindParticipant(identity, material) {
    id(identity);
    keys(material, ['source', 'configuration', 'tools', 'knowledge', 'interfaces']);
    const result = {id: identity};
    for (const key of Object.keys(material)) result[`${key}Hash`] = await digest(`specialist-${key}`, material[key]);
    return freeze(result);
}
export function validateContract(raw) {
    const c = clone(raw);
    keys(c, ['schema', 'missionId', 'mission', 'exclusions', 'proposalDigest', 'createdAt', 'expiresAt',
        'participants', 'alternativeRationale', 'evaluation', 'metrics', 'constraints', 'review']);
    fail(c.schema === SCHEMA, 'VERSION'); id(c.missionId); label(c.mission); label(c.exclusions); hash(c.proposalDigest);
    time(c.createdAt); time(c.expiresAt); fail(Date.parse(c.expiresAt) > Date.parse(c.createdAt), 'EXPIRY');
    keys(c.participants, ROLES); ROLES.forEach(role => participant(c.participants[role]));
    unique(ROLES.map(role => c.participants[role]), 'id');
    // A second label for the same complete implementation is not a distinct comparator.
    const implementations = ROLES.map(role => {
        const {id: ignored, ...pins} = c.participants[role]; return canonical(pins);
    });
    fail(new Set(implementations).size === 3, 'DUPLICATE_IMPLEMENTATION'); label(c.alternativeRationale);
    const e = c.evaluation;
    keys(e, ['taskSetCommitment', 'formationSetCommitment', 'protocolHash', 'resourcePolicyHash', 'trialCount', 'custodianId']);
    for (const key of ['taskSetCommitment', 'formationSetCommitment', 'protocolHash', 'resourcePolicyHash']) hash(e[key]);
    fail(e.taskSetCommitment !== e.formationSetCommitment, 'FORMATION_REUSE');
    integer(e.trialCount, 1, 10000); id(e.custodianId);
    list(c.metrics, DIMENSIONS.length, 16); unique(c.metrics, 'id');
    fail(DIMENSIONS.every(d => c.metrics.some(m => m.dimension === d)), 'DIMENSIONS');
    for (const m of c.metrics) {
        keys(m, ['id', 'dimension', 'unit', 'direction', 'minimumGain', 'methodHash', 'uncertaintyMethodHash']);
        id(m.id); fail(DIMENSIONS.includes(m.dimension), 'DIMENSION'); label(m.unit, 100);
        fail(['higher', 'lower'].includes(m.direction), 'DIRECTION'); integer(m.minimumGain); hash(m.methodHash); hash(m.uncertaintyMethodHash);
    }
    list(c.constraints, 1, 16); unique(c.constraints, 'id');
    c.constraints.forEach(row => { keys(row, ['id', 'requirementHash']); id(row.id); hash(row.requirementHash); });
    keys(c.review, ['reviewerId', 'organizationId', 'independencePolicyHash', 'conflictDisclosureHash', 'custodyPolicyHash']);
    id(c.review.reviewerId); id(c.review.organizationId);
    for (const key of ['independencePolicyHash', 'conflictDisclosureHash', 'custodyPolicyHash']) hash(c.review[key]);
    fail(!ROLES.some(role => [c.review.reviewerId, e.custodianId].includes(c.participants[role].id)), 'ROLE_CONFLICT');
    // Different identifiers are necessary metadata, never proof of independent people or organizations.
    return c;
}
export async function freezeContract(raw) {
    const contract = validateContract(raw);
    return freeze({schema: 'specialist-evaluation-freeze/v1', contract,
        contractDigest: await digest('specialist-evaluation-contract', contract)});
}
export async function validateFrozen(raw) {
    keys(raw, ['schema', 'contract', 'contractDigest']); fail(raw.schema === 'specialist-evaluation-freeze/v1', 'FREEZE_VERSION');
    hash(raw.contractDigest); const frozen = await freezeContract(raw.contract);
    fail(frozen.contractDigest === raw.contractDigest, 'CONTRACT_CHANGED'); return frozen;
}
/** Evidence is metadata only. No hidden cases, answers, signer keys or executable paths are accepted. */
export async function validateReport(raw, frozen) {
    const f = await validateFrozen(frozen), c = f.contract, r = clone(raw);
    keys(r, ['schema', 'contractDigest', 'attemptId', 'startedAt', 'finishedAt', 'state', 'evidenceDigest', 'rows', 'failures']);
    fail(r.schema === 'specialist-evaluation-report/v1', 'REPORT_VERSION'); hash(r.contractDigest);
    fail(r.contractDigest === f.contractDigest, 'WRONG_CONTRACT'); id(r.attemptId); time(r.startedAt);
    fail(Date.parse(r.startedAt) >= Date.parse(c.createdAt), 'PRE_FREEZE_RESULT');
    fail(['complete', 'interrupted', 'stopped', 'failed', 'uncertain'].includes(r.state), 'STATE');
    if (r.finishedAt !== null) { time(r.finishedAt); fail(Date.parse(r.finishedAt) >= Date.parse(r.startedAt), 'TIME_ORDER'); }
    fail(r.state !== 'complete' || r.finishedAt !== null, 'MISSING_FINISH'); hash(r.evidenceDigest);
    list(r.rows, 0, 3); unique(r.rows, 'role');
    for (const row of r.rows) {
        keys(row, ['role', 'participantDigest', 'taskSetCommitment', 'protocolHash', 'resourcePolicyHash', 'trialCount', 'metrics', 'constraints']);
        fail(ROLES.includes(row.role), 'ROLE'); hash(row.participantDigest);
        fail(row.participantDigest === await digest('specialist-participant', c.participants[row.role]), 'PARTICIPANT_CHANGED');
        for (const key of ['taskSetCommitment', 'protocolHash', 'resourcePolicyHash']) fail(row[key] === c.evaluation[key], 'UNFAIR_CONDITIONS');
        integer(row.trialCount, 0, c.evaluation.trialCount);
        list(row.metrics, c.metrics.length, c.metrics.length); unique(row.metrics, 'id');
        for (const metric of row.metrics) {
            keys(metric, ['id', 'lower', 'upper', 'evidenceDigest']);
            fail(c.metrics.some(m => m.id === metric.id), 'METRIC_ID');
            if (metric.lower === null || metric.upper === null) fail(metric.lower === null && metric.upper === null, 'PARTIAL_INTERVAL');
            else { integer(metric.lower, -MAX); integer(metric.upper, -MAX); fail(metric.lower <= metric.upper, 'INTERVAL'); }
            if (metric.evidenceDigest !== null) hash(metric.evidenceDigest);
            fail(metric.lower === null || metric.evidenceDigest !== null, 'MISSING_EVIDENCE');
        }
        list(row.constraints, c.constraints.length, c.constraints.length); unique(row.constraints, 'id');
        row.constraints.forEach(item => {
            keys(item, ['id', 'status', 'evidenceDigest']); fail(c.constraints.some(x => x.id === item.id), 'CONSTRAINT_ID');
            fail(['unknown', 'reported-pass', 'reported-fail'].includes(item.status), 'CONSTRAINT_STATUS');
            if (item.evidenceDigest !== null) hash(item.evidenceDigest);
            fail(item.status === 'unknown' || item.evidenceDigest !== null, 'MISSING_EVIDENCE');
        });
    }
    list(r.failures, 0, 64);
    r.failures.forEach(item => { keys(item, ['role', 'code', 'evidenceDigest']); fail(ROLES.includes(item.role), 'ROLE'); id(item.code); hash(item.evidenceDigest); });
    return r;
}
function summarizeAttempt(c, report) {
    const complete = report.state === 'complete' && report.rows.length === 3
        && report.rows.every(row => row.trialCount === c.evaluation.trialCount);
    const comparisons = c.metrics.map(metric => {
        const values = Object.fromEntries(report.rows.map(row => [row.role, row.metrics.find(m => m.id === metric.id)]));
        const known = complete && ROLES.every(role => values[role]?.lower !== null && values[role] !== undefined);
        const gains = Object.fromEntries(['incumbent', 'alternative'].map(role => [role, !known ? null
            : metric.direction === 'higher' ? values.candidate.lower - values[role].upper
                : values[role].lower - values.candidate.upper]));
        return {metricId: metric.id, conservativeGains: gains, status: !known ? 'unknown'
            : Object.values(gains).every(gain => gain >= metric.minimumGain) ? 'reported-threshold-met' : 'reported-threshold-missed'};
    });
    const failures = report.failures.map(failure => ({attemptId: report.attemptId, ...failure}));
    if (report.state === 'failed') failures.push({attemptId: report.attemptId, code: 'reported-failed-attempt'});
    for (const row of report.rows) for (const item of row.constraints) {
        if (item.status === 'reported-fail') failures.push({attemptId: report.attemptId, role: row.role,
            code: 'reported-constraint-failure', constraintId: item.id, evidenceDigest: item.evidenceDigest});
    }
    for (const row of comparisons) if (row.status === 'reported-threshold-missed') {
        failures.push({attemptId: report.attemptId, code: 'reported-metric-regression', metricId: row.metricId,
            conservativeGains: row.conservativeGains});
    }
    const unknown = !complete || comparisons.some(row => row.status === 'unknown')
        || report.rows.some(row => row.constraints.some(item => item.status === 'unknown'));
    const advantage = ['incumbent', 'alternative'].every(role => comparisons.some(row => row.conservativeGains[role] > 0));
    const status = failures.length ? 'retain-incumbent' : !complete ? (report.state === 'complete' ? 'reported-incomplete' : report.state)
        : unknown ? 'evidence-needed' : advantage ? 'reported-comparison-ready-for-review' : 'retain-incumbent';
    return {attemptId: report.attemptId, state: report.state, status, unknown, comparisons, failures};
}
export async function assess(frozen, reports = [], now = new Date().toISOString()) {
    const f = await validateFrozen(frozen), c = f.contract; time(now); list(reports, 0, 32);
    const validated = [];
    for (const r of reports) validated.push(await validateReport(r, f));
    unique(validated, 'attemptId');
    validated.forEach((r, index) => {
        fail(Date.parse(r.startedAt) <= Date.parse(now)
            && (r.finishedAt === null || Date.parse(r.finishedAt) <= Date.parse(now)), 'FUTURE_RESULT');
        fail(index === 0 || Date.parse(r.startedAt) >= Date.parse(validated[index - 1].startedAt), 'ATTEMPT_ORDER');
    });
    // Retain every attempt's derived comparison, not merely the latest successful run.
    const attemptResults = validated.map(report => summarizeAttempt(c, report));
    const failures = attemptResults.flatMap(result => result.failures);
    const gaps = ['Independent reviewer identity, conflicts and organizational separation are unverified.',
        'Protected-test custody, freshness and absence of leakage are unverified.',
        'Source authenticity, completeness of attempts and reported measurements are unverified.'];
    const expired = Date.parse(now) >= Date.parse(c.expiresAt);
    fail(Date.parse(now) >= Date.parse(c.createdAt), 'CLOCK_BEFORE_FREEZE');
    let status = 'uncommissioned', comparisons = [];
    if (validated.length) {
        const last = validated.at(-1), summary = attemptResults.at(-1);
        comparisons = summary.comparisons;
        status = last.state === 'complete' ? summary.status : last.state;
        if (last.state === 'complete' && last.rows.length === 3
            && last.rows.every(row => row.trialCount === c.evaluation.trialCount)) {
            status = attemptResults.some(result => result.status === 'retain-incumbent') ? 'retain-incumbent'
                : attemptResults.some(result => result.unknown) ? 'evidence-needed' : summary.status;
        }
        if (attemptResults.some(result => result.unknown)) gaps.push('At least one retained attempt has incomplete or unknown outcomes; a later passing report does not erase them.');
        if (failures.length) gaps.push('Retained failures require explicit resolution in a new evaluation contract; a passing retry does not clear them.');
        if (validated.some(report => report.finishedAt !== null && Date.parse(report.finishedAt) >= Date.parse(c.expiresAt))) {
            gaps.push('A report completed outside the contract validity window.');
        }
    }
    const reportedComparison = status;
    if (expired) status = 'expired';
    return freeze({schema: 'specialist-evaluation-assessment/v1', contractDigest: f.contractDigest, missionId: c.missionId,
        candidate: c.participants.candidate, status, comparisons, failures, attemptResults, attempts: validated.length,
        expiresAt: c.expiresAt, assessedAt: now, gaps, reportedComparison, verification: 'uncommissioned',
        independentVerdict: 'not-established', admission: 'not-requested', independentProof: false,
        designation: 'not-earned', authority: 'none', nextDecision: 'Keep incumbent; commission a separately governed fresh evaluation if warranted.',
        limitations: ['All supplied results remain reports, even when signed. No trusted reviewer registry or custody verifier is commissioned.',
            'Beating these two comparators would establish only the registered mission comparison, not general ASI.',
            'A new candidate, source, dependency, task, metric or resource policy requires a new contract and fresh evidence.',
            'No provider, network, wallet, native execution, settlement or production admission occurs here.']});
}
export async function exportRecord(frozen, reports = []) {
    const f = await validateFrozen(frozen); list(reports, 0, 32);
    const history = [];
    for (const report of reports) history.push(await validateReport(report, f));
    unique(history, 'attemptId');
    const content = {schema: 'specialist-evaluation-record/v1', frozen: f, reports: history};
    return freeze({...content, recordDigest: await digest('specialist-evaluation-record', content)});
}
export async function restoreRecord(bytes, now = new Date().toISOString()) {
    const parsed = parseBounded(bytes); keys(parsed, ['schema', 'frozen', 'reports', 'recordDigest']);
    fail(parsed.schema === 'specialist-evaluation-record/v1', 'RECORD_VERSION');
    const record = await exportRecord(parsed.frozen, parsed.reports);
    fail(record.recordDigest === parsed.recordDigest, 'RECORD_CHANGED');
    return freeze({record, assessment: await assess(record.frozen, record.reports, now),
        recovery: 'historical-reports-only', authority: 'none', nextAction: 'Fresh authorization and governed verification remain required.'});
}
/** Illustrative contract scaffold only; replace every placeholder commitment before real commissioning. */
export function exampleContract(now = new Date().toISOString()) {
    time(now);
    const pin = n => n.toString(16).padStart(64, '0');
    return {schema: SCHEMA, missionId: 'illustrative-mission', mission: 'Replace with one measurable, bounded mission.',
        exclusions: 'Illustrative scaffold. No real candidate, protected cases, evaluator or test has been commissioned.',
        proposalDigest: pin(1), createdAt: now, expiresAt: new Date(Date.parse(now) + 86400000).toISOString(),
        participants: Object.fromEntries(ROLES.map((role, index) => [role, {id: `illustrative-${role}`, sourceHash: pin(index + 2),
            configurationHash: pin(5), toolsHash: pin(6), knowledgeHash: pin(7), interfacesHash: pin(8)}])),
        alternativeRationale: 'Replace with the evidence for selecting the best credible alternative and its limitations.',
        evaluation: {taskSetCommitment: pin(9), formationSetCommitment: pin(10), protocolHash: pin(11),
            resourcePolicyHash: pin(12), trialCount: 1, custodianId: 'unassigned-custodian'},
        metrics: DIMENSIONS.map(dimension => ({id: dimension, dimension, unit: 'define-common-integer-scaled-unit',
            direction: dimension === 'quality' || dimension === 'robustness' ? 'higher' : 'lower', minimumGain: 0,
            methodHash: pin(13), uncertaintyMethodHash: pin(14)})),
        constraints: [{id: 'mission-safety', requirementHash: pin(15)}],
        review: {reviewerId: 'unassigned-reviewer', organizationId: 'unassigned-organization', independencePolicyHash: pin(16),
            conflictDisclosureHash: pin(17), custodyPolicyHash: pin(18)}};
}
export async function reportTemplate(frozen, now = new Date().toISOString()) {
    const f = await validateFrozen(frozen); time(now);
    return {schema: 'specialist-evaluation-report/v1', contractDigest: f.contractDigest, attemptId: 'replace-attempt-id',
        startedAt: now, finishedAt: null, state: 'uncertain', evidenceDigest: '0'.repeat(64),
        rows: await Promise.all(ROLES.map(async role => ({role,
            participantDigest: await digest('specialist-participant', f.contract.participants[role]),
            taskSetCommitment: f.contract.evaluation.taskSetCommitment, protocolHash: f.contract.evaluation.protocolHash,
            resourcePolicyHash: f.contract.evaluation.resourcePolicyHash, trialCount: 0,
            metrics: f.contract.metrics.map(m => ({id: m.id, lower: null, upper: null, evidenceDigest: null})),
            constraints: f.contract.constraints.map(c => ({id: c.id, status: 'unknown', evidenceDigest: null}))}))), failures: []};
}
