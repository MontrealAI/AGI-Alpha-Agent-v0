// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {buildIndex,compareIndexes,resolvePointer,sha256,stable} from '../src/schema_inventory.mjs';
import {updateIndex} from '../src/incremental_index.mjs';
import {createAdapter} from '../src/adapter.mjs';

const copy = value => structuredClone(value);
function document() {
  return {swagger: '2.0', info: {title: 'Independent unit-control API', version: '1'}, produces: ['application/json'],
    paths: {
      '/cats': {get: {operationId: 'cats', responses: {'200': {schema: {$ref: '#/definitions/Cat'}}}}},
      '/dogs': {get: {operationId: 'dogs', responses: {'200': {schema: {$ref: '#/definitions/Dog'}}}}},
      '/array': {get: {responses: {'206': {schema: {type: 'array', items: {$ref: '#/definitions/Cat'}}}}}},
      '/inline': {get: {responses: {'200': {schema: {type: 'object', properties: {value: {type: 'number'}}}}}}},
    }, definitions: {
      Cat: {type: 'object', required: ['id'], properties: {id: {type: 'integer'}, child: {$ref: '#/definitions/Child'}}},
      Child: {type: 'object', properties: {name: {type: 'string', maxLength: 10}}},
      Dog: {type: 'object', properties: {breed: {type: 'string'}}},
      Unused: {type: 'object', properties: {unused: {type: 'string'}}},
    }};
}
async function equivalence(before, after) {
  const oldIndex = await buildIndex(before);
  const incremental = await updateIndex(before, after, oldIndex);
  assert.equal(stable(incremental.index), stable(await buildIndex(after)));
  assert.equal(stable(compareIndexes(oldIndex, incremental.index)), stable(compareIndexes(oldIndex, await buildIndex(after))));
  return incremental;
}

test('deep shared reference mutation invalidates every affected response, not unrelated work', async () => {
  const before = document(), after = copy(before); after.definitions.Child.properties.name.maxLength = 4;
  const result = await equivalence(before, after);
  assert.equal(result.work.recomputedResponses, 2);
  assert.equal(result.work.reusedResponses, 2);
  const dossier = compareIndexes(await buildIndex(before), result.index);
  assert.deepEqual(dossier.changes.map(row => row.responseId).sort(), ['GET /array 206', 'GET /cats 200']);
});

test('unreferenced definition changes consume no response reconstruction', async () => {
  const before = document(), after = copy(before); after.definitions.Unused.properties.unused.type = 'boolean';
  const result = await equivalence(before, after);
  assert.equal(result.work.recomputedResponses, 0);
  assert.equal(result.work.reusedResponses, 4);
});

test('replacing a reference, removing its target and later resolving it preserve fresh-build equality', async () => {
  const before = document(), redirect = copy(before);
  redirect.paths['/cats'].get.responses['200'].schema.$ref = '#/definitions/Dog';
  await equivalence(before, redirect);
  const missing = copy(before); delete missing.definitions.Child;
  const lost = await equivalence(before, missing);
  assert.ok(lost.index.responses.find(row => row.path === '/cats').warnings.some(row => row.code === 'UNRESOLVED_REFERENCE'));
  await equivalence(missing, before);
});

test('recursive references remain explicitly unassessed and invalidate correctly when broken', async () => {
  const before = document(); before.definitions.Child.properties.parent = {$ref: '#/definitions/Cat'};
  const index = await buildIndex(before);
  assert.ok(index.responses.find(row => row.path === '/cats').warnings.some(row => row.code === 'REFERENCE_CYCLE_UNASSESSED'));
  const after = copy(before); delete after.definitions.Child.properties.parent;
  await equivalence(before, after);
});

