// SPDX-License-Identifier: Apache-2.0
/**
 * Spawn a Web Worker.
 *
 * We prefer direct module workers because strict CSP blocks inline scripts in
 * sandboxed iframe bootstraps unless additional hashes/nonces are maintained.
 */
export async function createSandboxWorker(url: string | URL): Promise<Worker> {
  const worker = new Worker(url.toString(), { type: 'module' });
  return worker;
}
