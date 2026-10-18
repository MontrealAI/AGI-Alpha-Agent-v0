// SPDX-License-Identifier: Apache-2.0
import * as alpha from './engine.mjs';
import { validateResearch } from './research.mjs';

const LIMIT = 250000;
const fail = message => { throw Error(message); };
const encoder = new TextEncoder();
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));

async function sourceDigest(text) {
    const digest = await crypto.subtle.digest('SHA-256', encoder.encode(text));
    return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

function reviewedModule(source, name) {
    if (typeof source !== 'string' || !source.startsWith('// SPDX-License-Identifier: Apache-2.0\n')
        || encoder.encode(source).length > LIMIT) fail(`${name} must be reviewed Apache-2.0 source of at most ${LIMIT} bytes.`);
    let body = source;
    if (name === 'research') {
        const dependency = "import * as alpha from './engine.mjs';";
        if (source.split(dependency).length !== 2) fail('Research source must declare its one known engine import.');
        body = body.replace(dependency, '');
    }
    body = body.replace(/^export (?=(?:async )?function |const )/gm, '');
    if (/^\s*(?:import|export)\b/m.test(body) || /\bimport\s*\(/.test(body)
        || /\b(?:eval|Function|fetch|XMLHttpRequest|WebSocket)\s*\(/.test(body)) {
        fail(`${name} contains an unsupported import, export, dynamic evaluator, or external-service call.`);
    }
    return body;
}

export async function buildPlanCapability(mission, report, options) {
    alpha.validateJoinMission(mission);
    if (!exact(options, ['sourceHash', 'engineSource', 'researchSource'])
        || typeof options.sourceHash !== 'string' || !/^[a-f0-9]{64}$/.test(options.sourceHash)) {
        fail('Capability creation requires exact reviewed sources and a source identity.');
    }
    await validateResearch(report, mission, { sourceHash: options.sourceHash });
    const engine = reviewedModule(options.engineSource, 'engine');
    const research = reviewedModule(options.researchSource, 'research');
    const metadata = {
        schema: 'successor-retained-capability/v1', sourceHash: options.sourceHash,
        componentHashes: { engine: await sourceDigest(options.engineSource), research: await sourceDigest(options.researchSource) },
        retainedPlan: report.decision.retainedPlan, planHash: report.decision.retainedPlanHash, objective: report.objective,
        origin: { decision: report.decision.state, frozenNomineeCommitment: report.frozen.commitment },
        qualification: 'local_engineering_only', protectedHoldout: false, independentlyQualified: false, externalAuthority: false,
        scope: [
            'Runs the exact retained typed join program on newly supplied bounded CSV inputs and rechecks its complete output.',
            'The host supplies reviewed engine and research source. Component hashes identify those bytes; this is not a publisher signature.',
            'The sourceHash identifies the host research context; the component hashes identify the two modules embedded in this capability.',
            'The auxiliary-row resource proxy is checked for each new input. It is not an operating-system memory sandbox.',
            'No filesystem reads, built-in module imports, model calls, network calls, credentials, funding, or external authority are included.',
            'CSV output escapes formula-like cells; exact JSON preserves original input strings. No economic or general capability claim.',
        ],
    };
    const source = '// SPDX-License-Identifier: Apache-2.0\n'
        + '// Standalone retained SUCCESSOR join program. Import this module and call reconcileCatalogs with CSV strings.\n'
        + 'const __engine = (() => {\n' + engine + '\nreturn Object.freeze({createJoinMission,verifyJoinResult,'
        + 'exportJoinedCsv,exportReconciliationCsv,reconcile,DEFAULT_LIMITS,validateJoinMission,createSampleMission,'
        + 'executeJoin,verifyExperiment});\n})();\n'
        + 'const __research = ((alpha) => {\n' + research
        + '\nreturn Object.freeze({executePlan,validatePlan});\n})(__engine);\n'
        + 'const __freeze = value => { if(value && typeof value === "object") {Object.freeze(value);'
        + 'for(const child of Object.values(value)) __freeze(child);} return value; };\n'
        + 'export const metadata = __freeze(' + JSON.stringify(metadata) + ');\n'
        + `export function reconcileCatalogs(input) {
    const mission = __engine.createJoinMission(input);
    const execution = __research.executePlan(mission, metadata.retainedPlan);
    if (execution.metrics.peakAuxiliaryRows > metadata.objective.maxAuxiliaryRows) {
        throw Error('New input exceeds the retained program auxiliary-row constraint; no result was admitted.');
    }
    __engine.verifyJoinResult(mission, execution.pairs);
    const reconciliation = __engine.reconcile(mission, execution.pairs);
    const joinedCsv = __engine.exportJoinedCsv(mission, execution.pairs);
    const unmatchedLeftCsv = __engine.exportReconciliationCsv(mission, reconciliation, 'unmatched_left');
    const unmatchedRightCsv = __engine.exportReconciliationCsv(mission, reconciliation, 'unmatched_right');
    const conflictsCsv = __engine.exportReconciliationCsv(mission, reconciliation, 'conflicts');
    const scope = {qualification:'local_engineering_only',independentlyQualified:false,protectedHoldout:false,
        externalAuthority:false,sourceHash:metadata.sourceHash,planHash:metadata.planHash};
    const exactJson = JSON.stringify({schema:'successor-retained-result/v1',mission,plan:metadata.retainedPlan,
        pairs:execution.pairs,metrics:execution.metrics,reconciliation,scope},null,2)+'\\n';
    if (new TextEncoder().encode(exactJson).length > mission.limits.maxOutputBytes * 4) {
        throw Error('Exact retained-program artifact exceeds its bounded output budget.');
    }
    return {pairs:execution.pairs,metrics:execution.metrics,reconciliation,joinedCsv,unmatchedLeftCsv,
        unmatchedRightCsv,conflictsCsv,exactJson,scope};
}
`;
    if (encoder.encode(source).length > LIMIT * 2 + 20000) fail('Standalone capability source exceeds its file budget.');
    return source;
}
