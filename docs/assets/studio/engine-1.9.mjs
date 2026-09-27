// SPDX-License-Identifier: Apache-2.0
// Decision support over explicit inputs. No network, model, wallet or external execution.
import { runMission } from "./mission-engine-1.9.mjs";

export const SCHEMA = "agialpha.decision.v1";
const fail = (message) => {
    throw new Error(message);
};
const sum = (xs) => xs.reduce((a, b) => a + b, 0);
const clone = (x) => structuredClone(x);
const number = (x, name, low = 0, high = 1e9, whole = true) => {
    if (
        typeof x !== "number" ||
        !Number.isFinite(x) ||
        x < low ||
        x > high ||
        (whole && !Number.isInteger(x))
    )
        fail(
            `${name}: enter ${whole ? "a whole number" : "a number"} from ${low} to ${high}.`,
        );
    return x;
};
const text = (x, name, max = 2000, empty = false) => {
    if (typeof x !== "string" || (!empty && !x.trim()) || x.length > max)
        fail(`${name}: text is missing or too long (limit ${max}).`);
    return x;
};
const exactKeys = (x, keys, name) => {
    if (
        !x ||
        typeof x !== "object" ||
        Array.isArray(x) ||
        Object.keys(x).some((k) => !keys.includes(k)) ||
        keys.some((k) => !(k in x))
    )
        fail(`${name}: fields do not match the documented schema.`);
};
const rows = (x, name, keys, max = 100) => {
    if (!Array.isArray(x) || x.length < 1 || x.length > max)
        fail(`${name}: supply 1–${max} rows.`);
    x.forEach((r) => exactKeys(r, keys, name));
    if (keys.includes("id")) {
        x.forEach((r) => {
            if (!/^[A-Za-z0-9_-]{1,64}$/.test(r.id))
                fail(
                    `${name}: IDs need 1–64 letters, digits, hyphens or underscores.`,
                );
        });
        if (new Set(x.map((r) => r.id)).size !== x.length)
            fail(`${name}: duplicate IDs.`);
    }
    return x;
};
const params = (p, rules) => {
    exactKeys(p, Object.keys(rules), "Parameters");
    for (const [key, rule] of Object.entries(rules))
        number(p[key], key, ...rule);
};
const result = (
    method,
    verdict,
    summary,
    metrics,
    headers,
    data,
    detail,
    checks,
    limits,
    jobs = [],
) => ({
    method,
    verdict,
    summary,
    metrics,
    headers,
    rows: data,
    detail,
    checks,
    limits,
    jobs,
});
const job = (id, objective, acceptance, owner = "Independent reviewer") => ({
    id,
    objective,
    acceptance,
    owner,
    state: "OPEN",
    execution: "Unassigned plan; no external job has been submitted",
});

