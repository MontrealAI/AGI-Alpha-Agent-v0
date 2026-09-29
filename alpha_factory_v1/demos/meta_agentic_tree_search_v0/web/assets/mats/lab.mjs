// SPDX-License-Identifier: Apache-2.0
import {
    evaluate,
    verify,
    validate,
    parse,
    canonical,
    artifacts,
    REPORT_SCHEMA,
    SCHEMA,
    uct,
} from "./engine.mjs?v=1.20.0";
import { zipFiles } from "../compounding/engine.mjs?v=1.20.0";
const $ = (id) => document.getElementById(id),
    storageKey = "agialpha.mats.settings.v1";
const fields = [
    "iterations",
    "depth",
    "seed",
    "exploration",
    "trainingSamples",
    "evaluationSamples",
    "escapePenalty",
];
let cases = [],
    source = null,
    report = null,
    revision = 0,
    busy = 0,
    dirty = false,
    jsonDirty = false,
    historical = [];
const setText = (id, value) => {
    $(id).textContent = String(value);
};
const fmt = (value) =>
    new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
function element(tag, text, className = "") {
    const item = document.createElement(tag);
    item.textContent = String(text);
    if (className) item.className = className;
    return item;
}
function state() {
    for (const id of ["download", "export"])
        $(id).disabled = !report || dirty || jsonDirty || !!busy;
    $("run").disabled = !source || jsonDirty || !!busy;
    $("apply").disabled = !!busy;
    $("save").disabled = !source || jsonDirty || !!busy;
    for (const id of ["iteration", "episode", "node", "previous", "next"])
        $(id).disabled = !report;
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
        "Settings changed. Results below belong to the previous run; run the search to update them.",
    );
}
function fill(next) {
    for (const id of fields) {
        $("" + id).value =
            id === "seed"
                ? next.seed
                : id === "exploration"
                  ? next.search.explorationBps / 10000
                  : id === "escapePenalty"
                    ? next.objective.escapePenalty
                    : next.search[id];
    }
    $("auditOracle").checked = next.search.auditOracle;
    $("json").value = JSON.stringify(next, null, 2);
    $("case").value = cases.some((item) => item.id === next.id)
        ? next.id
        : "custom";
    setText("case-note", next.note);
}
function configured() {
    if (!source) throw Error("Choose or import a planning case first.");
    const next = structuredClone(source);
    for (const id of fields) {
        const control = $(id);
        if (!control.value.trim() || !control.checkValidity())
            throw Error(
                "Check " +
                    control.closest("label").childNodes[0].textContent.trim() +
                    ": use a value within its displayed limits.",
            );
        const value = Number(control.value);
        if (id === "seed") next.seed = value;
        else if (id === "exploration")
            next.search.explorationBps = Math.round(value * 10000);
        else if (id === "escapePenalty") next.objective.escapePenalty = value;
        else next.search[id] = value;
    }
    next.search.auditOracle = $("auditOracle").checked;
    return validate(next);
}
function row(parent, values) {
    const item = document.createElement("tr");
    for (const value of values) item.append(element("td", value));
    parent.append(item);
}
function gateDescription(gate) {
    const r = report.result,
        n = report.input.search.evaluationSamples,
        g = report.input.gates,
        c = r.evaluation.candidate;
    const descriptions = {
        gain:
            fmt(r.gainTotal / n) +
            " utility gain per workload; at least " +
            fmt(g.minGain),
        quality:
            c.totals.escaped +
            " of " +
            n +
            " workloads escape with a defect; ceiling " +
            fmt(g.maxEscapeBps / 100) +
            "%",
        deadline:
            c.p95Minutes +
            " minutes at the 95th percentile; deadline " +
            g.deadline,
        cost:
            fmt(c.totals.cost / n) +
            " cost units per workload; ceiling " +
            g.maxMeanCost,
        review:
            fmt(c.totals.reviewMinutes / n) +
            " reviewer minutes per workload; ceiling " +
            g.maxReviewMinutes,
    };
    return descriptions[gate.id];
}
function render() {
    const r = report.result,
        s = report.input,
        n = s.search.evaluationSamples;
    setText("result-title", s.title);
    setText(
        "status",
        r.status === "REVIEW_REQUIRED"
            ? "Ready for independent review"
            : "Keep the baseline",
    );
    $("status").className =
        "badge " + (r.status === "REVIEW_REQUIRED" ? "pass" : "hold");
    setText(
        "result-note",
        r.status === "REVIEW_REQUIRED"
            ? "All five model gates pass. The proposed workflow remains unapproved; the baseline is still active."
            : "At least one independent model gate fails. Keep the baseline and inspect the failed conditions.",
    );
    setText("gain", (r.gainTotal > 0 ? "+" : "") + fmt(r.gainTotal / n));
    setText("evaluated", r.uniqueEvaluations + " / " + r.designSpace);
    setText(
        "space",
        r.simulationEpisodes +
            " search workloads · " +
            r.oracle.evaluations +
            " separate oracle evaluations",
    );
    setText(
        "gap",
        r.oracle.enabled
            ? fmt(r.oracle.gapTotal / s.search.trainingSamples)
            : "Not audited",
    );
    $("gates").replaceChildren();
    for (const gate of r.gates) {
        const card = element("div", "", "gate" + (gate.passed ? "" : " hold"));
        card.append(
            element(
                "strong",
                (gate.passed ? "PASS · " : "HOLD · ") + gate.label,
            ),
        );
        const detail = element("span", gateDescription(gate));
        detail.title =
            "Exact comparison: " +
            gate.observed +
            " " +
            gate.comparison +
            " " +
            gate.limit;
        card.append(detail);
        $("gates").append(card);
    }
    $("comparison").replaceChildren();
    for (const [label, key, format] of [
        ["Mean utility", "utility", (v) => fmt(v / n)],
        ["Mean resource cost", "cost", (v) => fmt(v / n) + " units"],
        ["Mean delivery time", "makespan", (v) => fmt(v / n) + " min"],
        ["Escaped defects", "escaped", (v) => v + " / " + n],
        ["Mean reviewer effort", "reviewMinutes", (v) => fmt(v / n) + " min"],
        ["Detected rework events", "rework", (v) => String(v)],
    ])
        row($("comparison"), [
            label,
            format(r.evaluation.baseline.totals[key]),
            format(r.evaluation.candidate.totals[key]),
        ]);
    row($("comparison"), [
        "95th-percentile delivery",
        r.evaluation.baseline.p95Minutes + " min",
        r.evaluation.candidate.p95Minutes + " min",
    ]);
    $("policy").replaceChildren();
    s.stages.forEach((stage, index) =>
        row($("policy"), [
            stage.label + " · " + stage.metaAgent,
            stage.choices[stage.baseline].label,
            stage.choices[r.candidate[index]].label,
        ]),
    );
    $("iteration").max = r.trace.length;
    $("iteration").value = r.trace.length;
    $("episode").max = n;
    $("episode").value = 1;
    setText("hash", "Run SHA-256 · " + report.sha256);
    renderIteration();
    renderEpisode();
}
function renderIteration() {
    if (!report) return;
    const r = report.result,
        index = Number($("iteration").value) - 1,
        event = r.trace[index];
    setText("iteration-label", index + 1 + " / " + r.trace.length);
    const prefix = r.trace.slice(0, index + 1),
        visible = new Set([
            0,
            ...prefix
                .map((item) => item.expanded)
                .filter((item) => item !== null),
        ]);
    historical = r.nodes.map(() => ({ visits: 0, totalQ: 0 }));
    for (const item of prefix)
        for (const id of item.path) {
            historical[id].visits++;
            historical[id].totalQ += item.valueQ;
        }
    const nodes = r.nodes.filter((node) => visible.has(node.id));
    const positions = new Map(),
        maxDepth = Math.max(...nodes.map((item) => item.depth), 1);
    const ranks = new Map();
    let leaves = 0;
    function place(id) {
        const children = r.nodes[id].children.filter((child) =>
            visible.has(child),
        );
        const rank = children.length
            ? children.map(place).reduce((a, b) => a + b, 0) / children.length
            : leaves++;
        ranks.set(id, rank);
        return rank;
    }
    place(0);
    for (const item of nodes)
        positions.set(item.id, [
            35 + (item.depth / maxDepth) * 685,
            25 + ((ranks.get(item.id) + 1) / (leaves + 1)) * 280,
        ]);
    const svg = $("tree"),
        ns = "http://www.w3.org/2000/svg";
    svg.querySelectorAll("g").forEach((item) => item.remove());
    const group = document.createElementNS(ns, "g");
    function shape(tag, attributes) {
        const item = document.createElementNS(ns, tag);
        for (const [key, value] of Object.entries(attributes))
            item.setAttribute(key, String(value));
        group.append(item);
    }
    for (const item of nodes) {
        if (item.parent === null) continue;
        const a = positions.get(item.parent),
            b = positions.get(item.id),
            active = event.path.includes(item.id);
        shape("line", {
            x1: a[0],
            y1: a[1],
            x2: b[0],
            y2: b[1],
            stroke: active ? "#765297" : "#d6cddd",
            "stroke-width": active ? 2.8 : 1,
        });
    }
    for (const item of nodes) {
        const [x, y] = positions.get(item.id),
            active = event.path.includes(item.id);
        shape("circle", {
            cx: x,
            cy: y,
            r: item.id === 0 ? 7 : active ? 5 : 3,
            fill: active ? "#765297" : "#afa1bd",
            stroke: item.id === event.expanded ? "#9b6219" : "none",
            "stroke-width": 2,
        });
    }
    svg.append(group);
    setText(
        "tree-description",
        nodes.length +
            " expanded nodes through iteration " +
            (index + 1) +
            ". Highlighted path: " +
            event.path.join(", ") +
            ". Use the node selector for exact statistics.",
    );
    const change =
        event.expanded === null ? null : r.nodes[event.expanded].rewrite;
    setText(
        "iteration-detail",
        (change
            ? report.input.stages[change.stage].metaAgent +
              " rewrote " +
              report.input.stages[change.stage].label +
              ". "
            : "Revisited an expanded terminal design. ") +
            event.rollout.length +
            " further rollout rewrites; " +
            fmt(event.utilityTotal / report.input.search.trainingSamples) +
            " mean training utility. Backpropagated once to each of " +
            event.path.length +
            " selected nodes.",
    );
    $("node").replaceChildren();
    for (const item of nodes) {
        const option = element(
            "option",
            "Node " +
                item.id +
                " · depth " +
                item.depth +
                " · " +
                historical[item.id].visits +
                " visits",
        );
        option.value = item.id;
        $("node").append(option);
    }
    $("node").value = event.expanded ?? event.path.at(-1);
    renderNode();
    $("rollout-policy").replaceChildren();
    report.input.stages.forEach((stage, i) =>
        row($("rollout-policy"), [
            stage.label,
            stage.choices[event.policy[i]].label,
        ]),
    );
}
function renderNode() {
    if (!report) return;
    const node = report.result.nodes[Number($("node").value)],
        stats = historical[node.id];
    const mean = stats.visits ? stats.totalQ / stats.visits / 1000000 : 0;
    const confidence =
        node.parent === null
            ? "root"
            : fmt(
                  uct(
                      stats.totalQ,
                      stats.visits,
                      historical[node.parent].visits,
                      report.input.search.explorationBps,
                  ) / 1000000,
              );
    setText(
        "node-detail",
        "After iteration " +
            $("iteration").value +
            ": " +
            stats.visits +
            " visits · mean normalized rollout value " +
            fmt(mean) +
            " · UCT value " +
            confidence +
            " · policy [" +
            node.policy.join(", ") +
            "]. Choice indices follow scenario order.",
    );
}
function renderEpisode() {
    if (!report) return;
    const index = Number($("episode").value) - 1,
        e = report.result.evaluation.candidate.episodes[index],
        b = report.result.evaluation.baseline.episodes[index];
    setText(
        "episode-detail",
        "Workload " +
            (index + 1) +
            ": baseline " +
            b.makespan +
            " min / " +
            b.cost +
            " cost units; candidate " +
            e.makespan +
            " min / " +
            e.cost +
            " cost units. Candidate escaped defects: " +
            e.escaped +
            ".",
    );
    $("schedule").replaceChildren();
    for (const task of e.stages) {
        const stage = report.input.stages[task.stage],
            pool = report.input.resources.find(
                (item) => item.id === stage.resource,
            );
        row($("schedule"), [
            stage.label,
            pool.label + " / " + (task.lane + 1),
            task.start + " → " + task.end,
            task.rework ? "Detected and repaired" : "None",
        ]);
    }
}
async function run(next) {
    const token = ++revision;
    busy++;
    dirty = true;
    clearError();
    state();
    setText(
        "notice",
        "Searching competing branches and evaluating the frozen design…",
    );
    try {
        next = validate(next);
        await new Promise((resolve) => requestAnimationFrame(resolve));
        const computed = await evaluate(next);
        if (token !== revision) return;
        source = next;
        report = computed;
        dirty = false;
        jsonDirty = false;
        fill(next);
        render();
        setText(
            "notice",
            "Search complete. All calculations ran locally. Candidate proposals remain unapproved.",
        );
    } catch (error) {
        if (token === revision) failure(error);
    } finally {
        busy--;
        state();
    }
}
function download(name, bytes, mime) {
    const url = URL.createObjectURL(new Blob([bytes], { type: mime })),
        a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
for (const id of [...fields, "auditOracle"])
    $(id).addEventListener("input", stale);
$("case").addEventListener("change", () => {
    const next = cases.find((item) => item.id === $("case").value);
    if (next) run(structuredClone(next));
});
$("run").addEventListener("click", () => {
    try {
        run(configured());
    } catch (error) {
        failure(error);
    }
});
$("iteration").addEventListener("input", renderIteration);
$("node").addEventListener("change", renderNode);
$("episode").addEventListener("input", renderEpisode);
$("previous").addEventListener("click", () => {
    $("iteration").value = Math.max(1, Number($("iteration").value) - 1);
    renderIteration();
});
$("next").addEventListener("click", () => {
    $("iteration").value = Math.min(
        Number($("iteration").max),
        Number($("iteration").value) + 1,
    );
    renderIteration();
});
$("json").addEventListener("input", () => {
    jsonDirty = true;
    revision++;
    state();
    setText(
        "notice",
        "JSON edited. Apply the model before running or exporting. Previous results are unchanged.",
    );
});
$("apply").addEventListener("click", () => {
    try {
        const input = parse($("json").value);
        run(validate(input));
    } catch (error) {
        failure(error);
    }
});
$("download").addEventListener("click", () => {
    if (report && !dirty && !jsonDirty && !busy)
        download("run.json", canonical(report) + "\n", "application/json");
});
$("export").addEventListener("click", async () => {
    if (!report || dirty || jsonDirty || busy) return;
    const token = revision,
        current = report;
    busy++;
    state();
    clearError();
    try {
        const files = await artifacts(current);
        if (token !== revision) return;
        download(
            "mats-" +
                current.input.id +
                "-" +
                current.sha256.slice(0, 12) +
                ".zip",
            zipFiles(
                Object.fromEntries(
                    Object.entries(files).map(([name, data]) => [
                        name,
                        new TextDecoder("utf-8", { fatal: true }).decode(data),
                    ]),
                ),
            ),
            "application/zip",
        );
    } catch (error) {
        failure(error);
    } finally {
        busy--;
        state();
    }
});
$("import").addEventListener("change", async () => {
    const file = $("import").files[0];
    if (!file) return;
    const token = ++revision;
    busy++;
    dirty = true;
    state();
    clearError();
    try {
        if (file.size > 1000000) throw Error("Input exceeds 1 MB");
        const input = parse(
            new TextDecoder("utf-8", { fatal: true }).decode(
                await file.arrayBuffer(),
            ),
        );
        let next;
        if (input.schema === REPORT_SCHEMA) next = (await verify(input)).input;
        else if (input.schema === SCHEMA) next = validate(input);
        else throw Error("Unsupported scenario or run schema");
        if (token === revision) await run(next);
    } catch (error) {
        if (token === revision) failure(error);
    } finally {
        busy--;
        state();
        $("import").value = "";
    }
});
$("save").addEventListener("click", () => {
    try {
        const input = configured();
        localStorage.setItem(
            storageKey,
            canonical({ schema: storageKey, input }),
        );
        clearError();
        setText(
            "notice",
            "Settings saved on this device. Saving does not run or approve a design.",
        );
    } catch (error) {
        failure(error);
    }
});
$("restore").addEventListener("click", () => {
    try {
        const saved = localStorage.getItem(storageKey);
        if (!saved) throw Error("No saved MATS settings on this device.");
        const value = parse(saved);
        if (
            value.schema !== storageKey ||
            canonical(Object.keys(value).sort()) !==
                canonical(["input", "schema"])
        )
            throw Error("Unsupported saved settings");
        run(validate(value.input));
    } catch (error) {
        failure(error);
    }
});
$("clear").addEventListener("click", () => {
    try {
        localStorage.removeItem(storageKey);
        clearError();
        setText(
            "notice",
            "Saved MATS settings cleared. Current results and other applications’ data remain intact.",
        );
    } catch (error) {
        failure(error);
    }
});
async function start() {
    state();
    try {
        const response = await fetch(
            new URL("./scenarios.json", import.meta.url),
        );
        if (!response.ok)
            throw Error("Unable to load the bundled planning cases");
        cases = parse(await response.text());
        for (const item of cases) validate(item);
        for (const item of cases) {
            const option = element("option", item.title);
            option.value = item.id;
            $("case").append(option);
        }
        const custom = element("option", "Imported / edited model");
        custom.value = "custom";
        custom.disabled = true;
        $("case").append(custom);
        const selected = new URLSearchParams(location.search).get("case");
        source = structuredClone(
            cases.find((item) => item.id === selected) || cases[0],
        );
        await run(source);
        if (
            document.documentElement.dataset.packaged !== "true" &&
            "serviceWorker" in navigator
        )
            navigator.serviceWorker
                .register(new URL("../../service-worker.js", import.meta.url))
                .catch(() => {});
    } catch (error) {
        failure(error);
        setText(
            "notice",
            "The lab could not start. Reload this page or use the supported local CLI.",
        );
    } finally {
        state();
    }
}
start();
