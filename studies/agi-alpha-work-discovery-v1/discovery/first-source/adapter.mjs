// SPDX-License-Identifier: Apache-2.0
import {buildIndex,compareIndexes,sha256} from './schema_inventory.mjs';
import {updateIndex} from './incremental_index.mjs';

export function createAdapter(mode='full') {
  if(!['full','incremental'].includes(mode)) throw Error('UNSUPPORTED_MODE');
  return {manifest:{id:'api-response-assurance',version:1,en:'API response change assurance',
    fr:'Vérification des changements de réponses API',scope:'Complete structural GET 2xx JSON response inventory with unresolved scope disclosed.',
    artifact:'response-dossier.json'},
    validate(input) {
      if(!input || Object.keys(input).sort().join('|')!=='newSpec|oldSpec|source') throw Error('INPUT_FIELDS');
      for(const key of ['oldSpec','newSpec']) {
        if(typeof input[key]!=='string'||input[key].length>750000) throw Error('SPEC_BOUND');
        const parsed=JSON.parse(input[key]);
        if(!parsed || typeof parsed!=='object'||!parsed.paths) throw Error('SPEC_REQUIRED');
      }
      if(typeof input.source!=='string'||!input.source||input.source.length>1000) throw Error('SOURCE_REQUIRED');
    },
    async execute(input,checkpoint) {
      const oldDocument=JSON.parse(input.oldSpec),newDocument=JSON.parse(input.newSpec);
      const before=await buildIndex(oldDocument,checkpoint);
      let after,work;
      if(mode==='incremental') {const updated=await updateIndex(oldDocument,newDocument,before,checkpoint);after=updated.index;work=updated.work;}
      else {after=await buildIndex(newDocument,checkpoint);work={reusedResponses:0,recomputedResponses:after.responses.length};}
      const dossier=compareIndexes(before,after);
      const text=JSON.stringify(dossier,null,2)+'\n';
      if(text.length>195000) throw Error('DOSSIER_ARTIFACT_BOUND');
      const report=['# API response assurance / Vérification des réponses API','',
        `Source: ${input.source}`,`Structural changes / Changements structurels: ${dossier.changes.length}`,
        `Responses assessed / Réponses évaluées: ${before.responses.length} -> ${after.responses.length}`,
        `Unassessed scope records / Éléments hors portée: ${dossier.unassessed.length}`,'',
        'Decision: review the exact changed fields before upgrading consumers. No whole-API compatibility approval is issued.',
        'Décision : examiner les champs modifiés avant la mise à niveau des clients. Aucune approbation globale de compatibilité.',
        '',...dossier.changes.slice(0,100).map(c=>`- ${c.kind}: ${c.responseId} ${c.address.join('/') || '(root)'}`),
        '',...dossier.limits.map(l=>`- ${l}`)].join('\n');
      return {decision:dossier.changes.length?'RESPONSE_CHANGES_REQUIRE_REVIEW':'NO_SCOPED_STRUCTURAL_CHANGE',
        summary:{oldResponses:before.responses.length,newResponses:after.responses.length,changedSurfaces:dossier.changes.length,
          unassessed:dossier.unassessed.length,mode},
        evidence:{dossierDigest:sha256(dossier),oldIndexDigest:sha256(before),newIndexDigest:sha256(after),work,
          source:input.source,independentAcceptanceRequired:true,fullCompatibilityClaim:false},
        artifacts:[{name:'response-dossier.json',type:'application/json',content:text},
          {name:'upgrade-review.md',type:'text/markdown',content:report+'\n'}],
        limits:dossier.limits};
    }};
}
