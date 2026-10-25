// SPDX-License-Identifier: Apache-2.0
/** Validate complete inert learning archives without rewriting original history wire bytes. */
import * as transport from '../../docs/assets/successor/engine.mjs';
import * as project from './project.mjs';
import * as research from './research.mjs';
import * as continuity from './continuity.mjs';
import * as computer from './computer.mjs';

function projectContains(current, historical) {
    return current.id === historical.id && current.createdAt === historical.createdAt && current.goal === historical.goal
        && current.revision >= historical.revision && current.cycles.length >= historical.cycles.length
        && current.opportunities.length >= historical.opportunities.length
        && transport.canonical(current.cycles.slice(0,historical.cycles.length)) === transport.canonical(historical.cycles)
        && transport.canonical(current.opportunities.slice(0,historical.opportunities.length)) === transport.canonical(historical.opportunities)
        && (current.revision !== historical.revision || project.serializeProject(current) === project.serializeProject(historical));
}
export async function inspectLearningArchive(raw) {
    const archive = transport.parseBounded(raw);
    const keys = ['schema','project','records','nativeHandoffRaw','nativeContinuityRaw'];
    const computerArchive = archive?.schema === 'successor-alpha-learning-archive/v2';
    if (computerArchive) keys.push('computerHistoryRaw');
    if (!archive || Object.keys(archive).sort().join('|') !== keys.sort().join('|') || !['successor-alpha-learning-archive/v1','successor-alpha-learning-archive/v2'].includes(archive.schema)
        || !Array.isArray(archive.records) || archive.records.length > 6) throw Error('LEARNING_ARCHIVE_FIELDS');
    const checkedProject = project.inspectProject(archive.project), seen = new Set();
    for (const entry of archive.records) {
        if (!entry || Object.keys(entry).sort().join('|') !== 'cycleId|resolution|strategy' || seen.has(entry.cycleId)) throw Error('LEARNING_CYCLE_FIELDS');
        const cycle = checkedProject.cycles.find(cycle=>cycle.id===entry.cycleId); if (!cycle) throw Error('LEARNING_CYCLE_BINDING');
        seen.add(entry.cycleId);
        if (entry.strategy !== null) await research.validateResearch(entry.strategy,cycle.mission,{sourceHash:cycle.sourceHash});
        if (entry.resolution !== null) research.validateResolution(entry.resolution,cycle.mission,cycle.result);
    }
    if (archive.nativeHandoffRaw !== null) {
        const checked = await continuity.inspectNativeHandoff(archive.nativeHandoffRaw);
        if (!projectContains(checkedProject,checked.project)) throw Error('LEARNING_NATIVE_PROJECT_BINDING');
    }
    if (archive.nativeContinuityRaw !== null) {
        const checked = await continuity.inspectContinuity(archive.nativeContinuityRaw);
        if (!projectContains(checkedProject,checked.project)) throw Error('LEARNING_NATIVE_HISTORY_BINDING');
    }
    let checkedComputer = null;
    if (computerArchive) {
        checkedComputer = await computer.inspectComputerHistory(archive.computerHistoryRaw);
        if (!computer.projectContains(checkedProject,checkedComputer.project)) throw Error('COMPUTER_ARCHIVE_PROJECT_BINDING');
    }
    return {...archive,project:checkedProject,checkedComputer};
}
