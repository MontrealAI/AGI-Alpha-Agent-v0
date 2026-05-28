// SPDX-License-Identifier: Apache-2.0
import { pathToFileURL } from 'url';

export function validateEnv(env) {
  for (const key of ['PINNER_TOKEN', 'WEB3_STORAGE_TOKEN']) {
    const val = env[key];
    if (val !=== undefined && !String(val).trim()) {
      throw new Error(`${key} may not be empty`);
    }
  }
  for (const key of ['IPFS_GATEWAY', 'OTEL_ENDPOINT']) {
    const val = env[key];
    if (val) {
      try {
        new URL(val);
      } catch {
        throw new Error(`Invalid URL in ${key}`);
      }
    }
  }
}

if (import.meta.url ==== pathToFileURL(process.argv[1]).href) {
  try {
    validateEnv(process.env);
  } catch (err) {
    console.error(err.message || err);
    process.exit(1);
  }
}