function portfolio(input) {
    const { parameters: p, datasets: d } = input;
    params(p, {
        budget: [1, 1e9],
        staff_days: [1, 100000],
        years: [1, 10],
        discount_percent: [0, 50],
        benefit_percent: [0, 200],
    });
    exactKeys(d, ["projects"], "Datasets");
    const items = rows(
        d.projects,
        "Projects",
        [
            "id",
            "name",
            "cost",
            "annual_benefit",
            "annual_cost",
            "staff_days",
            "requires",
        ],
        18,
    );
    items.forEach((r) => {
        text(r.name, "Project name", 120);
        text(r.requires, "Dependencies", 120, true);
        for (const k of ["cost", "annual_benefit", "annual_cost"])
            number(r[k], k, 0, 1e8);
        number(r.staff_days, "staff_days", 0, 100000);
    });
    const ids = new Map(items.map((r, i) => [r.id, i]));
    const deps = items.map((r) =>
        r.requires
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
    );
    deps.forEach((ds, i) =>
        ds.forEach((id) => {
            if (!ids.has(id) || id === items[i].id)
                fail(`Unknown or self dependency: ${id}.`);
        }),
    );
    const closures = new Map(), visiting = new Set();
    const closure = (i) => {
        if (closures.has(i)) return closures.get(i);
        if (visiting.has(i)) fail("Project dependencies contain a cycle.");
        visiting.add(i);
        const mask = (1 << i) | deps[i].reduce((m, id) => m | closure(ids.get(id)), 0);
        visiting.delete(i);
        closures.set(i, mask);
        return mask;
    };
    items.forEach((_, i) => closure(i));
    const annuity = sum(
        Array.from(
            { length: p.years },
            (_, i) => 1 / (1 + p.discount_percent / 100) ** (i + 1),
        ),
    );
    const evaluate = (budget, scale) => {
        const values = items.map((r) =>
            Math.round(
                (((r.annual_benefit * scale) / 100 - r.annual_cost) * annuity -
                    r.cost) *
                    100,
            ),
        );
        let best = { mask: 0, cost: 0, days: 0, npv: 0 },
            baseline = null,
            feasible = 0;
        for (let mask = 0; mask < 2 ** items.length; mask++) {
            let cost = 0,
                days = 0,
                npv = 0,
                valid = true;
            for (let i = 0; i < items.length; i++)
                if (mask & (1 << i)) {
                    cost += items[i].cost;
                    days += items[i].staff_days;
                    npv += values[i];
                    if (deps[i].some((id) => !(mask & (1 << ids.get(id)))))
                        valid = false;
                }
            if (!valid || cost > budget || days > p.staff_days) continue;
            feasible++;
            if (npv > best.npv || (npv === best.npv && cost < best.cost))
                best = { mask, cost, days, npv };
        }
        // A transparent dependency-aware input-order baseline, including prerequisite closure.
        let mask = 0;
        for (let i = 0; i < items.length; i++) {
            const trial = mask | closure(i),
                selected = items.filter((_, j) => trial & (1 << j));
            if (
                sum(selected.map((r) => r.cost)) <= budget &&
                sum(selected.map((r) => r.staff_days)) <= p.staff_days
            )
                mask = trial;
        }
        baseline = {
            mask,
            cost: sum(
                items.filter((_, i) => mask & (1 << i)).map((r) => r.cost),
            ),
            npv: sum(values.filter((_, i) => mask & (1 << i))),
        };
        return { best, baseline, values, feasible };
    };
    const solved = evaluate(p.budget, p.benefit_percent),
        { best, baseline, values } = solved;
    const selected = items.filter((_, i) => best.mask & (1 << i));
    if (
        sum(selected.map((r) => r.cost)) > p.budget ||
        sum(selected.map((r) => r.staff_days)) > p.staff_days
    )
        fail("Portfolio constraint check failed.");
    const sensitivity = [-20, 0, 20].map((change) => {
        const scaled = Math.max(0, p.benefit_percent + change),
            x = evaluate(p.budget, scaled).best;
        return {
            scenario: `Benefits at ${scaled}%`,
            value: x.npv / 100,
            selected: items
                .filter((_, i) => x.mask & (1 << i))
                .map((r) => r.id),
        };
    });
    return result(
        "Exact dependency-constrained subset optimization",
        selected.length ? "PLAN" : "HOLD",
        selected.length
            ? `Fund ${selected.length} projects. The selected portfolio uses ${best.days} staff days and leaves ${p.budget - best.cost} USD unallocated.`
            : "No positive-NPV feasible portfolio. Retain the budget.",
        [
            ["Modeled NPV", best.npv / 100, "USD"],
            ["Capital committed", best.cost, "USD"],
            ["NPV vs input order", (best.npv - baseline.npv) / 100, "USD"],
            ["Feasible portfolios", solved.feasible, ""],
        ],
        [
            "Project",
            "Decision",
            "Capital (USD)",
            "NPV (USD)",
            "Staff days",
            "Prerequisites",
        ],
        items.map((r, i) => [
            r.name,
            best.mask & (1 << i) ? "Fund" : "Defer",
            r.cost,
            values[i] / 100,
            r.staff_days,
            r.requires || "None",
        ]),
        {
            selected: selected.map((r) => r.id),
            best,
            baseline,
            sensitivity,
            annuity,
            examined: 2 ** items.length,
        },
        [
            "Every subset compared; prerequisite closure and two capacity constraints checked.",
            "Discounted annual cash flows calculated, then rounded to cents per project.",
            "Benefit shocks re-optimize the portfolio; they are scenarios, not probabilities.",
        ],
        "All cash flows are supplied assumptions. No tax, inflation, financing, residual value or shared-benefit interactions are modeled. NPV is a scenario calculation, not realized wealth.",
        selected.map((r) =>
            job(
                `VERIFY-${r.id}`,
                `Validate ${r.name} economics before commitment`,
                `Obtain attributable evidence for ${r.annual_benefit} USD annual benefit, ${r.annual_cost} USD operating cost and ${r.staff_days} staff days.`,
            ),
        ),
    );
}

