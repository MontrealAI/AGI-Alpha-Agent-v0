// SPDX-License-Identifier: Apache-2.0
import { validate, parse, REPORT_SCHEMA } from "./engine.mjs?v=1.15.0";
import { zipFiles } from "../compounding/engine.mjs?v=1.15.0";
const $ = (id) => document.getElementById(id),
    clone = (value) => structuredClone(value);
const money = (value) =>
        (value < 0 ? "−$" : "$") + Math.abs(value).toLocaleString("en-US"),
    num = (value) => value.toLocaleString("en-US");
const STORAGE = "agialpha.business3.draft.v1";
const policyFields = [
    ["budgetUsd", "Capital ceiling / USD", 0, 1e9, 1],
    ["staffDays", "Available staff days", 0, 100000, 1],
    ["reviewMinutes", "Review capacity / minutes", 0, 100000, 1],
    ["jobBudgetTokens", "Job budget / AGIALPHA", 0, 1e7, 1],
    ["maxProjects", "Maximum ventures", 0, 16, 1],
    ["maxPerSector", "Maximum per sector", 1, 16, 1],
    ["discountBps", "Annual discount rate / %", 0, 100, 100],
    ["benefitHaircutBps", "Downside cash-flow shock / %", 0, 100, 100],
    ["costOverrunBps", "Capital overrun / %", 0, 100, 100],
    ["minEvidenceBps", "Minimum evidence score / %", 0, 100, 100],
    ["minDownsideNpvUsd", "Minimum downside NPV / USD", -1e9, 1e9, 1],
];
let cases = [],
    draft = null,
    report = null,
    files = null,
    worker = null,
    sequence = 0,
    rawDirty = false;
