// SPDX-License-Identifier: Apache-2.0
import {createHash} from 'node:crypto';

export const FACT_KEYS = Object.freeze(['type','format','enum','required','minimum','maximum',
  'exclusiveMinimum','exclusiveMaximum','multipleOf','minLength','maxLength','pattern','minItems','maxItems',
  'uniqueItems','minProperties','maxProperties','nullable']);
const METHODS = new Set(['get','put','post','delete','options','head','patch','trace']);
export const stable = value => JSON.stringify(value, (_key, item) => item && typeof item === 'object' && !Array.isArray(item)
  ? Object.fromEntries(Object.keys(item).sort().map(key => [key,item[key]])) : item);
export const sha256 = value => createHash('sha256').update(typeof value === 'string' ? value : stable(value)).digest('hex');
const escapePointer = key => String(key).replaceAll('~','~0').replaceAll('/','~1');
const unescapePointer = key => key.replaceAll('~1','/').replaceAll('~0','~');
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);

export function resolvePointer(document, reference) {
  if (typeof reference !== 'string' || !reference.startsWith('#/')) throw Error('UNSUPPORTED_REFERENCE');
  let value = document;
  for (const token of reference.slice(2).split('/').map(unescapePointer)) {
    if (!object(value) && !Array.isArray(value)) throw Error('UNRESOLVED_REFERENCE');
    if (!Object.hasOwn(value,token)) throw Error('UNRESOLVED_REFERENCE');
    value = value[token];
  }
  return value;
}

export function factsFor(schema) {
  const facts = {};
  for (const key of FACT_KEYS) if (Object.hasOwn(schema,key)) {
    const value=schema[key];
    facts[key]=Array.isArray(value) && ['enum','required'].includes(key)
      ? [...value].sort((a,b)=>stable(a)<stable(b)?-1:stable(a)>stable(b)?1:0) : value;
  }
  if (typeof schema.additionalProperties === 'boolean') facts.additionalProperties = schema.additionalProperties;
  return facts;
}

export function responseRoots(document) {
  if (!object(document) || !object(document.paths)) throw Error('API_PATHS_REQUIRED');
  if (document.swagger !== '2.0' && !/^3\.[01]\./.test(document.openapi || '')) throw Error('UNSUPPORTED_API_VERSION');
  const roots=[];
  for (const path of Object.keys(document.paths).sort()) {
    const item=document.paths[path];
    if (!object(item)) throw Error('INVALID_PATH_ITEM');
    if (item.$ref) {
      roots.push({responseId:`GET ${path} *`,path,status:'*',schema:null,pointer:`#/paths/${escapePointer(path)}`,
        warnings:['PATH_ITEM_REFERENCE_UNASSESSED']});
      continue;
    }
    const operation=item.get;
    if (!operation) continue;
    if (!object(operation) || !object(operation.responses)) throw Error('RESPONSE_OBJECT_REQUIRED');
    for (const status of Object.keys(operation.responses).sort()) {
      if (!/^2(?:[0-9]{2}|XX)$/.test(status)) continue;
      let response=operation.responses[status];
      let pointer=`#/paths/${escapePointer(path)}/get/responses/${escapePointer(status)}`;
      const warnings=[];
      const seen=new Set();
      while (object(response) && typeof response.$ref === 'string') {
        if(seen.has(response.$ref)){warnings.push('RESPONSE_REFERENCE_CYCLE');response=null;break;}
        seen.add(response.$ref);
        try {pointer=response.$ref;response=resolvePointer(document,response.$ref);}
        catch {warnings.push('RESPONSE_REFERENCE_UNRESOLVED');response=null;break;}
      }
      let schema=null;
      if (document.swagger === '2.0') {
        const media=operation.produces || document.produces || [];
        if(media.length && !media.includes('application/json')) warnings.push('NON_JSON_RESPONSE_UNASSESSED');
        else {schema=response?.schema || null;pointer+='/schema';}
      } else {
        const content=response?.content || {};
        schema=content['application/json']?.schema || null;
        if(Object.keys(content).some(key=>key!=='application/json' && key.endsWith('+json')))
          warnings.push('ADDITIONAL_JSON_MEDIA_UNASSESSED');
        pointer+='/content/application~1json/schema';
      }
      if(!schema) warnings.push('NO_JSON_SCHEMA');
      roots.push({responseId:`GET ${path} ${status}`,path,status,schema,pointer,warnings,
        operationId:operation.operationId || null});
    }
  }
  return roots;
}

