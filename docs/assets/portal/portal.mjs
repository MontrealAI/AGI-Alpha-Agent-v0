import { verifyAgentExport } from "./verify-export.mjs";
// SPDX-License-Identifier: Apache-2.0
const $ = (id) => document.getElementById(id);
const clone = (value) => structuredClone(value);
const memoryKey = "agialpha.portal.reviewed.v1";
let examples, request, activeWorker, result, resultRequest, aiWorker, aiTimeout;
const methods = {
    allocation: "Exact bounded search",
    research: "Source-grounded extraction",
    schedule: "Job-priority search",
    forecast: "Temporal holdout comparison",
};
const hints = {
    allocation:
        "Edit the options, budget and risk limit. Values are your planning assumptions. Up to 18 indivisible items.",
    research:
        "Paste sources you are allowed to use. The browser ranks exact passages against your goal; it does not browse the web.",
    schedule:
        "Each job lists operations in order as machine:duration, separated by commas. Up to 7 jobs, with one job per machine at a time.",
    forecast:
        "Paste 12–2,000 observations, oldest first. Selection uses training data; the final holdout is evaluated separately.",
};
function node(tag, content, className) {
    const element = document.createElement(tag);
    if (content !== undefined) element.textContent = content;
    if (className) element.className = className;
    return element;
}
function status(message, error = false) {
    $("mission-status").textContent = message;
    $("mission-status").classList.toggle("error", error);
}
function invalidate() {
    result = undefined;
    resultRequest = undefined;
    $("mission-result").hidden = true;
    if (activeWorker) stopMission();
}
function sync() {
    request.goal = $("mission-goal").value;
    $("mission-json").value = JSON.stringify(request, null, 2);
    invalidate();
}
function input(value, type, label, change) {
    const el = node("input");
    el.type = type;
    el.value = value;
    el.setAttribute("aria-label", label);
    if (type === "number") {
        el.step = "1";
        el.min = "0";
    } else el.maxLength = 300;
    el.addEventListener("input", () => {
        change(
            type === "number"
                ? el.value === ""
                    ? NaN
                    : Number(el.value)
                : el.value,
        );
        sync();
    });
    return el;
}
function field(label, value, change, type = "number") {
    const wrap = node("label", label);
    wrap.append(input(value, type, label, change));
    return wrap;
}
function makeTable(headers) {
    const wrap = node("div", undefined, "table-wrap");
    const table = node("table"),
        head = node("thead"),
        row = node("tr"),
        body = node("tbody");
    for (const header of headers) {
        const th = node("th", header);
        th.scope = "col";
        row.append(th);
    }
    head.append(row);
    table.append(head, body);
    wrap.append(table);
    return { wrap, body };
}
function removeButton(action, label) {
    const button = node("button", "×");
    button.type = "button";
    button.setAttribute("aria-label", label);
    button.addEventListener("click", action);
    return button;
}
function addButton(label, action) {
    const button = node("button", label, "text-button");
    button.type = "button";
    button.addEventListener("click", action);
    return button;
}
function renderFields() {
    const root = $("mission-fields");
    root.replaceChildren();
    const work = request.work;
    $("mission-help").textContent = hints[work.kind];
    $("method-chip").textContent = methods[work.kind];
    for (const button of document.querySelectorAll("[data-kind]"))
        button.setAttribute(
            "aria-pressed",
            String(button.dataset.kind === work.kind),
        );
    if (work.kind === "allocation") {
        const fields = node("div", undefined, "fields-row");
        fields.append(
            field("Budget", work.budget, (v) => (work.budget = v)),
            field("Maximum risk", work.max_risk, (v) => (work.max_risk = v)),
            field(
                "Unit label",
                work.unit || "",
                (v) => (work.unit = v),
                "text",
            ),
        );
        const { wrap, body } = makeTable(["Item", "Cost", "Value", "Risk", ""]);
        work.items.forEach((item, i) => {
            const row = node("tr");
            for (const key of ["id", "cost", "value", "risk"]) {
                const cell = node("td");
                cell.append(
                    input(
                        item[key],
                        key === "id" ? "text" : "number",
                        `Item ${i + 1} ${key}`,
                        (value) => (item[key] = value),
                    ),
                );
                row.append(cell);
            }
            const cell = node("td");
            cell.append(
                removeButton(
                    () => {
                        work.items.splice(i, 1);
                        renderFields();
                        sync();
                    },
                    `Remove item ${i + 1}`,
                ),
            );
            row.append(cell);
            body.append(row);
        });
        root.append(
            fields,
            wrap,
            addButton("+ Add option", () => {
                if (work.items.length >= 18)
                    return status("The browser supports up to 18 items.", true);
                work.items.push({
                    id: `Item-${crypto.randomUUID().slice(0, 6)}`,
                    cost: 1,
                    value: 1,
                    risk: 0,
                });
                renderFields();
                sync();
            }),
        );
    } else if (work.kind === "research") {
        work.sources.forEach((source, i) => {
            const block = node("div", undefined, "source-block");
            block.append(
                field(
                    `Source ${i + 1} title`,
                    source.title,
                    (v) => (source.title = v),
                    "text",
                ),
            );
            const label = node("label", `Source ${i + 1} text`),
                area = node("textarea");
            area.value = source.text;
            area.rows = 3;
            area.maxLength = 20000;
            area.addEventListener("input", () => {
                source.text = area.value;
                sync();
            });
            label.append(area);
            block.append(
                label,
                addButton(`Remove source ${i + 1}`, () => {
                    work.sources.splice(i, 1);
                    renderFields();
                    sync();
                }),
            );
            root.append(block);
        });
        root.append(
            addButton("+ Add source", () => {
                if (work.sources.length >= 20)
                    return status("Use up to 20 sources.", true);
                work.sources.push({
                    id: crypto.randomUUID(),
                    title: "New source",
                    text: "",
                });
                renderFields();
                sync();
            }),
        );
    } else if (work.kind === "schedule") {
        work.jobs.forEach((job, i) => {
            const block = node("div", undefined, "source-block"),
                row = node("div", undefined, "fields-row");
            row.append(
                field(`Job ${i + 1} ID`, job.id, (v) => (job.id = v), "text"),
                field(`Job ${i + 1} due time`, job.due, (v) => (job.due = v)),
            );
            const label = node("label", `Job ${i + 1} operations`),
                area = node("textarea");
            area.value = job.operations
                .map((op) => `${op.machine}:${op.duration}`)
                .join(", ");
            area.rows = 2;
            area.maxLength = 2000;
            area.addEventListener("input", () => {
                job.operations = area.value.split(",").map((part) => {
                    const colon = part.lastIndexOf(":");
                    return {
                        machine: part.slice(0, colon).trim(),
                        duration:
                            colon < 0 ? NaN : Number(part.slice(colon + 1)),
                    };
                });
                sync();
            });
            label.append(area);
            block.append(
                row,
                label,
                addButton(`Remove job ${i + 1}`, () => {
                    work.jobs.splice(i, 1);
                    renderFields();
                    sync();
                }),
            );
            root.append(block);
        });
        root.append(
            addButton("+ Add job", () => {
                if (work.jobs.length >= 7)
                    return status(
                        "Use up to 7 jobs in browser priority search.",
                        true,
                    );
                work.jobs.push({
                    id: `Job-${work.jobs.length + 1}`,
                    due: 20,
                    operations: [{ machine: "mill", duration: 1 }],
                });
                renderFields();
                sync();
            }),
        );
    } else if (work.kind === "forecast") {
        const label = node(
                "label",
                "Observations, separated by commas or whitespace",
                "field-label",
            ),
            area = node("textarea");
        area.rows = 4;
        area.value = work.observations.join(", ");
        area.maxLength = 50000;
        area.addEventListener("input", () => {
            work.observations = area.value.trim()
                ? area.value
                      .trim()
                      .split(/[\s,;]+/)
                      .map(Number)
                : [];
            sync();
        });
        label.append(area);
        const row = node("div", undefined, "fields-row");
        row.append(
            field(
                "Holdout observations",
                work.holdout,
                (v) => (work.holdout = v),
            ),
            field("Future periods", work.horizon, (v) => (work.horizon = v)),
            field("Season length", work.season ?? 1, (v) => (work.season = v)),
        );
        root.append(label, row);
    }
}
function loadMission(data) {
    if (
        !data ||
        typeof data.goal !== "string" ||
        !data.work ||
        !methods[data.work.kind]
    )
        throw new Error(
            "Import a supported native mission with goal and work fields.",
        );
    const work = data.work;
    if (
        work.kind === "allocation" &&
        (!Array.isArray(work.items) ||
            work.items.length > 18 ||
            work.items.some((x) => !x || typeof x !== "object"))
    )
        throw new Error("Allocation needs at most 18 item objects.");
    if (
        work.kind === "research" &&
        (!Array.isArray(work.sources) ||
            work.sources.length > 20 ||
            work.sources.some((x) => !x || typeof x !== "object"))
    )
        throw new Error("Research needs at most 20 source objects.");
    if (
        work.kind === "schedule" &&
        (!Array.isArray(work.jobs) ||
            work.jobs.length > 7 ||
            work.jobs.some(
                (x) =>
                    !x ||
                    !Array.isArray(x.operations) ||
                    x.operations.length > 12 ||
                    x.operations.some((op) => !op || typeof op !== "object"),
            ))
    )
        throw new Error(
            "Schedule needs up to 7 jobs with 1–12 operation objects each.",
        );
    if (
        work.kind === "forecast" &&
        (!Array.isArray(work.observations) || work.observations.length > 2000)
    )
        throw new Error("Forecast needs up to 2,000 observations.");
    if (JSON.stringify(data).length > 250000)
        throw new Error("Mission exceeds 250,000 characters.");
    invalidate();
    request = clone(data);
    $("mission-goal").value = request.goal;
    renderFields();
    $("mission-json").value = JSON.stringify(request, null, 2);
    status("Ready. Review the inputs, then run your mission.");
}
function download(data, name) {
    const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
    );
    const link = node("a");
    link.href = url;
    link.download = name;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
}
async function digest(value) {
    const bytes = await crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(JSON.stringify(value)),
    );
    return [...new Uint8Array(bytes)]
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
}
function format(value) {
    return typeof value === "number"
        ? Number(value.toFixed(5)).toLocaleString()
        : String(value);
}
function chart(result) {
    const root = $("result-chart");
    root.replaceChildren();
    if (result.kind !== "forecast") return;
    const observed = result.evidence.observations,
        future = result.evidence.future,
        all = [...observed, ...future];
    const min = Math.min(...all),
        max = Math.max(...all),
        span = max - min || 1;
    const ns = "http://www.w3.org/2000/svg",
        svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 900 190");
    svg.setAttribute("role", "img");
    svg.setAttribute(
        "aria-label",
        "Observed series in green; future baseline estimates in dashed orange. Exact values are in the table.",
    );
    function line(values, start, color, dashed) {
        const el = document.createElementNS(ns, "polyline");
        el.setAttribute(
            "points",
            values
                .map(
                    (value, i) =>
                        `${20 + ((i + start) / Math.max(1, all.length - 1)) * 860},${160 - ((value - min) / span) * 135}`,
                )
                .join(" "),
        );
        el.setAttribute("fill", "none");
        el.setAttribute("stroke", color);
        el.setAttribute("stroke-width", "3");
        if (dashed) el.setAttribute("stroke-dasharray", "7 5");
        svg.append(el);
    }
    line(observed, 0, "#446b37");
    line([observed.at(-1), ...future], observed.length - 1, "#a25b22", true);
    root.append(
        svg,
        node(
            "p",
            "Observed history — green. Future estimates — dashed orange.",
            "helper",
        ),
    );
}
function renderResult(data) {
    result = data;
    $("mission-result").hidden = false;
    $("result-method").textContent = data.method;
    $("result-summary").textContent = data.summary;
    $("result-metrics").replaceChildren(
        ...data.metrics.map(([label, value]) => {
            const el = node("div", undefined, "metric");
            el.append(node("b", format(value)), node("small", label));
            return el;
        }),
    );
    const { wrap, body } = makeTable(data.headers);
    for (const row of data.rows) {
        const tr = node("tr");
        row.forEach((value) => tr.append(node("td", format(value))));
        if (data.kind === "allocation" && row[1] === "Yes")
            tr.className = "winner";
        body.append(tr);
    }
    $("result-table").replaceChildren(wrap);
    $("result-checks").replaceChildren(
        ...data.checks.map((check) => node("li", check)),
    );
    $("result-limits").textContent = data.limits;
    $("result-json").textContent = JSON.stringify(data, null, 2);
    $("review-note").value = "";
    $("approve-result").disabled = false;
    $("reject-result").disabled = false;
    chart(data);
    $("mission-result").scrollIntoView({
        behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
            ? "instant"
            : "smooth",
        block: "start",
    });
}
function setBusy(busy) {
    $("run-mission").disabled = busy;
    $("stop-mission").hidden = !busy;
}
function stopMission() {
    activeWorker?.terminate();
    activeWorker = undefined;
    setBusy(false);
    status("Stopped. No result was approved or saved.");
}
function saved() {
    try {
        const values = JSON.parse(localStorage.getItem(memoryKey) || "[]");
        return Array.isArray(values)
            ? values
                  .filter(
                      (value) =>
                          value?.payload?.request?.work?.kind &&
                          typeof value.payload.request.goal === "string",
                  )
                  .slice(-20)
            : [];
    } catch {
        $("storage-status").textContent =
            "Browser storage is unavailable or unreadable. Export reports to keep your work.";
        return [];
    }
}
function renderMemory() {
    const items = saved();
    $("history-count").textContent = `${items.length} saved`;
    $("history-list").replaceChildren(
        ...items
            .slice()
            .reverse()
            .map((item) => {
                const row = node("div", undefined, "history-row");
                row.append(
                    node(
                        "span",
                        `${item.payload.request.work.kind} · ${item.payload.request.goal}`,
                    ),
                );
                row.append(
                    addButton("Load inputs", () =>
                        guarded(async () => {
                            if ((await digest(item.payload)) !== item.sha256)
                                throw new Error(
                                    "Stored report integrity check failed. Use your independently retained export.",
                                );
                            loadMission(item.payload.request);
                            $("workbench").scrollIntoView();
                        }),
                    ),
                    addButton("Export", () =>
                        download(item, "agialpha-browser-report.json"),
                    ),
                );
                return row;
            }),
    );
}
async function guarded(action) {
    try {
        await action();
    } catch (error) {
        status(error.message, true);
    }
}
$("mission-goal").addEventListener("input", sync);
$("apply-json").addEventListener("click", () =>
    guarded(() => loadMission(JSON.parse($("mission-json").value))),
);
$("mission-import").addEventListener("change", () =>
    guarded(async () => {
        const file = $("mission-import").files[0];
        if (!file) return;
        if (file.size > 512 * 1024)
            throw new Error("Choose a JSON file smaller than 512 KiB.");
        let data = JSON.parse(await file.text());
        if (data.schema === "agialpha-browser-report-v1") {
            if ((await digest(data.payload)) !== data.sha256)
                throw new Error("Report integrity check failed.");
            data = data.payload.request;
        }
        loadMission(data);
        $("mission-import").value = "";
    }),
);
for (const button of document.querySelectorAll("[data-kind]"))
    button.addEventListener("click", () => {
        if (examples) loadMission(examples[button.dataset.kind]);
    });
