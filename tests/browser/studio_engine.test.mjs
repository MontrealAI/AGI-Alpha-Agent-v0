// SPDX-License-Identifier: Apache-2.0
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { solve, verify, csv, brief } from "../../docs/assets/studio/engine.mjs";
import { parseCSV, inputCSV } from "../../docs/assets/studio/fields.mjs";
const cases = JSON.parse(
    fs.readFileSync(
        new URL("../../docs/assets/studio/cases.json", import.meta.url),
    ),
);
const scenario = (id) => structuredClone(cases.find((c) => c.id === id).input);

for (const c of cases)
    test(`${c.id}: complete useful output and deterministic dossier replay`, () => {
        const r = solve(c.input);
        assert.ok(r.output.rows.length);
        assert.ok(r.output.checks.length >= 1);
        assert.ok(r.output.limits.length > 40);
        assert.deepEqual(verify(JSON.parse(JSON.stringify(r))), r);
        assert.ok(csv(r).includes(r.output.headers[0]));
        assert.ok(brief(r).includes(c.title));
        const changed = structuredClone(r);
        changed.output.rows[0][0] = "Tampered";
        assert.throws(() => verify(changed), /failed replay/);
    });

test("every preserved demo has exactly one practical destination", () => {
    const catalog = JSON.parse(
        fs.readFileSync(
            new URL(
                "../../alpha_factory_v1/demos/catalog.json",
                import.meta.url,
            ),
        ),
    );
    const mapped = cases.flatMap((c) => c.legacy);
    assert.equal(new Set(mapped).size, mapped.length);
    assert.deepEqual(
        mapped.toSorted(),
        catalog.entries.map((e) => e.id).toSorted(),
    );
});

test("portfolio optimum agrees with independent powerset oracle and dependencies are binding", () => {
    const input = scenario("capital");
    input.parameters = {
        budget: 200,
        staff_days: 12,
        years: 1,
        discount_percent: 0,
        benefit_percent: 100,
    };
    input.datasets.projects = [
        {
            id: "base",
            name: "Foundation",
            cost: 70,
            annual_benefit: 10,
            annual_cost: 0,
            staff_days: 3,
            requires: "",
        },
        {
            id: "dependent",
            name: "Dependent high value",
            cost: 90,
            annual_benefit: 300,
            annual_cost: 10,
            staff_days: 6,
            requires: "base",
        },
        {
            id: "standalone",
            name: "Standalone",
            cost: 150,
            annual_benefit: 240,
            annual_cost: 0,
            staff_days: 10,
            requires: "",
        },
    ];
    let states = [[]];
    for (const item of input.datasets.projects)
        states = states.flatMap((s) => [s, [...s, item]]);
    const feasible = states.filter(
        (s) =>
            s.reduce((n, r) => n + r.cost, 0) <= 200 &&
            s.reduce((n, r) => n + r.staff_days, 0) <= 12 &&
            s.every((r) => !r.requires || s.some((d) => d.id === r.requires)),
    );
    const expected = Math.max(
        ...feasible.map((s) =>
            s.reduce(
                (n, r) => n + r.annual_benefit - r.annual_cost - r.cost,
                0,
            ),
        ),
    );
    const r = solve(input);
    assert.equal(r.output.detail.best.npv / 100, expected);
    assert.deepEqual(r.output.detail.selected, ["base", "dependent"]);
    input.parameters.staff_days = 8;
    assert.equal(solve(input).output.verdict, "HOLD");
    input.datasets.projects[0].requires = "dependent";
    assert.throws(() => solve(input), /cycle/);
    input.datasets.projects[0].requires = "missing";
    assert.throws(() => solve(input), /Unknown/);
});

