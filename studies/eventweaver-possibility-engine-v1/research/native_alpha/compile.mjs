// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import {compilePlan, verifyPlan} from './docs/assets/nova-studio/plan.mjs';
const specs = JSON.parse(fs.readFileSync(process.argv[2] || 0, 'utf8'));
const plan = compilePlan(specs);
verifyPlan(plan);
process.stdout.write(JSON.stringify(plan, null, 2) + '\n');