$("reset-example").addEventListener("click", () => {
    if (examples && request) loadMission(examples[request.work.kind]);
});
$("export-mission").addEventListener("click", () =>
    guarded(() => {
        if (!request) throw new Error("Wait for the examples to load.");
        download(request, `agialpha-${request.work.kind}-mission.json`);
        status(
            "Inputs downloaded. Import this file in your local agent console to continue.",
        );
    }),
);
$("stop-mission").addEventListener("click", stopMission);
$("mission-form").addEventListener("submit", (event) => {
    event.preventDefault();
    guarded(() => {
        if (!request) throw new Error("The examples are still loading.");
        invalidate();
        const snapshot = clone(request);
        resultRequest = snapshot;
        setBusy(true);
        status("Running locally. You can stop the worker at any time.");
        activeWorker = new Worker(
            new URL("./mission-worker.mjs", import.meta.url),
            { type: "module" },
        );
        activeWorker.onmessage = (event) => {
            if (event.data.type === "progress") status(event.data.message);
            else {
                setBusy(false);
                activeWorker.terminate();
                activeWorker = undefined;
                if (event.data.type === "error")
                    status(event.data.message, true);
                else {
                    renderResult(event.data.result);
                    status(
                        "Checks complete. Inspect the result and add your review.",
                    );
                }
            }
        };
        activeWorker.onerror = () => {
            activeWorker?.terminate();
            activeWorker = undefined;
            setBusy(false);
            status(
                "The mission worker could not start. Reload the current site over HTTPS, then retry.",
                true,
            );
        };
        activeWorker.postMessage(snapshot);
    });
});
$("approve-result").addEventListener("click", () =>
    guarded(async () => {
        if (!result || !resultRequest)
            throw new Error("Run a mission before reviewing.");
        const note = $("review-note").value.trim();
        if (!note)
            throw new Error("Add a review note explaining what you checked.");
        $("approve-result").disabled = true;
        $("reject-result").disabled = true;
        const payload = {
            id: crypto.randomUUID(),
            created_at: new Date().toISOString(),
            request: clone(resultRequest),
            result: clone(result),
            review: { approved: true, note },
            provenance:
                "Browser algorithms; human review is self-declared; no agent signature or payment verification.",
        };
        const report = {
            schema: "agialpha-browser-report-v1",
            payload,
            sha256: await digest(payload),
        };
        if ($("remember-result").checked) {
            try {
                const items = saved();
                items.push(report);
                localStorage.setItem(
                    memoryKey,
                    JSON.stringify(items.slice(-20)),
                );
                renderMemory();
                $("storage-status").textContent =
                    "Reviewed inputs and results saved on this device only.";
            } catch {
                $("storage-status").textContent =
                    "Could not save in browser storage. Your downloaded report keeps the result.";
            }
        }
        download(report, `agialpha-${payload.result.kind}-reviewed.json`);
        $("approve-result").disabled = true;
        $("reject-result").disabled = true;
        status(
            "Review recorded and report exported. No payment or external action was taken.",
        );
    }),
);
$("reject-result").addEventListener("click", () => {
    if (result) {
        $("approve-result").disabled = true;
        $("reject-result").disabled = true;
        status(
            "Result rejected. Adjust the inputs and run again. Nothing was saved.",
        );
    }
});
$("clear-history").addEventListener("click", () =>
    guarded(() => {
        localStorage.removeItem(memoryKey);
        renderMemory();
        $("storage-status").textContent =
            "Saved browser mission memory cleared. Downloaded files remain with you.";
    }),
);
const wheelDescriptions = [
    "Give the mission a goal and bounded, explicit inputs.",
    "Bring source evidence and observations to the problem.",
    "Compare alternatives using a disclosed method.",
    "Build a candidate allocation, schedule, forecast or brief.",
    "Inspect trade-offs, constraints and independent checks.",
    "Review and export; retain useful work and continue with your agent.",
];
for (const button of document.querySelectorAll(".wheel-node"))
    button.addEventListener("click", () => {
        for (const other of document.querySelectorAll(".wheel-node"))
            other.setAttribute("aria-pressed", String(other === button));
        $("wheel-caption").textContent =
            `${button.textContent.trim().replace(/^\d+\s*/, "")} · ${wheelDescriptions[Number(button.dataset.stage)]}`;
    });
