// SPDX-License-Identifier: Apache-2.0
import { setup } from './setup.mjs';
await setup();
await import('./server.mjs');
