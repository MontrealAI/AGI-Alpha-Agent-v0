// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';import assert from 'node:assert/strict';
import {ecosystemChoice} from '../../docs/assets/nova-studio/ecosystem-choice.mjs';
test('all selectable combinations explain scope without fabricating adapter authority',()=>{for(const goal of ['prepare','execute'])for(const market of ['ascension','jobs-v0','manager'])for(const executor of ['native','fleet']){const choice=ecosystemChoice({goal,market,executor});assert.ok(choice.en&&choice.fr);assert.equal(choice.token,market==='manager'?'USDC':'AGIALPHA');if(executor==='fleet'||market==='manager')assert.equal(choice.action,null);else if(market==='jobs-v0')assert.equal(choice.action,'native-jobs');else assert.equal(choice.action,goal==='prepare'?'project':'runtime');}});
test('unknown inputs cannot enable a route',()=>{assert.throws(()=>ecosystemChoice({goal:'prepare',market:'token-match',executor:'native'}));});