const cards = [...document.querySelectorAll(".demo-card")];
$("search-input").addEventListener("input", () => {
    const term = $("search-input").value.toLowerCase().trim();
    for (const card of cards)
        card.hidden = !`${card.textContent} ${card.dataset.summary || ""}`
            .toLowerCase()
            .includes(term);
    const count = cards.filter((card) => !card.hidden).length;
    $("result-count").textContent = `${count} of ${cards.length} entries`;
    $("no-results").hidden = count !== 0;
});
$("search-input").dispatchEvent(new Event("input"));
function installCommands() {
    const executable =
        $("platform").value === "windows"
            ? ".\\.venv-agent\\Scripts\\alpha-agent.exe"
            : ".venv-agent/bin/alpha-agent";
    const python = $("platform").value === "windows" ? "python" : "python3";
    $("install-commands").textContent =
        `${python} install_agent.py --release-dir . --venv .venv-agent\n${executable} --home ./agent-state init\n${executable} --home ./agent-state doctor\n${executable} --home ./agent-state serve`;
}
$("platform").addEventListener("change", installCommands);
installCommands();
$("copy-install").addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText($("install-commands").textContent);
        $("copy-status").textContent =
            "Commands copied. Run them in the folder with your downloaded release files.";
    } catch {
        $("copy-status").textContent =
            "Clipboard unavailable. Select and copy the commands above.";
    }
});
function aiBusy(busy) {
    $("ai-generate").disabled = busy;
    $("ai-stop").hidden = !busy;
}
function aiStop() {
    clearTimeout(aiTimeout);
    aiWorker?.terminate();
    aiWorker = undefined;
    aiBusy(false);
    $("ai-status").textContent =
        "Stopped. No prompt was sent to a model provider. Cached model downloads may remain on this device.";
}
$("ai-stop").addEventListener("click", aiStop);
$("ai-generate").addEventListener("click", () => {
    const prompt = $("ai-prompt").value.trim();
    if (!prompt) {
        $("ai-status").textContent = "Enter text for the model to continue.";
        return;
    }
    aiBusy(true);
    $("ai-status").textContent =
        "Loading local model assets. The first download can take several minutes…";
    $("ai-output").textContent = "";
    if (!aiWorker) {
        aiWorker = new Worker(new URL("./model-worker.mjs", import.meta.url), {
            type: "module",
        });
        aiWorker.onmessage = (event) => {
            if (event.data.type === "progress")
                $("ai-status").textContent = event.data.message;
            else {
                clearTimeout(aiTimeout);
                aiBusy(false);
                if (event.data.type === "error") {
                    $("ai-status").textContent = event.data.message;
                    aiWorker.terminate();
                    aiWorker = undefined;
                } else {
                    $("ai-output").textContent = event.data.text;
                    $("ai-status").textContent =
                        `Generated locally · ${event.data.backend}. Review all output; this small model can repeat or invent text.`;
                    $("ai-generate").textContent = "Generate again ↗";
                }
            }
        };
        aiWorker.onerror = () => {
            aiStop();
            $("ai-status").textContent =
                "The local model could not start. Check network access, device memory and that you opened the full release. The four mission workflows still work without a model.";
        };
    }
    aiTimeout = setTimeout(() => {
        aiStop();
        $("ai-status").textContent =
            "Model loading or generation exceeded five minutes. Try again on a device with more memory or use the local agent.";
    }, 300000);
    aiWorker.postMessage({
        prompt,
        base: new URL(
            "alpha_agi_insight_v1/assets/local-llm/",
            document.baseURI,
        ).href,
    });
});
try {
    const response = await fetch(new URL("./examples.json", import.meta.url));
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    examples = await response.json();
    loadMission(examples.allocation);
    renderMemory();
} catch (error) {
    status(
        `Could not load mission examples (${error.message}). Reload this site or import a supported native mission JSON file.`,
        true,
    );
}
if ("serviceWorker" in navigator)
    navigator.serviceWorker.register("service-worker.js").catch(() => {
        $("storage-status").textContent =
            "Offline installation was unavailable. Keep a downloaded copy of important work.";
    });

$("verify-signed").addEventListener("click", async () => {
    $("verify-signed").disabled = true;
    $("signed-output").hidden = true;
    try {
        const file = $("signed-file").files[0];
        if (!file || file.size > 4 * 1024 * 1024)
            throw new Error(
                "Choose an agent export JSON file no larger than 4 MiB.",
            );
        const verification = await verifyAgentExport(
            JSON.parse(await file.text()),
            $("trusted-key").value.trim(),
        );
        $("signed-status").textContent =
            `Ed25519 signature and approved result verified · ${verification.identity} · mission ${verification.mission}. The supplied key is your trust anchor.`;
        $("signed-output").textContent = verification.canonical;
        $("signed-output").hidden = false;
    } catch (error) {
        $("signed-status").textContent =
            `Could not verify: ${error.message}. Use the local verifier if your browser lacks Ed25519 support.`;
    } finally {
        $("verify-signed").disabled = false;
    }
});
for (const id of ["signed-file", "trusted-key"])
    $(id).addEventListener("input", () => {
        $("signed-output").hidden = true;
        $("signed-status").textContent =
            "Inputs changed. Verify this file against the trusted public key.";
    });