test("procurement fixed fees and minimum supplier count match exhaustive quantity enumeration", () => {
    const input = scenario("supply");
    input.parameters = {
        demand: 6,
        max_share_percent: 67,
        lead_days: 10,
        min_ontime_percent: 90,
        min_suppliers: 2,
    };
    input.datasets.suppliers = [
        {
            id: "a",
            name: "A",
            unit_cost: 3,
            setup_cost: 20,
            capacity: 6,
            lead_days: 5,
            ontime_percent: 99,
        },
        {
            id: "b",
            name: "B",
            unit_cost: 8,
            setup_cost: 0,
            capacity: 6,
            lead_days: 5,
            ontime_percent: 99,
        },
        {
            id: "c",
            name: "C",
            unit_cost: 6,
            setup_cost: 4,
            capacity: 6,
            lead_days: 5,
            ontime_percent: 99,
        },
    ];
    let min = Infinity;
    for (let a = 0; a <= 4; a++)
        for (let b = 0; b <= 4; b++)
            for (let c = 0; c <= 4; c++)
                if (
                    a + b + c === 6 &&
                    [a, b, c].filter((x) => x > 0).length >= 2
                )
                    min = Math.min(
                        min,
                        3 * a + (a ? 20 : 0) + 8 * b + 6 * c + (c ? 4 : 0),
                    );
    const r = solve(input);
    assert.equal(r.output.detail.cost, min);
    assert.equal(
        r.output.detail.quantities.reduce((a, b) => a + b),
        6,
    );
    input.parameters.max_share_percent = 10;
    assert.equal(solve(input).output.verdict, "HOLD");
    input.parameters.max_share_percent = 67;
    input.parameters.lead_days = 1;
    assert.equal(solve(input).output.verdict, "HOLD");
});

test("energy dispatch matches a hand-derived arbitrage case and conserves terminal inventory", () => {
    const input = scenario("energy");
    input.parameters = {
        capacity_kwh: 2,
        power_kw: 2,
        initial_kwh: 0,
        charge_efficiency_percent: 100,
        degradation_cents: 0,
    };
    input.datasets.hours = [
        {
            id: "cheap",
            load_kwh: 0,
            solar_kwh: 0,
            tariff_cents: 10,
            grid_limit_kwh: 2,
        },
        {
            id: "peak",
            load_kwh: 2,
            solar_kwh: 0,
            tariff_cents: 100,
            grid_limit_kwh: 2,
        },
    ];
    const r = solve(input);
    assert.equal(r.output.detail.cost, 20);
    assert.deepEqual(
        r.output.detail.path.map((x) => x.end),
        [2, 0],
    );
    input.parameters.initial_kwh = 2;
    assert.equal(solve(input).output.detail.cost, 200); // cannot borrow free initial energy
    input.parameters.initial_kwh = 0;
    input.datasets.hours[0].grid_limit_kwh = 0;
    input.datasets.hours[1].grid_limit_kwh = 0;
    assert.equal(solve(input).output.verdict, "HOLD");
});

test("energy solar surplus cannot be counted as paid exports or discharge", () => {
    const input = scenario("energy");
    input.datasets.hours = [
        {
            id: "sun",
            load_kwh: 2,
            solar_kwh: 20,
            tariff_cents: 100,
            grid_limit_kwh: 0,
        },
    ];
    const r = solve(input);
    assert.equal(r.output.detail.cost, 0);
    assert.equal(r.output.detail.path[0].discharge, 0);
    assert.ok(r.output.detail.path[0].curtail >= 0);
});

test("delivery plan respects precedence and single-resource capacity", () => {
    const input = scenario("delivery"),
        r = solve(input),
        ops = r.output.detail.operations;
    assert.equal(r.output.detail.makespan, 76);
    assert.equal(r.output.detail.tardiness, 20);
    assert.equal(r.output.detail.baseline_makespan, 90);
    assert.equal(r.output.verdict, "HOLD");
    for (const [i, a] of ops.entries())
        for (const b of ops.slice(i + 1))
            if (a.machine === b.machine)
                assert.ok(a.end <= b.start || b.end <= a.start);
    for (const j of new Set(ops.map((r) => r.job))) {
        const seq = ops
            .filter((r) => r.job === j)
            .sort((a, b) => a.sequence - b.sequence);
        for (let i = 1; i < seq.length; i++)
            assert.ok(seq[i].start >= seq[i - 1].end);
    }
    input.datasets.operations[1].due++;
    assert.throws(() => solve(input), /same due/);
});

