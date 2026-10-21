// SPDX-License-Identifier: Apache-2.0
// Six closed, versioned data artifacts inherit one frozen mission/source commitment.
import * as contract from './discovery-lab-contract.mjs';
export const ARTIFACT_SCHEMA = 'discovery-lab-artifact/v1';
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const same = (a, b) => contract.canonical(a) === contract.canonical(b);
const fields = ['schema', 'kind', ...contract.BINDING_KEYS, 'inputArtifacts', 'scope', 'assumptions',
    'payload', 'checkerOutcome', 'attempts', 'costs', 'dependencies', 'invalidations', 'executionMode', 'state'];
export async function validateArtifact(input) {
    contract.canonical(input);
    if (!exact(input, [...fields, 'digest']) || input.schema !== ARTIFACT_SCHEMA
        || !contract.STAGES.includes(input.kind) || input.executionMode !== 'synthetic-local') {
        throw Error('Unsupported versioned Discovery Lab artifact.');
    }
    contract.validateBindings(Object.fromEntries(contract.BINDING_KEYS.map(key => [key, input[key]])));
    const stage = input.payload;
    if (!exact(stage, ['kind', 'inputs', 'scope', 'assumptions', 'program', 'evidence', 'checker',
        'attempts', 'reason', 'status', 'cost']) || stage.kind !== input.kind || !same(input.scope, stage.scope)
        || !same(input.assumptions, stage.assumptions) || !same(input.checkerOutcome, stage.checker)
        || !same(input.attempts, stage.attempts) || !same(input.costs, stage.cost)
        || !same(input.dependencies, stage.inputs) || input.state !== stage.status
        || !['searching', 'candidate', 'qualifying', 'accepted', 'rejected', 'inconclusive', 'paused',
            'invalidated', 'superseded'].includes(input.state)
        || !Array.isArray(input.attempts) || !Array.isArray(input.dependencies)
        || !input.dependencies.every(kind => contract.STAGES.indexOf(kind) >= 0
            && contract.STAGES.indexOf(kind) < contract.STAGES.indexOf(input.kind))
        || !exact(input.costs, ['acquisitions', 'search', 'checking', 'memoryWords', 'storageBytes', 'workerSlots', 'installations'])
        || !Object.values(input.costs).every(value => Number.isSafeInteger(value) && value >= 0 && !Object.is(value, -0))
        || !exact(input.invalidations, ['changed', 'earliest', 'invalidated'])
        || !Array.isArray(input.invalidations.changed) || !Array.isArray(input.invalidations.invalidated)
        || !input.invalidations.changed.every(value => typeof value === 'string' && /^[A-Za-z][A-Za-z0-9]{0,63}$/.test(value))
        || ![null, ...contract.STAGES].includes(input.invalidations.earliest)
        || !input.invalidations.invalidated.every(value => contract.STAGES.includes(value))
        || input.state === 'accepted' && (!stage.program || stage.checker?.accepted !== true)
        || !Array.isArray(input.inputArtifacts)
        || input.inputArtifacts.length !== contract.STAGES.indexOf(input.kind)
        || !input.inputArtifacts.every(value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value))
        || new Set(input.inputArtifacts).size !== input.inputArtifacts.length) {
        throw Error('Artifact payload, checker, costs or dependency commitment mismatch.');
    }
    const body = Object.fromEntries(fields.map(key => [key, input[key]]));
    if (input.digest !== await contract.payloadDigest(body)) throw Error('Artifact digest mismatch.');
    return JSON.parse(contract.canonical(input));
}
export async function makeArtifacts(bindings, result) {
    const bound = contract.validateBindings(bindings);
    contract.canonical(result);
    if (result.schema !== 'discovery-lab-campaign/v1' || !Array.isArray(result.stages)
        || result.stages.length !== 6 || !result.stages.every((stage, index) => stage.kind === contract.STAGES[index])) {
        throw Error('All six ordered campaign artifacts are required.');
    }
    const artifacts = [];
    for (const stage of result.stages) {
        const body = {schema: ARTIFACT_SCHEMA, kind: stage.kind, ...bound,
            inputArtifacts: artifacts.map(artifact => artifact.digest), scope: stage.scope,
            assumptions: stage.assumptions, payload: stage, checkerOutcome: stage.checker, attempts: stage.attempts,
            costs: stage.cost, dependencies: stage.inputs, invalidations: result.invalidations,
            executionMode: 'synthetic-local', state: stage.status};
        artifacts.push(await validateArtifact({...body, digest: await contract.payloadDigest(body)}));
    }
    return artifacts;
}
