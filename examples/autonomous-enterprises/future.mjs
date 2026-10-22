// SPDX-License-Identifier: Apache-2.0
import {copy, same, need, digest, completeConstructionWork, chargeReplay, noteFailedReplay} from './protocol.mjs';
import {buildFoundry, executeQualified} from './foundry.mjs';
import {qualifyArtifact, verifyBundle, specificationApplication} from './checker.mjs';
import {applySpecialist} from './specialist.mjs';

export const TREATMENTS = Object.freeze(['inherited', 'capability-removed', 'from-scratch',
    'competent-static-specialist', 'unrestricted-same-primitive-joint']);
function artifact(bundle, kind) {
    const result = bundle.envelopes.find(item => item.artifact.kind === kind && item.artifact.n === bundle.maxN);
    need(result, 'The frozen executable interface is unavailable.'); return result;
}
function specification(task, n) {
    return specificationApplication(task.kind, task.inputs, task.kind === 'inverse'
        ? {kernel: Array.from({length: n}, (_, i) => String(i ? 1 : n + 1))} : {});
}
export async function evaluateFuture(bundle, freeze, bank, perTaskLimit) {
    bundle = copy(bundle); freeze = copy(freeze); bank = copy(bank);
    need(freeze.bundleDigest === await digest(bundle) && bank.freezeDigest === freeze.digest,
        'Future tasks must use the exact previously frozen executable bytes.');
    const {digest: freezeDigest, ...frozenFields} = freeze, {digest: bankDigest, ...bankFields} = bank;
    need(freezeDigest === await digest(frozenFields) && bankDigest === await digest(bankFields)
        && bank.tasks.length >= 1 && bank.tasks.length <= 3, 'Future freeze or task-bank commitment changed.');
    let admission;
    try { admission = await verifyBundle(bundle); }
    catch (error) { noteFailedReplay(); throw error; }
    chargeReplay('bundleReplayWork', admission.currentReplayWork);
    const runs = []; let joint = null;
    for (const task of bank.tasks) {
        for (const treatment of TREATMENTS) {
            let retained = bundle, buildWork = 0, path, result;
            const modelBuildWork = completeConstructionWork(bundle);
            const needsBuild = treatment === 'from-scratch' || treatment === 'unrestricted-same-primitive-joint' && !joint;
            const n = bundle.maxN, directWork = task.kind === 'walsh' ? n * (n - 1)
                : task.kind === 'xor-convolution' ? 2 * n * n - n : 3 * n;
            const producingWork = treatment === 'capability-removed' ? directWork
                : treatment === 'competent-static-specialist' && task.kind === 'inverse' ? 3 * n
                    : artifact(bundle, task.kind).artifact.operatingWork;
            const required = (needsBuild ? modelBuildWork : 0) + producingWork + directWork + n;
            if (required > perTaskLimit) {
                runs.push({taskId: task.id, treatment, state: 'INCONCLUSIVE', reason: 'CONSTRUCTION_ALLOWANCE_EXHAUSTED',
                    path: 'not-started', constructionWork: 0, arithmetic: 0, output: null, accepted: false});
                continue;
            }
            if (needsBuild) {
                retained = await buildFoundry({qualifyArtifact, maxN: bundle.maxN});
                buildWork = completeConstructionWork(retained);
                if (treatment === 'unrestricted-same-primitive-joint') joint = retained;
            } else if (treatment === 'unrestricted-same-primitive-joint') retained = joint;
            if (treatment === 'capability-removed') {
                result = specification(task, bundle.maxN);
                path = 'direct-classical-definition/no-artifact-dependencies';
            } else if (treatment === 'competent-static-specialist') {
                result = applySpecialist(task.kind, task.inputs);
                path = 'fixed-fast-specialist/no-generated-artifact-dependencies';
            } else {
                const selected = artifact(retained, task.kind);
                result = executeQualified(selected.artifact, retained.envelopes, task.inputs);
                path = 'restricted-ast/' + selected.digest;
            }
            const expected = specification(task, bundle.maxN);
            const totalWork = buildWork + result.arithmetic + expected.arithmetic + result.output.length;
            const accepted = same(result.output, expected.output);
            runs.push({taskId: task.id, treatment,
                state: totalWork > perTaskLimit ? 'INCONCLUSIVE' : accepted ? 'ACCEPTED' : 'REJECTED',
                reason: totalWork > perTaskLimit ? 'MEASURED_LOGICAL_ALLOWANCE_EXCEEDED' : 'COMPLETE_EXACT_OUTPUT_CHECK',
                path, constructionWork: buildWork, arithmetic: result.arithmetic, acceptanceWork: expected.arithmetic
                    + result.output.length, totalWork, output: result.output, accepted: accepted && totalWork <= perTaskLimit});
        }
    }
    const value = {schema: 'autonomous-enterprise-future-evaluation/v1', freezeDigest: freeze.digest,
        taskBankDigest: bank.digest, perTaskLimit, treatments: [...TREATMENTS], runs,
        removalChangedExecutedPath: runs.filter(run => run.treatment === 'capability-removed')
            .every(run => run.path === 'direct-classical-definition/no-artifact-dependencies'),
        constructionComparison: bundle.controls,
        lineage: {historicalConstructionAndBothInverseControls: completeConstructionWork(bundle),
            knownFutureTreatmentWork: runs.reduce((total, run) => total + (run.totalWork || 0), 0),
            totalComplete: false, unknown: ['bit complexity', 'wall-clock overhead', 'coordination', 'review', 'money', 'energy']},
        currentBundleAdmissionWork: admission.currentReplayWork,
        interpretation: 'Matched declared allowances and public inputs. The fixed fast specialist ties generated Walsh/convolution operating counts and has a cheaper fixed-kernel inverse. Its supplied code and proof authoring are unmeasured. Joint comparison uses the same supplied recipes; initial and research-control charges remain visible.',
        operationalPilot: 'NOT_RUN', authority: []};
    return {...value, digest: await digest(value)};
}
export async function verifyFuture(bundle, freeze, bank, report) {
    report = copy(report);
    const current = await evaluateFuture(bundle, freeze, bank, report.perTaskLimit);
    chargeReplay('futureReplayWork', current.lineage.knownFutureTreatmentWork);
    need(same(report, current), 'Future invocation, comparisons or lineage changed.');
    return {verified: true, reportDigest: report.digest,
        currentReplayWork: current.lineage.knownFutureTreatmentWork + current.currentBundleAdmissionWork,
        scope: 'Local protocol replay; distinct extra replay work, no operational or institutional acceptance'};
}