test('allOf branches, array items and schema-valued maps each retain their own field addresses', async () => {
  const doc = document();
  doc.paths['/inline'].get.responses['200'].schema = {type: 'object', properties: {
    rows: {type: 'array', items: {allOf: [{$ref: '#/definitions/Dog'}, {type: 'object', properties: {active: {type: 'boolean'}}}]}},
    map: {type: 'object', additionalProperties: {$ref: '#/definitions/Child'}},
  }};
  const row = (await buildIndex(doc)).responses.find(value => value.path === '/inline');
  const addresses = row.nodes.map(node => stable(node.address));
  assert.ok(addresses.includes(stable(['p:rows', 'i:', 'allOf:0', 'p:breed'])));
  assert.ok(addresses.includes(stable(['p:rows', 'i:', 'allOf:1', 'p:active'])));
  assert.ok(addresses.includes(stable(['p:map', 'a:', 'p:name'])));
  const after = copy(doc); after.definitions.Dog.properties.breed.enum = ['hound', 'terrier'];
  await equivalence(doc, after);
});

test('escaped reference keys and unusual field names resolve without prototype assumptions', async () => {
  const doc = document(); doc.definitions['a/b~c'] = JSON.parse('{"type":"object","properties":{"__proto__":{"type":"string"},"a/b":{"type":"integer"}}}');
  doc.paths['/cats'].get.responses['200'].schema = {$ref: '#/definitions/a~1b~0c'};
  assert.equal(resolvePointer(doc, '#/definitions/a~1b~0c'), doc.definitions['a/b~c']);
  const row = (await buildIndex(doc)).responses.find(value => value.path === '/cats');
  assert.ok(row.nodes.some(node => stable(node.address) === stable(['p:__proto__'])));
  assert.ok(row.nodes.some(node => node.sourcePointer.endsWith('/properties/a~1b')));
});

test('path/response additions and removals preserve complete identifiers', async () => {
  const before = document(), after = copy(before);
  delete after.paths['/dogs'];
  after.paths['/cats'].get.responses['201'] = {schema: {type: 'string'}};
  const result = await equivalence(before, after);
  const dossier = compareIndexes(await buildIndex(before), result.index);
  assert.deepEqual(dossier.removedResponses, ['GET /dogs 200']);
  assert.deepEqual(dossier.addedResponses, ['GET /cats 201']);
});

test('shared response-object ref and operation metadata changes invalidate appropriately', async () => {
  const before = document();
  before.responses = {shared: {schema: {$ref: '#/definitions/Cat'}}};
  before.paths['/cats'].get.responses['200'] = {$ref: '#/responses/shared'};
  const changed = copy(before); changed.responses.shared.schema = {$ref: '#/definitions/Dog'};
  await equivalence(before, changed);
  const renamed = copy(before); renamed.paths['/cats'].get.operationId = 'new-cats-operation';
  const result = await equivalence(before, renamed);
  assert.equal(result.index.responses.find(row => row.path === '/cats').operationId, 'new-cats-operation');
});

test('GET success scope excludes POST, default and error behavior explicitly', async () => {
  const doc = document();
  doc.paths['/cats'].post = {responses: {'200': {schema: {type: 'string'}}}};
  doc.paths['/cats'].get.responses['404'] = {schema: {type: 'object'}};
  doc.paths['/cats'].get.responses.default = {schema: {type: 'integer'}};
  const index = await buildIndex(doc);
  assert.equal(index.responses.length, 4);
  assert.ok(index.responses.every(row => row.responseId.startsWith('GET ') && !row.responseId.endsWith('404')));
  assert.ok(compareIndexes(index, index).limits.some(text => /default\/error/.test(text)));
});

test('non-JSON text and file responses are visible exclusions, not silently assessed JSON', async () => {
  const doc = document();
  doc.paths['/cats'].get.produces = ['text/plain'];
  doc.paths['/cats'].get.responses['200'].schema = {type: 'string'};
  doc.paths['/file'] = {get: {produces: ['application/octet-stream'], responses: {'200': {schema: {type: 'file'}}}}};
  const index = await buildIndex(doc);
  for (const path of ['/cats', '/file']) {
    const row = index.responses.find(value => value.path === path);
    assert.equal(row.nodes.length, 0);
    assert.ok(row.warnings.some(warning => warning.code === 'NON_JSON_RESPONSE_UNASSESSED'));
  }
});

