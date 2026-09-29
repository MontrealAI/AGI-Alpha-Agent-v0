// SPDX-License-Identifier: Apache-2.0
import {
    evaluate,
    verify,
    validate,
    parse,
    canonical,
    artifacts,
    REPORT_SCHEMA,
} from "./engine.mjs?v=1.20.0";
import { zipFiles } from "../compounding/engine.mjs?v=1.20.0";
const $ = (id) => document.getElementById(id),
    storageKey = "agialpha.experience.settings.v1";
const fields = [
    "steps",
    "evaluationSteps",
    "memoryWindow",
    "seed",
    "exploration",
    "costWeight",
    "incidentPenalty",
    "proxyWeight",
];
let cases = [],
    source = null,
    report = null,
    revision = 0,
    dirty = false,
    jsonDirty = false,
    busy = 0;
const setText = (id, text) => {
    $(id).textContent = text;
};
function node(tag, text, className = "") {
    const item = document.createElement(tag);
    item.textContent = text;
    if (className) item.className = className;
    return item;
}
function state() {
    for (const id of ["download", "export"])
        $(id).disabled = !report || dirty || jsonDirty || busy;
    $("save").disabled = !source || jsonDirty || busy;
    $("run").disabled = busy || jsonDirty || !source;
    $("apply").disabled = busy;
    $("episode").disabled = !report;
}
function failure(error) {
    $("error").hidden = false;
    setText("error", error.message || String(error));
}
function clearError() {
    $("error").hidden = true;
    setText("error", "");
}
function stale() {
    revision++;
    dirty = true;
    state();
    setText(
        "notice",
        "Settings changed. Run the experiment to refresh results and enable exports.",
    );
}
function fill() {
    for (const id of fields)
        $(id).value =
            id === "seed"
                ? source.seed
                : id === "exploration"
                  ? source.training.explorationBps / 100
                  : id in source.training
                    ? source.training[id]
                    : source.reward[id];
    $("scenario").value = JSON.stringify(source, null, 2);
    setText("case-note", source.note);
    setText(
        "shift-note",
        source.training.shiftAt
            ? `Environment changes before interaction ${source.training.shiftAt + 1}. Retention is evaluated separately against the original environment.`
            : "No environment shift in this case. Change shiftAt in the full scenario to test adaptation.",
    );
    $("case").value = cases.some((c) => c.id === source.id)
        ? source.id
        : "custom";
}
function controls() {
    const next = structuredClone(source);
    for (const id of fields) {
        const control = $(id);
        if (!control.value.trim() || !control.checkValidity())
            throw Error(
                `Check ${control.closest("label").childNodes[0].textContent.trim()}: use a value within the displayed limits.`,
            );
        const value = Number(control.value);
        if (id === "seed") next.seed = value;
        else if (id === "exploration")
            next.training.explorationBps = Math.round(value * 100);
        else if (id in next.training) next.training[id] = value;
        else next.reward[id] = value;
    }
    return validate(next);
}
function row(parent, values) {
    const tr = document.createElement("tr");
    for (const value of values) tr.append(node("td", String(value)));
    parent.append(tr);
}
function draw() {
    const svg = $("performance");
    svg.querySelectorAll("g").forEach((n) => n.remove());
    const episodes = report.result.evaluation.episodes,
        n = episodes.length,
        curves = { baseline: [], candidate: [] };
    for (const name of Object.keys(curves)) {
        let total = 0;
        episodes.forEach((e, i) => {
            total += e[name].reward;
            curves[name].push(total / (i + 1));
        });
    }
    const values = [...curves.baseline, ...curves.candidate, 0],
        low = Math.floor(Math.min(...values) / 100) * 100,
        high = Math.ceil(Math.max(...values) / 100) * 100 + 100;
    const ns = "http://www.w3.org/2000/svg",
        g = document.createElementNS(ns, "g");
    function shape(tag, attrs, text) {
        const el = document.createElementNS(ns, tag);
        for (const [k, v] of Object.entries(attrs))
            el.setAttribute(k, String(v));
        if (text !== undefined) el.textContent = text;
        g.append(el);
        return el;
    }
    const y = (value) => 205 - ((value - low) / (high - low)) * 170;
    for (let i = 0; i < 5; i++) {
        const value = low + ((high - low) * i) / 4;
        shape("path", { d: `M55 ${y(value)} H660`, class: "grid" });
        shape(
            "text",
            { x: 46, y: y(value) + 4, "text-anchor": "end" },
            Math.round(value).toString(),
        );
    }
    for (const name of ["baseline", "candidate"])
        shape("path", {
            d: curves[name]
                .map(
                    (value, i) =>
                        `${i ? "L" : "M"}${55 + (i / (n - 1)) * 605} ${y(value)}`,
                )
                .join(" "),
            class: `${name}-line`,
        });
    shape("text", { x: 55, y: 232 }, "1");
    shape("text", { x: 660, y: 232, "text-anchor": "end" }, `${n} episodes`);
    shape("text", { x: 55, y: 17 }, "Cumulative mean reward / episode");
    svg.append(g);
    setText(
        "chart-desc",
        `Across ${n} held-out episodes, baseline mean reward is ${(report.result.evaluation.totals.baseline.reward / n).toFixed(1)} and candidate mean reward is ${(report.result.evaluation.totals.candidate.reward / n).toFixed(1)}. Exact totals are in the following table.`,
    );
}
function inspect() {
    if (!report) return;
    const event = report.result.training[Number($("episode").value) - 1],
        s = report.input;
    setText("episode-number", String(event.step));
    $("observation").replaceChildren();
    for (const [key, value] of [
        ["Context", s.contexts[event.context].label],
        ["Action", s.actions[event.action].label],
        ["Environment", event.phase],
        [
            "Outcome",
            `${event.success ? "Completed" : "Incomplete"} · ${event.incident ? "incident" : "no incident"}`,
        ],
        ["Resource cost", event.cost],
        ["Proxy score", event.proxy],
        ["Reward", event.reward],
    ])
        $("observation").append(node("dt", key), node("dd", String(value)));
}
function render() {
    const r = report.result,
        s = report.input,
        n = s.training.evaluationSteps,
        passed = r.gates.filter((g) => g.passed).length;
    setText(
        "decision",
        r.status === "REVIEW_REQUIRED"
            ? "Ready for independent review"
            : "Hold the baseline",
    );
    $("decision").classList.toggle("hold", passed < 6);
    setText(
        "gain",
        `${r.gainTotal >= 0 ? "+" : ""}${(r.gainTotal / n).toFixed(1)}`,
    );
    setText("incidents", `${r.evaluation.totals.candidate.incident} / ${n}`);
    setText("gate-count", `${passed} / 6`);
    $("totals").replaceChildren();
    for (const [metric, label] of [
        ["reward", "Reward"],
        ["success", "Successful outcomes"],
        ["incident", "Incidents"],
        ["cost", "Resource cost"],
        ["proxy", "Proxy score"],
    ])
        row($("totals"), [
            label,
            r.evaluation.totals.baseline[metric],
            r.evaluation.totals.candidate[metric],
        ]);
    $("gates").replaceChildren();
    const totals = r.evaluation.totals.candidate;
    const gateNotes = {
        gain: `Mean ${(r.gainTotal / n).toFixed(1)}; minimum ${s.gates.minGain}`,
        safety: `${((totals.incident / n) * 100).toFixed(1)}%; ceiling ${s.gates.maxIncidentBps / 100}%`,
        success: `${((totals.success / n) * 100).toFixed(1)}%; minimum ${s.gates.minSuccessBps / 100}%`,
        cost: `Mean ${(totals.cost / n).toFixed(1)}; ceiling ${s.gates.maxMeanCost}`,
        coverage: `At least ${s.gates.minSamples} retained observations per selected action`,
        retention: `Mean ${(r.retentionGainTotal / n).toFixed(1)}; floor ${-s.gates.maxRetentionLoss}`,
    };
    for (const gate of r.gates) {
        const item = node("div", "", `gate${gate.passed ? "" : " fail"}`);
        const description = node("span", gate.label);
        description.append(node("small", gateNotes[gate.id]));
        item.append(description, node("b", gate.passed ? "PASS" : "HOLD"));
        $("gates").append(item);
    }
    setText(
        "retention",
        `Original-environment retention: ${(r.retentionGainTotal / n).toFixed(1)} mean reward gain; maximum permitted loss ${s.gates.maxRetentionLoss}. No review result changes the active baseline.`,
    );
    $("policy").replaceChildren();
    s.contexts.forEach((ctx, i) => {
        const candidate = r.proposal.candidatePolicy[i];
        row($("policy"), [
            ctx.label,
            s.actions[ctx.baseline].label,
            s.actions[candidate].label,
            `${r.memory[i][candidate].length} / ${s.training.memoryWindow}`,
        ]);
    });
    $("episode").max = s.training.steps;
    $("episode").value = 1;
    inspect();
    draw();
    setText("hash", report.sha256);
}
async function run(next, imported = null) {
    const token = ++revision;
    busy += 1;
    dirty = true;
    clearError();
    state();
    setText(
        "notice",
        "Learning from outcomes, then testing the frozen candidate…",
    );
    try {
        const result = imported ? await verify(imported) : await evaluate(next);
        if (token !== revision) return;
        report = result;
        source = result.input;
        dirty = false;
        jsonDirty = false;
        fill();
        render();
        setText(
            "notice",
            `${imported ? "Imported run independently recomputed" : "Experiment complete"}. ${source.training.steps} training interactions; two separate ${source.training.evaluationSteps}-episode evaluation suites. Baseline remains active.`,
        );
    } catch (error) {
        if (token === revision) failure(error);
    } finally {
        busy -= 1;
        state();
    }
}
function download(name, bytes, mime) {
    const url = URL.createObjectURL(new Blob([bytes], { type: mime })),
        a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
for (const id of fields) $(id).addEventListener("input", stale);
$("run").addEventListener("click", () => {
    try {
        run(controls());
    } catch (error) {
        dirty = true;
        state();
        failure(error);
    }
});
$("episode").addEventListener("input", inspect);
$("case").addEventListener("change", () => {
    const selected = cases.find((c) => c.id === $("case").value);
    if (selected) run(selected);
});
$("reset").addEventListener("click", () =>
    run(cases.find((c) => c.id === $("case").value) || cases[0]),
);
$("scenario").addEventListener("input", () => {
    revision++;
    jsonDirty = true;
    state();
    setText(
        "notice",
        "JSON edits are pending. Apply the scenario or discard edits before exporting.",
    );
});
$("apply").addEventListener("click", () => {
    try {
        run(validate(parse($("scenario").value)));
    } catch (error) {
        failure(error);
    }
});
$("discard").addEventListener("click", () => {
    $("scenario").value = JSON.stringify(source, null, 2);
    jsonDirty = false;
    state();
    setText(
        "notice",
        dirty
            ? "Settings changed. Run the experiment to refresh results."
            : "JSON edits discarded. Current run remains available.",
    );
});
$("import").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const token = ++revision;
    dirty = true;
    busy += 1;
    state();
    clearError();
    try {
        if (file.size > 1000000) throw Error("Input exceeds 1 MB");
        const data = parse(
            new TextDecoder("utf-8", { fatal: true }).decode(
                await file.arrayBuffer(),
            ),
        );
        if (token !== revision) return;
        if (data?.schema === REPORT_SCHEMA) await run(data.input, data);
        else await run(data);
    } catch (error) {
        if (token === revision) failure(error);
    } finally {
        busy -= 1;
        event.target.value = "";
        state();
    }
});
$("save").addEventListener("click", () => {
    try {
        const next = controls();
        localStorage.setItem(storageKey, canonical(next));
        setText(
            "notice",
            "Settings saved in this browser. Run results are retained only in exports.",
        );
        clearError();
    } catch (error) {
        failure(error);
    }
});
$("restore").addEventListener("click", () => {
    try {
        const saved = localStorage.getItem(storageKey);
        if (!saved)
            throw Error(
                "No saved settings. Save a case first, or import a scenario.",
            );
        run(validate(parse(saved)));
    } catch (error) {
        failure(error);
    }
});
$("clear").addEventListener("click", () => {
    try {
        localStorage.removeItem(storageKey);
        setText(
            "notice",
            "Saved settings cleared. The open experiment is unchanged.",
        );
        clearError();
    } catch (error) {
        failure(error);
    }
});
$("download").addEventListener("click", () => {
    if (!report || dirty || jsonDirty || busy) return;
    download("run.json", canonical(report) + "\n", "application/json");
});
$("export").addEventListener("click", async () => {
    if (!report || dirty || jsonDirty || busy) return;
    const token = revision;
    busy += 1;
    state();
    try {
        const files = await artifacts(report);
        if (token === revision)
            download(
                "experience-review.zip",
                zipFiles(
                    Object.fromEntries(
                        Object.entries(files).map(([name, bytes]) => [
                            name,
                            new TextDecoder().decode(bytes),
                        ]),
                    ),
                ),
                "application/zip",
            );
    } catch (error) {
        failure(error);
    } finally {
        busy -= 1;
        state();
    }
});
state();
try {
    const response = await fetch(
        new URL("./scenarios.json?v=1.20.0", import.meta.url),
    );
    if (!response.ok)
        throw Error(
            `Could not load starter cases (HTTP ${response.status}). Reload or use the native CLI.`,
        );
    cases = parse(await response.text());
    for (const c of cases) {
        validate(c);
        const option = node("option", c.title);
        option.value = c.id;
        $("case").append(option);
    }
    const custom = node("option", "Imported scenario");
    custom.value = "custom";
    custom.disabled = true;
    $("case").append(custom);
    if (revision === 0) await run(cases[0]);
} catch (error) {
    failure(error);
    setText(
        "notice",
        "The lab could not start. Reload this page or use the Python command in the field guide.",
    );
    state();
}
if ("serviceWorker" in navigator && !document.documentElement.dataset.packaged)
    navigator.serviceWorker
        .register(new URL("../../service-worker.js", import.meta.url))
        .catch(() => {
            setText(
                "notice",
                "Experiment available. Offline page caching is unavailable in this browser; download a bundle to keep the evidence.",
            );
        });