test("inventory selection and held-out predictions cannot see the holdout labels", () => {
    const input = scenario("inventory"),
        a = solve(input).output.detail;
    for (const row of input.datasets.demand.slice(-input.parameters.holdout))
        row.units += 1000;
    const b = solve(input).output.detail;
    assert.equal(a.selected, b.selected);
    assert.deepEqual(a.training_scores, b.training_scores);
    assert.deepEqual(a.holdout_predictions, b.holdout_predictions);
    assert.notEqual(a.holdout_mae, b.holdout_mae);
    assert.equal(
        a.reorder,
        Math.max(
            0,
            Math.ceil(a.lead_demand + input.parameters.safety_units) -
                input.parameters.on_hand -
                input.parameters.on_order,
        ),
    );
    input.parameters.on_hand = 100000;
    assert.equal(solve(input).output.detail.reorder, 0);
});

test("proof ledger blocks missing, unbound, stale and failed evidence independently", () => {
    const input = scenario("proof");
    let r = solve(input).output;
    assert.equal(r.jobs.length, 5);
    assert.equal(r.detail.promotion, "HOLD");
    input.datasets.claims[0].quote = "Correct outputs: 111.";
    r = solve(input).output;
    assert.equal(r.detail.decisions[0].state, "UNBOUND");
    input.datasets.claims[0].quote = "Correct outputs: 1116.";
    input.datasets.claims[0].observed = 116;
    assert.equal(solve(input).output.detail.decisions[0].state, "UNBOUND");
    input.datasets.claims[0].observed = 1116;
    input.datasets.claims[0].age_days = 31;
    assert.equal(solve(input).output.detail.decisions[0].state, "STALE");
    input.datasets.claims = [scenario("proof").datasets.claims[0]];
    r = solve(input).output;
    assert.equal(r.verdict, "REVIEW");
    assert.equal(r.detail.promotion, "HOLD");
});

test("second-order candidate selection cannot be chosen on test outcomes", () => {
    const input = scenario("agency"),
        a = solve(input).output.detail;
    input.datasets.cases
        .filter((r) => r.partition === "test")
        .forEach((r) => {
            r.pipeline_a = 1 - r.truth;
            r.pipeline_b = r.truth;
        });
    const b = solve(input).output.detail;
    assert.equal(a.selected, b.selected);
    assert.deepEqual(a.training, b.training);
    assert.ok(b.saving < 0);
    assert.equal(solve(input).output.verdict, "HOLD");
    input.parameters.min_test_cases = 100;
    assert.equal(solve(input).output.detail.minimum_met, false);
});

test("schema validation rejects unknown fields, non-finite values and duplicate IDs", () => {
    for (const mutate of [
        (x) => (x.extra = true),
        (x) => (x.parameters.budget = NaN),
        (x) => (x.parameters.budget = "1"),
        (x) => (x.datasets.projects[1].id = x.datasets.projects[0].id),
        (x) => (x.datasets.projects[0].cost = -1),
        (x) => (x.kind = "constructor"),
    ]) {
        const input = scenario("capital");
        mutate(input);
        assert.throws(() => solve(input));
    }
});

test("CSV imports preserve quoted newlines and reject malformed headers, rows and empty numbers", () => {
    const records = [
        { id: "one", title: "A, B", text: 'Line one\n"Line two"' },
    ];
    assert.deepEqual(
        parseCSV(inputCSV(records), Object.keys(records[0])),
        records,
    );
    assert.throws(
        () => parseCSV("id,units\na,\n", ["id", "units"]),
        /requires a number/,
    );
    assert.throws(
        () => parseCSV("id,units\na,2,3", ["id", "units"]),
        /number of fields/,
    );
    assert.throws(
        () => parseCSV("wrong,units\na,2", ["id", "units"]),
        /header/,
    );
    assert.throws(
        () => parseCSV('id,units\na,"2', ["id", "units"]),
        /Unclosed/,
    );
});

test("CSV result downloads neutralize spreadsheet formulas while keeping numeric negatives", () => {
    const r = solve(scenario("capital"));
    r.output.rows = [['=HYPERLINK("x")', " +1", "@x", -5]];
    const out = csv(r);
    assert.ok(out.includes("'=HYPERLINK"));
    assert.ok(out.includes("' +1"));
    assert.ok(out.includes("'@x"));
    assert.ok(out.includes('"-5"'));
});

