// SPDX-License-Identifier: Apache-2.0
const data = JSON.parse(document.getElementById('bundle-data').textContent);
const sources = JSON.parse(document.getElementById('bundle-modules').textContent);
const moduleURLs = new Map();
const loading = new Set();

function moduleURL(name) {
    if (moduleURLs.has(name)) return moduleURLs.get(name);
    if (!Object.hasOwn(sources, name)) throw new Error(`BUNDLE_DEPENDENCY_MISSING:${name}`);
    if (loading.has(name)) throw new Error(`BUNDLE_IMPORT_CYCLE:${name}`);
    loading.add(name);
    const source = sources[name].replace(
        /^import\s+([\s\S]*?)\s+from\s+(['"])([^'"]+)\2\s*;/gm,
        (_, bindings, quote, target) => {
            if (!target.startsWith('.')) throw new Error(`EXTERNAL_IMPORT_DISABLED:${target}`);
            const resolved = new URL(target, `https://bundle.invalid/${name}`).pathname.slice(1);
            return `import ${bindings} from ${JSON.stringify(moduleURL(resolved))};`;
        },
    );
    if (/^import\s*['"]/m.test(source)) throw new Error(`SIDE_EFFECT_IMPORT_UNSUPPORTED:${name}`);
    const url = URL.createObjectURL(new Blob([source, `\n//# sourceURL=earned-turn/${name}`], {
        type: 'text/javascript',
    }));
    moduleURLs.set(name, url);
    loading.delete(name);
    return url;
}

try {
    if (!globalThis.crypto?.subtle) throw new Error('Web Crypto is unavailable. Open this file in a current desktop browser.');
    for (const [name, source] of Object.entries(sources)) {
        const bytes = new TextEncoder().encode(source);
        const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))]
            .map(value => value.toString(16).padStart(2, '0')).join('');
        if (digest !== data.module_manifest[name]) throw new Error(`SOURCE_BYTES_CHANGED:${name}`);
    }
    const {startApp} = await import(moduleURL('browser/app.mjs'));
    await startApp({data});
} catch (error) {
    const status = document.getElementById('app-status');
    status.hidden = false;
    status.className = 'notice error';
    status.textContent = `The local laboratory could not start: ${error.message}`;
    document.getElementById('start-button').disabled = true;
    console.error(error);
}