function procurement(input, stress = true) {
    const { parameters: p, datasets: d } = input;
    params(p, {
        demand: [1, 80],
        max_share_percent: [1, 100],
        lead_days: [1, 365],
        min_ontime_percent: [0, 100],
        min_suppliers: [1, 8],
    });
    exactKeys(d, ["suppliers"], "Datasets");
    const suppliers = rows(
        d.suppliers,
        "Suppliers",
        [
            "id",
            "name",
            "unit_cost",
            "setup_cost",
            "capacity",
            "lead_days",
            "ontime_percent",
        ],
        8,
    );
    suppliers.forEach((r) => {
        text(r.name, "Supplier name", 120);
        params(
            Object.fromEntries(
                Object.entries(r).filter(([k]) => !["id", "name"].includes(k)),
            ),
            {
                unit_cost: [1, 1e6],
                setup_cost: [0, 1e6],
                capacity: [0, 80],
                lead_days: [1, 365],
                ontime_percent: [0, 100],
            },
        );
    });
    const caps = suppliers.map((r) =>
        r.lead_days <= p.lead_days && r.ontime_percent >= p.min_ontime_percent
            ? Math.min(
                  r.capacity,
                  Math.floor((p.demand * p.max_share_percent) / 100),
              )
            : 0,
    );
    let states = new Map([["0,0", { cost: 0, quantities: [] }]]);
    for (let i = 0; i < suppliers.length; i++) {
        const next = new Map();
        for (const [key, state] of states) {
            const [volume, count] = key.split(",").map(Number);
            for (let q = 0; q <= Math.min(caps[i], p.demand - volume); q++) {
                const k = `${volume + q},${count + (q > 0 ? 1 : 0)}`,
                    cost =
                        state.cost +
                        q * suppliers[i].unit_cost +
                        (q ? suppliers[i].setup_cost : 0);
                if (!next.has(k) || cost < next.get(k).cost)
                    next.set(k, { cost, quantities: [...state.quantities, q] });
            }
        }
        states = next;
    }
    let best = null;
    for (const [key, state] of states) {
        const [volume, count] = key.split(",").map(Number);
        if (
            volume === p.demand &&
            count >= p.min_suppliers &&
            (!best || state.cost < best.cost)
        )
            best = state;
    }
    if (!best)
        return result(
            "Exact discrete procurement dynamic program",
            "HOLD",
            "No order meets volume, supplier count, capacity, lead-time and concentration constraints.",
            [
                ["Qualified capacity", sum(caps), "batches"],
                ["Required volume", p.demand, "batches"],
            ],
            ["Supplier", "Qualified capacity", "Reason"],
            suppliers.map((r, i) => [
                r.name,
                caps[i],
                caps[i]
                    ? "Available"
                    : "Lead time, reliability or capacity limit",
            ]),
            { feasible: false },
            ["Infeasibility retained; constraints were not relaxed."],
            "One batch is the operator-defined purchasing unit. Quoted costs and reliability are unverified inputs.",
            [
                job(
                    "SOURCE-CAPACITY",
                    "Resolve the supply shortfall",
                    "Obtain a qualified quote or explicitly revise demand/constraints.",
                ),
            ],
        );
    if (
        sum(best.quantities) !== p.demand ||
        best.quantities.some((q, i) => q > caps[i]) ||
        best.quantities.filter((q) => q > 0).length < p.min_suppliers
    )
        fail("Procurement constraint check failed.");
    const cost = sum(
        best.quantities.map(
            (q, i) =>
                q * suppliers[i].unit_cost + (q ? suppliers[i].setup_cost : 0),
        ),
    );
    if (cost !== best.cost) fail("Procurement invoice reconciliation failed.");
    const outages = stress
        ? suppliers.flatMap((r, i) => {
              if (!best.quantities[i]) return [];
              const trial = clone(input);
              trial.datasets.suppliers[i].capacity = 0;
              const x = procurement(trial, false);
              return [
                  {
                      scenario: `${r.name} unavailable`,
                      value: x.detail.feasible ? x.detail.cost : null,
                      feasible: x.detail.feasible,
                  },
              ];
          })
        : [];
    return result(
        "Exact discrete procurement dynamic program",
        "PLAN",
        `Allocate ${p.demand} batches across ${best.quantities.filter((q) => q > 0).length} suppliers. ${outages.filter((x) => !x.feasible).length} tested supplier outages cannot be covered with the stated capacities.`,
        [
            ["Landed order cost", best.cost, "USD"],
            ["Blended batch cost", best.cost / p.demand, "USD"],
            [
                "Largest supplier",
                (Math.max(...best.quantities) / p.demand) * 100,
                "%",
            ],
            [
                "Outage shortfalls",
                outages.filter((x) => !x.feasible).length,
                "",
            ],
        ],
        [
            "Supplier",
            "Batches",
            "Unit cost (USD)",
            "Setup (USD)",
            "Line total (USD)",
            "Lead days",
        ],
        suppliers.map((r, i) => [
            r.name,
            best.quantities[i],
            r.unit_cost,
            best.quantities[i] ? r.setup_cost : 0,
            best.quantities[i] * r.unit_cost +
                (best.quantities[i] ? r.setup_cost : 0),
            r.lead_days,
        ]),
        {
            feasible: true,
            cost: best.cost,
            quantities: best.quantities,
            sensitivity: outages,
        },
        [
            "All feasible discrete allocations searched by dynamic programming.",
            "Invoice totals independently recomputed.",
            "Selected supplier outages re-solved under the same constraints.",
        ],
        "Quoted reliability is a qualification threshold, not a probabilistic guarantee. Outage reallocation assumes unused quoted capacity remains available. No purchase orders are sent.",
        [
            job(
                "CONFIRM-QUOTES",
                "Confirm the proposed supplier split",
                "Obtain current signed quotes, available capacity, lead times and purchasing approval.",
            ),
        ],
    );
}

