// SPDX-License-Identifier: Apache-2.0
export const parameters = {
    budget: ["Capital budget", "USD"],
    staff_days: ["Delivery capacity", "staff days"],
    years: ["Evaluation horizon", "years"],
    discount_percent: ["Discount rate", "% per year"],
    benefit_percent: ["Benefit realization", "% of projected benefit"],
    demand: ["Required order", "batches"],
    max_share_percent: ["Maximum supplier share", "% of all batches"],
    lead_days: ["Latest acceptable lead time", "days"],
    min_ontime_percent: ["Minimum quoted on-time rate", "%"],
    min_suppliers: ["Minimum suppliers", "suppliers"],
    deadline: ["Delivery window", "elapsed work hours"],
    holdout: ["Untouched test window", "periods"],
    season: ["Season length", "periods"],
    lead_periods: ["Replenishment lead time", "periods"],
    on_hand: ["Available stock", "units"],
    on_order: ["Already ordered", "units"],
    safety_units: ["Explicit reserve", "units"],
    unit_cost: ["Incremental unit cost", "USD"],
    handle_minutes: ["Average handling time", "minutes per case"],
    shift_hours: ["Paid shift length", "hours per person"],
    shrinkage_percent: [
        "Unavailable time",
        "% for breaks, leave and non-service work",
    ],
    occupancy_percent: [
        "Handling occupancy",
        "% of remaining time spent handling cases",
    ],
    reserve_percent: ["Demand reserve", "% above the point forecast"],
    backlog: ["Starting backlog", "cases"],
    clear_backlog_periods: ["Clear backlog within", "shifts"],
    capacity_kwh: ["Usable battery capacity", "kWh"],
    power_kw: ["Charge / discharge limit", "kW"],
    initial_kwh: ["Starting stored energy", "kWh"],
    charge_efficiency_percent: ["Charge efficiency", "%"],
    degradation_cents: ["Discharge wear charge", "cents per kWh"],
    max_age_days: ["Maximum evidence age", "days"],
    false_negative_cost: ["Cost of a missed positive", "cents per case"],
    false_positive_cost: ["Cost of a false alarm", "cents per case"],
    baseline_cost: ["Baseline execution cost", "cents per case"],
    pipeline_a_cost: ["Pipeline A execution cost", "cents per case"],
    pipeline_b_cost: ["Pipeline B execution cost", "cents per case"],
    min_test_cases: ["Minimum test observations", "cases"],
};
const f = (label, type = "text", hint = "") => ({ label, type, hint });
export const fields = {
    id: f("ID"),
    name: f("Name"),
    cost: f("Capital · USD", "number"),
    annual_benefit: f("Annual benefit · USD", "number"),
    annual_cost: f("Annual operating cost · USD", "number"),
    staff_days: f("Staff days", "number"),
    requires: f(
        "Prerequisite IDs",
        "text",
        "Comma separated; blank means none",
    ),
    unit_cost: f("Cost per batch · USD", "number"),
    setup_cost: f("Fixed order cost · USD", "number"),
    capacity: f("Available batches", "number"),
    lead_days: f("Lead days", "number"),
    ontime_percent: f("On time · %", "number"),
    job: f("Job ID"),
    resource: f("Resource ID"),
    duration: f("Duration · hours", "number"),
    due: f("Job due · hours", "number"),
    units: f("Observed units", "number"),
    available_staff: f("Existing staff · people", "number"),
    extra_limit: f("Additional staff cap", "number"),
    extra_shift_cost: f("Cost per extra staff shift · USD", "number"),
    load_kwh: f("Load · kWh", "number"),
    solar_kwh: f("Solar · kWh", "number"),
    tariff_cents: f("Tariff · cents/kWh", "number"),
    grid_limit_kwh: f("Grid limit · kWh", "number"),
    claim: f("Acceptance claim", "long"),
    direction: f("Comparison", "direction"),
    threshold: f("Threshold", "number"),
    observed: f("Observed value", "nullable", "Blank means missing"),
    unit: f("Unit"),
    source_id: f("Source ID"),
    quote: f("Exact quotation", "long"),
    age_days: f("Evidence age · days", "number"),
    owner: f("Owner"),
    title: f("Source title"),
    text: f("Source record", "long"),
    partition: f("Partition", "partition"),
    truth: f("Verified label · 0/1", "number"),
    baseline: f("Baseline · 0/1", "number"),
    pipeline_a: f("Pipeline A · 0/1", "number"),
    pipeline_b: f("Pipeline B · 0/1", "number"),
};
export const datasetHelp = {
    projects:
        "Each row is indivisible. Annual benefits and operating costs recur for the evaluation horizon. Enter prerequisites by ID; cycles are rejected.",
    suppliers:
        "One batch is your purchasing unit. Fixed order costs apply once to each used supplier. Lead time and on-time rate are hard qualification filters.",
    operations:
        "Rows within each job define operation order. Each named resource handles one operation at a time. Due times are measured from the same starting zero.",
    demand: "Put observations in chronological order. The final holdout periods are excluded from model selection. Every row represents the same time interval.",
    coverage:
        "One row per future shift, in order. Existing staff are already funded. Additional staff are capped per shift and charged per person; unused capacity cannot move to another day. Historical periods must match the shift length.",
    hours: "Each row is one hour in chronological order. Import and storage constraints are enforced without load shedding. Solar excess may be curtailed; exports are not modeled.",
    claims: "Link each numeric observation to an exact quotation in Sources. Missing, stale, failed or unbound observations become proof jobs. Matching a quote does not authenticate it.",
    sources:
        "Paste the attributable source text. The engine checks quotations locally; it does not fetch URLs or authenticate documents.",
    cases: "0 = negative, 1 = positive. Select the pipeline using calibration records; evaluate it on separate test records. Import your recorded predictions and verified labels.",
};

