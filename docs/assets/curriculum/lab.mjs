// SPDX-License-Identifier: Apache-2.0
import {
    evaluate,
    verify,
    validate,
    parse,
    artifacts,
    REPORT_SCHEMA,
} from "./engine.mjs?v=1.22.0";
import { zipFiles as zip } from "../compounding/engine.mjs?v=1.22.0";
const $ = (id) => document.getElementById(id),
    KEY = "alpha-curriculum-settings-v1";
let cases = [],
    source = null,
    report = null,
    revision = 0,
    editorDirty = false;
function element(tag, text, cls) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
}
function say(message, error = false) {
    $("status").textContent = message;
    $("status").classList.toggle("error", error);
}
function invalidate(
    message = "Settings changed. Run the curriculum to refresh the evidence.",
) {
    revision++;
    report = null;
    $("download").disabled = true;
    $("download-run").disabled = true;
    $("results").hidden = true;
    $("gates").replaceChildren();
    $("families").replaceChildren();
    $("heldout-task").replaceChildren();
    $("heldout-detail").replaceChildren();
    $("run-hash").textContent = "";
    $("run-state").textContent = "Changes pending";
    $("review-state").textContent = "Awaiting run";
    $("review-state").className = "pill";
    $("export-status").textContent =
        "Exports are unavailable until the current settings are evaluated.";
    say(message);
}
function sync() {
    for (const [id, key] of [
        ["seed", "seed"],
        ["rounds", "rounds"],
        ["depth", "maxDepth"],
        ["temperature", "temperature"],
    ])
        $(id).value = source[key];
    $("source").value = JSON.stringify(source, null, 2);
    $("case-note").textContent = source.note;
    editorDirty = false;
}
function settings() {
    if (editorDirty)
        throw Error("Apply the edited JSON before running or saving.");
    return validate({
        ...source,
        seed: Number($("seed").value),
        rounds: Number($("rounds").value),
        maxDepth: Number($("depth").value),
        temperature: Number($("temperature").value),
    });
}
function percent(n) {
    return (n / 100).toFixed(2) + "%";
}
function program(p) {
    return p === null
        ? "No matching hypothesis within budget"
        : p.length
          ? "x → " + p.join(" → ")
          : "x → identity";
}
function table(headers, rows, caption) {
    const t = element("table");
    if (caption) t.append(element("caption", caption));
    const head = element("thead"),
        tr = element("tr");
    for (const h of headers) {
        const th = element("th", h);
        th.scope = "col";
        tr.append(th);
    }
    head.append(tr);
    const body = element("tbody");
    for (const row of rows) {
        const line = element("tr");
        for (const value of row) line.append(element("td", String(value)));
        body.append(line);
    }
    t.append(head, body);
    return t;
}
function svg(tag, attrs) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
    return node;
}
function chart(history) {
    const root = svg("svg", {
        viewBox: "0 0 720 210",
        role: "img",
        "aria-label": "Training solve rate for each curriculum round",
    });
    const title = svg("title", {});
    title.textContent =
        "Solve rate on changing training tasks; inspect each round below.";
    root.append(title);
    for (const p of [0, 50, 100]) {
        const y = 170 - p * 1.4;
        root.append(
            svg("line", {
                x1: 42,
                x2: 690,
                y1: y,
                y2: y,
                stroke: "#d6ddd8",
                "stroke-dasharray": "3 5",
            }),
        );
        const t = svg("text", { x: 4, y: y + 4 });
        t.textContent = p + "%";
        root.append(t);
    }
    const x = (i) =>
            history.length === 1 ? 365 : 50 + (i * 630) / (history.length - 1),
        y = (r) => 170 - r.recent.accuracyBps * 0.014;
    root.append(
        svg("polyline", {
            points: history.map((r, i) => `${x(i)},${y(r)}`).join(" "),
            fill: "none",
            stroke: "#005f60",
            "stroke-width": 3,
        }),
    );
    history.forEach((r, i) => {
        root.append(
            svg("circle", { cx: x(i), cy: y(r), r: 4, fill: "#005f60" }),
        );
        const t = svg("text", { x: x(i), y: 199, "text-anchor": "middle" });
        t.textContent = r.round;
        root.append(t);
    });
    $("curve").replaceChildren(root);
}
function inspectTask(task, answer, target) {
    target.replaceChildren(element("p", program(answer.program), "code"));
    target.append(
        table(
            ["Input", "Expected", "Prediction"],
            task.inputs.map((x, i) => [
                x,
                task.expected[i],
                answer.predictions === null ? "—" : answer.predictions[i],
            ]),
        ),
    );
    target.append(
        element(
            "p",
            `${answer.solved ? "Solved" : "Not solved"} · ${answer.tried} hypotheses · ${answer.operations} operations`,
            answer.solved ? "hint success" : "hint failed",
        ),
    );
}
function showTask() {
    if (!report) return;
    const h = report.result.history[Number($("round").value) - 1],
        i = Number($("task").value),
        task = h.tasks[i],
        answer = h.recent.details[i];
    $("examples").replaceChildren(
        table(
            ["Example input", "Example output"],
            task.examples,
            "The solver receives only these examples and the test inputs.",
        ),
    );
    inspectTask(task, answer, $("solution"));
    $("oracle").textContent = program(task.oracle);
}
function showRound() {
    if (!report) return;
    const h = report.result.history[Number($("round").value) - 1];
    $("round-label").value = h.round;
    $("round-summary").replaceChildren(
        ...[
            `Difficulty ${h.difficulty} → ${h.nextDifficulty}`,
            `${h.tasks.length} distinct tasks`,
            `${h.rejected} duplicate proposals rejected`,
            `${h.replaySize} replay tasks`,
        ].map((s) => element("span", s)),
    );
    $("task").replaceChildren(
        ...h.tasks.map((t, i) => {
            const o = element("option", `${t.id} · ${t.family}`);
            o.value = i;
            return o;
        }),
    );
    $("candidates").replaceChildren(
        ...h.candidates.map((c) => {
            const tr = element(
                "tr",
                undefined,
                c.agent.id === h.winner ? "selected" : "",
            );
            for (const v of [
                c.agent.id,
                percent(c.accuracyBps),
                c.meanOperations,
                c.entropyMilliNats + " mnats",
                c.freeEnergyProxy,
                c.agent.id === h.winner
                    ? "Selected"
                    : h.pareto.includes(c.agent.id)
                      ? "Pareto frontier"
                      : "Dominated",
            ])
                tr.append(element("td", String(v)));
            return tr;
        }),
    );
    $("selection-note").textContent =
        "Accuracy and operation cost define the Pareto frontier. Selection maximizes accuracy − mean operations + entropy weight × solved-family entropy. No held-out results are used.";
    showTask();
}
function showHeldout() {
    if (!report) return;
    const i = Number($("heldout-task").value),
        r = report.result,
        t = r.heldoutTasks[i];
    $("heldout-detail").replaceChildren(
        table(["Example input", "Example output"], t.examples),
    );
    const output = element("div");
    inspectTask(t, r.candidate.details[i], output);
    $("heldout-detail").append(
        output,
        element("p", "Reference: " + program(t.oracle), "hint"),
    );
}
function render(value) {
    report = value;
    const r = value.result;
    $("results").hidden = false;
    $("accuracy").textContent = percent(r.candidate.accuracyBps);
    $("gain").textContent =
        (r.gainBps >= 0 ? "+" : "") + (r.gainBps / 100).toFixed(2);
    $("cost").textContent = r.candidate.meanOperations;
    $("run-state").textContent = "Experiment complete";
    $("review-state").textContent =
        r.status === "HOLD"
            ? "Hold · baseline retained"
            : "Eligible for review";
    $("review-state").className = "pill" + (r.status === "HOLD" ? " hold" : "");
    $("download").disabled = false;
    $("download-run").disabled = false;
    $("export-status").textContent =
        "Evidence corresponds to the current experiment. The baseline remains active.";
    $("run-hash").textContent = "Run SHA-256: " + value.sha256;
    chart(r.history);
    $("round").max = r.history.length;
    $("round").value = r.history.length;
    $("lineage-count").textContent = r.lineage.length + " CONFIGURATIONS";
    $("lineage").replaceChildren(
        ...r.lineage.map((n) =>
            element(
                "p",
                `Round ${n.round}: ${n.parent || "baseline seed"} → ${n.agent.id}`,
            ),
        ),
    );
    showRound();
    $("gates").replaceChildren(
        ...r.gates.map((g) => {
            const card = element(
                "div",
                undefined,
                "gate" + (g.passed ? "" : " hold"),
            );
            card.append(
                element("span", g.passed ? "PASS" : "HOLD"),
                element("h3", g.label),
                element(
                    "p",
                    g.id === "operations"
                        ? `${g.observed} ${g.comparison} ${g.limit} operations`
                        : `${percent(g.observed)} ${g.comparison} ${percent(g.limit)}`,
                ),
            );
            return card;
        }),
    );
    $("families").replaceChildren(
        ...Object.entries(r.candidate.families).map(([f, v]) => {
            const row = element("div", undefined, "family-row"),
                bar = element("div", undefined, "family-bar"),
                fill = element("span");
            fill.style.width = v.accuracyBps / 100 + "%";
            bar.append(fill);
            row.append(
                element("span", f),
                bar,
                element("span", `${v.correct}/${v.total}`),
            );
            return row;
        }),
    );
    $("heldout-task").replaceChildren(
        ...r.heldoutTasks.map((t, i) => {
            const o = element(
                "option",
                `${t.id} · ${r.candidate.details[i].solved ? "solved" : "not solved"}`,
            );
            o.value = i;
            return o;
        }),
    );
    showHeldout();
    say(
        `Completed ${value.input.rounds} rounds. Frozen solver ${r.candidate.agent.id}; ${r.candidate.correct}/${r.candidate.total} independent tasks solved. Baseline remains active.`,
    );
}
async function run() {
    try {
        const next = settings();
        invalidate("Running the curriculum and independent review…");
        source = next;
        sync();
        const current = revision;
        $("run-state").textContent = "Running";
        await new Promise((resolve) => setTimeout(resolve, 0));
        const result = await evaluate(source);
        if (current === revision) render(result);
    } catch (e) {
        invalidate(e.message);
        say(e.message, true);
    }
}
function download(data, name, type) {
    const url = URL.createObjectURL(new Blob([data], { type })),
        a = element("a");
    a.href = url;
    a.download = name;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
}
$("run").addEventListener("click", run);
for (const id of ["seed", "rounds", "depth", "temperature"])
    $(id).addEventListener("input", () => invalidate());
