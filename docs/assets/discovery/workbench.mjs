// SPDX-License-Identifier: Apache-2.0
import {
    METRICS,
    MAX_BYTES,
    parse,
    validate,
    evaluate,
    verify,
    artifacts,
} from "./engine.mjs?v=1.23.1";
import { zipFiles } from "../compounding/engine.mjs?v=1.23.1";
const $ = (id) => document.getElementById(id),
    key = "agialpha.insight.discovery.draft.v1";
let cases = [],
    scenario,
    report,
    revision = 0,
    dirty = false,
    inspected = "";
const labels = {
    REVIEW_REQUIRED: "Review required",
    CAPACITY_DEFERRED: "Capacity deferred",
    EVIDENCE_REQUIRED: "Evidence required",
};
const clone = (value) => structuredClone(value),
    score = (n) => (Math.floor(n / 10000) / 100).toFixed(2);
function message(value) {
    $("notice").textContent = value;
}
function fail(error) {
    $("error").hidden = false;
    $("error").textContent = error.message || String(error);
}
function lock() {
    revision++;
    report = null;
    $("export").disabled = true;
    $("dossier").disabled = true;
    $("hash").textContent = "Awaiting valid calculation";
}
function node(tag, content, className) {
    const el = document.createElement(tag);
    el.textContent = content;
    if (className) el.className = className;
    return el;
}
function sync() {
    $("case-note").textContent = scenario.note;
    for (const field of Object.keys(scenario.policy))
        $(field).value = String(
            scenario.policy[field] /
                (["minScoreBps", "minCoverageBps"].includes(field) ? 100 : 1),
        );
    $("weights").replaceChildren();
    for (const metric of METRICS) {
        const label = node("label", metric[0].toUpperCase() + metric.slice(1)),
            input = document.createElement("input");
        input.type = "number";
        input.min = "0";
        input.max = "10000";
        input.step = "1";
        input.value = scenario.weights[metric];
        input.dataset.metric = metric;
        input.addEventListener("input", editControls);
        label.append(input);
        $("weights").append(label);
    }
    $("scenario").value = JSON.stringify(scenario, null, 2);
    dirty = false;
}
async function calculate() {
    lock();
    const current = revision;
    $("error").hidden = true;
    message("Recomputing the portfolio…");
    try {
        const next = await evaluate(scenario);
        if (current !== revision) return;
        report = next;
        render();
        $("export").disabled = false;
        $("dossier").disabled = false;
        message(
            next.result.selectedIds.length
                ? "Ready for independent review. No jobs submitted; no funds committed."
                : "No portfolio selected. Inspect the evidence gates and review capacity.",
        );
    } catch (error) {
        if (current === revision) {
            fail(error);
            message("Resolve the input error to calculate and export.");
        }
    }
}
function editControls() {
    if (dirty) {
        fail(
            Error(
                "Apply or discard the pending JSON edits before changing controls.",
            ),
        );
        return;
    }
    for (const field of Object.keys(scenario.policy)) {
        const input = $(field),
            value = input.valueAsNumber;
        if (!input.checkValidity() || !Number.isFinite(value)) {
            lock();
            fail(
                Error(
                    "Enter a valid " + field + " within the displayed bounds.",
                ),
            );
            return;
        }
        scenario.policy[field] = Math.round(
            value *
                (["minScoreBps", "minCoverageBps"].includes(field) ? 100 : 1),
        );
    }
    for (const input of $("weights").querySelectorAll("input")) {
        if (!input.checkValidity() || !Number.isFinite(input.valueAsNumber)) {
            lock();
            fail(Error("Weights must be integers from 0 through 10000."));
            return;
        }
        scenario.weights[input.dataset.metric] = input.valueAsNumber;
    }
    $("scenario").value = JSON.stringify(scenario, null, 2);
    void calculate();
}
function inspect(id) {
    inspected = id;
    const item = scenario.opportunities.find((o) => o.id === id);
    if (!item) return;
    $("inspect-title").textContent = item.title;
    $("thesis").textContent = item.thesis;
    $("mission").replaceChildren();
    for (const [title, value] of [
        ["Goal", item.goal],
        ["Success metric", item.successMetric],
    ])
        $("mission").append(node("dt", title), node("dd", value));
    $("signals").replaceChildren();
    const references = new Set();
    for (const metric of METRICS) {
        const signal = item.signals[metric],
            tr = document.createElement("tr");
        for (const value of [
            metric,
            ...["low", "base", "high"].map((level) =>
                (signal[level] / 100).toFixed(2),
            ),
            signal.source || "Missing",
        ])
            tr.append(node("td", value));
        $("signals").append(tr);
        if (signal.source) references.add(signal.source);
    }
    $("sources").replaceChildren();
    for (const source of scenario.sources.filter((s) => references.has(s.id))) {
        const details = document.createElement("details");
        details.className = "source";
        details.append(
            node("summary", `${source.title} · ${source.kind}`),
            node("blockquote", source.excerpt),
        );
        const a = node("a", "Open supplied source ↗");
        a.href = source.url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        details.append(a);
        $("sources").append(details);
    }
    if (!references.size)
        $("sources").append(
            node("p", "No excerpts supplied for this opportunity."),
        );
}
function render() {
    const result = report.result;
    $("selected").textContent = String(result.selectedIds.length);
    $("minutes").textContent =
        `${result.reviewMinutesUsed} / ${scenario.policy.reviewMinutes}`;
    $("separation").textContent = result.rankSeparation
        ? "Separated"
        : "Overlapping";
    $("separation").title = result.rankSeparationMeaning;
    $("ranking").replaceChildren();
    for (const row of result.ranking) {
        const tr = document.createElement("tr");
        if (row.selected) tr.className = "chosen";
        const title = document.createElement("td"),
            button = node("button", row.title, "opportunity");
        button.addEventListener("click", () => inspect(row.id));
        title.append(button, node("span", row.sector, "sector"));
        const scores = document.createElement("td"),
            range = document.createElement("div");
        range.className = "range";
        range.setAttribute("aria-hidden", "true");
        const interval = document.createElement("i"),
            base = document.createElement("b");
        interval.style.left = score(row.scores.low) + "%";
        interval.style.width = score(row.scores.high - row.scores.low) + "%";
        base.style.left = score(row.scores.base) + "%";
        range.append(interval, base);
        scores.append(
            node(
                "span",
                [row.scores.low, row.scores.base, row.scores.high]
                    .map(score)
                    .join(" / "),
                "score-label",
            ),
            range,
        );
        const status = node("td", labels[row.status], "decision");
        status.title = row.reasons.join("; ");
        tr.append(
            title,
            scores,
            node("td", (row.coverageBps / 100).toFixed(2) + "%"),
            node("td", String(row.reviewMinutes)),
            status,
        );
        $("ranking").append(tr);
    }
    inspect(
        scenario.opportunities.some((o) => o.id === inspected)
            ? inspected
            : result.ranking[0].id,
    );
    $("handoff").textContent =
        `${result.jobs.length} unsubmitted jobs · ${result.novaSeedDrafts.length} plaintext seed drafts · ${result.unsubmittedBountyTokens.toLocaleString("en-US")} AGIALPHA in proposed bounties.`;
    $("hash").textContent = report.sha256;
}
async function adopt(value) {
    scenario = validate(value);
    sync();
    await calculate();
}
function download(bytes, name, type) {
    const url = URL.createObjectURL(new Blob([bytes], { type })),
        a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
for (const field of [
    "reviewMinutes",
    "minScoreBps",
    "minCoverageBps",
    "jobBountyTokens",
])
    $(field).addEventListener("input", editControls);
$("scenario").addEventListener("input", () => {
    dirty = true;
    lock();
    message("JSON edits pending. Apply or discard them before exporting.");
});
$("apply").addEventListener("click", () => {
    try {
        void adopt(parse($("scenario").value)).catch(fail);
    } catch (error) {
        fail(error);
    }
});
$("discard").addEventListener("click", () => {
    sync();
    void calculate();
});
$("reset").addEventListener(
    "click",
    () => void adopt(clone(cases.find((c) => c.id === $("case").value))),
);
$("case").addEventListener(
    "change",
    () => void adopt(clone(cases.find((c) => c.id === $("case").value))),
);
$("import").addEventListener("change", async () => {
    const file = $("import").files[0];
    if (!file) return;
    lock();
    const current = revision;
    try {
        if (file.size > MAX_BYTES) throw Error("Import exceeds 1 MB.");
        const value = parse(
            new TextDecoder("utf-8", { fatal: true }).decode(
                await file.arrayBuffer(),
            ),
        );
        const next =
            value.schema === "agialpha.insight.dossier.v1"
                ? (await verify(value)).input
                : validate(value);
        if (current !== revision) return;
        await adopt(next);
        message(
            "Imported and recomputed successfully. Review all supplied assumptions.",
        );
    } catch (error) {
        if (current === revision) fail(error);
    } finally {
        $("import").value = "";
    }
});
$("save").addEventListener("click", () => {
    try {
        if (!report || dirty)
            throw Error("Calculate valid inputs before saving a draft.");
        localStorage.setItem(key, JSON.stringify(scenario));
        message("Draft saved in this browser.");
    } catch (error) {
        fail(error);
    }
});
$("restore").addEventListener("click", async () => {
    try {
        const value = localStorage.getItem(key);
        if (!value) throw Error("No saved draft in this browser.");
        await adopt(parse(value));
        message("Saved draft restored and recomputed.");
    } catch (error) {
        fail(error);
    }
});
$("clear").addEventListener("click", () => {
    try {
        localStorage.removeItem(key);
        message("Saved draft cleared. Current inputs remain on the desk.");
    } catch (error) {
        fail(error);
    }
});
$("dossier").addEventListener("click", async () => {
    const current = revision,
        value = report;
    if (!value) return;
    try {
        const files = await artifacts(value);
        if (current === revision)
            download(
                files["dossier.json"],
                "insight-dossier.json",
                "application/json",
            );
    } catch (error) {
        fail(error);
    }
});
$("export").addEventListener("click", async () => {
    const current = revision,
        value = report;
    if (!value) return;
    try {
        const files = await artifacts(value);
        if (current === revision)
            download(
                zipFiles(
                    Object.fromEntries(
                        Object.entries(files).map(([name, data]) => [
                            name,
                            new TextDecoder().decode(data),
                        ]),
                    ),
                ),
                `insight-${value.sha256.slice(0, 16)}.zip`,
                "application/zip",
            );
    } catch (error) {
        fail(error);
    }
});
try {
    const response = await fetch(new URL("./scenarios.json", import.meta.url));
    if (!response.ok)
        throw Error(
            "Starter cases could not be loaded. Reload or use the Python guide.",
        );
    cases = parse(await response.text());
    for (const item of cases) {
        validate(item);
        const option = node("option", item.title);
        option.value = item.id;
        $("case").append(option);
    }
    await adopt(clone(cases[0]));
} catch (error) {
    fail(error);
    message("The workbench could not start.");
}
if ("serviceWorker" in navigator)
    navigator.serviceWorker
        .register(new URL("../../service-worker.js", import.meta.url))
        .catch(() =>
            message(
                "Offline caching is unavailable; current calculations still run locally.",
            ),
        );
