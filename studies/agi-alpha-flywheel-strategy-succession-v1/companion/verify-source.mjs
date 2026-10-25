// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {fileURLToPath} from 'node:url';
import {SOURCE_HASH,SOURCE_STATUS} from './binding.mjs';
export function verifySource({requireFrozen=false}={}){
 const root=path.dirname(fileURLToPath(import.meta.url)),manifest=JSON.parse(fs.readFileSync(path.join(root,'SOURCE_MANIFEST.json'),'utf8'));
 if(requireFrozen&&(SOURCE_STATUS!=='FROZEN_RESEARCH_SOURCE'||manifest.status!==SOURCE_STATUS))throw Error('SOURCE_NOT_FROZEN');
 if(manifest.source_hash!==SOURCE_HASH)throw Error('SOURCE_BINDING_MISMATCH');
 for(const file of manifest.files){const absolute=path.resolve(root,file.path);if(!absolute.startsWith(root+path.sep))throw Error('MANIFEST_PATH');const hash=crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex');if(hash!==file.sha256)throw Error(`SOURCE_CHANGED: ${file.path}`);}
 const digest=crypto.createHash('sha256').update(JSON.stringify(manifest.files)).digest('hex');if(digest!==SOURCE_HASH)throw Error('MANIFEST_ROOT_MISMATCH');
 return manifest;
}
