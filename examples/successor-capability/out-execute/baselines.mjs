// SPDX-License-Identifier: Apache-2.0
/** Competitive alternatives with their actual scope, not manufactured speedup claims. */
import {exhaustive, verifyArtifact} from './checker.mjs';
import {validateModel, same, clone} from './model.mjs';
export function fromScratch(input) {
    const model = validateModel(input), result = exhaustive(model);
    const validation = result.status === 'OPTIMAL' ? verifyArtifact(model, result.artifact, result.cost).factorLookups : 0;
    const inputEntries = model.factors.reduce((n, f) => n + f.costs.length, 0);
    return {...result, countedWork: inputEntries + result.work.assignments + result.work.factorLookups + validation,
        additionalWork: {inputEntries, outputFactorLookups: validation},
        scope: 'independent-full-enumeration-no-decomposition; no currency or wall-clock claim'};
}

/** A sufficient fixed-proof guard: unchanged support and a constant cost shift per factor.
 * The previous optimum is known from this runner's own execution, never an imported asserted hash.
 */
export function fixedCertificateRunner() {
    let previous = null;
    return input => {
        const model = validateModel(input), entries = model.factors.reduce((n, f) => n + f.costs.length, 0);
        let guarded = previous !== null && same(model.variables, previous.model.variables)
            && same(model.factors.map(({id, scope}) => ({id, scope})), previous.model.factors.map(({id, scope}) => ({id, scope})));
        let delta = 0, guardEntries = 0;
        if (guarded) for (const [i, factor] of model.factors.entries()) {
            const old = previous.model.factors[i]; let localDelta = null;
            for (let j = 0; j < factor.costs.length; j++) {
                guardEntries++;
                if ((factor.costs[j] === null) !== (old.costs[j] === null)) guarded = false;
                if (factor.costs[j] !== null && old.costs[j] !== null) {
                    const difference = factor.costs[j] - old.costs[j];
                    if (localDelta !== null && localDelta !== difference) guarded = false;
                    localDelta = difference;
                }
            }
            delta += localDelta || 0;
        }
        let result;
        if (guarded && previous.result.status !== 'INCONCLUSIVE') {
            const cost = previous.result.cost === null ? null : previous.result.cost + delta;
            const artifact = clone(previous.result.artifact);
            const outputFactorLookups = artifact === null ? 0 : verifyArtifact(model, artifact, cost).factorLookups;
            result = {status: previous.result.status, artifact, cost, retained: true,
                countedWork: entries + guardEntries + outputFactorLookups,
                work: {assignments: 0, factorLookups: outputFactorLookups, guardEntries, inputEntries: entries}};
        } else {
            result = {...fromScratch(model), retained: false}; result.countedWork += guardEntries;
            result.work.guardEntries = guardEntries;
        }
        previous = {model: clone(model), result: clone(result)};
        return {...result, certificateScope: 'known-local-optimum + equal forbidden support + constant finite factor shifts'};
    };
}
