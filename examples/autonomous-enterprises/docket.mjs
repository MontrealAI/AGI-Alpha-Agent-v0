// SPDX-License-Identifier: Apache-2.0
// Extend the canonical thirteen sections; the existing run.json remains the complete replay authority.
import {canonical} from '../successor-capability/discovery-lab-contract.mjs';
import {summary} from './history.mjs';
import {syntheticCapitalExample, capitalControls} from './capital.mjs';
export function extendDocket(files, inspection) {
    if (!inspection.enterprises) return files;
    const state = inspection.enterprises, overview = summary(state);
    const records = state.attempts;
    const add = (path, value) => {
        const before = JSON.parse(files[path]); before.autonomousEnterprises = value;
        files[path] = canonical(before) + '\n';
    };
    files['00_manifest.md'] += '\nAutonomous Enterprises is an additive paper companion within the same mission and thirteen-section docket.\n';
    files['01_claims_matrix.md'] += '\n| Autonomous Enterprises | Independent bounded reimplementation; companion package not obtained |\n'
        + '| Selected construction recipes | Actual receipts; restricted classical arithmetic templates |\n'
        + '| Funding and settlement | Synthetic only; no collected revenue or transaction |\n';
    files['02_environment.md'] += '\nEnterprise artifacts use restricted JSON ASTs and exact bounded rational arithmetic. Hashing, bit complexity and engineering are not included in the declared arithmetic metric.\n';
    add('03_benchmark_tasks/spec.json', records.map(row => ({attempt: row.attempt, charter: row.charter,
        freeze: row.freeze || null, taskBank: row.bank || null})));
    add('04_baselines/comparison.json', records.map(row => ({attempt: row.attempt,
        constructionControls: row.bundle?.controls || null, actualRecipePlans: row.bundle?.plans || null,
        futureComparisons: row.future || null})));
    const comparisons = JSON.parse(files['04_baselines/comparison.json']);
    comparisons.autonomousCapitalModel = {example: syntheticCapitalExample(), controls: capitalControls(),
        accounting: 'Synthetic cash units, distinct from foundry arithmetic work. Analysis overhead is unmeasured, not zero.'};
    files['04_baselines/comparison.json'] = canonical(comparisons) + '\n';
    add('06_proof_bundles/capability.json', records.map(row => ({attempt: row.attempt,
        evidenceLocation: '05_agialpha_runs/run.json → workspace.events: complete artifacts, rejected attempts and certificates',
        artifactDigests: row.freeze?.artifactDigests || row.bundle?.envelopes.map(item => item.digest) || [],
        independentReplay: row.bundleProof ? {verified: row.bundleProof.verified,
            countedWorkPerReplay: row.bundleProof.currentReplayWork} : null,
        successor: row.successor || null})));
    add('07_replay_logs/replay.json', records.map(row => ({attempt: row.attempt, eventDigests: row.events,
        currentBundleReplayWork: row.bundleProof?.currentReplayWork || null,
        currentFutureReplayWork: row.futureProof?.currentReplayWork || null,
        replayIsAdditionalWork: true})));
    add('08_cost_ledgers/costs.json', records.map(row => ({attempt: row.attempt,
        selectedComparison: row.bundle?.counts || null, completeObservedBuild: row.bundle?.observedWorkLedger || null,
        constructionReservation: row.reservation, unknownConstructionSpent: row.unknownSpent,
        invocationReservation: row.invocation || null, futureObservedWork: row.futureSpent ?? null,
        successor: row.successor ? {observedWork: row.successor.observedSuccessorWork,
            lineageWork: row.successor.lineageWork} : null,
        admissionAllowancePerCompleteReplay: row.charter.admissionLimit,
        currentBundleReplayWork: row.bundleProof?.currentReplayWork || null,
        currentFutureReplayWork: row.futureProof?.currentReplayWork || null,
        totalComplete: false, excluded: row.bundle?.excludedCosts || ['Unstarted or interrupted work is unknown.']})));
    add('09_safety_ledgers/safety.json', overview);
    add('10_validator_reports/review.json', {checker: 'Separately authored restricted interpreter and complete basis certificates',
        organizationalIndependence: false, originalCompanion: 'NOT_OBTAINED', operationalPilot: 'NOT_RUN'});
    add('12_summary_tables/outcome.json', overview);
    return files;
}
