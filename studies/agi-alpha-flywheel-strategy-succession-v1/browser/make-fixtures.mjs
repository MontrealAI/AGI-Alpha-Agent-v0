// SPDX-License-Identifier: Apache-2.0
// Development-only generator. Normal bundle builds reuse frozen input bytes.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {demoConfiguration} from '../companion/scenarios.mjs';

if (!process.argv.includes('--regenerate-development-fixtures')) {
    throw new Error('Explicit --regenerate-development-fixtures required; never regenerate after a study freeze.');
}
const root = path.dirname(fileURLToPath(import.meta.url));
const config = demoConfiguration();
const source = `// SPDX-License-Identifier: Apache-2.0
// Fixed synthetic demonstration inputs; all live results are computed afresh.
// Generated once by make-fixtures.mjs before the scientific/browser freeze.
const CONFIG = ${JSON.stringify(config, null, 2)};

export function browserConfiguration({diagnostic = false} = {}) {
    const config = JSON.parse(JSON.stringify(CONFIG));
    config.policy.mode = diagnostic ? 'diagnostic' : 'flywheel';
    config.policy.totalWork = diagnostic ? 5000000 : 3000000;
    config.policy.discoveryWork = diagnostic ? 1500000 : 750000;
    config.policy.label = diagnostic
        ? 'Fresh diagnostic construction; correctness-only retention is separate from economic admission'
        : 'Fresh selective execution; full costs can rationally retain the incumbent';
    return config;
}
`;
await fs.writeFile(path.join(root, 'mission-fixtures.mjs'), source);
const sha = value => createHash('sha256').update(value).digest('hex');
const parents = {};
for (const name of ['core.mjs', 'scenarios.mjs', 'development_tasks.mjs']) {
    parents[`companion/${name}`] = sha(await fs.readFile(path.join(root, '..', 'companion', name)));
}
const record = {
    schema: 'strategy-succession-browser-fixtures/v1',
    phase: 'DEVELOPMENT_BEFORE_FREEZE',
    construction_runtime: process.version,
    generator: 'browser/make-fixtures.mjs --regenerate-development-fixtures',
    source_parents: parents,
    file: 'mission-fixtures.mjs',
    sha256: sha(source),
    missions: config.tasks.map(task => ({id: task.id, scope: task.scope, deadline: task.deadline})),
    qualification: Object.fromEntries(Object.entries(config.qualification).map(([stage, corpus]) => [stage, {
        training: corpus.training.map(task => task.id),
        validation: corpus.validation.map(task => task.id),
    }])),
    purpose: 'Six finite public synthetic demonstration missions and fixed development/qualification corpora; separate from protected confirmation tasks.',
    input_construction: 'Repair inputs include a pre-disruption conventional schedule, locked work and a changed capacity calendar. This creates synthetic mission inputs; it is not a retained candidate or paid demand.',
    replay_status: 'Inputs are fixed; schedules, discovery, qualification, admission, and local recovery execute freshly in the browser.',
    reason_frozen: 'A development reload test observed regenerated fixture baseline_work vary from 6096 to 6115. Fixed inputs make configuration identity stable; the failed run and exact digest inputs are retained.',
};
await fs.writeFile(path.join(root, 'FIXTURE_PROVENANCE.json'), `${JSON.stringify(record, null, 2)}\n`);
console.log(JSON.stringify({file: record.file, sha256: record.sha256, missions: config.tasks.length}));
