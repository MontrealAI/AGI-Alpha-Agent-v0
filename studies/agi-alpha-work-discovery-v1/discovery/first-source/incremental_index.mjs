// SPDX-License-Identifier: Apache-2.0
import {buildIndex,enumerateResponse,responseRoots,resolvePointer,sha256,stable} from './schema_inventory.mjs';

export async function updateIndex(oldDocument,newDocument,oldIndex,checkpoint=async()=>{}) {
  if(oldIndex.sourceDigest!==sha256(oldDocument)) throw Error('OLD_INDEX_SOURCE_MISMATCH');
  const expected=await buildIndex(oldDocument,checkpoint);
  if(stable(expected)!==stable(oldIndex)) throw Error('OLD_INDEX_EVIDENCE_MISMATCH');
  const oldRoots=new Map(responseRoots(oldDocument).map(root=>[root.responseId,root]));
  const oldResponses=new Map(oldIndex.responses.map(response=>[response.responseId,response]));
  const comparison=new Map(),responses=[];let reused=0,recomputed=0;
  function referenceUnchanged(ref) {
    if(!comparison.has(ref)) {
      let same=false;
      try {same=stable(resolvePointer(oldDocument,ref))===stable(resolvePointer(newDocument,ref));} catch {same=false;}
      comparison.set(ref,same);
    }
    return comparison.get(ref);
  }
  for(const root of responseRoots(newDocument)) {
    await checkpoint('incremental-response');
    const previous=oldResponses.get(root.responseId),previousRoot=oldRoots.get(root.responseId);
    const unchanged=previous && previousRoot && stable(previousRoot)===stable(root)
      && previous.dependencies.every(referenceUnchanged);
    if(unchanged){responses.push(structuredClone(previous));reused++;}
    else {responses.push(await enumerateResponse(newDocument,root,checkpoint));recomputed++;}
  }
  return {index:{schema:'alpha-response-index/v1',sourceDigest:sha256(newDocument),responses,
    counts:{responses:responses.length,nodes:responses.reduce((sum,r)=>sum+r.nodes.length,0),
      warnings:responses.reduce((sum,r)=>sum+r.warnings.length,0)}},
    work:{reusedResponses:reused,recomputedResponses:recomputed,referenceComparisons:comparison.size,
      fullOldIndexRevalidation:true}};
}
