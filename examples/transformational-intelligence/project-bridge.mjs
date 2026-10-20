// SPDX-License-Identifier: Apache-2.0
/** UI routing delegates validation to installed native, Fleet and Computer Use modules. */
import {createTIProject,appendTIProject,inspectTIProject,createSummaryHandoff} from './vendor/fleet/local-runtime/transformation/project.mjs';
import {assertPublicContent,inspectTransformationEnvelope} from './inspector.mjs';
import {createProject} from '../successor-alpha/project.mjs';
import {createComputerHandoff,inspectComputerHandoff,inspectComputerReturn} from '../successor-alpha/computer.mjs';

export const receivers = {
    public:assertPublicContent,
    native:inspectTransformationEnvelope,
    handoff:inspectComputerHandoff,
    computer:raw=>{const value=JSON.parse(raw);return inspectComputerReturn(value.handoffRaw,value.returnRaw);},
};
export async function createProjectHistory(requestRaw) {
    return createTIProject(requestRaw,receivers);
}
export async function inspectProjectHistory(raw) {
    return inspectTIProject(raw,receivers);
}
export async function appendProjectHistory(raw,kind,eventRaw) {
    return appendTIProject(raw,kind,eventRaw,receivers);
}
export async function prepareSummaryHandoff(projectRaw) {
    const checked=await inspectProjectHistory(projectRaw);
    if(checked.handoffRaw)return {projectRaw,handoffRaw:checked.handoffRaw};
    if(!checked.nativeRaw)throw Error('Import a matching completed native result before preparing its summary.');
    const handoffRaw=await createSummaryHandoff(checked.nativeRaw,{
        inspectNative:inspectTransformationEnvelope,createProject,createComputerHandoff,
    });
    return {projectRaw:await appendProjectHistory(projectRaw,'computer-handoff',handoffRaw),handoffRaw};
}
