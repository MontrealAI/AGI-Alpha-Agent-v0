// SPDX-License-Identifier: Apache-2.0
import * as manager from './vendor/manager/site/assets/successor/alpha-project.mjs';
import * as jobs from './vendor/jobs/integrations/alpha-agent/project-transfer.mjs';
import * as fleet from './vendor/fleet/local-runtime/project/transfer.mjs';
import {CONTEXT} from './vendor/manager-context.mjs';
export const managerContext=Object.freeze({...CONTEXT,validateNative:manager.validateBrowserAlpha});
export const managerInspector=Object.freeze({source:CONTEXT.managerSource,inspect:raw=>manager.inspectAlphaProject(raw,managerContext)});
export const jobsOptions=Object.freeze({managerInspector});
export const receivers=Object.freeze({manager:managerInspector.inspect,jobs:raw=>jobs.inspectProjectTransfer(raw,jobsOptions),fleet:raw=>fleet.inspectProjectReturn(raw)});
export async function managerImport(raw,language){return manager.importAlphaProject(raw,{language,mappingAcknowledgement:manager.MAPPING},managerContext);}
export async function managerAdvance(raw,action,budget){return manager.advanceAlphaProject(raw,{action,budget},managerContext);}
export async function jobsImport(raw,amountBaseUnits,compiledAt){return jobs.importAlphaProject(raw,{...jobsOptions,amountBaseUnits,compiledAt});}
export async function jobsRun(raw){return jobs.runProjectTransfer(raw,jobsOptions);}
export async function fleetRequest(raw,options){return fleet.createProjectRequest(raw,options);}
