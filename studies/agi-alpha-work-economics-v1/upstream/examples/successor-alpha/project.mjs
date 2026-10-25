// SPDX-License-Identifier: Apache-2.0
import * as alpha from './engine.mjs';
import { canonical, parseBounded } from '../../docs/assets/successor/engine.mjs';

export const VERSION = 'successor-alpha-project/v1';
let engineSource = '';
let deployment = null;
const copy = value => parseBounded(canonical(value));
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).sort().join('|') === [...keys].sort().join('|');
const text = (value, max, field) => {
    if (typeof value !== 'string' || !value.trim() || value.length > max) throw Error(`Invalid ${field}.`);
    return value;
};
const time = value => typeof value === 'string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(value)
    && Number.isFinite(Date.parse(value)) && new Date(value).toISOString() === value;
const id = value => typeof value === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(value);
const escapeHtml = value => String(value).replace(/[&<>"']/g, char =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));

export function configure(options) {
    if (typeof options.engineSource !== 'string' || options.engineSource.length > 1000000) throw Error('Invalid engine source.');
    engineSource = options.engineSource;
    deployment = options.deployment ? copy(options.deployment) : null;
}

export function tableCsv(table) {
    return [table.headers, ...table.rows].map(row => row.map(cell =>
        '"' + String(cell).replaceAll('"', '""') + '"').join(',')).join('\n') + '\n';
}

export function createProject({ name = 'My SUCCESSOR Ω', goal = 'Reconcile two public catalogs and retain a reusable method.' } = {}) {
    const now = new Date().toISOString();
    return { schema: VERSION, id: crypto.randomUUID(), revision: 0, name: text(name, 80, 'name'),
        goal: text(goal, 2000, 'goal'), createdAt: now, updatedAt: now, cycles: [], opportunities: [],
        qualification: 'not_independently_qualified', authority: 'none' };
}

function validateCycle(cycle) {
    if (!exact(cycle, ['id', 'createdAt', 'sourceHash', 'mission', 'result', 'origin'])) throw Error('Invalid cycle fields.');
    if (!id(cycle.id) || !time(cycle.createdAt) || !/^[0-9a-f]{64}$/.test(cycle.sourceHash)
        || cycle.origin !== 'local_engineering_run') throw Error('Invalid cycle identity.');
    alpha.validateJoinMission(cycle.mission);
    const r = cycle.result;
    alpha.verifyExperiment(cycle.mission, r);
    if (!r || r.schemaVersion !== 1 || r.missionKind !== 'catalog_join'
        || !Array.isArray(r.strategies) || r.strategies.length !== alpha.STRATEGIES.length
        || r.assessment?.externalAuthority !== false || r.assessment?.independentReview !== 'pending'
        || r.assessment?.superiorityClaim !== false) throw Error('Invalid local result scope.');
    const ids = r.strategies.map(s => s.strategyId);
    if (canonical(ids) !== canonical(alpha.STRATEGIES.map(s => s.id))) throw Error('Invalid comparison methods.');
    for (const strategy of r.strategies) {
        if (!strategy.verified || !strategy.metrics || !Number.isSafeInteger(strategy.metrics.elapsedMicros)
            || strategy.metrics.elapsedMicros < 0) throw Error('Invalid recorded measurement.');
        alpha.verifyJoinResult(cycle.mission, strategy.pairs);
    }
    // Imported measurements remain historical even when their output can be recomputed.
    alpha.buildArtifacts(cycle.mission, r);
}

export function inspectProject(serialized) {
    const p = typeof serialized === 'string' ? parseBounded(serialized) : copy(serialized);
    if (!exact(p, ['schema', 'id', 'revision', 'name', 'goal', 'createdAt', 'updatedAt', 'cycles',
        'opportunities', 'qualification', 'authority']) || p.schema !== VERSION || !id(p.id)
        || !time(p.createdAt) || !time(p.updatedAt) || !Number.isSafeInteger(p.revision) || p.revision < 0
        || p.qualification !== 'not_independently_qualified' || p.authority !== 'none'
        || !Array.isArray(p.cycles) || p.cycles.length > 6 || !Array.isArray(p.opportunities)
        || p.opportunities.length > 12) throw Error('Unsupported or invalid SUCCESSOR project.');
    text(p.name, 80, 'name'); text(p.goal, 2000, 'goal');
    const seen = new Set();
    for (const cycle of p.cycles) {
        if (seen.has(cycle.id)) throw Error('Duplicate cycle identity.');
        seen.add(cycle.id); validateCycle(cycle);
    }
    for (const opportunity of p.opportunities) validateOpportunity(opportunity);
    return p;
}

export function serializeProject(dossier) {
    return canonical(inspectProject(dossier));
}

export function renameProject(dossier, name) {
    const next = inspectProject(dossier);
    text(name, 80, 'name');
    if (next.name !== name) {
        next.name = name; next.revision += 1; next.updatedAt = new Date().toISOString();
    }
    return next;
}

export function appendCycle(dossier, { mission, result, sourceHash }) {
    const next = inspectProject(dossier);
    if (next.cycles.length >= 6) throw Error('This project contains six full cycles. Export it before starting a separate project.');
    const cycle = { id: crypto.randomUUID(), createdAt: new Date().toISOString(), sourceHash,
        mission: copy(mission), result: copy(result), origin: 'local_engineering_run' };
    validateCycle(cycle);
    next.cycles.push(cycle); next.revision += 1; next.updatedAt = cycle.createdAt;
    canonical(next);
    return next;
}

export function planOpportunity(fields) {
    const keys = ['goal', 'currentApproach', 'alternative', 'target', 'evidence', 'budget'];
    if (!exact(fields, keys)) throw Error('Unsupported opportunity fields.');
    const p = { schema: 'alpha-opportunity/v1', state: 'hypothesis',
        ...Object.fromEntries(keys.map(key => [key, text(fields[key], 2000, key)])),
        nextExperiment: 'Freeze a measurable target and compare one candidate with the current approach and a credible alternative.',
        independentReview: 'not_commissioned', authority: 'none' };
    return p;
}

function validateOpportunity(p) {
    if (!exact(p, ['schema', 'state', 'goal', 'currentApproach', 'alternative', 'target', 'evidence',
        'budget', 'nextExperiment', 'independentReview', 'authority']) || p.schema !== 'alpha-opportunity/v1'
        || p.state !== 'hypothesis' || p.independentReview !== 'not_commissioned' || p.authority !== 'none') {
        throw Error('Invalid opportunity scope.');
    }
    for (const key of ['goal', 'currentApproach', 'alternative', 'target', 'evidence', 'budget', 'nextExperiment']) {
        text(p[key], 2000, key);
    }
}

export function addOpportunity(dossier, fields) {
    const next = inspectProject(dossier);
    if (next.opportunities.length >= 12) throw Error('Export this project before recording more opportunities.');
    next.opportunities.push(planOpportunity(fields)); next.revision += 1; next.updatedAt = new Date().toISOString();
    return inspectProject(next);
}

export function estimateValue(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)
        || Object.keys(input).some(k => !['beforeMinutes', 'afterMinutes', 'runsPerMonth', 'hourlyValueCents', 'setupCents'].includes(k))) {
        throw Error('Unsupported value estimate fields.');
    }
    const { beforeMinutes, afterMinutes, runsPerMonth, hourlyValueCents, setupCents = 0 } = input;
    const values = { beforeMinutes, afterMinutes, runsPerMonth, hourlyValueCents, setupCents };
    if (Object.values(values).some(v => !Number.isSafeInteger(v) || v < 0 || v > 1000000)) throw Error('Use whole, nonnegative values up to 1,000,000.');
    const product = BigInt(beforeMinutes - afterMinutes) * BigInt(runsPerMonth) * BigInt(hourlyValueCents);
    const magnitude = ((product < 0n ? -product : product) + 30n) / 60n;
    const monthlyCents = Number(product < 0n ? -magnitude : magnitude);
    const netFirstMonthCents = monthlyCents - setupCents;
    if (!Number.isSafeInteger(monthlyCents)) throw Error('Estimate exceeds supported range.');
    return { schema: 'alpha-value-estimate/v1', inputs: values, monthlyCents, netFirstMonthCents,
        breakEvenMonths: monthlyCents > 0 ? Math.ceil(setupCents / monthlyCents) : null,
        status: 'user_supplied_assumptions', realizedValueMeasured: false,
        excludes: ['unentered operating costs', 'unentered integration costs', 'risk and error costs'] };
}

