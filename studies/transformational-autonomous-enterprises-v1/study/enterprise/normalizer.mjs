// SPDX-License-Identifier: Apache-2.0
import { LIMITS, invariant, exactKeys, label, safeInteger, deepFreeze, optionalMeter } from './protocol.mjs';

export function flatReduce(rows, { meter } = {}) {
  meter = optionalMeter(meter);
  invariant(Array.isArray(rows) && rows.length > 0 && rows.length <= LIMITS.flatRows, 'ROW_LIMIT', `Flat reduction requires 1..${LIMITS.flatRows} rows.`);
  const totals = new Map();
  for (const row of rows) { meter.tick('flat-input-row'); exactKeys(row, ['group', 'amount']); label(row.group, 'group'); safeInteger(row.amount, 'row amount'); invariant(Math.abs(row.amount) <= LIMITS.flatInputAbs, 'FLAT_INPUT_LIMIT', 'A flat input exceeds the declared absolute amount bound.'); totals.set(row.group, (totals.get(row.group) ?? 0n) + BigInt(row.amount)); }
  return deepFreeze([...totals].sort(([a], [b]) => { meter.tick('flat-sort-group'); return a < b ? -1 : a > b ? 1 : 0; }).map(([group, amount]) => { meter.tick('flat-output-row'); return { group, amount: amount.toString() }; }));
}
export function normalizeRows(rows, { meter } = {}) {
  meter = optionalMeter(meter);
  invariant(Array.isArray(rows) && rows.length > 0 && rows.length <= LIMITS.flatRows, 'ROW_LIMIT', 'Output rows must be nonempty and bounded.');
  const known = new Set();
  const normalized = rows.map(row => { meter.tick('normalize-output-row'); exactKeys(row, ['group', 'amount']); label(row.group, 'group'); invariant(!known.has(row.group), 'DUPLICATE_OUTPUT', 'Output groups must be unique.'); known.add(row.group); invariant(typeof row.amount === 'string' && /^(0|-?[1-9][0-9]*)$/u.test(row.amount), 'INVALID_DECIMAL', 'Output amount must be a canonical decimal integer string.'); invariant(row.amount.replace('-', '').length <= LIMITS.integerDigits, 'INTEGER_DIGIT_LIMIT', 'Output magnitude ceiling reached.'); return { group: row.group, amount: row.amount }; });
  normalized.sort((a, b) => { meter.tick('normalize-sort-row'); return a.group < b.group ? -1 : a.group > b.group ? 1 : 0; });
  const quoted = value => /[",\r\n]/u.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
  const csv = `group,amount\n${normalized.map(row => `${quoted(row.group)},${row.amount}`).join('\n')}\n`;
  const limit = BigInt(LIMITS.outputAbs);
  let total = 0n;
  const excessive = normalized.filter(row => { meter.tick('delivery-bound-check'); const amount = BigInt(row.amount); total += amount; return amount > limit || amount < -limit; }).map(row => row.group);
  const totalLimit = BigInt(LIMITS.outputTotalAbs); const totalExceeded = total > totalLimit || total < -totalLimit;
  const infeasible = excessive.length > 0 || totalExceeded;
  return deepFreeze({ rows: normalized, csv, delivery: { status: infeasible ? 'infeasible' : 'ready', reason: infeasible ? 'An output group or the signed aggregate exceeds the declared native-delivery absolute bound.' : null, excessiveGroups: excessive, totalAmount: total.toString(), totalExceeded, outputAbsLimit: LIMITS.outputAbs, outputTotalAbsLimit: LIMITS.outputTotalAbs, nativeExecution: 'not-yet-run', settlement: 'not-connected', authority: 'none' } });
}