function schedule(input) {
    const { parameters: p, datasets: d } = input;
    params(p, { deadline: [1, 100000] });
    exactKeys(d, ["operations"], "Datasets");
    const operations = rows(
        d.operations,
        "Operations",
        ["id", "job", "resource", "duration", "due"],
        84,
    );
    const jobs = [];
    operations.forEach((r) => {
        text(r.job, "Job", 64);
        text(r.resource, "Resource", 64);
        number(r.duration, "Duration", 1, 100000);
        number(r.due, "Due", 1, 100000);
        let j = jobs.find((x) => x.id === r.job);
        if (!j) {
            j = { id: r.job, due: r.due, operations: [] };
            jobs.push(j);
        }
        if (j.due !== r.due)
            fail(`All ${r.job} operations must share the same due time.`);
        j.operations.push({ machine: r.resource, duration: r.duration });
    });
    const r = runMission({
            goal: input.title,
            work: { kind: "schedule", jobs, unit: "hours" },
        }),
        e = r.evidence;
    const deadlineMet = e.makespan <= p.deadline;
    return result(
        r.method,
        deadlineMet && e.tardiness === 0 ? "PLAN" : "HOLD",
        `${r.summary} ${deadlineMet ? "Delivery window met." : "Delivery window exceeded."} Total lateness: ${e.tardiness} hours.`,
        [...r.metrics.map(([k, v]) => [k, v, "hours"])],
        r.headers,
        r.rows,
        { ...e, deadline: p.deadline },
        r.checks,
        r.limits +
            " Hours are elapsed work hours from a common zero; shifts, breaks and setup changes must be included in durations.",
        [
            job(
                "RELEASE-SCHEDULE",
                "Authorize the resource reservation",
                "Confirm durations, resource availability, shift calendars and all due times before issuing the schedule.",
            ),
        ],
    );
}

function inventory(input) {
    const { parameters: p, datasets: d } = input;
    params(p, {
        holdout: [2, 100],
        season: [1, 100],
        lead_periods: [1, 30],
        on_hand: [0, 1e7],
        on_order: [0, 1e7],
        safety_units: [0, 1e7],
        unit_cost: [0, 1e6],
    });
    exactKeys(d, ["demand"], "Datasets");
    const series = rows(d.demand, "Demand", ["id", "units"], 1000);
    series.forEach((r) => number(r.units, "Observed units", 0, 1e7));
    const r = runMission({
            goal: input.title,
            work: {
                kind: "forecast",
                observations: series.map((x) => x.units),
                holdout: p.holdout,
                season: p.season,
                horizon: p.lead_periods,
                unit: "units per period",
            },
        }),
        e = r.evidence;
    const demand = sum(e.future.map((x) => Math.max(0, x))),
        target = Math.ceil(demand + p.safety_units),
        reorder = Math.max(0, target - p.on_hand - p.on_order);
    return result(
        r.method,
        e.holdout_mae <= e.baseline_mae ? "PLAN" : "HOLD",
        `Order-up-to target: ${target} units. Proposed replenishment: ${reorder} units after existing stock and open orders. ${e.holdout_mae > e.baseline_mae ? "The selected model underperformed last-value on holdout; review before use." : ""}`,
        [
            ["Proposed order", reorder, "units"],
            ["Order cost", reorder * p.unit_cost, "USD"],
            ["Holdout MAE", e.holdout_mae, "units"],
            ["Baseline MAE", e.baseline_mae, "units"],
        ],
        r.headers,
        r.rows,
        {
            ...e,
            target,
            reorder,
            cost: reorder * p.unit_cost,
            lead_demand: demand,
            sensitivity: [-20, 0, 20].map((x) => ({
                scenario: `Lead demand ${x >= 0 ? "+" : ""}${x}%`,
                value: Math.max(
                    0,
                    Math.ceil(demand * (1 + x / 100) + p.safety_units) -
                        p.on_hand -
                        p.on_order,
                ),
            })),
        },
        [
            ...r.checks,
            "Negative future demand is clamped to zero for inventory calculations only.",
        ],
        r.limits +
            " Safety stock is an explicit operator input, not a statistically calibrated service-level guarantee. Stockouts, promotions and changing lead times can invalidate this plan.",
        [
            job(
                "VALIDATE-DEMAND",
                "Validate demand and inventory position",
                "Reconcile observations, stock on hand, open orders and supplier lead time; explain holdout error before replenishment.",
            ),
        ],
    );
}

