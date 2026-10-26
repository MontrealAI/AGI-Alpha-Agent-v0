import {createHash} from 'node:crypto';
import {studio} from './studio-api.mjs';
import {fail,canonical,keys} from './vendor/manager/site/assets/successor/safe.mjs';
const hash=value=>createHash('sha256').update(value).digest('hex');
const fields=new Set(['schema','id','role','version','status','phase','startedAt','finishedAt','scope','scopeHash','specHash','deliveryHash','files','review','error','requests','evidenceType','independent','isRevision','revisionSource','title','profile','criteria','hasFiles','currentScope','specification','interpretation']);
// A bound receipt is still an editable historical controller record, not an attestation.
export async function validateReceiptBinding(handoff,receipt,role=null){
  keys(handoff,['schema','specification','specHash','delivery','deliveryHash'],'FLEET_HANDOFF_FIELDS');
  fail(handoff.schema==='agi-studio-handoff/v1'&&['computer-work/v1','computer-work/v2'].includes(handoff.specification?.profile)&&typeof handoff.delivery==='string','FLEET_HANDOFF_SCHEMA');
  fail(hash(canonical(handoff.specification))===handoff.specHash&&hash(handoff.delivery)===handoff.deliveryHash,'FLEET_HANDOFF_HASH');
  fail(receipt&&typeof receipt==='object'&&!Array.isArray(receipt)&&Object.keys(receipt).every(k=>fields.has(k)),'FLEET_RECEIPT_FIELDS');
  fail(receipt.schema==='agi-studio-run/v1'&&['agent','node'].includes(receipt.role)&&(!role||receipt.role===role)&&receipt.evidenceType==='local-controller-record'&&receipt.independent===false,'FLEET_RECEIPT_SCHEMA');
  fail(typeof receipt.id==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(receipt.id)&&typeof receipt.version==='string'&&/^\d+\.\d+\.\d+$/.test(receipt.version),'FLEET_RECEIPT_SCHEMA');
  fail(receipt.specHash===handoff.specHash&&receipt.deliveryHash===handoff.deliveryHash&&canonical(receipt.specification)===canonical(handoff.specification),'FLEET_RECEIPT_BINDING');
  fail(receipt.hasFiles===true&&receipt.profile===handoff.specification.profile&&receipt.title===handoff.specification.title&&canonical(receipt.criteria)===canonical(handoff.specification.criteria),'FLEET_RECEIPT_BINDING');
  if(receipt.role==='node'){
    fail(['checked','needs-review'].includes(receipt.status)&&receipt.phase===receipt.status&&receipt.error===null&&typeof receipt.finishedAt==='string'&&Number.isFinite(Date.parse(receipt.finishedAt)),'FLEET_RECEIPT_REVIEW_INCOMPLETE');
    keys(receipt.review,['verdict','checks','safeToReview'],'FLEET_RECEIPT_REVIEW');
    const {computerVerdict}=await studio('node');let verdict;
    try{verdict=computerVerdict(handoff.specification,{safeToReview:receipt.review.safeToReview,checks:receipt.review.checks});}
    catch{fail(false,'FLEET_RECEIPT_REVIEW');}
    fail(receipt.review.verdict===verdict.verdict&&receipt.status===(verdict.verdict==='consistent'?'checked':'needs-review'),'FLEET_RECEIPT_REVIEW');
  }
  return receipt;
}
