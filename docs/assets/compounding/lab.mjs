// SPDX-License-Identifier: Apache-2.0
import {
    example,
    freeze,
    run,
    verify,
    reviewRun,
    decision,
    canonical,
    parse,
    validateSpec,
    exportDocket,
} from "./engine.mjs";
const $ = (selector) => document.querySelector(selector);
const ROOT = new URL("../../", import.meta.url);
const STORAGE = "agialpha.compounding.v1";
let spec = example(),
    capability = null,
    report = null,
    busy = false;
let timers = { control: null, treatment: null },
    started = { control: null, treatment: null };
const fmt = (value) =>
    (value / 1000).toLocaleString(undefined, { maximumFractionDigits: 2 });
const status = (message, error = false) => {
    $("#lab-status").textContent = message;
    $("#lab-status").classList.toggle("error", error);
};
function save() {
    try {
        localStorage.setItem(STORAGE, canonical({ spec, report }));
    } catch {
        status("Storage unavailable. Download your run to keep the evidence.");
    }
}
function reset() {
    capability = null;
    report = null;
    timers = { control: null, treatment: null };
    started = { control: null, treatment: null };
    save();
}
function download(name, data, type = "application/json") {
    const url = URL.createObjectURL(new Blob([data], { type }));
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function chart() {
    const target = $("#prediction-chart");
    if (!report) {
        target.replaceChildren(
            Object.assign(document.createElement("p"), {
                textContent: "Freeze a policy, then test the next mission.",
            }),
        );
        return;
    }
    const i = Number($("#task-view").value) || 0,
        task = report.spec.tasks[i],
        a = report.core.arms;
    const actual = [...task.observed, ...task.heldout],
        control = [
            ...task.observed,
            ...a.B5.tasks[i].predictions_milli.map((x) => x / 1000),
        ],
        treatment = [
            ...task.observed,
            ...a.B6.tasks[i].predictions_milli.map((x) => x / 1000),
        ];
    const values = [...actual, ...control, ...treatment],
        lo = Math.min(...values) - 10,
        hi = Math.max(...values) + 10;
    const x = (j) => 42 + (j * 500) / (actual.length - 1),
        y = (v) => 205 - ((v - lo) * 175) / (hi - lo);
    const path = (arr) =>
        arr
            .map(
                (v, j) =>
                    `${j ? "L" : "M"}${x(j).toFixed(2)},${y(v).toFixed(2)}`,
            )
            .join(" ");
    const ns = "http://www.w3.org/2000/svg",
        svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 580 245");
    svg.setAttribute("aria-hidden", "true");
    const node = (tag, attrs, text) => {
        const n = document.createElementNS(ns, tag);
        for (const [k, v] of Object.entries(attrs))
            n.setAttribute(k, String(v));
        if (text) n.textContent = text;
        svg.append(n);
        return n;
    };
    for (let j = 0; j < 4; j++) {
        const v = lo + ((hi - lo) * j) / 3;
        node("line", {
            x1: 42,
            x2: 548,
            y1: y(v),
            y2: y(v),
            stroke: "#dce0d3",
        });
        node(
            "text",
            { x: 0, y: y(v) + 3, fill: "#5a6954", "font-size": 9 },
            String(Math.round(v)),
        );
    }
    node("line", {
        x1: x(task.observed.length - 0.5),
        x2: x(task.observed.length - 0.5),
        y1: 15,
        y2: 208,
        stroke: "#abb69c",
        "stroke-dasharray": "3 5",
    });
    node(
        "text",
        { x: 45, y: 232, fill: "#596950", "font-size": 9 },
        "CALIBRATION",
    );
    node(
        "text",
        { x: x(task.observed.length), y: 232, fill: "#596950", "font-size": 9 },
        "HELD-OUT FUTURE",
    );
    node("path", {
        d: path(control),
        stroke: "#9b563c",
        "stroke-width": 2,
        fill: "none",
        "stroke-dasharray": "5 4",
    });
    node("path", {
        d: path(treatment),
        stroke: "#897021",
        "stroke-width": 3,
        fill: "none",
    });
    node("path", {
        d: path(actual),
        stroke: "#183b2c",
        "stroke-width": 1.5,
        fill: "none",
    });
    actual.forEach((v, j) =>
        node("circle", { cx: x(j), cy: y(v), r: 2.5, fill: "#183b2c" }),
    );
    target.replaceChildren(svg);
    target.setAttribute(
        "aria-label",
        `Task ${task.id}: current-stack absolute error ${fmt(a.B5.tasks[i].error_milli)}, with-memory error ${fmt(a.B6.tasks[i].error_milli)}. Exact predictions are in the expandable ledger.`,
    );
}
function render() {
    $("#laboratory").setAttribute("aria-busy", String(busy));
    document.querySelectorAll("[data-scenario]").forEach((button) => {
        const selected = button.dataset.scenario === spec.scenario;
        button.classList.toggle("active", selected);
        button.setAttribute("aria-pressed", String(selected));
        button.disabled = busy;
    });
    for (const id of [
        "freeze",
        "apply-spec",
        "download-spec",
        "task-seed",
        "call-cost",
        "human-cost",
        "import-run",
    ])
        $("#" + id).disabled = busy;
    $("#compare").disabled = busy || !capability;
    for (const id of ["export-docket", "export-run"])
        $("#" + id).disabled = busy || !report;
    for (const arm of ["control", "treatment"]) {
        $("#timer-" + arm).disabled = busy || !report;
        $("#timer-" + arm).textContent =
            started[arm] !== null
                ? "Finish " +
                  (arm === "control" ? "current-stack" : "treatment") +
                  " review"
                : "Review " +
                  (arm === "control" ? "current stack" : "treatment");
        $("#time-" + arm).textContent =
            started[arm] !== null
                ? "Timing review…"
                : timers[arm] === null
                  ? "Not recorded"
                  : `${(timers[arm] / 1000).toFixed(2)} seconds`;
    }
    for (const button of document.querySelectorAll("[data-verdict]"))
        button.disabled =
            busy ||
            !report ||
            !timers.control ||
            !timers.treatment ||
            started.control !== null ||
            started.treatment !== null;
    $("#task-seed").value = spec.seed;
    $("#call-cost").value = spec.call_cost_milli;
    $("#human-cost").value = spec.human_cost_milli_per_second;
    $("#spec-json").value = JSON.stringify(spec, null, 2);
    $("#policy-name").textContent = capability
        ? capability.policy.replace("seasonal-", "Seasonal / period ")
        : "A policy, waiting to be learned.";
    $("#policy-note").textContent = capability
        ? "Selected by walk-forward error on Mandate A only. Frozen before future-task evaluation."
        : `${spec.training.length} observations from Mandate A. Ten candidate policies. No future-task answers.`;
    $("#training-hash").textContent = capability
        ? capability.training_sha256
        : "Not frozen";
    $("#capability-hash").textContent = capability
        ? capability.sha256
        : "Not frozen";
    $("#training-cost").textContent = capability
        ? `${capability.training_forecast_calls} prior forecast calls · charged in full`
        : "Charged in full to treatment";
    $("#gain").textContent = report
        ? fmt(report.core.metrics.advantage_before_human_milli)
        : "—";
    $("#wins").textContent = report
        ? `${report.core.metrics.task_wins} / ${spec.tasks.length}`
        : "—";
    $("#run-state").textContent = report
        ? "EXECUTED · E2"
        : capability
          ? "FROZEN · READY"
          : "AWAITING EXECUTION";
    const rows = $("#baseline-rows");
    rows.replaceChildren();
    if (report)
        for (const [id, arm] of Object.entries(report.core.arms)) {
            const tr = document.createElement("tr");
            if (id === "B6") tr.className = "highlight";
            const names = {
                B0: "B0 / Last value",
                B3: "B3 / Fixed trend",
                B5: "B5 / Current stack",
                B6: "B6 / With memory",
            };
            for (const value of [
                names[id],
                fmt(arm.error_milli),
                arm.forecast_calls,
            ]) {
                const td = document.createElement("td");
                td.textContent = value;
                tr.append(td);
            }
            rows.append(tr);
        }
    else {
        const tr = document.createElement("tr"),
            td = document.createElement("td");
        td.colSpan = 3;
        td.textContent = "Results will appear after execution.";
        tr.append(td);
        rows.append(tr);
    }
    const selected = $("#task-view").value;
    $("#task-view").replaceChildren();
    if (report)
        spec.tasks.forEach((t, i) => {
            const o = document.createElement("option");
            o.value = i;
            o.textContent = t.id;
            $("#task-view").append(o);
        });
    $("#task-view").value = selected || "0";
    $("#task-view").disabled = !report;
    $("#raw-results").textContent = report
        ? JSON.stringify(
              {
                  arms: report.core.arms,
                  metrics: report.core.metrics,
                  observations: report.observations,
                  review: report.review,
              },
              null,
              2,
          )
        : "No run yet.";
    const outcome = report ? decision(report) : null;
    $("#local-verdict").textContent =
        outcome?.bounded_transfer === "accepted" ? "ACCEPTED" : "HOLD";
    $("#local-note").textContent =
        outcome?.bounded_transfer === "accepted"
            ? "Positive cost-adjusted transfer on these tasks, within the declared forecast-error bound."
            : report?.review
              ? "The recorded review does not establish a positive, bounded transfer claim. Failure stays in the dossier."
              : "Execute and review the evidence before accepting a local claim.";
    $("#adjusted-gain").textContent =
        outcome?.adjusted_advantage_milli !== null && outcome
            ? `${fmt(outcome.adjusted_advantage_milli)} adjusted modeled units`
            : "Human review cost is pending.";
    $("#eci-level").textContent = report
        ? "E2 / Executed locally"
        : "Awaiting execution";
    $("#eci-executed").classList.toggle("current", !!report);
    chart();
}
async function perform(action) {
    if (busy) return;
    const focused = document.activeElement;
    busy = true;
    render();
    try {
        await action();
    } catch (error) {
        status(error.message, true);
    } finally {
        busy = false;
        render();
        if (focused?.isConnected && !focused.disabled)
            focused.focus({ preventScroll: true });
    }
}
for (const button of document.querySelectorAll("[data-scenario]"))
    button.addEventListener("click", () =>
        perform(async () => {
            spec = example(
                button.dataset.scenario,
                Number($("#task-seed").value),
            );
            reset();
            status("Scenario selected. Freeze the capability to begin.");
        }),
    );
for (const id of ["task-seed", "call-cost", "human-cost"])
    $("#" + id).addEventListener("change", () => {
        const seed = Number($("#task-seed").value),
            cost = Number($("#call-cost").value),
            human = Number($("#human-cost").value);
        perform(async () => {
            const candidate =
                id === "task-seed" && spec.scenario !== "custom"
                    ? example(spec.scenario, seed)
                    : parse(canonical(spec));
            candidate.seed = seed;
            candidate.call_cost_milli = cost;
            candidate.human_cost_milli_per_second = human;
            await validateSpec(candidate);
            spec = candidate;
            reset();
            status(
                "Inputs changed. Prior results and reviews have been cleared.",
            );
        });
    });
$("#apply-spec").addEventListener("click", () => {
    const raw = $("#spec-json").value;
    perform(async () => {
        const candidate = parse(raw);
        await validateSpec(candidate);
        spec = candidate;
        reset();
        status("Specification loaded. Freeze the capability before execution.");
    });
});
$("#freeze").addEventListener("click", () =>
    perform(async () => {
        capability = await freeze(spec.training);
        report = null;
        timers = { control: null, treatment: null };
        started = { control: null, treatment: null };
        save();
        status(
            `Capability frozen: ${capability.policy}. The next mission will use this policy.`,
        );
    }),
);
$("#compare").addEventListener("click", () =>
    perform(async () => {
        const next = await run(spec);
        if (next.core.capability.sha256 !== capability.sha256)
            throw new Error("Frozen capability changed");
        await verify(next);
        report = next;
        timers = { control: null, treatment: null };
        started = { control: null, treatment: null };
        save();
        status(
            "Future tasks executed and replayed. Inspect the predictions, then review both arms.",
        );
    }),
);
$("#task-view").addEventListener("change", chart);
for (const arm of ["control", "treatment"])
    $("#timer-" + arm).addEventListener("click", () => {
        if (!report) return;
        const other = arm === "control" ? "treatment" : "control";
        if (started[other] !== null) {
            status("Finish the other review timer first.", true);
            return;
        }
        if (started[arm] === null) {
            started[arm] = performance.now();
            timers[arm] = null;
            report.review = null;
            status(
                "Inspect the raw predictions and costs. Finish the timer when your review is complete.",
            );
        } else {
            timers[arm] = Math.max(
                1,
                Math.floor(performance.now() - started[arm]),
            );
            started[arm] = null;
            status(
                "Elapsed review time recorded. It does not attest active attention.",
            );
        }
        save();
        render();
    });
for (const button of document.querySelectorAll("[data-verdict]"))
    button.addEventListener("click", () =>
        perform(async () => {
            report = await reviewRun(
                report,
                button.dataset.verdict,
                $("#reviewer").value,
                $("#review-reason").value,
                timers.control,
                timers.treatment,
                "browser-elapsed",
            );
            save();
            status(
                "Review bound to the exact run. Export the complete dossier, including all open proof obligations.",
            );
        }),
    );
$("#download-spec").addEventListener("click", () =>
    download("spec.json", JSON.stringify(spec, null, 2) + "\n"),
);
$("#export-run").addEventListener("click", () =>
    perform(async () => {
        await verify(report);
        download("run.json", JSON.stringify(report, null, 2) + "\n");
        status("Run exported for browser or native replay.");
    }),
);
$("#export-docket").addEventListener("click", () =>
    perform(async () => {
        download(
            "evidence-docket.zip",
            await exportDocket(report),
            "application/zip",
        );
        status(
            "Evidence Docket exported: thirteen manuscript sections plus file checksums.",
        );
    }),
);
$("#import-run").addEventListener("change", () => {
    const file = $("#import-run").files[0];
    perform(async () => {
        if (!file) return;
        if (file.size > 1000000) throw new Error("Import exceeds one megabyte");
        const candidate = parse(await file.text());
        await verify(candidate);
        spec = candidate.spec;
        report = candidate;
        capability = candidate.core.capability;
        started = { control: null, treatment: null };
        // Preserve the imported review, but a new decision needs new measurements.
        timers = { control: null, treatment: null };
        if (candidate.review) {
            $("#reviewer").value = candidate.review.reviewer;
            $("#review-reason").value = candidate.review.reason;
        }
        save();
        status(
            "Imported run recomputed on this device. External independence is still unestablished.",
        );
    });
    $("#import-run").value = "";
});
await perform(async () => {
    const saved = localStorage.getItem(STORAGE);
    if (saved) {
        const state = parse(saved);
        if (Object.keys(state).sort().join(",") !== "report,spec")
            throw new Error("Invalid saved workspace");
        await validateSpec(state.spec);
        if (state.report) {
            await verify(state.report);
            if (canonical(state.report.spec) !== canonical(state.spec))
                throw new Error("Saved inputs differ from run");
            report = state.report;
            capability = report.core.capability;
            timers = { control: null, treatment: null };
            if (report.review) {
                $("#reviewer").value = report.review.reviewer;
                $("#review-reason").value = report.review.reason;
            }
        }
        spec = state.spec;
        status(
            "Saved workspace recovered and all recorded predictions replayed.",
        );
    } else
        status(
            "Choose a scenario, then freeze a capability learned from Mandate A.",
        );
});
document.documentElement.dataset.compoundingReady = "true";
if ("serviceWorker" in navigator)
    navigator.serviceWorker
        .register(new URL("service-worker.js", ROOT), { scope: ROOT.pathname })
        .catch(() =>
            status(
                "Offline cache unavailable. You can still run and export the experiment.",
            ),
        );
