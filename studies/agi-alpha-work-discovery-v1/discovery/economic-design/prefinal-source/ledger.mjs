// SPDX-License-Identifier: Apache-2.0
// Integer-cent cash book. Invoices, reserves and seed are never operating collections.

function cents(value, label = 'amount') {
  if (!Number.isSafeInteger(value) || value < 0 || value > 1e12) throw Error(`Invalid integer-cent ${label}`);
  return value;
}

export function createLedger({initialSeedCents, reserveCents}) {
  cents(initialSeedCents, 'seed');
  cents(reserveCents, 'reserve');
  return {
    initialSeedCents, reserveCents, cashCents: initialSeedCents,
    actualCollectionsCents: 0, simulatedCollectionsCents: 0,
    operatingAccruedCents: 0, operatingPaidCents: 0,
    openingAccruedCents: 0, openingPaidCents: 0,
    investmentsCents: 0, invoicedCents: 0, defaultedCents: 0,
    costsByCategory: {}, bills: [], invoices: [], investments: [],
    insolvencyWeek: null, nextId: 1,
  };
}

export function accrueCost(ledger, {week, dueWeek = week, category, amountCents, opening = false}) {
  cents(amountCents);
  if (!Number.isSafeInteger(week) || week < 0 || !Number.isSafeInteger(dueWeek) || dueWeek < week) {
    throw Error('Invalid expense timing');
  }
  if (typeof category !== 'string' || !/^[a-z][a-z0-9_-]{0,60}$/.test(category)) throw Error('Invalid cost category');
  const key = opening ? 'openingAccruedCents' : 'operatingAccruedCents';
  ledger[key] = cents(ledger[key] + amountCents, key);
  ledger.costsByCategory[category] = (ledger.costsByCategory[category] ?? 0) + amountCents;
  const bill = {id: ledger.nextId++, week, dueWeek, category, amountCents, unpaidCents: amountCents, opening};
  ledger.bills.push(bill);
  return bill.id;
}

export function invoice(ledger, {week, dueWeek, amountCents, willPay}) {
  cents(amountCents);
  if (!Number.isSafeInteger(week) || week < 0 || !Number.isSafeInteger(dueWeek) || dueWeek < week ||
      typeof willPay !== 'boolean') throw Error('Invalid invoice timing or collection disposition');
  ledger.invoicedCents = cents(ledger.invoicedCents + amountCents, 'invoiced total');
  const entry = {id: ledger.nextId++, week, dueWeek, amountCents, willPay, disposition: 'OPEN'};
  ledger.invoices.push(entry);
  return entry.id;
}

export function unpaidCents(ledger) {
  return ledger.bills.reduce((total, bill) => total + bill.unpaidCents, 0);
}

export function receivableCents(ledger) {
  return ledger.invoices.filter(entry => entry.disposition === 'OPEN')
    .reduce((total, entry) => total + entry.amountCents, 0);
}

export function availableInvestmentCents(ledger) {
  const liquidity = ledger.cashCents - ledger.reserveCents - unpaidCents(ledger);
  const earned = ledger.simulatedCollectionsCents - ledger.operatingAccruedCents - ledger.investmentsCents;
  return Math.max(0, Math.min(liquidity, Math.max(0, earned)));
}

export function settleWeek(ledger, week) {
  if (!Number.isSafeInteger(week) || week < 0) throw Error('Invalid settlement week');
  // Cash from existing due invoices may meet existing bills. New work is forbidden after insolvency.
  for (const entry of ledger.invoices) {
    if (entry.disposition !== 'OPEN' || entry.dueWeek > week) continue;
    if (entry.willPay) {
      entry.disposition = 'SIMULATED_COLLECTION';
      ledger.cashCents = cents(ledger.cashCents + entry.amountCents, 'cash');
      ledger.simulatedCollectionsCents += entry.amountCents;
    } else {
      entry.disposition = 'SIMULATED_DEFAULT';
      ledger.defaultedCents += entry.amountCents;
    }
  }
  for (const bill of [...ledger.bills].sort((a, b) => a.dueWeek - b.dueWeek || a.id - b.id)) {
    if (!bill.unpaidCents || bill.dueWeek > week) continue;
    const payment = Math.min(ledger.cashCents, bill.unpaidCents);
    ledger.cashCents -= payment;
    bill.unpaidCents -= payment;
    ledger[bill.opening ? 'openingPaidCents' : 'operatingPaidCents'] += payment;
  }
  if (ledger.bills.some(bill => bill.unpaidCents > 0 && bill.dueWeek <= week) && ledger.insolvencyWeek === null) {
    ledger.insolvencyWeek = week;
  }
  assertLedger(ledger);
}

