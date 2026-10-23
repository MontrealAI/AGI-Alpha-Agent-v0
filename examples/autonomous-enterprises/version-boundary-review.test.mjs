// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as workspace from '../successor-capability/workspace.mjs';
import * as controller from './controller.mjs';
import {defaultCharter} from './protocol.mjs';
import {digest} from '../../docs/assets/successor/engine.mjs';

const source = {constructor: '1'.repeat(64), checker: '2'.repeat(64), closure: '3'.repeat(64)};
const charter = {...defaultCharter(source), maxN: 2, constructionLimit: 100_000, perTaskLimit: 100_000, taskLimit: 1};
const changed = {...workspace.DEFAULT_BRIEF, title: 'An explicitly changed successor proposal'};
const blocked = /active enterprise attempt/i;
async function begin() { return controller.start(await workspace.createWorkspace(), charter); }

test('a live construction reservation refuses a new version without losing stop or its original history', async () => {
    const value = await begin(), before = workspace.canonical(value);
    await assert.rejects(workspace.addSuccessor(value, changed, null, 'A later proposal'), blocked);
    assert.equal(workspace.canonical(value), before);
    const stopped = await controller.stop(value, 'Stop this reserved attempt before editing.');
    assert.equal((await controller.state(stopped)).history.at(-1).state, 'CANCELLED');
    assert.equal(workspace.canonical(stopped.events.slice(0, value.events.length)), workspace.canonical(value.events));
});

test('a frozen active factory refuses proposal changes and can still commit its later tasks', async () => {
    let value = await begin();
    for (let i = 0; i < 2; i++) value = await controller.next(value, {expectedSource: source});
    assert.equal((await controller.state(value)).current.state, 'FROZEN');
    const before = workspace.canonical(value);
    await assert.rejects(workspace.addSuccessor(value, changed, null, 'A later proposal'), blocked);
    assert.equal(workspace.canonical(value), before);
    const continued = await controller.next(value, {expectedSource: source, seed: 77});
    assert.equal((await controller.state(continued)).current.state, 'TASKS_COMMITTED');
    assert.equal(workspace.canonical(continued.events.slice(0, value.events.length)), workspace.canonical(value.events));
});

test('an otherwise valid rehashed version import cannot bypass an active enterprise reservation', async () => {
    const base = await workspace.createWorkspace();
    const ordinary = await workspace.addSuccessor(base, changed, null, 'A valid legacy successor');
    const active = await controller.start(base, charter);
    const value = JSON.parse(workspace.canonical(active));
    const payload = ordinary.events.at(-1).payload;
    const event = {sequence: value.events.length, kind: 'version', previous: value.events.at(-1).digest, payload};
    event.digest = await digest('capability-event', {missionId: value.missionId, ...event});
    value.events.push(event); value.revision = value.events.length - 1;
    await assert.rejects(workspace.parseWorkspace(workspace.canonical(value)), blocked);
    assert.equal((await controller.state(active)).current.state, 'RESERVED');
});

test('ordinary and reconciled stopped histories can add versions without erasing unknown historical reservations', async () => {
    const base = await workspace.createWorkspace();
    const ordinary = await workspace.addSuccessor(base, changed, null, 'Preserve the legacy successor path');
    assert.equal((await workspace.inspectWorkspace(ordinary)).latest.number, 2);
    const active = await controller.start(base, charter);
    const stopped = await controller.stop(active, 'Keep unknown work explicit.');
    const later = await workspace.addSuccessor(stopped, changed, null, 'An independent later proposal');
    const inspection = await workspace.inspectWorkspace(later);
    assert.equal(inspection.latest.number, 2);
    assert.equal(inspection.enterprises.active, null);
    assert.equal(inspection.enterprises.attempts[0].unresolvedReservation, true);
    assert.equal(workspace.canonical(later.events.slice(0, stopped.events.length)), workspace.canonical(stopped.events));
    await assert.rejects(controller.start(later, charter), /unknown|unresolved|reconcil|spent/i);
});