const downloads = [
    $("b3-download"),
    $("b3-download-json"),
    $("b3-download-jobs"),
];
function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
}
function status(message, error = false) {
    $("b3-status").textContent = message;
    $("b3-status").dataset.error = String(error);
}
function stop() {
    if (worker) worker.terminate();
    worker = null;
    $("b3-cancel").disabled = true;
    $("b3-run").disabled = !draft;
    sequence++;
}
function invalidate(
    message = "Inputs changed. Recalculate before exporting a decision.",
) {
    stop();
    report = null;
    files = null;
    downloads.forEach((b) => (b.disabled = true));
    $("b3-results").hidden = true;
    status(message);
}
function syncJson() {
    $("b3-json").value = JSON.stringify(draft, null, 2);
    rawDirty = false;
}
function numberField(label, value, min, max, scale, onInput) {
    const wrapper = node("label", undefined, "b3-field"),
        input = node("input");
    wrapper.append(node("span", label), input);
    input.type = "number";
    input.required = true;
    input.min = String(min);
    input.max = String(max);
    input.step = String(1 / scale);
    input.value = String(value / scale);
    input.addEventListener("input", () => {
        const raw = input.value.trim();
        const parsed = raw === "" ? NaN : Number(raw) * scale;
        onInput(Number.isFinite(parsed) ? Math.round(parsed * 1e8) / 1e8 : NaN);
        invalidate();
        syncJson();
    });
    return wrapper;
}
function renderInputs() {
    $("b3-policy-fields").replaceChildren();
    for (const [key, label, min, max, scale] of policyFields) {
        const field = numberField(
            label,
            draft.policy[key],
            min,
            max,
            scale,
            (value) => {
                draft.policy[key] = value;
            },
        );
        field.querySelector("input").id = "b3-policy-" + key;
        $("b3-policy-fields").append(field);
    }
    $("b3-case-note").textContent = draft.provenance.note;
    $("b3-candidate-count").textContent = draft.projects.length + " CANDIDATES";
    $("b3-projects").replaceChildren();
    for (const p of draft.projects) {
        const detail = node("details", undefined, "b3-project"),
            summary = node("summary"),
            name = node("span", p.name, "b3-project-name"),
            cost = node("span", money(p.costUsd), "b3-project-cost");
        name.append(node("small", p.sector));
        cost.append(node("small", "CAPITAL / USD"));
        summary.append(name, cost);
        detail.append(summary);
        const fields = node("div", undefined, "b3-project-fields");
        for (const [key, label, min, max, scale] of [
            ["costUsd", "Capital / USD", 1, 1e8, 1],
            ["staffDays", "Staff days", 1, 100000, 1],
            ["reviewMinutes", "Review / minutes", 1, 100000, 1],
            ["bountyTokens", "Bounty / AGIALPHA", 1, 1e6, 1],
            ["evidenceBps", "Evidence score / %", 0, 100, 100],
            ["durationDays", "Job deadline / days", 1, 90, 1],
        ]) {
            const field = numberField(
                `${p.name}: ${label}`,
                p[key],
                min,
                max,
                scale,
                (value) => {
                    p[key] = value;
                    if (key === "costUsd")
                        cost.firstChild.textContent = money(value);
                },
            );
            fields.append(field);
        }
        p.cashflowsUsd.forEach((value, index) =>
            fields.append(
                numberField(
                    `${p.name}: year ${index + 1} net USD`,
                    value,
                    -1e8,
                    1e8,
                    1,
                    (next) => {
                        p.cashflowsUsd[index] = next;
                    },
                ),
            ),
        );
        detail.append(
            fields,
            node("p", "Success metric: " + p.metric),
            node("p", "Sources: " + p.sources.join(" | ")),
        );
        if (p.requires.length)
            detail.append(node("p", "Requires: " + p.requires.join(", ")));
        if (p.excludes.length)
            detail.append(node("p", "Excludes: " + p.excludes.join(", ")));
        $("b3-projects").append(detail);
    }
    syncJson();
}
function setDraft(source) {
    draft = clone(validate(source));
    invalidate("Ready. Edit the assumptions or calculate this case.");
    renderInputs();
    $("b3-run").disabled = false;
}
function metrics(result) {
    const p = result.portfolio;
    $("b3-metrics").replaceChildren();
    for (const [value, label] of [
        [p ? money(p.expectedNpvUsd) : "—", "3-year expected NPV / USD"],
        [p ? money(p.downsideNpvUsd) : "—", "Policy-downside NPV / USD"],
        [String(p?.projectIds.length || 0), "Selected ventures"],
        [String(result.jobs.length), "Unsubmitted proof jobs"],
    ]) {
        const card = node("div", undefined, "b3-metric");
        card.append(node("strong", value), node("span", label));
        $("b3-metrics").append(card);
    }
}
function renderOpportunity(value) {
    const host = $("b3-opportunity-chart"),
        chosen = new Set(value.result.portfolio?.projectIds || []),
        projects = new Map(value.input.projects.map((p) => [p.id, p])),
        rows = [...value.result.analysis].sort(
            (a, b) =>
                b.expectedNpvUsd - a.expectedNpvUsd || a.id.localeCompare(b.id),
        ),
        values = rows.flatMap((r) => [r.expectedNpvUsd, r.downsideNpvUsd]),
        low = Math.min(0, ...values),
        high = Math.max(0, ...values),
        span = Math.max(high - low, 1),
        zero = (-low / span) * 100;
    host.replaceChildren();
    for (const row of rows) {
        const item = node("li", undefined, "b3-value-row"),
            label = node("div", undefined, "b3-value-label"),
            plot = node("div", undefined, "b3-value-plot"),
            amounts = node("div", undefined, "b3-value-amounts"),
            state = chosen.has(row.id)
                ? "Selected"
                : row.evidenceEligible
                  ? "Not selected"
                  : "Below evidence threshold";
        item.dataset.projectId = row.id;
        item.dataset.selected = String(chosen.has(row.id));
        label.append(
            node("strong", projects.get(row.id).name),
            node("span", state),
        );
        plot.setAttribute("aria-hidden", "true");
        plot.style.setProperty("--b3-zero", `${zero}%`);
        for (const [key, name, className] of [
            ["expectedNpvUsd", "Expected", "b3-expected"],
            ["downsideNpvUsd", "Downside", "b3-downside"],
        ]) {
            const bar = node("span", undefined, `b3-value-bar ${className}`),
                amount = row[key];
            bar.style.left = `${((Math.min(0, amount) - low) / span) * 100}%`;
            bar.style.width = `${(Math.abs(amount) / span) * 100}%`;
            bar.dataset.value = String(amount);
            plot.append(bar);
            amounts.append(
                node("span", `${name}: ${money(amount)}`, className),
            );
        }
        item.append(label, plot, amounts);
        host.append(item);
    }
}
function renderResult(value) {
    report = value;
    const r = value.result,
        p = r.portfolio,
        source = value.input,
        byId = new Map(source.projects.map((p) => [p.id, p])),
        rows = new Map(r.analysis.map((p) => [p.id, p]));
    $("b3-verdict").textContent = r.status.replaceAll("_", " ");
    $("b3-summary").textContent =
        r.status === "REVIEW_REQUIRED"
            ? `A feasible ${p.projectIds.length}-venture plan under your declared constraints. Its expected value comes from your inputs; review the evidence before committing resources.`
            : r.status === "NO_FEASIBLE_PORTFOLIO"
              ? "No portfolio meets every declared constraint. Nothing is approved or queued. Review the budget, downside floor, dependencies and review capacity."
              : "Holding capital is the best feasible result under these assumptions. No jobs are created. Change the assumptions only when evidence supports the change.";
    metrics(r);
    renderOpportunity(value);
    $("b3-selected").replaceChildren();
    for (const id of p?.projectIds || []) {
        const item = byId.get(id),
            row = rows.get(id),
            element = node("div", undefined, "b3-selection");
        element.append(
            node("h4", item.name),
            node(
                "p",
                `${item.sector} · ${money(row.stressedCostUsd)} reserved · ${money(row.expectedNpvUsd)} expected NPV`,
            ),
        );
        $("b3-selected").append(element);
    }
    if (!p?.projectIds.length)
        $("b3-selected").append(node("p", "No ventures selected."));
    $("b3-resources").replaceChildren();
    for (const [key, limit, label, unit] of [
        ["stressedCostUsd", "budgetUsd", "Capital with contingency", "USD"],
        ["staffDays", "staffDays", "Staff capacity", "days"],
        ["reviewMinutes", "reviewMinutes", "Independent review", "minutes"],
        ["bountyTokens", "jobBudgetTokens", "Job escrow budget", "AGIALPHA"],
    ]) {
        const used = p?.[key] || 0,
            available = source.policy[limit],
            element = node("div", undefined, "b3-resource"),
            line = node("div"),
            bar = node("progress");
        line.append(
            node("span", label),
            node("span", `${num(used)} / ${num(available)} ${unit}`),
        );
        bar.max = Math.max(available, 1);
        bar.value = used;
        bar.setAttribute(
            "aria-label",
            `${label}: ${used} of ${available} ${unit}`,
        );
        element.append(line, bar);
        $("b3-resources").append(element);
    }
    $("b3-method").textContent =
        `Exact search: ${num(r.search.subsets)} subsets, ${num(r.search.feasible)} feasible. Maximize expected NPV while satisfying all constraints. Ties favor downside value, lower resource use and then project IDs.`;
    $("b3-comparison").textContent =
        r.comparison.upliftUsd === null
            ? "The greedy baseline could not find a feasible plan."
            : `${money(r.comparison.upliftUsd)} expected-NPV improvement over greedy standalone project ranking, on these supplied inputs. This is an optimizer comparison, not measured investment performance.`;
    $("b3-sensitivity").replaceChildren();
    for (const s of r.sensitivity) {
        const tr = node("tr");
        for (const t of [
            s.scenario,
            money(s.npvUsd),
            money(s.capitalUsd),
            s.budgetFits
                ? "Within ceiling"
                : "Outside ceiling / no feasible plan",
        ])
            tr.append(node("td", t));
        $("b3-sensitivity").append(tr);
    }
    $("b3-jobs").replaceChildren();
    r.jobs.forEach((job, index) => {
        const card = node("article", undefined, "b3-job"),
            item = byId.get(p.projectIds[index]),
            payout = r.settlementPreview[index];
        card.append(
            node(
                "small",
                `JOB ${String(index + 1).padStart(2, "0")} / ${item.sector.toUpperCase()}`,
            ),
            node("h3", job.goal),
            node("p", "Success metric: " + job.successMetric),
            node(
                "footer",
                `${num(item.bountyTokens)} AGIALPHA · ${item.durationDays} days · review required`,
            ),
            node(
                "p",
                `Illustrative accepted payout: ${Number(BigInt(payout.netBaseUnits) / 10n ** 16n) / 100} AGIALPHA to the agent; ${Number(BigInt(payout.burnBaseUnits) / 10n ** 16n) / 100} burned (1%). No settlement has occurred.`,
            ),
        );
        $("b3-jobs").append(card);
    });
    if (!r.jobs.length)
        $("b3-jobs").append(
            node("p", "No jobs are issued for a held or infeasible portfolio."),
        );
    $("b3-roles").replaceChildren();
    for (const role of r.roles)
        $("b3-roles").append(
            node(
                "p",
                `${role.role}: ${role.scope}. Candidates: ${role.projectIds.join(", ") || "none in this case"}.`,
                "b3-small",
            ),
        );
    $("b3-screened").replaceChildren(node("h3", "Evidence screening"));
    for (const row of r.analysis)
        $("b3-screened").append(
            node(
                "p",
                `${byId.get(row.id).name}: ${row.evidenceEligible ? "passes the supplied evidence threshold" : "below the supplied evidence threshold"}; expected NPV ${money(row.expectedNpvUsd)}; downside NPV ${money(row.downsideNpvUsd)}.`,
                "b3-small",
            ),
        );
    $("b3-hash").textContent = "Dossier SHA-256 · " + value.sha256;
    $("b3-results").hidden = false;
}
function calculate({ input, text, verify = false } = {}) {
    stop();
    report = null;
    files = null;
    downloads.forEach((b) => (b.disabled = true));
    $("b3-results").hidden = true;
    const id = sequence;
    $("b3-run").disabled = true;
    $("b3-cancel").disabled = false;
    status(
        verify
            ? "Recomputing the imported dossier…"
            : "Evaluating every bounded portfolio against your constraints…",
    );
    worker = new Worker(new URL("./worker.mjs?v=1.15.0", import.meta.url), {
        type: "module",
    });
    worker.onerror = () => {
        if (id === sequence) {
            stop();
            status(
                "Calculation worker could not load. Reload this release or use the Python CLI from the guide.",
                true,
            );
        }
    };
    worker.onmessage = async ({ data }) => {
        if (id !== sequence || data.id !== id) return;
        if (data.error) {
            stop();
            status(data.error, true);
            return;
        }
        try {
            const bundle = data.files;
            if (id !== sequence) return;
            stop();
            draft = clone(data.report.input);
            renderInputs();
            renderResult(data.report);
            files = bundle;
            downloads.forEach((b) => (b.disabled = false));
            $("b3-download-jobs").disabled = !report.result.jobs.length;
            status(
                verify
                    ? "Dossier verified: every decision, job and commitment matches recomputation."
                    : "Calculation complete. Review the downside and job evidence before proceeding.",
            );
        } catch (error) {
            if (id === sequence) {
                stop();
                status(error.message, true);
            }
        }
    };
    worker.postMessage({ id, input, text, verify });
}
function download(name, data, type = "application/json") {
    const href = URL.createObjectURL(new Blob([data], { type })),
        a = node("a");
    a.href = href;
    a.download = name;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(href), 2000);
}
function currentInput() {
    return rawDirty ? parse($("b3-json").value) : validate(draft);
}
$("b3-form").addEventListener("submit", (event) => {
    event.preventDefault();
    try {
        calculate({ input: currentInput() });
    } catch (error) {
        invalidate();
        status(error.message, true);
    }
});
$("b3-json").addEventListener("input", () => {
    rawDirty = true;
    invalidate("JSON changed. Calculate to validate and apply these inputs.");
});
$("b3-cancel").addEventListener("click", () =>
    invalidate("Calculation cancelled. Your inputs are retained."),
);
$("b3-case").addEventListener("change", () =>
    setDraft(cases.find((c) => c.id === $("b3-case").value)),
);
$("b3-import").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;
    invalidate("Reading local JSON…");
    const id = sequence;
    try {
        if (file.size > 2000000) throw Error("File exceeds 2,000,000 bytes");
        const content = await file.text();
        if (id !== sequence) return;
        const value = parse(content, 2000000);
        calculate({ text: content, verify: value?.schema === REPORT_SCHEMA });
    } catch (error) {
        if (id === sequence) status(error.message, true);
    }
});
$("b3-save").addEventListener("click", () => {
    try {
        const source = validate(currentInput());
        localStorage.setItem(STORAGE, JSON.stringify(source));
        $("b3-restore").disabled = false;
        status(
            "Draft saved on this device. Export the dossier for a portable copy.",
        );
    } catch (error) {
        status("Draft could not be saved: " + error.message, true);
    }
});
$("b3-restore").addEventListener("click", () => {
    try {
        const saved = localStorage.getItem(STORAGE);
        if (!saved) throw Error("No saved draft exists");
        setDraft(parse(saved));
        status(
            "Saved draft restored. Recalculate to obtain a current decision.",
        );
    } catch (error) {
        status("Draft could not be restored: " + error.message, true);
    }
});
$("b3-clear").addEventListener("click", () => {
    try {
        localStorage.removeItem(STORAGE);
        $("b3-restore").disabled = true;
        status(
            "Saved Business 3 draft cleared. The current inputs and other workspaces are unchanged.",
        );
    } catch (error) {
        status("Saved draft could not be cleared: " + error.message, true);
    }
});
$("b3-download").addEventListener("click", () => {
    if (files && report)
        download(
            `business3-${report.sha256.slice(0, 12)}.zip`,
            zipFiles(files),
            "application/zip",
        );
});
$("b3-download-json").addEventListener("click", () => {
    if (files) download("dossier.json", files["dossier.json"]);
});
$("b3-download-jobs").addEventListener("click", () => {
    if (files && report.result.jobs.length)
        download("jobs.json", files["jobs.json"]);
});
try {
    const response = await fetch(
        new URL("./scenarios.json?v=1.15.0", import.meta.url),
    );
    if (!response.ok)
        throw Error(`Cases unavailable (HTTP ${response.status})`);
    cases = parse(await response.text());
    cases.forEach(validate);
    $("b3-case").replaceChildren();
    for (const c of cases) {
        const option = node("option", c.title);
        option.value = c.id;
        $("b3-case").append(option);
    }
    $("b3-case").disabled = false;
    setDraft(cases[0]);
    try {
        $("b3-restore").disabled = !localStorage.getItem(STORAGE);
    } catch {
        status(
            "Ready. Device storage is unavailable; you can still calculate and download your work.",
        );
    }
    document.documentElement.dataset.business3Ready = "true";
} catch (error) {
    status(
        "The enterprise workspace could not load: " +
            error.message +
            ". Reload or use the Python CLI in the demo guide.",
        true,
    );
}