function energy(input) {
    const { parameters: p, datasets: d } = input;
    params(p, {
        capacity_kwh: [1, 100],
        power_kw: [1, 100],
        initial_kwh: [0, 100],
        charge_efficiency_percent: [50, 100],
        degradation_cents: [0, 1000],
    });
    if (p.initial_kwh > p.capacity_kwh)
        fail("Initial charge exceeds battery capacity.");
    exactKeys(d, ["hours"], "Datasets");
    const hours = rows(
        d.hours,
        "Hours",
        ["id", "load_kwh", "solar_kwh", "tariff_cents", "grid_limit_kwh"],
        48,
    );
    hours.forEach((r) => {
        for (const k of ["load_kwh", "solar_kwh", "grid_limit_kwh"])
            number(r[k], k, 0, 1000);
        number(r.tariff_cents, "tariff_cents", 0, 10000);
    });
    let states = new Map([[p.initial_kwh, { cost: 0, path: [] }]]);
    for (const r of hours) {
        const next = new Map();
        for (const [soc, state] of states)
            for (
                let delta = -Math.min(soc, p.power_kw);
                delta <= Math.min(p.capacity_kwh - soc, p.power_kw);
                delta++
            ) {
                const charge =
                        delta > 0
                            ? Math.ceil(
                                  (delta * 100) / p.charge_efficiency_percent,
                              )
                            : 0,
                    discharge = Math.max(0, -delta);
                if (
                    charge > p.power_kw ||
                    discharge > Math.max(0, r.load_kwh - r.solar_kwh)
                )
                    continue;
                const grid = Math.max(
                    0,
                    r.load_kwh + charge - r.solar_kwh - discharge,
                );
                if (grid > r.grid_limit_kwh) continue;
                const curtail = Math.max(
                        0,
                        r.solar_kwh + discharge - r.load_kwh - charge,
                    ),
                    cost =
                        state.cost +
                        grid * r.tariff_cents +
                        discharge * p.degradation_cents;
                const k = soc + delta;
                if (!next.has(k) || cost < next.get(k).cost)
                    next.set(k, {
                        cost,
                        path: [
                            ...state.path,
                            {
                                hour: r.id,
                                start: soc,
                                end: k,
                                charge,
                                discharge,
                                grid,
                                curtail,
                                cost:
                                    grid * r.tariff_cents +
                                    discharge * p.degradation_cents,
                            },
                        ],
                    });
            }
        states = next;
    }
    let best = null;
    for (const [soc, state] of states)
        if (soc >= p.initial_kwh && (!best || state.cost < best.cost))
            best = state;
    const baselineCost = sum(
        hours.map(
            (r) => Math.max(0, r.load_kwh - r.solar_kwh) * r.tariff_cents,
        ),
    );
    const baselineFeasible = hours.every(
        (r) => Math.max(0, r.load_kwh - r.solar_kwh) <= r.grid_limit_kwh,
    );
    if (!best)
        return result(
            "Discrete battery dispatch dynamic program",
            "HOLD",
            "No dispatch can serve all load and restore the starting charge under these grid and battery limits.",
            [["Intervals", hours.length, "hours"]],
            ["Hour", "Load", "Solar", "Grid limit"],
            hours.map((r) => [r.id, r.load_kwh, r.solar_kwh, r.grid_limit_kwh]),
            { feasible: false },
            ["Infeasible schedules are rejected; unmet load is never hidden."],
            "Hourly model, integer kWh. No equipment is controlled.",
            [
                job(
                    "ENERGY-SHORTFALL",
                    "Resolve unmet load",
                    "Provide additional generation, storage or an explicitly revised critical-load schedule.",
                ),
            ],
        );
    best.path.forEach((r, i) => {
        const h = hours[i];
        if (
            r.grid + h.solar_kwh + r.discharge !==
                h.load_kwh + r.charge + r.curtail ||
            r.grid > h.grid_limit_kwh ||
            r.start !== (i ? best.path[i - 1].end : p.initial_kwh)
        )
            fail("Independent energy balance check failed.");
    });
    if (
        sum(best.path.map((r) => r.cost)) !== best.cost ||
        best.path.at(-1).end < p.initial_kwh
    )
        fail("Energy cost or terminal charge check failed.");
    return result(
        "Exact dispatch on a 1 kWh state grid",
        "PLAN",
        `Serve every interval and finish with ${best.path.at(-1).end} kWh. ${baselineFeasible ? "Compare the tariff cost below." : "A no-battery schedule violates the import limit; savings are not claimed against an infeasible baseline."}`,
        [
            ["Dispatch cost", best.cost / 100, "USD"],
            [
                "No-battery cost",
                baselineFeasible ? baselineCost / 100 : "Infeasible",
                "USD",
            ],
            [
                "Cost reduction",
                baselineFeasible ? (baselineCost - best.cost) / 100 : "N/A",
                "USD",
            ],
            ["Grid energy", sum(best.path.map((r) => r.grid)), "kWh"],
        ],
        [
            "Hour",
            "Charge from bus (kWh)",
            "Discharge (kWh)",
            "Grid (kWh)",
            "Stored (kWh)",
            "Curtailed (kWh)",
            "Cost (USD)",
        ],
        best.path.map((r) => [
            r.hour,
            r.charge,
            r.discharge,
            r.grid,
            r.end,
            r.curtail,
            r.cost / 100,
        ]),
        {
            feasible: true,
            cost: best.cost,
            path: best.path,
            baseline_cost: baselineCost,
            baseline_feasible: baselineFeasible,
        },
        [
            "Per-interval energy balance independently reconciled.",
            "Charge/discharge power, storage and grid capacity enforced.",
            "Terminal charge is at least initial charge; energy is not borrowed from the boundary.",
        ],
        "One-hour intervals, integer kWh, constant charge efficiency rounded conservatively, ideal discharge and no export. Capital cost, aging beyond the supplied wear charge, weather uncertainty and electrical constraints require separate engineering validation.",
        [
            job(
                "DISPATCH-REVIEW",
                "Review the proposed dispatch",
                "Validate load/solar forecasts, tariff, inverter limits and the storage model before any physical dispatch.",
            ),
        ],
    );
}