export function prepareHandoff(dossier, route = 'USDC') {
    const p = inspectProject(dossier);
    if (!['USDC', 'AGIALPHA'].includes(route)) throw Error('Choose USDC or AGIALPHA explicitly.');
    return { schema: 'alpha-unfunded-work-brief/v1', projectId: p.id, projectRevision: p.revision,
        route, state: 'unfunded_draft', goal: p.goal, name: p.name,
        market: route === 'USDC' ? 'AGIJobManager' : 'AscensionJobMarket / AGI Jobs v0',
        deployment: route === 'AGIALPHA' && deployment ? copy(deployment) : null,
        sourceCycles: p.cycles.map(c => ({ id: c.id, sourceHash: c.sourceHash })),
        packages: ['Implement or improve the scoped capability', 'Challenge correctness and omitted requirements',
            'Independently evaluate a frozen candidate against competitive alternatives'],
        requiredBeforeCommission: ['named owner and independent reviewer', 'exact inputs and permitted rights',
            'candidate and comparator commitments', 'protected evaluation protocol', 'acceptance criteria',
            'price, deadlines and reviewer capacity', 'explicit funding and authorization'],
        qualification: 'not_independently_qualified', authority: 'none', transactionPrepared: false };
}

export function buildReport(mission, result, { name = 'SUCCESSOR Ω', goal = 'Reconcile public catalogs.', language = 'en' } = {}) {
    alpha.validateJoinMission(mission);
    alpha.verifyExperiment(mission, result);
    const fr = language === 'fr', rec = result.reconciliation;
    const title = fr ? 'Votre résultat utile' : 'Your useful result';
    const rows = result.strategies.map(s => '<tr>' + [s.label, s.pairs.length, s.metrics.logicalOperations,
        s.metrics.indexedRows, s.metrics.elapsedMicros].map(v => '<td>' + escapeHtml(v) + '</td>').join('') + '</tr>').join('');
    return '<!doctype html><html lang="' + (fr ? 'fr' : 'en') + '"><meta charset="utf-8">'
        + '<meta name="viewport" content="width=device-width,initial-scale=1">'
        + '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
        + '<title>' + escapeHtml(name) + '</title><style>body{margin:3rem auto;padding:0 1.2rem;max-width:65rem;color:#261c39;background:#faf7ff;font:17px/1.65 system-ui}h1{font-size:2.5rem}table{border-collapse:collapse;width:100%}td,th{padding:.7rem;border:1px solid #d8cde8;text-align:left}.scroll{overflow:auto}small{color:#514563}</style>'
        + '<h1>' + title + ' · ' + escapeHtml(name) + '</h1><p>' + escapeHtml(goal) + '</p><p>'
        + escapeHtml(`${mission.left.rows.length} × ${mission.right.rows.length}`) + (fr ? ' lignes source' : ' source rows')
        + ' · ' + rec.matchedPairs + (fr ? ' correspondances' : ' matched pairs') + ' · ' + rec.unmatchedLeft.length
        + ' / ' + rec.unmatchedRight.length + (fr ? ' lignes sans correspondance' : ' unmatched rows') + ' · '
        + rec.conflicts.length + (fr ? ' paires en conflit' : ' conflicting pairs') + '</p><div class="scroll"><table><thead><tr>'
        + (fr ? ['Méthode', 'Paires', 'Opérations logiques', 'Lignes indexées', 'Temps local (µs)']
            : ['Method', 'Pairs', 'Logical operations', 'Indexed rows', 'Local time (µs)']).map(v => '<th>' + v + '</th>').join('')
        + '</tr></thead><tbody>' + rows + '</tbody></table></div><h2>' + (fr ? 'Portée des preuves' : 'Evidence scope')
        + '</h2><p>' + (fr ? 'Résultat local vérifiable. Les mesures temporelles sont descriptives; la qualification indépendante et la valeur économique réalisée restent à établir.'
            : 'Locally checked result. Timings are descriptive; independent qualification and realized economic value remain unestablished.')
        + '</p><ul>' + result.measurementNotes.map(v => '<li>' + escapeHtml(v) + '</li>').join('')
        + '</ul><p><small>SUCCESSOR Ω · Alpha Agent · Apache-2.0</small></p></html>';
}

