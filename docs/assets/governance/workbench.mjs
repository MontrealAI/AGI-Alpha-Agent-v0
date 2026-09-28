// SPDX-License-Identifier: Apache-2.0
import {
    evaluate,
    validate,
    verify,
    parse,
    canonical,
    artifacts,
    REPORT_SCHEMA,
    MAX_BYTES,
} from "./engine.mjs?v=1.16.0";
import { zipFiles } from "../compounding/engine.mjs?v=1.16.0";
const $ = (id) => document.getElementById(id);
const STORE = "agialpha.governance.draft.v1";
let scenario,
    report,
    cases = [],
    revision = 0,
    jsonDirty = false;
const exports = ["gov-download", "gov-dossier", "gov-download-jobs"];
const fields = [
    [
        "incentive",
        "incentives",
        "discountBps",
        "Future value δ / %",
        100,
        0,
        99.99,
        "How much the next round matters; distinct from the legacy update rate.",
    ],
    [
        "incentive",
        "incentives",
        "detectionBps",
        "Deviation detection / %",
        100,
        0,
        100,
        "Assumed probability of detecting a unilateral deviation.",
    ],
    [
        "incentive",
        "incentives",
        "stake",
        "Slashable stake / utility units",
        1,
        0,
        100000,
        "Utility-equivalent penalty, not an AGIALPHA exchange rate.",
    ],
    [
        "risk",
        "risk",
        "perActionFemto",
        "Per-action failure upper bound",
        1e15,
        0,
        1,
        "Probability from 0 to 1; scientific notation is accepted.",
    ],
    [
        "risk",
        "risk",
        "actions",
        "Actions in the envelope",
        1,
        1,
        1e12,
        "Include the full planned deployment scope.",
    ],
    [
        "risk",
        "risk",
        "budgetFemto",
        "Total failure budget",
        1e15,
        0,
        1,
        "Maximum acceptable union bound for the full envelope.",
    ],
    [
        "policy",
        "policy",
        "quorumBps",
        "Required participation / %",
        100,
        0.01,
        100,
        "Share of eligible validators casting a valid nonzero ballot.",
    ],
    [
        "policy",
        "policy",
        "supportBps",
        "Required support / %",
        100,
        50.01,
        100,
        "Share of positive votes among all positive and negative votes.",
    ],
    [
        "policy",
        "policy",
        "minStakeTokens",
        "Validator stake floor / AGIALPHA",
        1,
        1,
        1e6,
        "Whole tokens; supplied stake still needs chain verification.",
    ],
    [
        "policy",
        "policy",
        "jobBountyTokens",
        "Bounty per review job / AGIALPHA",
        1,
        1,
        1e6,
        "Nine unsubmitted jobs; 18-decimal base units in the exported specs.",
    ],
];
function el(tag, text, cls) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
}
function status(message) {
    $("gov-status").textContent = message;
}
function invalidate(
    message = "Inputs changed. Evaluate again to create current evidence.",
) {
    revision++;
    report = null;
    $("gov-results").hidden = true;
    exports.forEach((id) => ($(id).disabled = true));
    status(message);
}
// Convert decimal/scientific input exactly into integer schema units; never round a risk bound down.
export function units(raw, scale) {
    const m = String(raw).match(/^([+-]?)(\d*)(?:\.(\d*))?(?:e([+-]?\d+))?$/i);
    if (!m || (!m[2] && !m[3]) || String(raw).length > 60)
        throw Error("Enter a finite number");
    const exponent = Number(m[4] || 0) - (m[3] || "").length;
    if (Math.abs(exponent) > 40)
        throw Error("Value is outside the supported precision");
    let numerator =
        BigInt((m[2] || "0") + (m[3] || "")) *
        BigInt(scale) *
        (m[1] === "-" ? -1n : 1n);
    if (exponent >= 0) numerator *= 10n ** BigInt(exponent);
    else {
        const divisor = 10n ** BigInt(-exponent);
        if (numerator % divisor)
            throw Error(
                "Value cannot be represented exactly in the documented units",
            );
        numerator /= divisor;
    }
    const result = Number(numerator);
    if (!Number.isSafeInteger(result))
        throw Error("Value exceeds the exact integer range");
    return result;
}
function current() {
    if (jsonDirty)
        throw Error("Apply the edited JSON before evaluating or saving.");
    const value = structuredClone(scenario);
    for (const [, section, key, label, scale] of fields) {
        try {
            value[section][key] = units($(`gov-${key}`).value, scale);
        } catch (error) {
            throw Error(`${label}: ${error.message}`);
        }
    }
    value.upgrade.paused = $("gov-paused").checked;
    document.querySelectorAll("#gov-validators input").forEach((input) => {
        const v = value.validators[Number(input.dataset.index)],
            key = input.dataset.field;
        v[key] =
            key === "eligible"
                ? input.checked
                : ["votes", "credits", "stakeTokens"].includes(key)
                  ? units(input.value, 1)
                  : key === "name"
                    ? input.value + ".alpha.club.agi.eth"
                    : input.value;
    });
    return validate(value);
}
function load(
    value,
    message = "Case loaded. Review the assumptions, then evaluate all nine gates.",
) {
    value = validate(value);
    invalidate(message);
    scenario = value;
    jsonDirty = false;
    for (const [group, section, key, label, scale, min, max, hint] of fields) {
        let input = $(`gov-${key}`);
        if (!input) {
            const wrapper = el("label", label);
            input = el("input");
            input.id = `gov-${key}`;
            input.type = "number";
            input.step = String(1 / scale);
            input.min = String(min);
            input.max = String(max);
            input.required = true;
            wrapper.append(input, el("small", hint));
            $(`gov-${group}-fields`).append(wrapper);
        }
        input.value = String(value[section][key] / scale);
    }
    $("gov-paused").checked = value.upgrade.paused;
    $("gov-validators").replaceChildren();
    value.validators.forEach((v, index) => {
        const row = el("tr");
        for (const key of [
            "name",
            "controller",
            "credits",
            "votes",
            "stakeTokens",
            "eligible",
        ]) {
            const cell = el("td"),
                input = el("input");
            input.dataset.index = index;
            input.dataset.field = key;
            input.setAttribute("aria-label", `${v.name}: ${key}`);
            if (key === "eligible") {
                input.type = "checkbox";
                input.checked = v[key];
            } else if (key === "name" || key === "controller") {
                input.type = "text";
                input.value = key === "name" ? v[key].split(".")[0] : v[key];
                input.maxLength = 40;
                input.required = true;
            } else {
                input.type = "number";
                input.min = key === "votes" ? "-1000" : "0";
                input.max = key === "votes" ? "1000" : "1000000";
                input.step = "1";
                input.value = v[key];
                input.required = true;
            }
            cell.append(input);
            row.append(cell);
        }
        $("gov-validators").append(row);
    });
    $("gov-json").value = JSON.stringify(value, null, 2);
    $("gov-case-note").textContent = value.note;
    $("gov-run").disabled = false;
    $("gov-save").disabled = false;
}
function probability(femto) {
    return (Number(femto) / 1e15).toLocaleString("en-US", {
        maximumSignificantDigits: 7,
    });
}
function chart(source) {
    const {
        reward: r,
        temptation: t,
        punishment: p,
        detectionBps: q,
        stake: s,
        discountBps: d,
    } = source.incentives;
    const deviation = t - (q * s) / 10000,
        continuation = (q * p + (10000 - q) * r) / 10000,
        low = Math.min(r, deviation, continuation),
        high = Math.max(r, deviation, continuation),
        padding = Math.max(1, (high - low) * 0.15);
    const y = (n) =>
            190 - ((n - low + padding) / (high - low + 2 * padding)) * 145,
        x = (n) => 48 + 360 * n;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 450 245");
    svg.setAttribute("role", "img");
    svg.setAttribute(
        "aria-label",
        `Cooperative reward ${r}; deviation alternative ${deviation} at delta zero and ${continuation} at delta one. Current incentive margin ${(Number(report.result.incentives.marginNumerator) / 1e8).toFixed(2)} utility units.`,
    );
    const append = (tag, attrs, text) => {
        const node = document.createElementNS(svg.namespaceURI, tag);
        for (const [k, v] of Object.entries(attrs))
            node.setAttribute(k, String(v));
        if (text !== undefined) node.textContent = text;
        svg.append(node);
    };
    for (const value of [...new Set([r, deviation, continuation])]) {
        append("line", {
            x1: 48,
            y1: y(value),
            x2: 408,
            y2: y(value),
            stroke: "#ced6c2",
            "stroke-dasharray": "3 4",
        });
        append(
            "text",
            {
                x: 40,
                y: y(value) + 4,
                "text-anchor": "end",
                fill: "#455d49",
                "font-size": 11,
            },
            String(Math.round(value * 100) / 100),
        );
    }
    append("line", { x1: 48, y1: 190, x2: 408, y2: 190, stroke: "#91a28d" });
    append("path", {
        d: `M48 ${y(r)}H408`,
        stroke: "#416f3b",
        "stroke-width": 3,
        fill: "none",
    });
    append("path", {
        d: `M48 ${y(deviation)}L408 ${y(continuation)}`,
        stroke: "#9a4b2c",
        "stroke-width": 3,
        fill: "none",
    });
    append("line", {
        x1: x(d / 10000),
        y1: 32,
        x2: x(d / 10000),
        y2: 190,
        stroke: "#274d42",
        "stroke-dasharray": "4 4",
    });
    append("circle", {
        cx: x(d / 10000),
        cy: y((1 - d / 10000) * deviation + (d / 10000) * continuation),
        r: 5,
        fill: "#9a4b2c",
    });
    for (const n of [0, 0.25, 0.5, 0.75, 1])
        append(
            "text",
            {
                x: x(n),
                y: 210,
                "text-anchor": "middle",
                fill: "#455d49",
                "font-size": 11,
            },
            `${n * 100}%`,
        );
    append(
        "text",
        { x: 48, y: 18, fill: "#416f3b", "font-size": 11 },
        "━ Cooperative reward",
    );
    append(
        "text",
        { x: 224, y: 18, fill: "#8b3825", "font-size": 11 },
        "━ Deviation alternative",
    );
    append(
        "text",
        {
            x: 228,
            y: 236,
            "text-anchor": "middle",
            fill: "#455d49",
            "font-size": 11,
        },
        "Future value δ (100% is the limiting endpoint)",
    );
    $("gov-incentive-chart").replaceChildren(svg);
}
function render(value) {
    report = value;
    const r = value.result,
        s = value.input,
        passed = r.gates.filter((g) => g.passed).length;
    $("gov-verdict").textContent = r.status.replaceAll("_", " ");
    $("gov-verdict").classList.toggle("blocked", passed < 9);
    $("gov-result-summary").textContent =
        passed === 9
            ? "All nine modeled gates pass. The next step is independent verification—not automatic approval."
            : `${9 - passed} ${9 - passed === 1 ? "gate needs" : "gates need"} attention. Resolve the blocked conditions before independent review.`;
    $("gov-metrics").replaceChildren();
    for (const [label, value, note] of [
        ["Modeled gates", `${passed} / 9`, "Passes remain conditional"],
        [
            "Valid participation",
            `${r.ballot.participants} / ${r.ballot.eligible}`,
            "Eligible, staked validators",
        ],
        [
            "Vote balance",
            `${r.ballot.yes} : ${r.ballot.no}`,
            "Support : opposition",
        ],
        [
            "Review budget",
            r.reservedBountyTokens.toLocaleString("en-US"),
            "AGIALPHA · unsubmitted",
        ],
    ]) {
        const node = el("div", undefined, "gov-metric");
        node.append(el("span", label), el("b", value), el("small", note));
        $("gov-metrics").append(node);
    }
    $("gov-gates").replaceChildren();
    $("gov-jobs").replaceChildren();
    r.gates.forEach((g, index) => {
        const node = el(
                "article",
                undefined,
                `gov-gate ${g.passed ? "" : "blocked"}`,
            ),
            head = el("div", undefined, "gov-gate-head");
        head.append(
            el("span", String(index + 1).padStart(2, "0")),
            el("b", g.passed ? "PASS / MODEL" : "BLOCKED"),
        );
        node.append(head, el("h3", g.title), el("p", g.nextStep));
        $("gov-gates").append(node);
        const job = el("details", undefined, "gov-job");
        job.append(
            el("summary", g.title),
            el("p", `Goal: ${r.jobs[index].goal}`),
            el("p", `Success metric: ${g.nextStep}`),
            el(
                "small",
                `${s.policy.jobBountyTokens} AGIALPHA · 7-day delivery window`,
            ),
        );
        $("gov-jobs").append(job);
    });
    chart(s);
    $("gov-incentive-detail").textContent =
        `At δ = ${s.incentives.discountBps / 100}%, the cooperation margin is ${Number(r.incentives.marginNumerator) / 1e8} utility units. Nonnegative passes this conditional check. The dashed line marks the current assumption.`;
    $("gov-risk-detail").replaceChildren();
    for (const [label, value] of [
        ["Per-action upper bound", probability(s.risk.perActionFemto)],
        ["Planned actions", s.risk.actions.toLocaleString("en-US")],
        ["Expected count upper bound", probability(r.risk.exposureFemto)],
        ["Union bound", probability(r.risk.unionBoundFemto)],
        ["Total risk budget", probability(s.risk.budgetFemto)],
        [
            "Largest admissible per-action bound",
            probability(r.risk.maxPerActionFemto),
        ],
        [
            "Upgrade waiting time remaining",
            `${r.upgrade.secondsRemaining.toLocaleString("en-US")} seconds`,
        ],
    ]) {
        const row = el("div");
        row.append(el("dt", label), el("dd", value));
        $("gov-risk-detail").append(row);
    }
    $("gov-hash").textContent = `Dossier SHA-256: ${value.sha256}`;
    exports.forEach((id) => ($(id).disabled = false));
    $("gov-results").hidden = false;
    status(
        `${passed} of 9 modeled gates pass. ${r.status === "BLOCKED" ? "Blocked conditions are listed below." : "Independent review is still required."} Exports are ready.`,
    );
}
function download(data, name, type) {
    const url = URL.createObjectURL(new Blob([data], { type })),
        a = el("a");
    a.href = url;
    a.download = name;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
}
async function exportFile(kind) {
    try {
        if (!report) throw Error("Evaluate current inputs first.");
        const token = revision,
            snapshot = report,
            files = await artifacts(snapshot);
        if (token !== revision) return;
        if (kind === "zip")
            download(
                zipFiles(files),
                `governance-${snapshot.sha256.slice(0, 12)}.zip`,
                "application/zip",
            );
        else {
            const name = kind === "jobs" ? "jobs.json" : "dossier.json";
            download(files[name], name, "application/json");
        }
    } catch (error) {
        status(`Export failed: ${error.message}`);
    }
}
$("gov-form").addEventListener("input", (event) => {
    if (event.target.id === "gov-case") return;
    if (event.target.id === "gov-json") jsonDirty = true;
    invalidate();
    if (!jsonDirty) {
        try {
            $("gov-json").value = JSON.stringify(current(), null, 2);
        } catch {
            /* Keep edits visible until validation. */
        }
    }
});
$("gov-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
        const value = current();
        invalidate("Evaluating the supplied assumptions…");
        const token = revision,
            result = await evaluate(value);
        if (token !== revision) return;
        scenario = value;
        render(result);
        $("gov-results").focus();
    } catch (error) {
        invalidate(`Review the inputs: ${error.message}`);
    }
});
$("gov-case").addEventListener("change", () => {
    const value = cases.find((c) => c.id === $("gov-case").value);
    if (value) load(value);
});
$("gov-apply").addEventListener("click", () => {
    try {
        load(
            parse($("gov-json").value),
            "Scenario JSON applied. Evaluate to generate current evidence.",
        );
    } catch (error) {
        invalidate(`JSON not applied: ${error.message}`);
    }
});
$("gov-import").addEventListener("change", async () => {
    const file = $("gov-import").files[0];
    if (!file) return;
    invalidate("Checking the imported file…");
    const token = revision;
    try {
        if (file.size > MAX_BYTES)
            throw Error(`Input exceeds ${MAX_BYTES} bytes`);
        const raw = parse(
            new TextDecoder("utf-8", { fatal: true }).decode(
                await file.arrayBuffer(),
            ),
        );
        const verified =
            raw.schema === REPORT_SCHEMA ? await verify(raw) : null;
        const source = verified ? verified.input : validate(raw);
        if (token !== revision) return;
        load(source, "Imported scenario. Evaluate after any edits.");
        if (verified) {
            render(verified);
            status(
                "Imported dossier independently recomputed; every result and job matches.",
            );
        }
    } catch (error) {
        if (token === revision) invalidate(`Import rejected: ${error.message}`);
    } finally {
        $("gov-import").value = "";
    }
});
$("gov-save").addEventListener("click", () => {
    try {
        localStorage.setItem(STORE, canonical(current()));
        $("gov-restore").disabled = false;
        status(
            "Draft saved in this browser. Export a dossier for a portable copy.",
        );
    } catch (error) {
        status(`Draft not saved: ${error.message}`);
    }
});
$("gov-restore").addEventListener("click", () => {
    try {
        const value = localStorage.getItem(STORE);
        if (!value) throw Error("No saved draft is available");
        load(
            parse(value),
            "Saved draft restored. Evaluate to create current evidence.",
        );
    } catch (error) {
        invalidate(`Draft not restored: ${error.message}`);
    }
});
$("gov-clear").addEventListener("click", () => {
    try {
        localStorage.removeItem(STORE);
        $("gov-restore").disabled = true;
        status("Saved draft cleared. The open proposal is unchanged.");
    } catch (error) {
        status(`Draft could not be cleared: ${error.message}`);
    }
});
$("gov-download").addEventListener("click", () => exportFile("zip"));
$("gov-dossier").addEventListener("click", () => exportFile("dossier"));
$("gov-download-jobs").addEventListener("click", () => exportFile("jobs"));
try {
    const response = await fetch(
        new URL("./scenarios.json?v=1.16.0", import.meta.url),
    );
    if (!response.ok) throw Error(`Cases could not load (${response.status})`);
    cases = parse(await response.text());
    cases.forEach(validate);
    $("gov-case").replaceChildren(
        ...cases.map((c) => {
            const option = el("option", c.title);
            option.value = c.id;
            return option;
        }),
    );
    $("gov-case").disabled = false;
    load(cases[0]);
    try {
        $("gov-restore").disabled = !localStorage.getItem(STORE);
    } catch {
        status(
            "Cases ready. Draft storage is unavailable; exported files still work.",
        );
    }
} catch (error) {
    status(
        `Workspace could not start: ${error.message}. Reload, or use the Python CLI in the demo guide.`,
    );
}