function evidence(input) {
    const { parameters: p, datasets: d } = input;
    params(p, { max_age_days: [1, 3650] });
    exactKeys(d, ["claims", "sources"], "Datasets");
    const sources = rows(d.sources, "Sources", ["id", "title", "text"], 30);
    sources.forEach((r) => {
        text(r.title, "Source title", 200);
        text(r.text, "Source text", 12000);
    });
    const claims = rows(
        d.claims,
        "Claims",
        [
            "id",
            "claim",
            "direction",
            "threshold",
            "observed",
            "unit",
            "source_id",
            "quote",
            "age_days",
            "owner",
        ],
        40,
    );
    const decisions = claims.map((r) => {
        for (const k of ["claim", "unit", "owner"]) text(r[k], k, 500);
        text(r.source_id, "Source ID", 64, true);
        text(r.quote, "Quote", 2000, true);
        number(r.threshold, "Threshold", -1e9, 1e9, false);
        if (r.observed !== null)
            number(r.observed, "Observed", -1e9, 1e9, false);
        number(r.age_days, "Evidence age", 0, 10000);
        if (![">=", "<="].includes(r.direction))
            fail("Direction must be >= or <=.");
        const source = sources.find((s) => s.id === r.source_id),
            cited = !!(
                source &&
                r.quote.trim() &&
                source.text.includes(r.quote)
            );
        // The exact quote must contain the asserted number as a numeric token. This is traceability, not semantic verification.
        const numbers = (r.quote.match(/-?\d+(?:\.\d+)?/g) || []).map(Number);
        let state = "MET",
            reason =
                "Threshold met in operator-supplied evidence; source truth and interpretation require review.";
        if (r.observed === null) {
            state = "MISSING";
            reason = "No observation supplied.";
        } else if (!cited || !numbers.includes(r.observed)) {
            state = "UNBOUND";
            reason =
                "Observation must appear in an exact quote from the referenced source.";
        } else if (r.age_days > p.max_age_days) {
            state = "STALE";
            reason = "Evidence exceeds the allowed age.";
        } else if (
            !(r.direction === ">="
                ? r.observed >= r.threshold
                : r.observed <= r.threshold)
        ) {
            state = "FAILED";
            reason = "Observed value does not meet the acceptance threshold.";
        }
        return { ...r, state, reason };
    });
    const debt = decisions.filter((r) => r.state !== "MET");
    return result(
        "Explicit criteria and exact-quotation reconciliation",
        debt.length ? "HOLD" : "REVIEW",
        `${debt.length} of ${claims.length} criteria need work. ${debt.length ? "Convert each gap into the scoped jobs below." : "All supplied criteria reconcile; independent review is still required."}`,
        [
            ["Criteria met", claims.length - debt.length, ""],
            ["Proof debt", debt.length, "jobs"],
            ["Source records", sources.length, ""],
            ["Promotion", "HOLD", ""],
        ],
        ["Claim", "Required", "Observed", "State", "Source", "Reason"],
        decisions.map((r) => [
            r.claim,
            `${r.direction} ${r.threshold} ${r.unit}`,
            r.observed === null ? "Missing" : `${r.observed} ${r.unit}`,
            r.state,
            r.source_id || "None",
            r.reason,
        ]),
        { decisions, promotion: "HOLD", sensitivity: [] },
        [
            "Exact quotations matched against supplied source text.",
            "Numeric tokens, thresholds, age and missing observations checked.",
            "No automatic capability promotion or token/NFT valuation.",
        ],
        "This checks structured evidence supplied by you. It does not authenticate sources, verify quote semantics, measure real-world performance or replace an independent reviewer. Chronicle promotion remains in the signed Proof Bloom workflow.",
        debt.map((r) =>
            job(
                `PROVE-${r.id}`,
                r.claim,
                `Return attributable evidence of ${r.direction} ${r.threshold} ${r.unit}, no older than ${p.max_age_days} days; include method, raw observations, reviewer and exact source quotation. Current gap: ${r.reason}`,
                r.owner,
            ),
        ),
    );
}