$("source").addEventListener("input", () => {
    editorDirty = true;
    invalidate("JSON changed. Apply the JSON, then run the curriculum.");
});
$("apply").addEventListener("click", () => {
    try {
        const value = validate(parse($("source").value));
        invalidate("JSON applied. Run the curriculum to evaluate it.");
        source = value;
        sync();
    } catch (e) {
        invalidate(e.message);
        say(e.message, true);
    }
});
$("case").addEventListener("change", () => {
    source = structuredClone(cases.find((c) => c.id === $("case").value));
    invalidate();
    sync();
    run();
});
$("reset").addEventListener("click", () => {
    source = structuredClone(
        cases.find((c) => c.id === $("case").value) || cases[0],
    );
    invalidate();
    sync();
    run();
});
$("round").addEventListener("input", showRound);
$("task").addEventListener("change", showTask);
$("heldout-task").addEventListener("change", showHeldout);
$("save").addEventListener("click", () => {
    try {
        localStorage.setItem(KEY, JSON.stringify(settings()));
        $("storage-status").textContent =
            "Settings saved on this device. Restore them explicitly when needed.";
    } catch (e) {
        $("storage-status").textContent = "Could not save: " + e.message;
    }
});
$("restore").addEventListener("click", () => {
    try {
        const data = localStorage.getItem(KEY);
        if (!data) throw Error("No saved settings on this device.");
        const restored = validate(parse(data));
        invalidate(
            "Saved settings restored. Run the curriculum to evaluate them.",
        );
        source = restored;
        sync();
        $("storage-status").textContent =
            "Saved settings restored; no results were restored.";
    } catch (e) {
        $("storage-status").textContent = "Could not restore: " + e.message;
    }
});
$("forget").addEventListener("click", () => {
    try {
        localStorage.removeItem(KEY);
        $("storage-status").textContent = "Saved settings removed.";
    } catch (e) {
        $("storage-status").textContent =
            "Could not remove settings: " + e.message;
    }
});
$("import").addEventListener("change", async () => {
    const file = $("import").files[0];
    if (!file) return;
    invalidate("Validating the imported file…");
    const current = revision;
    try {
        if (file.size > 1000000) throw Error("Input exceeds 1,000,000 bytes.");
        const raw = parse(
            new TextDecoder("utf-8", { fatal: true }).decode(
                await file.arrayBuffer(),
            ),
        );
        if (raw.schema === REPORT_SCHEMA) {
            const value = await verify(raw);
            if (current !== revision) return;
            source = value.input;
            sync();
            render(value);
            say(
                "Imported run independently recomputed and verified. Baseline remains active.",
            );
        } else {
            const value = validate(raw);
            if (current !== revision) return;
            source = value;
            sync();
            say("Scenario imported. Run the curriculum to evaluate it.");
        }
    } catch (e) {
        if (current === revision) say("Import rejected: " + e.message, true);
    } finally {
        $("import").value = "";
    }
});
for (const [id, bundle] of [
    ["download", true],
    ["download-run", false],
])
    $(id).addEventListener("click", async () => {
        if (!report) return;
        const snapshot = report,
            current = revision;
        try {
            $("export-status").textContent =
                "Recomputing the evidence before export…";
            const files = await artifacts(snapshot);
            if (current !== revision) return;
            if (bundle)
                download(
                    zip(
                        Object.fromEntries(
                            Object.entries(files).map(([name, bytes]) => [
                                name,
                                new TextDecoder().decode(bytes),
                            ]),
                        ),
                    ),
                    `curriculum-${snapshot.sha256.slice(0, 12)}.zip`,
                    "application/zip",
                );
            else download(files["run.json"], "run.json", "application/json");
            $("export-status").textContent = bundle
                ? "Six-file evidence ZIP downloaded."
                : "Verified run JSON downloaded.";
        } catch (e) {
            $("export-status").textContent = "Export failed: " + e.message;
        }
    });
try {
    const response = await fetch(new URL("./scenarios.json", import.meta.url));
    if (!response.ok) throw Error("Bundled scenarios could not be loaded.");
    cases = parse(await response.text()).map(validate);
    $("case").replaceChildren(
        ...cases.map((c) => {
            const o = element("option", c.title);
            o.value = c.id;
            return o;
        }),
    );
    source = structuredClone(cases[0]);
    sync();
    await run();
    if (
        "serviceWorker" in navigator &&
        !document.documentElement.dataset.packaged
    )
        navigator.serviceWorker
            .register(new URL("../../service-worker.js", import.meta.url))
            .catch(() => {});
} catch (e) {
    say(
        "Could not start: " +
            e.message +
            " Reload this page or use the Python guide.",
        true,
    );
    $("run-state").textContent = "Unavailable";
}
