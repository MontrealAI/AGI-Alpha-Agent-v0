// SPDX-License-Identifier: Apache-2.0
/** Node-only provenance for installed repository source, not a supplied assertion. */
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {relative, dirname, resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {CHECKER_VERSION} from './model.mjs';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const hash = text => createHash('sha256').update(text).digest('hex');
export async function installedSource() {
    async function closure(entry) {
        const sources = {};
        async function visit(path) {
            const name = relative(root, path).replaceAll('\\', '/');
            if (Object.hasOwn(sources, name)) return;
            if (name.startsWith('../')) throw Error('Source dependency escapes the repository.');
            const text = await readFile(path, 'utf8'); sources[name] = hash(text);
            for (const match of text.matchAll(/^import\s+[^;]*?from\s+['"]([^'"]+)['"];?/gm)) {
                if (!match[1].startsWith('.')) throw Error('Unexpected non-repository core dependency.');
                await visit(resolve(dirname(path), match[1]));
            }
        }
        await visit(resolve(root, entry));
        const sorted = Object.fromEntries(Object.entries(sources).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0));
        return {sources: sorted, sha256: hash(JSON.stringify(sorted))};
    }
    const compiler = await closure('examples/successor-capability/out-execute/engine.mjs');
    const checker = await closure('examples/successor-capability/out-execute/checker.mjs');
    return {source: {compilerSha256: compiler.sha256, checkerSha256: checker.sha256, evaluatorVersion: CHECKER_VERSION},
        compilerSources: compiler.sources, checkerSources: checker.sources,
        authenticity: 'local-installed-bytes-not-external-attestation'};
}
