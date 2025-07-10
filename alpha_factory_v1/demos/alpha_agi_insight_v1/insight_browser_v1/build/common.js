// SPDX-License-Identifier: Apache-2.0
import { promises as fs } from 'fs';
import fsSync from 'fs';
import path from 'path';
import { createHash } from 'crypto';
import { injectEnv } from './env_inject.js';

export async function copyAssets(manifest, repoRoot, outDir) {
  for (const rel of manifest.files) {
    const dest = path.join(outDir, rel);
    await fs.mkdir(path.dirname(dest), { recursive: true });
    await fs.copyFile(rel, dest).catch(() => {});
  }
  const i18nDir = manifest.dirs.translations;
  if (fsSync.existsSync(i18nDir)) {
    await fs.mkdir(path.join(outDir, i18nDir), { recursive: true });
    for (const f of await fs.readdir(i18nDir)) {
      await fs.copyFile(path.join(i18nDir, f), path.join(outDir, i18nDir, f));
    }
  }
  const criticsSrc = path.join(repoRoot, manifest.dirs.critics);
  if (fsSync.existsSync(criticsSrc)) {
    await fs.mkdir(path.join(outDir, manifest.dirs.critics), { recursive: true });
    for (const f of await fs.readdir(criticsSrc)) {
      await fs.copyFile(path.join(criticsSrc, f), path.join(outDir, manifest.dirs.critics, f));
    }
  }
  for (const dirKey of ['wasm', 'wasm_llm']) {
    const dir = manifest.dirs[dirKey];
    if (fsSync.existsSync(dir)) {
      await fs.mkdir(path.join(outDir, dir), { recursive: true });
      for (const f of await fs.readdir(dir)) {
        await fs.copyFile(path.join(dir, f), path.join(outDir, dir, f));
      }
    }
  }
}

export { injectEnv };
export async function checkGzipSize(file, maxBytes = 5 * 1024 * 1024) {
  const {gzipSizeFromFile} = await import('gzip-size');
  const size = await gzipSizeFromFile(file);
  if (size > maxBytes) {
    throw new Error(`gzip size ${size} bytes exceeds limit`);
  }
}

export async function generateServiceWorker(outDir, manifest, version) {
  const { injectManifest } = await import('workbox-build');
  const swSrc = 'sw.js';
  const swTemp = path.join(outDir, 'sw.build.js');
  const swDest = path.join(outDir, 'sw.js');
  const swTemplate = await fs.readFile(swSrc, 'utf8');
  await fs.writeFile(swTemp, swTemplate.replace('__CACHE_VERSION__', version));
  await injectManifest({
    swSrc: swTemp,
    swDest,
    globDirectory: outDir,
    globPatterns: manifest.precache,
    injectionPoint: 'self.__WB_MANIFEST',
  });
  await fs.unlink(swTemp);
  const swData = await fs.readFile(swDest);
  const swHash = createHash('sha384').update(swData).digest('base64');
  let wbPath = path.join(outDir, 'workbox-sw.js');
  if (!fsSync.existsSync(wbPath)) wbPath = path.join(outDir, 'assets', 'lib', 'workbox-sw.js');
  let wbHash = '';
  if (fsSync.existsSync(wbPath)) {
    wbHash = createHash('sha384').update(fsSync.readFileSync(wbPath)).digest('base64');
  }
  const indexPath = path.join(outDir, 'index.html');
  let indexText = await fs.readFile(indexPath, 'utf8');
  indexText = indexText.replace(".register('sw.js')", ".register('service-worker.js')");
  indexText = indexText.replace('__SW_HASH__', `sha384-${swHash}`);
  indexText = indexText.replace(
    /(script-src 'self' 'wasm-unsafe-eval')/,
    `$1 'sha384-${swHash}'`
  );
  await fs.writeFile(indexPath, indexText);
  let swText = swData.toString('utf8');
  swText = swText.replace('__WORKBOX_SW_HASH__', `sha384-${wbHash}`);
  await fs.writeFile(swDest, swText);
}