test("deadline-feasible schedule wins over a faster late schedule", () => {
    const input = scenario("delivery");
    input.parameters.deadline = 30;
    input.datasets.operations = [
        { id: "b1", job: "B", resource: "M1", duration: 2, due: 30 },
        { id: "b2", job: "B", resource: "M2", duration: 3, due: 30 },
        { id: "a1", job: "A", resource: "M1", duration: 10, due: 20 },
        { id: "a2", job: "A", resource: "M2", duration: 10, due: 20 },
    ];
    const r = solve(input).output;
    assert.equal(r.verdict, "PLAN");
    assert.deepEqual(r.detail.order, ["A", "B"]);
    assert.equal(r.detail.makespan, 23);
    assert.equal(r.detail.tardiness, 0);
    assert.equal(r.detail.feasible_orders, 1);
    // B first finishes everything sooner, but A misses its hour-20 commitment.
    assert.equal(r.detail.baseline_makespan, 22);
    assert.equal(r.detail.baseline_tardiness, 2);
    input.parameters.deadline = 22;
    assert.equal(solve(input).output.verdict, "HOLD");
});

test("schedule objective agrees with an independently enumerated policy oracle", () => {
    const input = scenario("delivery");
    input.datasets.operations = [
        { id: "a1", job: "A", resource: "M1", duration: 5, due: 9 },
        { id: "a2", job: "A", resource: "M2", duration: 4, due: 9 },
        { id: "b1", job: "B", resource: "M2", duration: 2, due: 5 },
        { id: "b2", job: "B", resource: "M1", duration: 3, due: 5 },
        { id: "c1", job: "C", resource: "M1", duration: 1, due: 10 },
    ];
    input.parameters.deadline = 13;
    const scores = [];
    for (const order of ["ABC", "ACB", "BAC", "BCA", "CAB", "CBA"]) {
        const machines = {},
            ends = {};
        for (const id of order)
            for (const op of input.datasets.operations.filter(
                (r) => r.job === id,
            )) {
                ends[id] =
                    Math.max(ends[id] || 0, machines[op.resource] || 0) +
                    op.duration;
                machines[op.resource] = ends[id];
            }
        const end = Math.max(...Object.values(ends));
        const late = Object.keys(ends).reduce(
            (n, id) =>
                n +
                Math.max(
                    0,
                    ends[id] -
                        input.datasets.operations.find((r) => r.job === id).due,
                ),
            0,
        );
        scores.push([late + Math.max(0, end - 13), end]);
    }
    scores.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const actual = solve(input).output.detail;
    assert.deepEqual([actual.violation_hours, actual.makespan], scores[0]);
});

test("service staffing accounts for productive time, backlog, caps and per-shift costs", () => {
    const input = scenario("service");
    input.datasets.demand = Array.from({ length: 21 }, (_, i) => ({
        id: `d${i}`,
        units: 30,
    }));
    input.datasets.coverage = [
        {
            id: "day1",
            available_staff: 1,
            extra_limit: 1,
            extra_shift_cost: 120,
        },
        {
            id: "day2",
            available_staff: 1,
            extra_limit: 0,
            extra_shift_cost: 150,
        },
    ];
    input.parameters = {
        holdout: 7,
        season: 7,
        handle_minutes: 10,
        shift_hours: 8,
        shrinkage_percent: 50,
        occupancy_percent: 100,
        reserve_percent: 0,
        backlog: 18,
        clear_backlog_periods: 2,
    };
    const r = solve(input).output,
        d = r.detail;
    // Each person can handle 24 cases. Day 1 needs 39 cases: add one staff, clear all 18 old cases.
    // Day 2 has only 24 slots for 30 new cases: six cases remain; day-1 spare time cannot transfer.
    assert.deepEqual(
        d.shifts.map((r) => [r.extra, r.capacity, r.end_backlog]),
        [
            [1, 48, 0],
            [0, 24, 6],
        ],
    );
    assert.equal(d.productive_minutes, 240);
    assert.equal(d.cost, 120);
    assert.equal(d.shortfall_periods, 1);
    assert.equal(r.verdict, "HOLD");
    input.datasets.coverage[1].extra_limit = 1;
    const repaired = solve(input).output;
    assert.equal(repaired.verdict, "PLAN");
    assert.equal(repaired.detail.cost, 270);
    assert.equal(repaired.detail.ending_backlog, 0);
});

