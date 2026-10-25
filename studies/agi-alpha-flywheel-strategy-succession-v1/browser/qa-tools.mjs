// SPDX-License-Identifier: Apache-2.0
// Optional development QA dependency loader; not included in the browser bundle.
import {createRequire} from 'node:module';
import {existsSync} from 'node:fs';
import path from 'node:path';

const require = createRequire(import.meta.url);
let playwright;
try {
    playwright = require('playwright');
} catch {
    const modules = process.env.AGI_PLAYWRIGHT_MODULES ?? process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
    if (!modules) throw new Error('Optional browser QA requires Playwright 1.62.1; run npm install in browser/.');
    playwright = require(path.join(modules, 'playwright'));
}
export const {chromium} = playwright;
const suppliedChrome = '/tmp/successor-chrome/chrome-headless-shell-linux64/chrome-headless-shell';
export const executablePath = process.env.AGI_BROWSER_CHROME
    ?? (existsSync(suppliedChrome) ? suppliedChrome : undefined);