function benchmark(input) {
    const { parameters: p, datasets: d } = input;
    params(p, {
        false_negative_cost: [0, 100000],
        false_positive_cost: [0, 100000],
        baseline_cost: [0, 10000],
        pipeline_a_cost: [0, 10000],
        pipeline_b_cost: [0, 10000],
        min_test_cases: [1, 500],
    });
    exactKeys(d, ["cases"], "Datasets");
    const cases = rows(
        d.cases,
        "Cases",
        ["id", "partition", "truth", "baseline", "pipeline_a", "pipeline_b"],
        1000,
    );
    cases.forEach((r) => {
        if (!["calibration", "test"].includes(r.partition))
            fail("Partition must be calibration or test.");
        for (const k of ["truth", "baseline", "pipeline_a", "pipeline_b"])
            number(r[k], k, 0, 1);
    });
    const calibration = cases.filter((r) => r.partition === "calibration"),
        test = cases.filter((r) => r.partition === "test");
    if (!calibration.length || !test.length)
        fail("Both calibration and test records are required.");
    const score = (subset, key) => {
        const fn = subset.filter((r) => r.truth === 1 && r[key] === 0).length,
            fp = subset.filter((r) => r.truth === 0 && r[key] === 1).length;
        return {
            name: key,
            count: subset.length,
            fn,
            fp,
            correct: subset.length - fn - fp,
            cost:
                fn * p.false_negative_cost +
                fp * p.false_positive_cost +
                subset.length * p[`${key}_cost`],
        };
    };
    const training = ["pipeline_a", "pipeline_b"]
        .map((k) => score(calibration, k))
        .sort((a, b) => a.cost - b.cost || a.name.localeCompare(b.name));
    const selected = training[0].name,
        arms = ["baseline", selected].map((k) => score(test, k)),
        saving = arms[0].cost - arms[1].cost;
    return result(
        "Calibration-only policy selection; separate test accounting",
        saving > 0 && test.length >= p.min_test_cases ? "REVIEW" : "HOLD",
        `${selected} selected on calibration cost. On ${test.length} separate test cases it ${saving >= 0 ? "reduces" : "increases"} modeled error + execution cost by ${Math.abs(saving)} cents.`,
        [
            ["Test cost reduction", saving / 100, "USD"],
            ["Test cases", test.length, ""],
            ["Missed positives", arms[1].fn, ""],
            ["False alarms", arms[1].fp, ""],
        ],
        [
            "Arm",
            "Test cases",
            "Correct",
            "False negatives",
            "False positives",
            "Cost (USD)",
        ],
        arms.map((r) => [r.name, r.count, r.correct, r.fn, r.fp, r.cost / 100]),
        {
            selected,
            training,
            arms,
            saving,
            minimum_met: test.length >= p.min_test_cases,
            errors: test
                .filter((r) => r[selected] !== r.truth)
                .map((r) => ({
                    id: r.id,
                    truth: r.truth,
                    prediction: r[selected],
                })),
        },
        [
            "Candidate selection uses calibration labels only.",
            "Test confusion matrices and weighted costs recomputed from individual records.",
            "Execution cost charged on every case, including correct classifications.",
        ],
        "Predictions and labels are supplied records, not a live model run. Split independence, label quality and complete costs require external verification. This single comparison does not establish general capability or automatic promotion.",
        [
            job(
                "REPLICATE-PIPELINE",
                "Independently replicate the selected policy",
                "Freeze the selected pipeline before collecting a fresh labeled test set; verify leakage controls, false-negative costs and complete execution/review costs.",
            ),
        ],
    );
}