export function buildCapability(mission, result) {
    alpha.validateJoinMission(mission);
    alpha.verifyExperiment(mission, result);
    if (!engineSource) throw Error('The reusable engine source is unavailable. Save your project and use the repository CLI.');
    const selected = result.candidateStrategyId;
    if (!alpha.STRATEGIES.some(s => s.id === selected)) throw Error('Unsupported strategy.');
    return engineSource + '\n' + `
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import {constants} from 'node:fs';
import {resolve, join} from 'node:path';
import {pathToFileURL} from 'node:url';
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const [leftFile, rightFile, leftKey, rightKey, output] = process.argv.slice(2);
  if (!leftFile || !rightFile || !leftKey || !rightKey || !output) {
    console.error('Usage: node successor-tool.mjs left.csv right.csv leftKey rightKey NEW-output-directory');
    process.exitCode = 2;
  } else {
    const fsStat = await import('node:fs/promises');
    const readBounded=async path=>{
      const initial=await fsStat.stat(path);
      if(!initial.isFile()||initial.size>200000)throw Error('Input must be a regular CSV file up to 200 KB.');
      const handle=await fsStat.open(path,constants.O_RDONLY|constants.O_NONBLOCK);
      try {
        const stat=await handle.stat();
        if(!stat.isFile()||stat.size>200000)throw Error('Input must be a regular CSV file up to 200 KB.');
        const bytes=Buffer.alloc(200001);
        let used=0;
        while(used<bytes.length){
          const {bytesRead}=await handle.read(bytes,used,bytes.length-used,null);
          if(bytesRead===0)break;
          used+=bytesRead;
        }
        if(used>200000)throw Error('CSV exceeds 200 KB.');
        return new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(0,used));
      }finally{await handle.close();}
    };
    const mission=createJoinMission({leftCsv:await readBounded(leftFile),rightCsv:await readBounded(rightFile),leftKey,rightKey});
    const result=await runJoinExperiment(mission);
    const files=buildArtifacts(mission,result);
    await mkdir(output,{recursive:false});
    for(const [key,name] of Object.entries({joinedCsv:'joined.csv',unmatchedLeftCsv:'unmatched-left.csv',unmatchedRightCsv:'unmatched-right.csv',conflictsCsv:'conflicts.csv',exactJson:'exact-result.json'})) {
      await writeFile(join(output,name),files[key],{encoding:'utf8',flag:'wx'});
    }
    await writeFile(join(output,'comparison.json'),JSON.stringify(result,null,2)+'\\n',{flag:'wx'});
    console.log('Reconciliation complete. Results are local engineering evidence; independent qualification remains pending.');
  }
}
`;
}
