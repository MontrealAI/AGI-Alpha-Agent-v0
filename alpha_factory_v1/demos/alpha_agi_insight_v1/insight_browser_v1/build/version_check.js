// SPDX-License-Identifier: Apache-2.0
import { pathToFileURL } from 'url';

export function requireNode20() {
  const [major] = process.versions.node.split('.').map(Number);
  if (major < 20) {
    console.error(
      `Node.js 20+ is required. Current version: ${process.versions.node}`
    );
    process.exit(1);
  }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  requireNode20();
}
