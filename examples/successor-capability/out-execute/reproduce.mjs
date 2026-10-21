// SPDX-License-Identifier: Apache-2.0
/** Fresh authored study, not reproduction of an unavailable manuscript companion. */
import {mkdir, writeFile, readFile} from 'node:fs/promises';
import {resolve, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {performance} from 'node:perf_hooks';
import {execute, retainCompletion, inspectArchive} from './engine.mjs';
import {weightedStream, containment} from './fixtures.mjs';
import {fromScratch, fixedCertificateRunner} from './baselines.mjs';
import {installedSource} from './source-manifest.mjs';
import {same} from './model.mjs';

export async function reproduce(destination, fixtureCount = 64) {
    if (!Number.isInteger(fixtureCount) || fixtureCount < 1 || fixtureCount > 64) throw Error('Fixture count must be 1..64.');
    await mkdir(destination, {recursive: false});
    const source = await installedSource(), started = performance.now();
    const summary = {schema: 'out-execute-authored-study/v1', protocol: 'xorshift32-explicit-scopes/v1',
        manuscriptCompanionReproduced: false, manuscriptClaimCounts: {snapshots: 576, semanticStops: 158},
        source, node: process.version, fixtures: fixtureCount, snapshots: 0, matches: 0, semanticStops: 0,
        updatedWitnesses: 0, constructed: 0, retained: 0, coordinatedBoundaryScans: 0,
        acceptanceBoundaryAssignments: 0, executionWork: 0, fullEnumerationWork: 0,
        fixedCertificateWork: 0, fixedCertificateRetentions: 0, matchedIncrementalWork: 0,
        localArchiveReopenAudit: {assignments: 0, factorLookups: 0, inputEntries: 0, boundaryCandidates: 0, scopeVisits: 0, profileComparisons: 0},
        limitations: ['Authored finite models, not natural tasks.', 'Manuscript companion files were not present in the source repository.',
            'Counted logical work is not CPU time, currency, industrial saving or total host instructions.',
            'Matched incremental baseline deliberately uses the same public qualified-contract algorithm; ties are expected.',
            'Full/reuse verification, comparison execution, archive reopen and output bytes are reported separately.'], fixturesFiles: []};
    for (let i = 0; i < fixtureCount; i++) {
        const seed = 310000 + i, snapshots = weightedStream(seed); let archive = null, baselineArchive = null;
        const fixed = fixedCertificateRunner(), records = [];
        for (const [revision, model] of snapshots.entries()) {
            const state = await execute(model, {source: source.source, archive, attemptId: `fixture-${seed}-revision-${revision}`});
            const matched = await execute(model, {source: source.source, archive: baselineArchive, attemptId: `incremental-${seed}-${revision}`});
            if (state.status !== 'COMPLETE' || matched.status !== 'COMPLETE') throw Error(`Inconclusive fixture ${seed}/${revision}`);
            const full = fromScratch(model), guarded = fixed(model), completion = state.completion;
            if (full.status === 'INCONCLUSIVE' || completion.selection.status !== full.status || completion.selection.cost !== full.cost
                || guarded.cost !== full.cost || matched.completion.selection.cost !== full.cost
                || matched.completion.countedWork !== completion.countedWork) throw Error(`Mismatch ${seed}/${revision}`);
            summary.snapshots++; summary.matches++; summary.semanticStops += Number(revision > 0 && completion.change.semanticStop);
            summary.updatedWitnesses += Number(revision > 0 && !same(archive.completions.at(-1).artifact, completion.artifact));
            summary.constructed += completion.change.rebuilt.length; summary.retained += completion.change.retained.length;
            summary.coordinatedBoundaryScans += Number(completion.work.boundaryAssignments > 0);
            summary.acceptanceBoundaryAssignments += completion.work.acceptanceBoundaryAssignments;
            summary.executionWork += completion.countedWork; summary.fullEnumerationWork += full.countedWork;
            summary.fixedCertificateWork += guarded.countedWork; summary.fixedCertificateRetentions += Number(guarded.retained);
            summary.matchedIncrementalWork += matched.completion.countedWork;
            records.push({revision, input: model, completionDigest: completion.digest, full, fixedCertificate: guarded,
                matchedIncremental: {completionDigest: matched.completion.digest, countedWork: matched.completion.countedWork}});
            archive = await retainCompletion(state); baselineArchive = await retainCompletion(matched);
        }
        const filename = `fixture-${seed}.json`; const raw = JSON.stringify({seed, records, archive, baselineArchive}, null, 2) + '\n';
        await writeFile(join(destination, filename), raw, {flag: 'wx'});
        const reopened = JSON.parse(await readFile(join(destination, filename), 'utf8'));
        const audit = await inspectArchive(reopened.archive);
        for (const key of Object.keys(summary.localArchiveReopenAudit)) summary.localArchiveReopenAudit[key] += audit.audit[key];
        summary.fixturesFiles.push({file: filename, bytes: Buffer.byteLength(raw)});
        process.stdout.write(`Checked fixture ${i + 1}/${fixtureCount}: ${summary.matches} exact snapshots\n`);
    }
    // A credible cheaper fixed-proof case remains visible, even when the wider interface is unnecessary.
    const guarded = fixedCertificateRunner(), model = containment();
    const baselineFirst = guarded(model), baselineSecond = guarded(model);
    const first = await execute(model, {source: source.source});
    const second = await execute(model, {source: source.source, archive: await retainCompletion(first)});
    summary.identicalInputControl = {fixedFirst: baselineFirst.countedWork, fixedSecond: baselineSecond.countedWork,
        boundaryFirst: first.completion.countedWork, boundarySecond: second.completion.countedWork,
        fixedRetained: baselineSecond.retained, outcome: 'A sufficient cheaper fixed proof is a legitimate alternative.'};
    summary.elapsedMilliseconds = Math.round(performance.now() - started);
    summary.totalSerializedBytes = summary.fixturesFiles.reduce((n, f) => n + f.bytes, 0);
    await writeFile(join(destination, 'summary.json'), JSON.stringify(summary, null, 2) + '\n', {flag: 'wx'});
    return summary;
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
    if (!process.argv[2]) throw Error('Usage: node reproduce.mjs NEW_OUTPUT_DIRECTORY [1..64]');
    const result = await reproduce(resolve(process.argv[2]), Number(process.argv[3] || 64));
    console.log(JSON.stringify({snapshots: result.snapshots, matches: result.matches, semanticStops: result.semanticStops,
        executionWork: result.executionWork, matchedIncrementalWork: result.matchedIncrementalWork,
        fullEnumerationWork: result.fullEnumerationWork, identicalInputControl: result.identicalInputControl}));
}
