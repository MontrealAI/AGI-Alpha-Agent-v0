// SPDX-License-Identifier: Apache-2.0
import { pathToFileURL } from 'url';

export function requireNode22() {
  const [major] = process.versions.node.split('.').map(Number);
  if (major < 22) {
    console.error(
      `Node.js 22+ is required. Current version: ${process.versions.node}`
    );
    process.exit(1);
  }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  requireNode22();
}