test('OpenAPI 3 application/json media is inspected while JSON-suffix media is disclosed', async () => {
  const doc = {openapi: '3.1.0', info: {title: 'Unit', version: '1'}, paths: {'/x': {get: {responses: {
    '200': {content: {'application/json': {schema: {type: 'object', properties: {x: {type: 'string'}}}},
      'application/problem+json': {schema: {type: 'string'}}}},
  }}}}};
  const row = (await buildIndex(doc)).responses[0];
  assert.ok(row.nodes.some(node => stable(node.address) === stable(['p:x'])));
  assert.ok(row.warnings.some(warning => warning.code === 'ADDITIONAL_JSON_MEDIA_UNASSESSED'));
});

test('unsupported composition forms and external references never imply assessed completeness', async () => {
  const doc = document(); doc.definitions.Child = {oneOf: [{type: 'string'}, {type: 'number'}]};
  doc.definitions.Dog = {$ref: 'https://example.invalid/schema.json#/Dog'};
  const index = await buildIndex(doc);
  assert.ok(index.responses.find(row => row.path === '/cats').warnings.some(row => row.code === 'UNASSESSED_oneOf'));
  assert.ok(index.responses.find(row => row.path === '/dogs').warnings.some(row => row.code === 'EXTERNAL_REFERENCE_UNASSESSED'));
});

test('nullable behavior in Moby x-nullable is not silently discarded', async () => {
  const before = document(), after = copy(before);
  before.definitions.Child.properties.name['x-nullable'] = true;
  after.definitions.Child.properties.name['x-nullable'] = false;
  const dossier = compareIndexes(await buildIndex(before), await buildIndex(after));
  assert.ok(dossier.changes.length > 0 || dossier.unassessed.some(row => /nullable/i.test(row.code)));
});

test('supported OpenAPI 3.1 header cannot silently lose const or schema interpretation constraints', async () => {
  const doc = {openapi: '3.1.0', info: {title: 'Unit', version: '1'}, paths: {'/x': {get: {responses: {
    '200': {content: {'application/json': {schema: {type: 'string', const: 'x', $id: 'https://example.invalid/schema'}}}},
  }}}}};
  const row = (await buildIndex(doc)).responses[0];
  for (const keyword of ['const', '$id']) {
    assert.ok(Object.hasOwn(row.nodes[0].facts, keyword) || row.warnings.some(warning => warning.code.includes(keyword)),
      `Keyword ${keyword} must be compared or explicitly unassessed`);
  }
});

test('cached index tampering cannot acquire trust through a matching source hash', async () => {
  const before = document(), after = copy(before), index = await buildIndex(before);
  index.responses[0].nodes[0].facts = {type: 'invented'};
  await assert.rejects(updateIndex(before, after, index), /INDEX|TRUST|EVIDENCE|SOURCE/);
  const fabricated = {schema: 'alpha-response-index/v1', sourceDigest: sha256(before), responses: [],
    counts: {responses: 0, nodes: 0, warnings: 0}};
  await assert.rejects(updateIndex(before, after, fabricated), /INDEX|TRUST|EVIDENCE|SOURCE/);
});

test('old input drift is rejected and completed incremental indexes support another fresh transition', async () => {
  const before = document(), first = copy(before), second = copy(before), index = await buildIndex(before);
  first.definitions.Child.properties.name.minLength = 1;
  second.definitions.Child.properties.name.minLength = 2;
  const result = await updateIndex(before, first, index);
  const next = await updateIndex(first, second, result.index);
  assert.equal(stable(next.index), stable(await buildIndex(second)));
  const drift = copy(before); drift.definitions.Child.properties.name.maxLength = 999;
  await assert.rejects(updateIndex(drift, second, index), /SOURCE|INDEX/);
});

test('asynchronous checkpoint mutation cannot mint a mixed-source trusted index', async () => {
  const doc = document();
  for (let i = 0; i < 130; i++) doc.definitions.Cat.properties[`z${i}`] = {type: 'integer'};
  let changed = false, result, rejected = false;
  try {
    result = await buildIndex(doc, async phase => {
      if (phase === 'schema-inventory' && !changed) {
        changed = true; doc.definitions.Cat.properties.id.type = 'string';
      }
    });
  } catch (error) {rejected = true; assert.match(String(error), /SOURCE|INPUT|DRIFT|FRAME|MUTAT/);}
  assert.equal(changed, true);
  if (!rejected) {
    const observedTypes = result.responses.filter(row => ['/cats', '/array'].includes(row.path)).flatMap(row =>
      row.nodes.filter(node => node.address.at(-1) === 'p:id').map(node => node.facts.type));
    assert.equal(new Set(observedTypes).size, 1, 'Shared source changed mid-run; both responses must bind one owned frame');
    const frozenDoc = document();
    for (let i = 0; i < 130; i++) frozenDoc.definitions.Cat.properties[`z${i}`] = {type: 'integer'};
    assert.ok(result.sourceDigest === sha256(frozenDoc) || result.sourceDigest === sha256(doc));
    assert.equal(stable(result), stable(await buildIndex(result.sourceDigest === sha256(doc) ? doc : frozenDoc)));
  }
});

