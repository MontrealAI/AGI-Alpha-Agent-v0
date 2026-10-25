// SPDX-License-Identifier: Apache-2.0
import * as accounting from './shadow-ledger.mjs';
import {canonical, parseBounded} from '../../docs/assets/successor/engine.mjs';

export const SCHEMA = 'successor-alpha-shadow-plans/v1';
const copy = value => parseBounded(canonical(value));
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value,key));
const fields = ['currency','acceptance','totalCollectedCents','priceAssumptionCents','totalOperatingCostCents',
    'operatingCostsComplete','capabilityCostCents','reserveCents','obligationCents','costBasis',
    'reinvestmentBps','humanMinutes','humanHourlyCents','traditionalMinutes'];

export function createPlans(project) {
    if (!project || typeof project.id !== 'string' || !Array.isArray(project.cycles)) throw Error('A project is required.');
    return {schema:SCHEMA,projectId:project.id,entries:[],authority:'none'};
}

export function inspectPlans(raw, project) {
    if (typeof raw === 'string' && new TextEncoder().encode(raw).length > 200000) throw Error('Planning history exceeds 200 KB.');
    const archive = typeof raw === 'string' ? parseBounded(raw) : copy(raw);
    if (!exact(archive,['schema','projectId','entries','authority']) || archive.schema !== SCHEMA
        || archive.authority !== 'none' || archive.projectId !== project?.id
        || !Array.isArray(archive.entries) || archive.entries.length > 24) throw Error('Planning history belongs to a different project or format.');
    for (const entry of archive.entries) {
        const cycle = project.cycles.find(item => item.id === entry.cycleId);
        if (!exact(entry,['cycleId','sourceHash','inputs']) || !cycle || entry.sourceHash !== cycle.sourceHash
            || !exact(entry.inputs,fields) || entry.inputs.costBasis !== 'assumed') throw Error('Planning inputs do not match a retained cycle.');
        accounting.planMission({...entry.inputs,missionId:cycle.id,reference:`local-cycle:${cycle.id}:${cycle.sourceHash}`});
    }
    return archive;
}

export function recordPlan(archive, project, inputs) {
    const next = inspectPlans(archive,project), cycle = project.cycles.at(-1);
    if (!cycle) throw Error('Complete a local catalogue mission before planning its economics.');
    const entry = {cycleId:cycle.id,sourceHash:cycle.sourceHash,inputs:copy(inputs)};
    if (next.entries.length && canonical(next.entries.at(-1)) === canonical(entry)) return next;
    if (next.entries.length >= 24) throw Error('Planning history contains 24 revisions. Export it before starting another project.');
    next.entries.push(entry);
    return inspectPlans(next,project);
}

export function replayPlans(raw, project) {
    const archive = inspectPlans(raw,project), latest = new Map();
    for (const entry of archive.entries) latest.set(entry.cycleId,entry);
    return {schema:SCHEMA,projectId:project.id,revisions:archive.entries.length,authority:'none',
        scope:'User-entered planning assumptions linked to locally checked catalogue cycles; no authenticated cash, commercial acceptance or spending authority.',
        missions:[...latest.values()].map(entry => ({cycleId:entry.cycleId,sourceHash:entry.sourceHash,
            ...accounting.planMission({...entry.inputs,missionId:entry.cycleId,reference:`local-cycle:${entry.cycleId}:${entry.sourceHash}`})}))};
}
