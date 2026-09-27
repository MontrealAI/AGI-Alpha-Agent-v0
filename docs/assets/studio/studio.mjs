// SPDX-License-Identifier: Apache-2.0
import { brief, csv, SCHEMA, REPORT_SCHEMA } from "./engine.mjs";
import {
    parameters,
    fields,
    datasetHelp,
    parseCSV,
    inputCSV,
} from "./fields.mjs";
const $ = (id) => document.getElementById(id);
const siteRoot = new URL("../../", import.meta.url);
const make = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
};
let cases = [],
    current = null,
    report = null,
    worker = null,
    epoch = 0;
let offsets = {};
const storageKey = "agialpha.decision.inputs.v1";
const format = (x) =>
    typeof x === "number"
        ? x.toLocaleString("en-US", { maximumFractionDigits: 2 })
        : String(x);
function status(message, error = false) {
    $("status").textContent = message;
    $("status").classList.toggle("error", error);
}
function busy(value) {
    document
        .querySelector(".workbench")
        .setAttribute("aria-busy", String(value));
    $("run").disabled = value;
    $("stop").hidden = !value;
}
function invalidate(
    message = "Inputs changed. Calculate again to produce a current plan.",
) {
    epoch++;
    worker?.terminate();
    worker = null;
    busy(false);
    report = null;
    $("results").hidden = true;
    $("visual").replaceChildren();
    status(message);
}
function download(content, name, type) {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const a = make("a");
    a.href = url;
    a.download = name;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function encode(value) {
    return (
        JSON.stringify(
            value,
            (k, v) => {
                if (typeof v === "number" && !Number.isFinite(v))
                    throw new Error(
                        "Complete all numeric inputs before saving.",
                    );
                return v;
            },
            2,
        ) + "\n"
    );
}
const guarded = (fn) => async () => {
    try {
        await fn();
    } catch (e) {
        status(e.message, true);
    }
};
function inputValue(control, meta) {
    if (meta.type === "nullable" && !control.value.trim()) return null;
    return ["number", "nullable"].includes(meta.type)
        ? control.value.trim()
            ? Number(control.value)
            : NaN
        : control.value;
}
function createControl(key, value, label, onChange) {
    const meta = fields[key] || { label: key, type: "text" };
    let node;
    if (["partition", "direction"].includes(meta.type)) {
        node = make("select");
        for (const v of meta.type === "partition"
            ? ["calibration", "test"]
            : [">=", "<="]) {
            const option = make("option", v);
            option.value = v;
            node.append(option);
        }
    } else if (meta.type === "long") {
        node = make("textarea");
        node.rows = 2;
        node.maxLength = 12000;
    } else {
        node = make("input");
        node.type = ["number", "nullable"].includes(meta.type)
            ? "number"
            : "text";
        if (node.type === "number") node.step = "any";
        else node.maxLength = 2000;
    }
    node.value = value ?? "";
    node.dataset.key = key;
    node.setAttribute("aria-label", label);
    if (meta.hint) node.title = meta.hint;
    node.addEventListener("input", () => {
        onChange(inputValue(node, meta));
        invalidate();
    });
    return node;
}
function renderDatasets(focus = null) {
    const open = Object.fromEntries(
        [...$("datasets").querySelectorAll("details[data-dataset]")].map(
            (s) => [s.dataset.dataset, s.open],
        ),
    );
    $("datasets").replaceChildren();
    for (const [name, records] of Object.entries(current.datasets)) {
        const section = make("details", undefined, "dataset");
        section.dataset.dataset = name;
        section.open =
            open[name] ??
            (Object.keys(current.datasets).length === 1 ||
                ["claims", "coverage"].includes(name));
        section.append(
            make(
                "summary",
                `${name.charAt(0).toUpperCase() + name.slice(1)} · ${records.length} records`,
            ),
        );
        const body = make("div", undefined, "dataset-body");
        body.append(make("p", datasetHelp[name]));
        const actions = make("div", undefined, "dataset-actions"),
            add = make("button", "Add row"),
            template = make("button", "Download editable CSV"),
            label = make("label", "Import CSV", "file-button"),
            upload = make("input");
        upload.type = "file";
        upload.accept = ".csv,text/csv";
        upload.setAttribute("aria-label", `Import ${name} CSV`);
        label.append(upload);
        template.addEventListener("click", () =>
            download(
                inputCSV(records),
                `${current.id}-${name}-inputs.csv`,
                "text/csv",
            ),
        );
        add.addEventListener("click", () => {
            if (records.length >= 1000) {
                status(
                    "Dataset is limited to 1,000 rows; individual workflow limits also apply.",
                    true,
                );
                return;
            }
            const r = Object.fromEntries(
                Object.keys(records[0]).map((k) => [
                    k,
                    fields[k]?.type === "number"
                        ? 0
                        : fields[k]?.type === "nullable"
                          ? null
                          : fields[k]?.type === "direction"
                            ? ">="
                            : fields[k]?.type === "partition"
                              ? "test"
                              : "",
                ]),
            );
            let n = records.length + 1;
            while (records.some((x) => x.id === `row_${n}`)) n++;
            r.id = `row_${n}`;
            records.push(r);
            offsets[name] = Math.floor((records.length - 1) / 12) * 12;
            invalidate(
                "New row added. Complete its fields before calculating.",
            );
            renderDatasets({ name, row: records.length - 1 });
        });
        upload.addEventListener(
            "change",
            guarded(async () => {
                const file = upload.files[0];
                if (!file) return;
                invalidate("Reading replacement data…");
                if (file.size > 256000) throw new Error("CSV exceeds 256 KB.");
                const readEpoch = epoch;
                const source = await file.text();
                if (readEpoch !== epoch) return;
                const parsed = parseCSV(source, Object.keys(records[0]));
                current.datasets[name] = parsed;
                offsets[name] = 0;
                current.provenance =
                    "Operator-edited / imported data. Source authenticity and completeness require operator review.";
                invalidate(
                    `Imported ${parsed.length} ${name} records. Review constraints, then calculate.`,
                );
                renderDatasets();
                $("provenance").textContent = current.provenance;
            }),
        );
        actions.append(add, template, label);
        body.append(actions);
        const wrap = make("div", undefined, "table-wrap");
        wrap.tabIndex = 0;
        wrap.setAttribute("role", "region");
        wrap.setAttribute("aria-label", `${name} input table`);
        const table = make("table"),
            head = make("thead"),
            tr = make("tr"),
            columns = Object.keys(records[0]);
        columns.forEach((k) => {
            const th = make("th", fields[k]?.label || k);
            th.scope = "col";
            tr.append(th);
        });
        tr.append(make("th", "Edit"));
        head.append(tr);
        table.append(head);
        const tbody = make("tbody");
        const offset = Math.min(
            offsets[name] || 0,
            Math.floor((records.length - 1) / 12) * 12,
        );
        records.slice(offset, offset + 12).forEach((r, visibleIndex) => {
            const i = offset + visibleIndex;
            const row = make("tr");
            row.dataset.index = i;
            columns.forEach((k) => {
                const td = make("td");
                td.append(
                    createControl(
                        k,
                        r[k],
                        `${name} row ${i + 1} ${fields[k]?.label || k}`,
                        (value) => {
                            r[k] = value;
                            current.provenance =
                                "Operator-edited inputs. Verify records and assumptions before use.";
                            $("provenance").textContent = current.provenance;
                        },
                    ),
                );
                row.append(td);
            });
            const td = make("td"),
                remove = make("button", "Remove");
            remove.setAttribute("aria-label", `Remove ${name} row ${i + 1}`);
            remove.disabled = records.length === 1;
            remove.addEventListener("click", () => {
                records.splice(i, 1);
                invalidate("Row removed. Recalculate the decision.");
                renderDatasets({ name, row: Math.min(i, records.length - 1) });
            });
            td.append(remove);
            row.append(td);
            tbody.append(row);
        });
        table.append(tbody);
        wrap.append(table);
        body.append(wrap);
        if (records.length > 12) {
            const pager = make("div", undefined, "dataset-actions"),
                previous = make("button", "Previous rows"),
                next = make("button", "Next rows"),
                count = make(
                    "span",
                    `Rows ${offset + 1}–${Math.min(offset + 12, records.length)} of ${records.length}`,
                );
            previous.disabled = offset === 0;
            next.disabled = offset + 12 >= records.length;
            previous.addEventListener("click", () => {
                offsets[name] = offset - 12;
                renderDatasets({ name, row: offsets[name] });
            });
            next.addEventListener("click", () => {
                offsets[name] = offset + 12;
                renderDatasets({ name, row: offsets[name] });
            });
            pager.append(previous, count, next);
            body.append(pager);
        }
        section.append(body);
        $("datasets").append(section);
    }
    if (focus) {
        const section = [...$("datasets").children].find(
            (s) => s.dataset.dataset === focus.name,
        );
        section.open = true;
        section
            .querySelector(`tr[data-index="${focus.row}"] [data-key]`)
            ?.focus();
    }
}
function load(input, updateURL = true) {
    invalidate(
        "Inputs ready. Review the constraints, then calculate your plan.",
    );
    current = structuredClone(input);
    offsets = {};
    $("datasets").replaceChildren();
    const entry = cases.find((c) => c.id === input.id && c.kind === input.kind),
        fallback = cases.find((c) => c.kind === input.kind);
    const meta = entry || fallback;
    $("case-title").textContent = input.title;
    $("case-category").textContent = meta?.category || "CUSTOM DECISION";
    $("case-question").textContent =
        meta?.question ||
        "Evaluate your supplied constraints and observations.";
    $("case-deliverable").textContent =
        meta?.deliverable ||
        "Decision brief · row-level plan · replayable dossier";
    $("case-art").src = new URL(
        `assets/studio/previews/${meta?.id || "capital"}.svg`,
        siteRoot,
    ).href;
    $("provenance").textContent = input.provenance;
    $("case-basis").textContent = input.provenance.startsWith("Constructed")
        ? "Constructed case · replace with your records"
        : "Operator-supplied inputs · verify source records";
    document.title = `${input.title} · AGI Alpha`;
    document
        .querySelectorAll(".case-choice")
        .forEach((b) =>
            b.setAttribute("aria-current", String(b.dataset.case === input.id)),
        );
    $("parameters").replaceChildren();
    for (const [key, value] of Object.entries(input.parameters)) {
        const [label, unit] = parameters[key] || [key, ""],
            wrap = make("div", undefined, "parameter"),
            l = make("label", label),
            control = make("input"),
            small = make("small", unit);
        control.type = "number";
        control.id = `parameter-${key}`;
        control.value = value;
        control.step = "1";
        l.htmlFor = control.id;
        control.setAttribute("aria-describedby", `${control.id}-unit`);
        small.id = `${control.id}-unit`;
        control.addEventListener("input", () => {
            current.parameters[key] = control.value.trim()
                ? Number(control.value)
                : NaN;
            current.provenance =
                "Operator-edited inputs. Verify records and assumptions before use.";
            $("provenance").textContent = current.provenance;
            $("case-basis").textContent =
                "Operator-edited inputs · verify assumptions";
            invalidate();
        });
        wrap.append(l, small, control);
        $("parameters").append(wrap);
    }
    renderDatasets();
    $("legacy-links").replaceChildren();
    for (const id of meta?.legacy || []) {
        const li = make("li"),
            a = make("a", id.replaceAll("_", " "));
        a.href = new URL(`demos/${id}/`, siteRoot).href;
        li.append(a);
        $("legacy-links").append(li);
    }
    if (updateURL)
        history.replaceState(null, "", `?case=${encodeURIComponent(input.id)}`);
}
function plot() {
    const { input: i, output: o } = report,
        d = o.detail;
    $("visual").replaceChildren();
    const ns = "http://www.w3.org/2000/svg",
        svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 850 310");
    svg.classList.add("plot");
    svg.setAttribute("role", "img");
    const el = (tag, attrs, text) => {
        const n = document.createElementNS(ns, tag);
        for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
        if (text !== undefined) n.textContent = text;
        svg.append(n);
        return n;
    };
    const title = (label) => {
        svg.setAttribute("aria-label", label);
        $("visual").append(make("p", label, "visual-heading"));
    };
    const axis = () => {
        el("line", { x1: 70, y1: 265, x2: 815, y2: 265, class: "axis" });
    };
    if (i.kind === "schedule") {
        title("Resource plan · elapsed work hours");
        const resources = [...new Set(d.operations.map((x) => x.machine))];
        svg.setAttribute("viewBox", `0 0 850 ${70 + resources.length * 52}`);
        resources.forEach((r, n) => {
            el("text", { x: 15, y: 52 + n * 52 }, r);
            const ops = d.operations.filter((x) => x.machine === r);
            ops.forEach((op) => {
                const x = 140 + (op.start / d.makespan) * 680;
                const rect = el("rect", {
                    x,
                    y: 32 + n * 52,
                    width: ((op.end - op.start) / d.makespan) * 680,
                    height: 32,
                    rx: 2,
                    class: "gantt",
                });
                const t = document.createElementNS(ns, "title");
                t.textContent = `${op.job}: ${op.start}–${op.end} hours`;
                rect.append(t);
            });
        });
        [0, 0.25, 0.5, 0.75, 1].forEach((f) =>
            el(
                "text",
                {
                    x: 140 + f * 680,
                    y: 25,
                    "text-anchor": f === 1 ? "end" : "start",
                },
                format(f * d.makespan),
            ),
        );
    } else if (i.kind === "service") {
        title(
            "Coverage by shift · required staff (solid), proposed staff (dashed)",
        );
        axis();
        const series = [
            d.shifts.map((r) => r.required_staff),
            d.shifts.map((r) => r.available_staff + r.extra),
        ];
        const max = Math.max(1, ...series.flat());
        series.forEach((values, n) =>
            el("polyline", {
                points: values
                    .map(
                        (v, k) =>
                            `${70 + (k / Math.max(1, values.length - 1)) * 740},${265 - (v / max) * 210}`,
                    )
                    .join(" "),
                class: n ? "secondary" : "line",
            }),
        );
        el("text", { x: 15, y: 60 }, format(max));
        el("text", { x: 70, y: 290 }, "First shift");
        el("text", { x: 815, y: 290, "text-anchor": "end" }, "Last shift");
    } else if (i.kind === "inventory") {
        title("Untouched holdout · observed (solid) and predicted (dashed)");
        axis();
        const series = [d.holdout_actual, d.holdout_predictions],
            max = Math.max(1, ...series.flat()),
            count = series[0].length;
        series.forEach((xs, n) =>
            el("polyline", {
                points: xs
                    .map(
                        (v, k) =>
                            `${70 + (k / Math.max(1, count - 1)) * 740},${265 - (v / max) * 210}`,
                    )
                    .join(" "),
                class: n ? "secondary" : "line",
            }),
        );
        el("text", { x: 15, y: 60 }, format(max));
        el("text", { x: 70, y: 290 }, "First test period");
        el(
            "text",
            { x: 815, y: 290, "text-anchor": "end" },
            "Last test period",
        );
    } else if (i.kind === "energy" && d.feasible) {
        title("Stored energy through the dispatch · kWh");
        axis();
        const values = [i.parameters.initial_kwh, ...d.path.map((x) => x.end)];
        el("polyline", {
            points: values
                .map(
                    (v, k) =>
                        `${70 + (k / (values.length - 1)) * 740},${265 - (v / i.parameters.capacity_kwh) * 210}`,
                )
                .join(" "),
            class: "line",
        });
        el("text", { x: 15, y: 60 }, String(i.parameters.capacity_kwh));
        el("text", { x: 70, y: 290 }, "Starting charge");
        el("text", { x: 815, y: 290, "text-anchor": "end" }, "Final charge");
    } else {
        let values = [],
            labels = [];
        if (i.kind === "portfolio") {
            values = i.datasets.projects.map((_, n) => o.rows[n][3]);
            labels = i.datasets.projects.map((r) => r.id);
            title("Individual modeled net present values · USD");
        } else if (i.kind === "procurement" && d.feasible) {
            values = d.quantities;
            labels = i.datasets.suppliers.map((r) => r.id);
            title("Allocated purchase batches by supplier");
        } else if (i.kind === "evidence") {
            labels = ["MET", "MISSING", "UNBOUND", "STALE", "FAILED"];
            values = labels.map(
                (s) => d.decisions.filter((r) => r.state === s).length,
            );
            title("Evidence criteria by state · promotion remains on hold");
        } else if (i.kind === "benchmark") {
            values = d.arms.map((r) => r.cost / 100);
            labels = d.arms.map((r) => r.name);
            title("Held-out error + execution cost · USD");
        } else return;
        const min = Math.min(0, ...values),
            max = Math.max(1, ...values),
            range = max - min,
            zero = 250 - ((0 - min) / range) * 190,
            step = 740 / values.length;
        el("line", { x1: 65, y1: zero, x2: 815, y2: zero, class: "axis" });
        values.forEach((v, k) => {
            const y = 250 - ((v - min) / range) * 190;
            el("rect", {
                x: 70 + k * step,
                y: Math.min(y, zero),
                width: step * 0.65,
                height: Math.max(1, Math.abs(zero - y)),
                rx: 2,
                class: v < 0 ? "muted" : "bar",
            });
            el(
                "text",
                { x: 70 + k * step, y: v >= 0 ? y - 8 : y + 17 },
                format(v),
            );
            el(
                "text",
                {
                    x: 70 + k * step,
                    y: 290,
                    transform: `rotate(-18 ${70 + k * step} 290)`,
                },
                labels[k],
            );
        });
    }
    $("visual").append(svg);
}
function render() {
    const o = report.output;
    $("results").hidden = false;
    $("result-summary").textContent = o.summary;
    $("verdict").textContent = o.verdict;
    $("verdict").dataset.state = o.verdict;
    $("metrics").replaceChildren();
    o.metrics.forEach(([label, value, unit]) => {
        const node = make("div", undefined, "metric");
        node.append(
            make("span", label),
            make("strong", format(value)),
            make("small", unit),
        );
        $("metrics").append(node);
    });
    const table = make("table"),
        thead = make("thead"),
        head = make("tr");
    o.headers.forEach((x) => {
        const th = make("th", x);
        th.scope = "col";
        head.append(th);
    });
    thead.append(head);
    table.append(thead);
    const body = make("tbody");
    o.rows.forEach((r) => {
        const tr = make("tr");
        r.forEach((x) => tr.append(make("td", format(x))));
        body.append(tr);
    });
    table.append(body);
    $("result-table").replaceChildren(table);
    $("method").textContent =
        `${o.method} · Calculation version ${report.calculation_version || "1.9.0 (archived replay)"}`;
    $("supporting-tables").replaceChildren();
    for (const section of o.detail.tables || []) {
        const wrapper = make("section"),
            scroll = make("div", undefined, "table-scroll");
        wrapper.append(make("h4", section.title));
        scroll.tabIndex = 0;
        scroll.setAttribute("role", "region");
        scroll.setAttribute("aria-label", section.title);
        const table = make("table"),
            head = make("thead"),
            row = make("tr"),
            body = make("tbody");
        for (const label of section.headers) {
            const cell = make("th", label);
            cell.scope = "col";
            row.append(cell);
        }
        head.append(row);
        table.append(head);
        for (const record of section.rows) {
            const row = make("tr");
            record.forEach((value) => row.append(make("td", format(value))));
            body.append(row);
        }
        table.append(body);
        scroll.append(table);
        wrapper.append(scroll);
        $("supporting-tables").append(wrapper);
    }
    $("checks").replaceChildren(...o.checks.map((x) => make("li", x)));
    $("limits").textContent = o.limits;
    $("details").textContent = JSON.stringify(o.detail, null, 2);
    $("jobs").replaceChildren();
    o.jobs.forEach((j) => {
        const node = make("article", undefined, "job"),
            text = make("div");
        text.append(
            make("h5", j.objective),
            make("p", j.acceptance),
            make("small", `Owner: ${j.owner} · ${j.state}`),
        );
        node.append(make("b", j.id), text);
        $("jobs").append(node);
    });
    if (!o.jobs.length)
        $("jobs").append(
            make(
                "p",
                "No missing structured criteria. Independent review is still required before capability promotion.",
            ),
        );
    const sensitivity = o.detail.sensitivity || [];
    $("sensitivity").hidden = !sensitivity.length;
    $("stress-bars").replaceChildren();
    const max = Math.max(1, ...sensitivity.map((s) => Math.abs(s.value || 0)));
    for (const s of sensitivity) {
        const row = make("div", undefined, "stress-row"),
            track = make("div", undefined, "stress-track"),
            fill = make("div", undefined, "stress-fill");
        fill.style.width = `${(Math.abs(s.value || 0) / max) * 100}%`;
        track.append(fill);
        row.append(
            make("span", s.scenario),
            track,
            make(
                "strong",
                s.value === null
                    ? "Infeasible"
                    : `${format(s.value)} ${s.unit || (current.kind === "procurement" ? "USD" : "")}${s.feasible === false ? " · shortfall" : ""}`,
                "stress-value",
            ),
        );
        if (s.note) row.append(make("small", s.note));
        if (s.selected)
            row.title = `Selected: ${s.selected.join(", ") || "none"}`;
        $("stress-bars").append(row);
    }
    plot();
}
function calculate(payload = { input: current }, imported = false) {
    invalidate("Calculating constraints, comparisons and verification checks…");
    busy(true);
    const ticket = epoch;
    worker = new Worker(new URL("./worker.mjs", import.meta.url), {
        type: "module",
    });
    worker.onmessage = ({ data }) => {
        if (ticket !== epoch) return;
        worker.terminate();
        worker = null;
        busy(false);
        if (data.error) {
            status(data.error, true);
            return;
        }
        if (imported) load(data.report.input);
        report = data.report;
        render();
        status(
            imported
                ? "Dossier replayed successfully. Calculations match its inputs; source authenticity remains unverified."
                : "Calculation complete. Inspect the plan, constraints and proof jobs before taking action.",
        );
        $("results-title").focus({ preventScroll: true });
        $("results").scrollIntoView({
            behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
                ? "instant"
                : "smooth",
            block: "start",
        });
    };
    worker.onerror = () => {
        if (ticket !== epoch) return;
        invalidate("Calculation could not start. Reload this page and retry.");
        status(
            "Calculation could not start. Reload this page and retry.",
            true,
        );
    };
    worker.postMessage(payload);
}
$("run").addEventListener("click", () => calculate());
$("stop").addEventListener("click", () =>
    invalidate("Calculation stopped. Inputs are preserved."),
);
$("reset").addEventListener("click", () =>
    load(
        (
            cases.find((c) => c.id === current.id) ||
            cases.find((c) => c.kind === current.kind)
        ).input,
    ),
);
$("save").addEventListener(
    "click",
    guarded(() => {
        localStorage.setItem(storageKey, encode(current));
        $("restore").disabled = false;
        $("clear").disabled = false;
        status(
            "Inputs saved on this browser. Calculations and external authority are not saved.",
        );
    }),
);
$("restore").addEventListener(
    "click",
    guarded(() => {
        const stored = localStorage.getItem(storageKey);
        if (!stored) throw new Error("No saved inputs found.");
        calculate({ input: JSON.parse(stored) }, true);
    }),
);
$("clear").addEventListener(
    "click",
    guarded(() => {
        localStorage.removeItem(storageKey);
        $("restore").disabled = true;
        $("clear").disabled = true;
        status("Saved inputs cleared. Downloaded files remain with you.");
    }),
);
$("import").addEventListener(
    "change",
    guarded(async () => {
        const file = $("import").files[0];
        $("import").value = "";
        if (!file) return;
        invalidate("Reading replacement dossier…");
        if (file.size > 1048576)
            throw new Error("Dossier exceeds the 1 MiB limit.");
        const readEpoch = epoch;
        const source = await file.text();
        if (readEpoch !== epoch) return;
        const value = JSON.parse(source);
        invalidate("Replaying the imported dossier…");
        if (
            ["agialpha.decision.report.v1", REPORT_SCHEMA].includes(
                value.schema,
            )
        )
            calculate({ report: value }, true);
        else if (value.schema === SCHEMA) calculate({ input: value }, true);
        else
            throw new Error(
                "Import a Decision Studio input or report JSON file.",
            );
    }),
);
for (const [id, ext, mime, content] of [
    ["brief", "md", "text/markdown", () => brief(report)],
    ["csv", "csv", "text/csv", () => csv(report)],
    ["report", "json", "application/json", () => encode(report)],
    [
        "jobs",
        "json",
        "application/json",
        () =>
            encode({
                schema: "agialpha.decision.jobs.v1",
                scenario: report.input.id,
                provenance: report.input.provenance,
                status: "UNSUBMITTED",
                jobs: report.output.jobs,
            }),
    ],
]) {
    $(`export-${id}`).addEventListener(
        "click",
        guarded(() => {
            if (!report) throw new Error("Calculate a current plan first.");
            download(content(), `${report.input.id}-${id}.${ext}`, mime);
            status(
                `${id} downloaded. Keep the dossier with its source records.`,
            );
        }),
    );
}
try {
    const response = await fetch(new URL("./cases.json", import.meta.url));
    if (!response.ok)
        throw new Error(`Case library unavailable (HTTP ${response.status}).`);
    cases = await response.json();
    for (const category of [...new Set(cases.map((c) => c.category))]) {
        $("case-list").append(make("p", category, "case-group"));
        cases
            .filter((c) => c.category === category)
            .forEach((c) => {
                const b = make("button", undefined, "case-choice");
                b.dataset.case = c.id;
                b.append(
                    make(
                        "span",
                        String(cases.indexOf(c) + 1).padStart(2, "0"),
                        "num",
                    ),
                    make("span", c.title),
                );
                b.addEventListener("click", () => load(c.input));
                $("case-list").append(b);
            });
    }
    const requested = new URL(location.href).searchParams.get("case"),
        entry = cases.find((c) => c.id === requested) || cases[0];
    load(entry.input);
    try {
        const saved = !!localStorage.getItem(storageKey);
        $("restore").disabled = !saved;
        $("clear").disabled = !saved;
    } catch {
        status(
            "Browser storage is unavailable. Downloads and calculations still work.",
        );
    }
    document.documentElement.dataset.studioReady = "true";
    if ("serviceWorker" in navigator)
        navigator.serviceWorker
            .register(new URL("service-worker.js", siteRoot))
            .catch(() => {});
} catch (error) {
    status(error.message, true);
    $("run").disabled = true;
}
