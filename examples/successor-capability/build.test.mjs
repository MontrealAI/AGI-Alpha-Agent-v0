// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {resolve, dirname} from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const read = path => readFileSync(resolve(root, path), 'utf8');
const hash = (value, encoding = 'hex') => createHash('sha256').update(value).digest(encoding);
const page = read('docs/successor/capabilities/index.html');

test('generated page binds exact repository source closure and CSP', () => {
    const manifest = JSON.parse(read('docs/successor/capabilities/sources.json'));
    const actual = Object.fromEntries(Object.entries(manifest.sources).map(([path, expected]) => {
        assert.equal(hash(read(path)), expected, `Stale source: ${path}`);
        return [path, expected];
    }));
    const sorted = Object.fromEntries(Object.entries(actual).sort(([left], [right]) => left.localeCompare(right)));
    assert.equal(hash(JSON.stringify(sorted)), manifest.sourceHash);
    assert.ok(page.includes(manifest.sourceHash));
    for (const tag of ['script', 'style']) {
        const match = page.match(new RegExp(`<${tag}>([\\s\\S]*?)</${tag}>`));
        assert.ok(match);
        assert.ok(page.includes(`${tag}-src 'sha256-${hash(match[1], 'base64')}'`));
    }
    assert.match(page, /connect-src 'none'/);
    assert.match(page, /form-action 'none'/);
    assert.doesNotMatch(page, /<script[^>]+src=|<link[^>]+stylesheet/i);
    assert.doesNotMatch(page, /\{\{(?:SCRIPT|STYLE|SOURCE_HASH)/);
});

test('research, preservation navigation and aggregate failure wiring remain available', () => {
    for (const paper of ['Transformational_Intelligence', 'Invent_the_Economy', 'Out_Evolve', 'The_World_as_an_Output']) {
        assert.ok(page.includes(`../../${paper}.pdf`));
        assert.ok(existsSync(resolve(root, 'docs', `${paper}.pdf`)));
    }
    for (const route of ['../mission/', '../discover/']) assert.ok(page.includes(`href="${route}"`));
    assert.ok(page.includes("latest.witnessAcceptance === 'fail'"));
    assert.ok(page.includes('The broad capability brief and economic hypotheses remain unevaluated.'));
    assert.ok(read('docs/successor/index.html').includes('href="capabilities/"'));
    assert.ok(read('docs/service-worker.js').includes('./successor/capabilities/index.html'));
});

test('every workshop section link has a unique local destination', () => {
    const ids = [...page.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
    assert.equal(new Set(ids).size, ids.length, 'Duplicate HTML IDs');
    for (const [, target] of page.matchAll(/\bhref="#([^"]+)"/g)) {
        assert.ok(ids.includes(target), `Missing section destination: ${target}`);
    }
});
