// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as workspace from '../successor-capability/workspace.mjs';
import * as controller from './controller.mjs';
import {defaultCharter} from './protocol.mjs';

test('a refused construction preflight releases only known unstarted work and retains the capped attempt', async () => {
    const source = {constructor: '1'.repeat(64), checker: '2'.repeat(64), closure: '3'.repeat(64)};
    let value = await controller.start(await workspace.createWorkspace(),
        {...defaultCharter(source), maxN: 2, constructionLimit: 0});
    value = await controller.next(value, {expectedSource: source});
    const stopped = (await controller.state(value)).history.at(-1);
    assert.equal(stopped.state, 'INCONCLUSIVE');
    assert.equal(stopped.actualConstructionWork, 0);
    assert.equal(stopped.unknownSpent, false);
    assert.equal(stopped.unresolvedReservation, false);
    assert.equal(value.events.at(-1).kind, 'enterprise-budget-refused');
    const next = await controller.start(value, {...defaultCharter(source), maxN: 2});
    assert.equal((await controller.state(next)).history.length, 2);
});