test('bounded independent mutation panel agrees with full rebuild across structural edits', async () => {
  const changes = [
    doc => {doc.definitions.Cat.required = ['id', 'child'];},
    doc => {delete doc.definitions.Cat.properties.id;},
    doc => {doc.definitions.Dog.additionalProperties = false;},
    doc => {doc.paths['/inline'].get.responses['200'].schema.properties.value.minimum = -1;},
    doc => {doc.paths['/inline'].get.responses['200'].schema.properties.value.enum = [1, 2, 3];},
    doc => {doc.definitions.Child.properties.name.pattern = '^[A-Z]';},
    doc => {doc.definitions.Cat.properties.list = {type: 'array', items: {$ref: '#/definitions/Dog'}};},
    doc => {doc.definitions.Child.properties.extra = {type: 'object', additionalProperties: {type: 'integer'}};},
    doc => {doc.paths['/inline'].get.responses['200'].schema.properties.value = {type: ['number', 'null']};},
    doc => {doc.produces = ['text/plain'];},
    doc => {doc.paths['/cats'].get.responses['2XX'] = {schema: {$ref: '#/definitions/Child'}};},
    doc => {doc.definitions.Cat.properties.child = {type: 'string'};},
  ];
  for (const change of changes) {const before = document(), after = copy(before); change(after); await equivalence(before, after);}
});

test('full and incremental deliver the same customer dossier and retain review limitations', async () => {
  const before = document(), after = copy(before); after.definitions.Child.properties.name.maxLength = 3;
  const input = {oldSpec: JSON.stringify(before), newSpec: JSON.stringify(after), source: 'Independent synthetic unit control'};
  const full = await createAdapter('full').execute(input, async () => {});
  const increment = await createAdapter('incremental').execute(input, async () => {});
  assert.equal(full.artifacts.find(file => file.name === 'response-dossier.json').content,
    increment.artifacts.find(file => file.name === 'response-dossier.json').content);
  assert.equal(full.evidence.fullCompatibilityClaim, false);
  assert.equal(increment.evidence.fullCompatibilityClaim, false);
});

test('large dossier fragments survive independent UTF-8 file writes at Unicode boundaries', async () => {
  async function produce(padding) {
    const before = {swagger: '2.0', produces: ['application/json'], paths: {'/x': {get: {responses: {
      '200': {schema: {type: 'string', enum: ['a'.repeat(padding) + '🙂']}},
    }}}}};
    const after = copy(before); after.paths['/x'].get.responses['200'].schema.enum = ['b'];
    return createAdapter('full').execute({oldSpec: JSON.stringify(before), newSpec: JSON.stringify(after),
      source: 'Synthetic Unicode packaging control'}, async () => {});
  }
  const small = await produce(0), text = small.artifacts.find(artifact => artifact.name === 'response-dossier.json').content;
  const emojiOffset = text.indexOf('🙂');
  assert.ok(emojiOffset > 0 && emojiOffset < 175000);
  const large = await produce(175000 - 1 - emojiOffset);
  const index = JSON.parse(large.artifacts.find(artifact => artifact.name === 'response-dossier-index.json').content);
  const parts = index.parts.map(name => large.artifacts.find(artifact => artifact.name === name).content);
  const onDisk = parts.map(part => Buffer.from(part, 'utf8').toString('utf8'));
  assert.ok(onDisk.every((text, i) => text === parts[i]), 'Each independently written fragment must preserve valid Unicode scalars');
  assert.equal(sha256(onDisk.join('')), index.digest);
  assert.doesNotThrow(() => JSON.parse(onDisk.join('')));
});
