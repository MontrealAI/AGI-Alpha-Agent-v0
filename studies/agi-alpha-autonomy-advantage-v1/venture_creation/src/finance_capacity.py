# SPDX-License-Identifier: Apache-2.0
"""Thin simulated cash/resource adapter; no payments, credentials or runtime authority.

Amounts are integer micro-USD. Time is continuous days. The accounting convention
matches the unchanged canonical shadow ledger: seed is financing, every committed
expense is accrued once, and only collections net of costs/reserves can be reinvested.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import math

MICROS = 1_000_000


def _finite(value, name, minimum=0):
    value = float(value)
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return value


def usd_to_micros(value):
    _finite(value, "USD")
    return int((Decimal(str(value)) * MICROS).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def micros_to_usd(value):
    return value / MICROS


def _fraction(value, name):
    value = _finite(value, name)
    if value > 1:
        raise ValueError(f"{name} must be <= 1")
    return value


def _scaled(amount, fraction):
    return int((Decimal(amount) * Decimal(str(fraction))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class CashBook:
    """Finite simulated cash with explicit commitments and delayed settlements.

    expense() records a commitment; advance() makes eligible payments. Funds reserve
    all unpaid commitments even before their due dates. Insufficient cash at a due
    date records an insolvency event, leaves the bill unpaid, and never borrows.
    """

    def __init__(self, seedUsd, baseReserveUsd=0, taxFraction=0, warrantyFraction=0):
        self.seedMicros = usd_to_micros(seedUsd)
        self.cashMicros = self.seedMicros
        self.baseReserveMicros = usd_to_micros(baseReserveUsd)
        self.taxFraction = _fraction(taxFraction, "taxFraction")
        self.warrantyFraction = _fraction(warrantyFraction, "warrantyFraction")
        self.collectedMicros = 0
        self.t = 0.0
        self.bills = []
        self.invoices = []
        self.events = []
        self.snapshots = []
        self.insolvent = False
        self.insolventAt = None

    def _time(self, t):
        t = _finite(t, "time")
        if t < self.t:
            raise ValueError("Cash events cannot precede the advanced clock")
        return t

    def expense(self, t, usd, category, ref, due=None):
        t = self._time(t)
        due = t if due is None else _finite(due, "expense due")
        if due < t:
            raise ValueError("Expense due date cannot precede commitment")
        if not category or not ref:
            raise ValueError("Expense category and reference are required")
        bill = dict(id=f"bill-{len(self.bills)}", t=t, due=due,
                    amountMicros=usd_to_micros(usd), category=str(category), ref=str(ref),
                    paid=False, paidAt=None, missedDue=False)
        self.bills.append(bill)
        self.events.append(dict(t=t, type="SIMULATED_COST_COMMITMENT", billId=bill["id"],
                                amountMicros=bill["amountMicros"], cashAfterMicros=self.cashMicros))
        return bill

    def invoice(self, t, job_id, usd, due, pays, fee_fraction=0, warranty_until=None):
        t = self._time(t)
        due = _finite(due, "invoice due")
        warranty_until = due if warranty_until is None else _finite(warranty_until, "warranty end")
        if due < t or warranty_until < t:
            raise ValueError("Invoice due/warranty dates cannot precede issue")
        if any(x["jobId"] == str(job_id) for x in self.invoices):
            raise ValueError("A commission may have only one invoice")
        if not isinstance(pays, bool):
            raise ValueError("pays must be a Boolean scenario outcome")
        row = dict(id=f"invoice-{len(self.invoices)}", jobId=str(job_id), t=t, due=due,
                   amountMicros=usd_to_micros(usd), pays=pays,
                   feeFraction=_fraction(fee_fraction, "fee_fraction"), warrantyUntil=warranty_until,
                   status="pending", collectedAt=None, cancelledAt=None, refundBillId=None)
        self.invoices.append(row)
        return row

    def _pay_due(self, t):
        for bill in sorted(self.bills, key=lambda x: (x["due"], x["t"], x["id"])):
            if bill["paid"] or bill["due"] > t or bill["t"] > t:
                continue
            if bill["amountMicros"] > self.cashMicros:
                if not bill["missedDue"]:
                    bill["missedDue"] = True
                    self.insolvent = True
                    self.insolventAt = t if self.insolventAt is None else self.insolventAt
                    self.events.append(dict(t=t, type="SIMULATED_UNFUNDED_DUE_OBLIGATION", billId=bill["id"],
                                            amountMicros=bill["amountMicros"], cashAfterMicros=self.cashMicros))
                continue
            self.cashMicros -= bill["amountMicros"]
            bill["paid"] = True
            bill["paidAt"] = t
            self.events.append(dict(t=t, type="SIMULATED_EXPENSE_PAYMENT", billId=bill["id"],
                                    amountMicros=-bill["amountMicros"], cashAfterMicros=self.cashMicros))

    def advance(self, t):
        """Settle all intervening dates in order; collect before bills at the same date."""
        t = self._time(t)
        dates = {t}
        dates.update(max(self.t, x["due"]) for x in self.bills
                     if not x["paid"] and x["due"] <= t and x["t"] <= t)
        dates.update(max(self.t, x["due"]) for x in self.invoices
                     if x["status"] == "pending" and x["due"] <= t and x["t"] <= t)
        for event_t in sorted(dates):
            self.t = event_t
            for invoice in self.invoices:
                if invoice["status"] != "pending" or invoice["due"] > event_t or invoice["t"] > event_t:
                    continue
                if not invoice["pays"]:
                    invoice["status"] = "defaulted"
                    self.events.append(dict(t=event_t, type="SIMULATED_INVOICE_DEFAULT", invoiceId=invoice["id"],
                                            amountMicros=0, cashAfterMicros=self.cashMicros))
                    continue
                invoice["status"] = "collected"
                invoice["collectedAt"] = event_t
                self.cashMicros += invoice["amountMicros"]
                self.collectedMicros += invoice["amountMicros"]
                self.events.append(dict(t=event_t, type="SIMULATED_COLLECTION", invoiceId=invoice["id"],
                                        amountMicros=invoice["amountMicros"], cashAfterMicros=self.cashMicros))
                fee = _scaled(invoice["amountMicros"], invoice["feeFraction"])
                if fee:
                    self.expense(event_t, micros_to_usd(fee), "paymentFees", invoice["id"])
            self._pay_due(event_t)
            self.assert_conservation()
        self.t = t
        return self.funds(t)

    def remedy(self, job_id, t, refund=True, delay=1):
        t = self._time(t)
        delay = _finite(delay, "refund delay")
        invoice = next((x for x in self.invoices if x["jobId"] == str(job_id)), None)
        if invoice is None:
            return None
        if invoice["t"] > t:
            raise ValueError("Cannot remedy an unissued invoice")
        if invoice["status"] == "pending":
            invoice["status"] = "cancelled"
            invoice["cancelledAt"] = t
            self.events.append(dict(t=t, type="SIMULATED_INVOICE_CANCELLATION", invoiceId=invoice["id"],
                                    amountMicros=0, cashAfterMicros=self.cashMicros))
        elif invoice["status"] == "collected" and refund and invoice["refundBillId"] is None:
            bill = self.expense(t, micros_to_usd(invoice["amountMicros"]), "refunds", invoice["id"], due=t + delay)
            invoice["refundBillId"] = bill["id"]
        return invoice

    def funds(self, t=None):
        """Read current commitments at t; does not collect, pay, or advance the clock."""
        t = self.t if t is None else self._time(t)
        bills = [x for x in self.bills if x["t"] <= t]
        accrued = sum(x["amountMicros"] for x in bills)
        paid = sum(x["amountMicros"] for x in bills if x["paid"])
        unpaid = accrued - paid
        receivable = sum(x["amountMicros"] for x in self.invoices if x["t"] <= t and x["status"] == "pending")
        warranty = sum(_scaled(x["amountMicros"], self.warrantyFraction) for x in self.invoices
                       if x["status"] == "collected" and x["warrantyUntil"] >= t and x["refundBillId"] is None)
        tax = _scaled(max(0, self.collectedMicros - accrued), self.taxFraction)
        reserve = self.baseReserveMicros + warranty + tax
        liquid = self.cashMicros - unpaid - reserve
        earned = self.collectedMicros - accrued - reserve
        amounts = dict(cash=self.cashMicros, collected=self.collectedMicros, accrued=accrued, paid=paid,
                       unpaid=unpaid, receivable=receivable, reserve=reserve,
                       availableOperating=max(0, min(liquid, earned)), liquidAfterObligations=liquid,
                       earnedAfterCosts=earned, baseReserve=self.baseReserveMicros, warrantyReserve=warranty,
                       taxReserve=tax)
        result = {key: micros_to_usd(value) for key, value in amounts.items()}
        result.update({key + "Micros": value for key, value in amounts.items()})
        result.update(t=t, seedCountsAsRevenue=False, insolvent=self.insolvent, insolventAt=self.insolventAt)
        return result

    def snapshot(self, t=None):
        row = self.funds(t)
        self.snapshots.append(deepcopy(row))
        return row

    def assert_conservation(self):
        paid = sum(x["amountMicros"] for x in self.bills if x["paid"])
        if self.cashMicros < 0 or self.cashMicros != self.seedMicros + self.collectedMicros - paid:
            raise AssertionError("Finite cash conservation failed")

    def native_projection_input(self, t=None):
        """Input for unchanged JS planMission; cents rounding only at this boundary."""
        f = self.funds(t)
        cents = lambda n: int((Decimal(n) / 10000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        common = dict(missionId="venture-creation-scenario", reference="SIMULATED receipts/costs; actual collections zero",
                      currency="USD", acceptance="accepted" if self.collectedMicros else "rejected",
                      totalCollectedCents=0, priceAssumptionCents=cents(self.collectedMicros),
                      operatingCostsComplete=True, capabilityCostCents=0,
                      reserveCents=cents(f["reserveMicros"]), costBasis="assumed", reinvestmentBps=0)
        return dict(accrual={**common, "totalOperatingCostCents": cents(f["accruedMicros"]), "obligationCents": 0},
                    liquidity={**common, "totalOperatingCostCents": cents(f["paidMicros"]), "obligationCents": cents(f["unpaidMicros"])},
                    expectedEarnedMicros=f["earnedAfterCostsMicros"],
                    expectedLiquidExcludingSeedMicros=f["liquidAfterObligationsMicros"] - self.seedMicros)

    def serialize(self):
        self.assert_conservation()
        return deepcopy(dict(schema="agialpha-venture-simulated-cash/v1", t=self.t,
                             actualCollectionsUsd=0, actualCompleteCostUsd=None, seedUsd=micros_to_usd(self.seedMicros),
                             seedMicros=self.seedMicros, baseReserveMicros=self.baseReserveMicros,
                             taxFraction=self.taxFraction, warrantyFraction=self.warrantyFraction,
                             funds=self.funds(), bills=self.bills, invoices=self.invoices,
                             events=self.events, snapshots=self.snapshots, insolvent=self.insolvent,
                             insolventAt=self.insolventAt, nativeProjectionInput=self.native_projection_input()))


class Capacity:
    """Finite model/GPU lanes with an aggregate fluid token/request quota.

    A quota virtual server serializes batch allotments; model service may overlap
    across lanes after those allotments. This conservative fluid approximation is
    not a claim of a provider's exact sliding-window scheduler. Model precedes GPU.
    """

    def __init__(self, modelLanes, gpuLanes, tpm, rpm):
        for name, value in (("modelLanes", modelLanes), ("gpuLanes", gpuLanes)):
            if isinstance(value, bool) or int(value) != value or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        self.model = [0.0] * int(modelLanes)
        self.gpu = [0.0] * int(gpuLanes)
        self.tpm = _finite(tpm, "tpm", 1e-12)
        self.rpm = _finite(rpm, "rpm", 1e-12)
        self.quotaAvailable = 0.0
        self.revision = 0
        self.committed = []

    def peek(self, start, modelHours, gpuHours, tokens, requests):
        start = _finite(start, "start")
        modelHours = _finite(modelHours, "modelHours")
        gpuHours = _finite(gpuHours, "gpuHours")
        tokens = _finite(tokens, "tokens")
        requests = _finite(requests, "requests")
        if int(tokens) != tokens or int(requests) != requests:
            raise ValueError("Token and request counts must be integers")
        needs_model = bool(modelHours or tokens or requests)
        if needs_model and not self.model:
            raise ValueError("Model work requires at least one model lane")
        if gpuHours and not self.gpu:
            raise ValueError("GPU work requires at least one GPU lane")
        model_lane = min(range(len(self.model)), key=lambda i: (self.model[i], i)) if needs_model else None
        quota_days = max(tokens / self.tpm, requests / self.rpm) / 1440
        model_start = max(start, self.model[model_lane], self.quotaAvailable) if needs_model else start
        model_end = model_start + max(modelHours / 24, quota_days)
        quota_end = model_start + quota_days if needs_model else self.quotaAvailable
        gpu_lane = min(range(len(self.gpu)), key=lambda i: (self.gpu[i], i)) if gpuHours else None
        gpu_start = max(model_end, self.gpu[gpu_lane]) if gpuHours else model_end
        completion = gpu_start + gpuHours / 24
        queue = (model_start - start) + (gpu_start - model_end)
        return dict(revision=self.revision, requestedStart=start, start=model_start,
                    completion=completion, end=completion, modelStart=model_start, modelEnd=model_end,
                    gpuStart=gpu_start, gpuEnd=completion, modelLane=model_lane, gpuLane=gpu_lane,
                    quotaEnd=quota_end, quotaDays=quota_days, queueDays=queue,
                    totalDurationDays=completion - start, serviceDays=max(modelHours / 24, quota_days) + gpuHours / 24,
                    modelHours=modelHours, gpuHours=gpuHours, tokens=int(tokens), requests=int(requests),
                    resourcePolicy="MODEL_THEN_GPU_SHARED_FLUID_QUOTA_NO_HUMAN")

    def commit(self, schedule):
        if schedule.get("revision") != self.revision:
            raise ValueError("Stale capacity preview; peek again before committing")
        expected = self.peek(schedule["requestedStart"], schedule["modelHours"], schedule["gpuHours"], schedule["tokens"], schedule["requests"])
        if schedule != expected:
            raise ValueError("Modified capacity preview")
        if schedule["modelLane"] is not None:
            self.model[schedule["modelLane"]] = schedule["modelEnd"]
            self.quotaAvailable = schedule["quotaEnd"]
        if schedule["gpuLane"] is not None:
            self.gpu[schedule["gpuLane"]] = schedule["gpuEnd"]
        self.committed.append(deepcopy(schedule))
        self.revision += 1
        return deepcopy(schedule)

    def serialize(self):
        return deepcopy(dict(schema="agialpha-venture-resource-adapter/v1", modelLaneAvailableDays=self.model,
                             gpuLaneAvailableDays=self.gpu, quotaAvailableDays=self.quotaAvailable,
                             tpm=self.tpm, rpm=self.rpm, revision=self.revision, schedules=self.committed,
                             actualGpuTrials=0, actualModelRequests=0))