test("service reserve shocks expose coverage shortfalls instead of suggesting cheaper success", () => {
    const r = solve(scenario("service")).output;
    assert.equal(r.detail.cost, 7920);
    assert.equal(r.detail.ending_backlog, 0);
    assert.equal(r.detail.sensitivity.at(-1).feasible, false);
    assert.match(r.detail.sensitivity.at(-1).note, /shifts below target/);
});

test("service forecast selection remains independent of holdout labels", () => {
    const input = scenario("service"),
        before = solve(input).output.detail;
    input.datasets.demand
        .slice(-input.parameters.holdout)
        .forEach((r) => (r.units += 1000));
    const after = solve(input).output.detail;
    assert.deepEqual(after.training_scores, before.training_scores);
    assert.deepEqual(after.holdout_predictions, before.holdout_predictions);
    assert.equal(solve(input).output.verdict, "HOLD");
});

test("repeated dependency edges have bounded traversal and preserve closure", () => {
    const input = scenario("capital");
    input.datasets.projects = Array.from({ length: 18 }, (_, i) => ({
        id: `p${i}`,
        name: `Project ${i}`,
        cost: 1,
        annual_benefit: 2,
        annual_cost: 0,
        staff_days: 1,
        requires: i
            ? Array(15)
                  .fill(`p${i - 1}`)
                  .join(",")
            : "",
    }));
    input.parameters = {
        budget: 18,
        staff_days: 18,
        years: 1,
        discount_percent: 0,
        benefit_percent: 100,
    };
    assert.equal(solve(input).output.detail.selected.length, 18);
    input.datasets.projects[0].requires = "p17";
    assert.throws(() => solve(input), /cycle/);
});

test("evidence numeric binding cannot confuse thousands, exponents or partial tokens", () => {
    const input = scenario("proof");
    const claim = input.datasets.claims[0];
    input.datasets.claims = [claim];
    claim.threshold = -10000;
    claim.direction = ">=";
    for (const [quote, observed, state] of [
        ["Value: 1,000.", 1000, "MET"],
        ["Value: 1,000.", 1, "UNBOUND"],
        ["Value: 1,000.", 0, "UNBOUND"],
        ["Value: 1e3.", 1000, "MET"],
        ["Value: 1e3.", 3, "UNBOUND"],
        ["Value: -12.5.", -12.5, "MET"],
        ["Value: −12.", 12, "UNBOUND"],
        ["Value: x123.", 123, "UNBOUND"],
        ["Value: 1,23.", 23, "UNBOUND"],
    ]) {
        claim.quote = quote;
        claim.observed = observed;
        input.datasets.sources.find((r) => r.id === claim.source_id).text =
            quote;
        assert.equal(
            solve(input).output.detail.decisions[0].state,
            state,
            quote + " / " + observed,
        );
    }
});

test("report version is bound and legacy dossiers replay with the archived policy", async () => {
    const legacy = await import("../../docs/assets/studio/engine-1.9.mjs");
    const old = legacy.solve(scenario("delivery"));
    assert.equal(old.output.detail.makespan, 66);
    assert.deepEqual(verify(old), old);
    const current = solve(old.input);
    assert.equal(current.calculation_version, "1.10.0");
    assert.equal(current.output.detail.makespan, 76);
    current.calculation_version = "unavailable";
    assert.throws(() => verify(current), /version/);
    old.output.detail.makespan = 76;
    assert.throws(() => verify(old), /failed replay/);
});

test("identifiers must be strings and scenario limits count UTF-8 bytes", () => {
    const input = scenario("capital");
    input.datasets.projects[0].id = 123;
    assert.throws(() => solve(input), /IDs/);
    const evidence = scenario("proof");
    evidence.datasets.sources = Array.from({ length: 8 }, (_, i) => ({
        id: `s${i}`,
        title: "Source",
        text: "漢".repeat(12000),
    }));
    assert.ok(JSON.stringify(evidence).length < 256000);
    assert.throws(() => solve(evidence), /256 KB/);
});

test("an actual previously exported service dossier retains its original inventory policy", () => {
    const archived = JSON.parse(
        fs.readFileSync(
            new URL(
                "../fixtures/decision-studio/service-1.9.json",
                import.meta.url,
            ),
        ),
    );
    assert.equal(archived.input.kind, "inventory");
    assert.deepEqual(verify(archived), archived);
    assert.equal(archived.output.detail.reorder, 1194);
});