export async function enumerateResponse(document,root,checkpoint=async()=>{}) {
  const nodes=[],warnings=root.warnings.map(code=>({responseId:root.responseId,address:[],code,pointer:root.pointer}));
  const refs=new Set(); let visits=0;
  async function walk(schema,address,pointer,refChain,ancestors,depth) {
    if(++visits>50000 || depth>40) throw Error('SCHEMA_WORK_BOUND');
    if(visits%100===0) await checkpoint('schema-inventory');
    if(!object(schema)) {
      warnings.push({responseId:root.responseId,address,code:'NON_OBJECT_SCHEMA_UNASSESSED',pointer});return;
    }
    if(Object.hasOwn(schema,'$ref')) {
      const reference=schema.$ref;
      if(Object.keys(schema).some(key=>key!=='$ref'))
        warnings.push({responseId:root.responseId,address,code:'REF_SIBLINGS_UNASSESSED',pointer});
      if(typeof reference!=='string' || !reference.startsWith('#/')) {
        warnings.push({responseId:root.responseId,address,code:'EXTERNAL_REFERENCE_UNASSESSED',pointer});return;
      }
      refs.add(reference);
      if(ancestors.includes(reference)) {
        warnings.push({responseId:root.responseId,address,code:'REFERENCE_CYCLE_UNASSESSED',pointer:reference});return;
      }
      let target;
      try {target=resolvePointer(document,reference);} catch {
        warnings.push({responseId:root.responseId,address,code:'UNRESOLVED_REFERENCE',pointer:reference});return;
      }
      return walk(target,address,reference,[...refChain,reference],[...ancestors,reference],depth+1);
    }
    nodes.push({responseId:root.responseId,address,facts:factsFor(schema),sourcePointer:pointer,refChain});
    for(const keyword of ['oneOf','anyOf','not','if','then','else','contains','prefixItems','unevaluatedProperties',
      'dependentSchemas','dependentRequired','patternProperties','propertyNames','discriminator','xml'])
      if(Object.hasOwn(schema,keyword)) warnings.push({responseId:root.responseId,address,code:`UNASSESSED_${keyword}`,pointer});
    if(object(schema.properties)) for(const name of Object.keys(schema.properties).sort())
      await walk(schema.properties[name],[...address,`p:${name}`],`${pointer}/properties/${escapePointer(name)}`,refChain,ancestors,depth+1);
    if(Object.hasOwn(schema,'items')) await walk(schema.items,[...address,'i:'],`${pointer}/items`,refChain,ancestors,depth+1);
    if(object(schema.additionalProperties)) await walk(schema.additionalProperties,[...address,'a:'],
      `${pointer}/additionalProperties`,refChain,ancestors,depth+1);
    if(Array.isArray(schema.allOf)) for(let i=0;i<schema.allOf.length;i++)
      await walk(schema.allOf[i],[...address,`allOf:${i}`],`${pointer}/allOf/${i}`,refChain,ancestors,depth+1);
  }
  if(root.schema) await walk(root.schema,[],root.pointer,[],[],0);
  nodes.sort((a,b)=>stable(a.address)<stable(b.address)?-1:stable(a.address)>stable(b.address)?1:0);
  return {responseId:root.responseId,path:root.path,status:root.status,operationId:root.operationId || null,
    nodes,warnings,dependencies:[...refs].sort(),visits};
}

export async function buildIndex(document,checkpoint=async()=>{}) {
  const responses=[];
  for(const root of responseRoots(document)) {await checkpoint('response-index');responses.push(await enumerateResponse(document,root,checkpoint));}
  return {schema:'alpha-response-index/v1',sourceDigest:sha256(document),responses,
    counts:{responses:responses.length,nodes:responses.reduce((sum,r)=>sum+r.nodes.length,0),
      warnings:responses.reduce((sum,r)=>sum+r.warnings.length,0)}};
}

export function compareIndexes(oldIndex,newIndex) {
  const flatten=index=>new Map(index.responses.flatMap(response=>response.nodes.map(node=>[stable([node.responseId,node.address]),node])));
  const previous=flatten(oldIndex),next=flatten(newIndex),changes=[];
  for(const key of [...new Set([...previous.keys(),...next.keys()])].sort()) {
    const oldNode=previous.get(key),newNode=next.get(key);
    if(oldNode && newNode && stable(oldNode.facts)===stable(newNode.facts)) continue;
    changes.push({key,responseId:(oldNode||newNode).responseId,address:(oldNode||newNode).address,
      kind:oldNode?(newNode?'CHANGED':'REMOVED'):'ADDED',oldFacts:oldNode?.facts ?? null,newFacts:newNode?.facts ?? null,
      oldPointer:oldNode?.sourcePointer ?? null,newPointer:newNode?.sourcePointer ?? null,
      oldRefChain:oldNode?.refChain ?? [],newRefChain:newNode?.refChain ?? []});
  }
  const oldIds=new Set(oldIndex.responses.map(r=>r.responseId)),newIds=new Set(newIndex.responses.map(r=>r.responseId));
  return {schema:'alpha-response-dossier/v1',oldSourceDigest:oldIndex.sourceDigest,newSourceDigest:newIndex.sourceDigest,
    addedResponses:[...newIds].filter(id=>!oldIds.has(id)).sort(),removedResponses:[...oldIds].filter(id=>!newIds.has(id)).sort(),
    changes,unassessed:[...oldIndex.responses.flatMap(r=>r.warnings.map(w=>({...w,side:'old'}))),
      ...newIndex.responses.flatMap(r=>r.warnings.map(w=>({...w,side:'new'})))],
    counts:{old:oldIndex.counts,new:newIndex.counts,changes:changes.length},
    limits:['Structural GET 2xx JSON schema surface assessment, not blanket compatibility certification.',
      'Optional property removal is a review signal, not necessarily a contract violation.',
      'Conjunction branch order may produce structural differences without semantic difference.',
      'Server behavior, authentication, requests, default/error responses and client runtime are outside scope.']};
}

export function apiInventory(document) {
  let operations=0;
  for(const item of Object.values(document.paths || {}))
    if(object(item)) operations+=Object.keys(item).filter(key=>METHODS.has(key)).length;
  return {paths:Object.keys(document.paths || {}).length,operations};
}
