// SPDX-License-Identifier: Apache-2.0
import {readFileSync} from 'node:fs';
import {evaluateAutomatedCosts} from '../../examples/successor-alpha/automated-costs.mjs';
import {replayLedger} from '../../examples/successor-alpha/shadow-ledger.mjs';
const request=JSON.parse(readFileSync(0,'utf8'));
if(!request||Object.keys(request).sort().join(',')!=='accounting,ledger')throw Error('COST_INPUT');
process.stdout.write(JSON.stringify({accounting:evaluateAutomatedCosts(request.accounting),ledger:replayLedger(request.ledger)}));