export function parseCSV(source, columns) {
    if (typeof source !== "string" || source.length > 256000)
        throw new Error("CSV must be no larger than 256 KB.");
    const records = [];
    let row = [],
        cell = "",
        quoted = false,
        closed = false;
    source = source.replace(/^\uFEFF/, "");
    for (let i = 0; i < source.length; i++) {
        const c = source[i];
        if (quoted) {
            if (c === '"' && source[i + 1] === '"') {
                cell += '"';
                i++;
            } else if (c === '"') {
                quoted = false;
                closed = true;
            } else cell += c;
        } else if (c === '"') {
            if (cell || closed) throw new Error("Unexpected CSV quote.");
            quoted = true;
        } else if (c === "," || c === "\n" || c === "\r") {
            row.push(cell);
            cell = "";
            closed = false;
            if (c !== ",") {
                if (c === "\r" && source[i + 1] === "\n") i++;
                records.push(row);
                row = [];
            }
        } else {
            if (closed)
                throw new Error("Unexpected text after a closing CSV quote.");
            cell += c;
        }
    }
    if (quoted) throw new Error("Unclosed CSV quotation.");
    if (cell || row.length || closed) {
        row.push(cell);
        records.push(row);
    }
    if (records.length < 2 || records[0].join(",") !== columns.join(","))
        throw new Error("CSV header must be exactly: " + columns.join(","));
    if (records.length > 1001) throw new Error("CSV exceeds 1,000 data rows.");
    return records.slice(1).map((values, i) => {
        if (values.length !== columns.length)
            throw new Error(`CSV row ${i + 2} has the wrong number of fields.`);
        return Object.fromEntries(
            columns.map((key, j) => {
                const value = values[j],
                    type = fields[key]?.type;
                if (type === "number" || type === "nullable") {
                    if (!value.trim() && type === "nullable")
                        return [key, null];
                    if (!value.trim() || !Number.isFinite(Number(value)))
                        throw new Error(
                            `CSV row ${i + 2}: ${key} requires a number.`,
                        );
                    return [key, Number(value)];
                }
                return [key, value];
            }),
        );
    });
}
export function inputCSV(records) {
    const keys = Object.keys(records[0]);
    const cell = (value) => {
        let s = String(value ?? "");
        if (typeof value !== "number" && /^[\s]*[=+@-]/.test(s)) s = "'" + s;
        return '"' + s.replaceAll('"', '""') + '"';
    };
    return (
        [keys, ...records.map((r) => keys.map((k) => r[k]))]
            .map((r) => r.map(cell).join(","))
            .join("\r\n") + "\r\n"
    );
}