const engines = {
    portfolio,
    procurement,
    schedule,
    inventory,
    energy,
    evidence,
    benchmark,
};
export function solve(raw) {
    const input = clone(raw);
    exactKeys(
        input,
        [
            "schema",
            "id",
            "title",
            "kind",
            "provenance",
            "parameters",
            "datasets",
        ],
        "Scenario",
    );
    if (input.schema !== SCHEMA || !Object.hasOwn(engines, input.kind))
        fail("Unsupported decision schema or workflow.");
    text(input.id, "Scenario ID", 80);
    text(input.title, "Title", 160);
    text(input.provenance, "Provenance", 1000);
    if (JSON.stringify(input).length > 256000)
        fail("Scenario exceeds the 256 KB input limit.");
    const output = engines[input.kind](input);
    return { schema: "agialpha.decision.report.v1", input, output };
}
export function verify(report) {
    exactKeys(report, ["schema", "input", "output"], "Report");
    if (report.schema !== "agialpha.decision.report.v1")
        fail("Unsupported report schema.");
    const replay = solve(report.input);
    if (canonical(replay.output) !== canonical(report.output))
        fail("Report failed replay: results differ from the supplied inputs.");
    return replay;
}
export function canonical(value) {
    if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
    if (value && typeof value === "object")
        return (
            "{" +
            Object.keys(value)
                .sort()
                .map((k) => JSON.stringify(k) + ":" + canonical(value[k]))
                .join(",") +
            "}"
        );
    return JSON.stringify(value);
}
export function csv(report) {
    const protect = (x) => {
        let s = String(x ?? "");
        if (/^[\s]*[=+@-]/.test(s) && typeof x !== "number") s = "'" + s;
        return '"' + s.replaceAll('"', '""') + '"';
    };
    return (
        [report.output.headers, ...report.output.rows]
            .map((row) => row.map(protect).join(","))
            .join("\r\n") + "\r\n"
    );
}
export function brief(report) {
    const { input: i, output: o } = report;
    return `# ${i.title}\n\n${i.provenance}\n\nStatus: ${o.verdict}. Human authorization pending.\n\n${o.summary}\n\n## Decision measures\n\n${o.metrics.map(([k, v, u]) => `- ${k}: ${typeof v === "number" ? Math.round(v * 100) / 100 : v} ${u}`).join("\n")}\n\n## Method and checks\n\n${o.method}\n\n${o.checks.map((x) => "- " + x).join("\n")}\n\n## Assumptions and limits\n\n${o.limits}\n\n## Work before execution\n\n${o.jobs.map((j) => `- ${j.id} — ${j.objective}\n  Acceptance: ${j.acceptance}\n  Owner: ${j.owner}`).join("\n")}\n\nFull inputs, row-level outputs and replayable calculation evidence accompany the JSON report. No external action was taken.\n`;
}