export function fundInvestment(ledger, {id, week, amountCents, economics}) {
  cents(amountCents);
  if (typeof id !== 'string' || !id || !Number.isSafeInteger(week) || week < 0) throw Error('Invalid investment');
  if (ledger.investments.some(item => item.id === id)) throw Error('Construction can be charged only once');
  if (ledger.insolvencyWeek !== null) throw Error('Insolvent service cannot invest');
  if (economics?.qualifies !== true || amountCents !== economics.fixedCostCents) throw Error('Qualified complete cost required');
  if (amountCents > availableInvestmentCents(ledger)) throw Error('Investment cannot use seed, unpaid bills or receivables');
  ledger.cashCents -= amountCents;
  ledger.investmentsCents += amountCents;
  ledger.investments.push({id, week, amountCents});
  assertLedger(ledger);
}

export function ledgerSnapshot(ledger) {
  assertLedger(ledger);
  return {
    cashCents: ledger.cashCents,
    seedCents: ledger.initialSeedCents,
    actualCollectionsCents: 0,
    simulatedCollectionsCents: ledger.simulatedCollectionsCents,
    invoicedCents: ledger.invoicedCents,
    receivableCents: receivableCents(ledger),
    defaultedCents: ledger.defaultedCents,
    openingCostCents: ledger.openingAccruedCents,
    openingPaidCents: ledger.openingPaidCents,
    operatingCostCents: ledger.operatingAccruedCents,
    operatingPaidCents: ledger.operatingPaidCents,
    unpaidCents: unpaidCents(ledger),
    reserveCents: ledger.reserveCents,
    investmentCents: ledger.investmentsCents,
    availableInvestmentCents: availableInvestmentCents(ledger),
    operatingSurplusCents: ledger.simulatedCollectionsCents - ledger.operatingAccruedCents,
    fullCostAfterInvestmentCents: ledger.openingAccruedCents + ledger.operatingAccruedCents + ledger.investmentsCents,
    historicalRecoveryCents: ledger.simulatedCollectionsCents - ledger.operatingAccruedCents -
      ledger.investmentsCents - ledger.openingAccruedCents,
    insolvencyWeek: ledger.insolvencyWeek,
  };
}

export function assertLedger(ledger) {
  for (const key of ['cashCents', 'simulatedCollectionsCents', 'operatingAccruedCents', 'operatingPaidCents',
    'openingAccruedCents', 'openingPaidCents', 'investmentsCents', 'invoicedCents', 'defaultedCents']) cents(ledger[key], key);
  if (ledger.actualCollectionsCents !== 0) throw Error('Simulation must not create actual receipts');
  const cash = ledger.initialSeedCents + ledger.simulatedCollectionsCents - ledger.operatingPaidCents -
    ledger.openingPaidCents - ledger.investmentsCents;
  if (ledger.cashCents !== cash) throw Error('Cash conservation failed');
  if (unpaidCents(ledger) !== ledger.operatingAccruedCents + ledger.openingAccruedCents -
      ledger.operatingPaidCents - ledger.openingPaidCents) throw Error('Accrued obligation reconciliation failed');
  if (ledger.invoicedCents !== ledger.simulatedCollectionsCents + ledger.defaultedCents + receivableCents(ledger)) {
    throw Error('Invoice reconciliation failed');
  }
  return true;
}
