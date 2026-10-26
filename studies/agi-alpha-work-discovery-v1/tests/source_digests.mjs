// SPDX-License-Identifier: Apache-2.0
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const documents = JSON.parse(readFileSync(0, 'utf8'));
if (!Array.isArray(documents) || documents.length !== 2) throw Error('TWO_DOCUMENTS_REQUIRED');
const digest = document => {
  const encoded = JSON.stringify(document, (_key, value) => value && typeof value === 'object' && !Array.isArray(value)
    ? Object.fromEntries(Object.keys(value).sort().map(key => [key, value[key]])) : value);
  return createHash('sha256').update(encoded, 'utf8').digest('hex');
};
process.stdout.write(JSON.stringify(documents.map(digest)) + '\n');
