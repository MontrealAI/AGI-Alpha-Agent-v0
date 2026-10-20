// SPDX-License-Identifier: Apache-2.0
/** Explicit local host runner. Fixed installed code; no network, credentials or imported programs. */
import { constants } from 'node:fs';
import { open, lstat, realpath, link, unlink } from 'node:fs/promises';
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash, randomUUID } from 'node:crypto';
import { runNativeHandoff, inspectNativeReturn, LIMITS } from './continuity.mjs';

const ROOT = fileURLToPath(new URL('../../', import.meta.url));
const ROOT_MODULES = Object.freeze([
    'examples/successor-alpha/engine.mjs', 'examples/successor-alpha/project.mjs',
    'examples/successor-alpha/research.mjs', 'examples/successor-alpha/continuity.mjs',
    'examples/successor-alpha/capability.mjs', 'examples/successor-alpha/computer.mjs',
    'examples/successor-alpha/learning.mjs',
    'docs/assets/successor/engine.mjs',
]);
const sha256 = value => createHash('sha256').update(value).digest('hex');
const inside = (root, path) => {
    const rel = relative(root, path);
    if (!rel || rel === '..' || rel.startsWith('..' + sep) || isAbsolute(rel)) {
        throw Error('Installed module must be a file inside the repository.');
    }
    return rel.split(sep).join('/');
};

/** Match the maintained generator's exact reviewed static JavaScript module closure. */
export async function computeInstalledSourceHash() {
    const root = await realpath(ROOT), visited = new Map();
    async function visit(filename) {
        const path = await realpath(filename), relativePath = inside(root, path);
        if (visited.has(relativePath)) return;
        const source = (await readBoundedFile(path, LIMITS.bytes)).replace(/\r\n?/g, '\n');
        visited.set(relativePath, sha256(source));
        const boundary = /^export\s+/m.exec(source)?.index ?? 0;
        const prefix = source.slice(0, boundary);
        // This deliberately matches scripts/generate_successor_alpha.py, including its first-export boundary.
        const imports = /^import\s+([^;]*?)\s+from\s+['"]([^'"]+)['"];/gm;
        for (const match of prefix.matchAll(imports)) {
            const location = match[2];
            if (!location.startsWith('.')) throw Error('Only repository-local static modules are supported.');
            await visit(resolve(dirname(path), location));
        }
    }
    for (const module of ROOT_MODULES) await visit(resolve(root, module));
    const sources = Object.fromEntries([...visited].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0));
    return sha256(JSON.stringify(sources));
}

/** Open special files without blocking, then admit only a bounded regular UTF-8 file. */
export async function readBoundedFile(filename, maximum = LIMITS.bytes) {
    const flags = constants.O_RDONLY | (constants.O_NONBLOCK ?? 0) | (constants.O_NOFOLLOW ?? 0);
    const handle = await open(filename, flags);
    try {
        const stat = await handle.stat();
        if (!stat.isFile() || stat.size > maximum) throw Error('Input must be a regular UTF-8 file up to 2 MB.');
        const buffer = Buffer.alloc(maximum + 1); let used = 0;
        while (used < buffer.length) {
            const { bytesRead } = await handle.read(buffer, used, buffer.length - used, null);
            if (!bytesRead) break;
            used += bytesRead;
        }
        if (used > maximum) throw Error('Input grew beyond its 2 MB limit.');
        // Python read_text(encoding='utf-8') retains a BOM. Keep it in the source identity too.
        return new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(buffer.subarray(0, used));
    } finally { await handle.close(); }
}

async function requireNewOutput(path) {
    try { await lstat(path); } catch (error) {
        if (error.code === 'ENOENT') return;
        throw error;
    }
    throw Error('Output already exists. Choose a new return filename; existing files are never overwritten.');
}

async function publishExclusive(filename, content) {
    const temporary = resolve(dirname(filename), '.alpha-native-' + randomUUID() + '.tmp');
    let handle, created = false;
    try {
        handle = await open(temporary, 'wx', 0o600); created = true;
        await handle.writeFile(content, 'utf8'); await handle.sync();
        await handle.close(); handle = null;
        // A same-directory hard link publishes the complete file atomically and refuses an existing destination.
        await link(temporary, filename);
    } finally {
        if (handle) await handle.close();
        if (created) await unlink(temporary).catch(error => { if (error.code !== 'ENOENT') throw error; });
    }
}

export async function runHandoffFile(input, output) {
    const destination = resolve(output);
    await requireNewOutput(destination);
    const handoff = await readBoundedFile(input), sourceHash = await computeInstalledSourceHash();
    const returned = await runNativeHandoff(handoff, { sourceHash });
    const checked = await inspectNativeReturn(handoff, returned);
    await publishExclusive(destination, returned);
    return { schema: 'successor-alpha-host-run/v1', projectId: checked.project.id,
        cycleId: checked.cycle.id, sourceHash, output: destination,
        files: checked.files.map(file => file.name), execution: 'installed-local-node',
        authority: 'none', independentlyQualified: false, settlement: 'not-connected' };
}

async function main(args) {
    if (args.length !== 2) {
        throw Error('Usage: node examples/successor-alpha/native-cli.mjs HANDOFF.json NEW-RETURN.json');
    }
    const result = await runHandoffFile(args[0], args[1]);
    process.stdout.write(JSON.stringify(result) + '\n');
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
    main(process.argv.slice(2)).catch(error => {
        process.stderr.write('Native catalog run refused: ' + error.message + '\n'); process.exitCode = 1;
    });
}
