// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const entries=[];
function visit(dir){for(const item of fs.readdirSync(dir,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name))){const full=path.join(dir,item.name);if(item.isDirectory()){if(item.name!=='__pycache__')visit(full);}else if(/\.(mjs|py)$/.test(item.name)&&!['binding.mjs','bind-source.mjs'].includes(item.name))entries.push({path:path.relative(root,full).replaceAll(path.sep,'/'),sha256:crypto.createHash('sha256').update(fs.readFileSync(full)).digest('hex')});}}
visit(root);
const sourceHash=crypto.createHash('sha256').update(JSON.stringify(entries)).digest('hex');
const status=process.argv.includes('--freeze')?'FROZEN_RESEARCH_SOURCE':'DEVELOPMENT_UNFROZEN';
fs.writeFileSync(path.join(root,'SOURCE_MANIFEST.json'),JSON.stringify({status,source_hash:sourceHash,files:entries},null,2)+'\n');
fs.writeFileSync(path.join(root,'binding.mjs'),`// SPDX-License-Identifier: Apache-2.0\n// Source binding; regenerate only before a new explicitly recorded freeze.\nexport const SOURCE_HASH='${sourceHash}';\nexport const SOURCE_STATUS='${status}';\n`);
console.log(JSON.stringify({status,source_hash:sourceHash,files:entries.length}));
