// SPDX-License-Identifier: Apache-2.0
import {
    validateScenario,
    makeGenome,
    curveQuote,
    tokenUnits,
    tokenDecimal,
    councilChecks,
    runSettlement,
    hawkDove,
    evolveStrategies,
    riskAudit,
    PAPER_RISKS,
    actionRisk,
    quadraticBallot,
    upgradeStatus,
    stakeDecision,
} from "./engine.mjs";
import { sealSeed, openSeed, hashObject } from "./crypto.mjs";

const $ = (id) => document.getElementById(id);
const all = (selector) => [...document.querySelectorAll(selector)];
const palette = [
    "#70e8db",
    "#b6a9ff",
    "#f6ca85",
    "#80bafa",
    "#f29fbc",
    "#c3dc94",
    "#ddaa78",
];
const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = String(text);
    if (cls) node.className = cls;
    return node;
};
const svgEl = (tag, attrs = {}, text) => {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attrs))
        node.setAttribute(key, String(value));
    if (text !== undefined) node.textContent = String(text);
    return node;
};
const num = (n, digits = 2) =>
    Number(n).toLocaleString("en-US", { maximumFractionDigits: digits });
let scenarios = [],
    scenario,
    analysis = null,
    genome = null,
    capsule = null,
    recovered = null;
let supply = 0,
    reserve = 0n,
    settlement = null,
    policies = [],
    activeWorker = null,
    revision = 0;
let activeStep = "insight",
    cryptoBusy = false;

function status(message, error = false) {
    $("lab-status").textContent = message;
    $("lab-status").classList.toggle("error", error);
}
function guarded(fn) {
    return async (event) => {
        try {
            await fn(event);
        } catch (error) {
            status(error.message, true);
        }
    };
}
function download(name, data, type = "application/json") {
    const content =
        typeof data === "string" ? data : JSON.stringify(data, null, 2) + "\n";
    const url = URL.createObjectURL(new Blob([content], { type }));
    const a = el("a");
    a.href = url;
    a.download = name;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function readFile(file, max = 350000) {
    if (!file) throw new Error("Choose a JSON file first.");
    if (file.size > max) throw new Error(`This file exceeds ${max / 1000} KB.`);
    try {
        return JSON.parse(await file.text());
    } catch {
        throw new Error("This file is not valid JSON.");
    }
}
function metrics(id, values) {
    $(id).replaceChildren(
        ...values.map(([title, value, note]) => {
            const card = el("div", undefined, "metric");
            card.append(
                el("span", title),
                el("strong", value),
                el("small", note),
            );
            return card;
        }),
    );
}
function table(id, headers, rows) {
    const t = el("table"),
        head = el("thead"),
        tr = el("tr"),
        body = el("tbody");
    headers.forEach((h) => tr.append(el("th", h)));
    head.append(tr);
    rows.forEach((row) => {
        const r = el("tr");
        row.forEach((v) => r.append(el("td", v)));
        body.append(r);
    });
    t.append(head, body);
    $(id).replaceChildren(t);
}
function chart(id, { xmax, ymax, xlabel = "", ylabel = "", height = 280 }) {
    xmax = Math.max(xmax, 1);
    ymax = Math.max(ymax, 1);
    const w = 650,
        left = 50,
        right = 24,
        top = 25,
        bottom = 40;
    const x = (v) => left + (v / xmax) * (w - left - right);
    const y = (v) => height - bottom - (v / ymax) * (height - top - bottom);
    const svg = svgEl("svg", {
        viewBox: `0 0 ${w} ${height}`,
        "aria-hidden": "true",
    });
    for (let i = 0; i <= 4; i++) {
        const xx = x((xmax * i) / 4),
            yy = y((ymax * i) / 4);
        svg.append(
            svgEl("line", {
                x1: left,
                x2: w - right,
                y1: yy,
                y2: yy,
                class: "gridline",
            }),
            svgEl(
                "text",
                { x: left - 10, y: yy + 3, "text-anchor": "end" },
                num((ymax * i) / 4),
            ),
            svgEl(
                "text",
                { x: xx, y: height - 19, "text-anchor": "middle" },
                num((xmax * i) / 4),
            ),
        );
    }
    svg.append(
        svgEl("line", {
            x1: left,
            x2: w - right,
            y1: y(0),
            y2: y(0),
            class: "axis",
        }),
        svgEl("text", { x: left, y: 12 }, ylabel),
        svgEl(
            "text",
            { x: w - right, y: height - 1, "text-anchor": "end" },
            xlabel,
        ),
    );
    $(id).replaceChildren(svg);
    return { svg, x, y };
}
function path(svg, points, color = palette[0], width = 2.3) {
    svg.append(
        svgEl("path", {
            d: points
                .map(
                    ([x, y], i) =>
                        `${i ? "L" : "M"}${x.toFixed(3)} ${y.toFixed(3)}`,
                )
                .join(" "),
            fill: "none",
            stroke: color,
            "stroke-width": width,
            "stroke-linejoin": "round",
        }),
    );
}
function showStep(step, scroll = true) {
    if (!all("[data-panel]").some((p) => p.dataset.panel === step)) return;
    activeStep = step;
    all("[data-panel]").forEach((p) => {
        p.hidden = p.dataset.panel !== step;
    });
    all("[data-step]").forEach((b) => {
        if (b.dataset.step === step) b.setAttribute("aria-current", "step");
        else b.removeAttribute("aria-current");
    });
    if (step === "governance") renderGovernance();
    if (scroll) {
        const panel = document.querySelector(`[data-panel="${step}"]`);
        const heading = panel.querySelector("h2");
        heading.tabIndex = -1;
        heading.focus({ preventScroll: true });
        panel.scrollIntoView({ block: "start" });
    }
}
function stopWork() {
    if (activeWorker) {
        activeWorker.worker.terminate();
        activeWorker.reject(
            new Error(
                "Calculation stopped. Change the inputs or run it again.",
            ),
        );
        activeWorker = null;
    }
    $("stop-analysis").hidden = true;
    $("stop-architect").hidden = true;
    $("analyse").disabled = false;
    $("run-architect").disabled = false;
}
function invalidate() {
    revision++;
    stopWork();
    analysis = null;
    genome = null;
    capsule = null;
    settlement = null;
    policies = [];
    supply = 0;
    reserve = 0n;
    $("seed-passphrase").value = "";
    $("operator-approval").checked = false;
    $("insight-results").hidden = true;
    $("settlement-results").hidden = true;
    $("architect-results").hidden = true;
    $("seed-status").textContent = "";
    $("settlement-status").textContent = "";
    $("architect-status").textContent = "";
    renderPlan();
    renderMarket();
    updateGates();
}
function updateGates() {
    const hasPlan = Boolean(genome),
        funded =
            hasPlan &&
            reserve >=
                tokenUnits(String(analysis.portfolio.evidence.totals.cost));
    $("seal-seed").disabled =
        !hasPlan || cryptoBusy || supply > 0 || Boolean(settlement);
    $("download-seed").disabled = !capsule;
    $("buy-lots").disabled = !capsule || Boolean(settlement);
    $("sell-lots").disabled = !capsule || Boolean(settlement) || !supply;
    $("settle-plan").disabled = !capsule || !funded || Boolean(settlement);
    all("[data-mission]").forEach((b) => {
        b.disabled = !hasPlan;
    });
    const completed = {
        insight: hasPlan,
        seed: Boolean(capsule),
        market: funded,
        sovereign: hasPlan,
        settlement: Boolean(settlement),
        architect: policies.length > 0,
    };
    all("#journey button").forEach((b) =>
        b.classList.toggle("completed", completed[b.dataset.step]),
    );
    if (!settlement)
        $("settlement-status").textContent = !hasPlan
            ? "Run Insight first."
            : !capsule
              ? "Seal the Nova-Seed first."
              : !funded
                ? "Fund the selected project costs in MARK before settlement."
                : "Funding is sufficient. Inspect the checks and confirm your review.";
    $("market-status").textContent = settlement
        ? "This mission has settled. Funding and redemption are closed; the ledger shows remaining escrow."
        : !capsule
          ? "Seal the Nova-Seed before funding this plan."
          : funded
            ? "The selected plan is funded. You can now inspect and settle it."
            : "Fund enough to cover the selected project costs.";
}
function renderInputs() {
    $("scenario-budget").value = scenario.budget;
    $("scenario-risk").value = scenario.risk_limit;
    $("scenario-json").value = JSON.stringify(scenario, null, 2);
    $("case-context").textContent =
        `${scenario.title} · ${scenario.opportunities.length} opportunities · editable scenario`;
    all(".case-card").forEach((b) =>
        b.setAttribute("aria-pressed", String(b.dataset.case === scenario.id)),
    );
    $("opportunity-inputs").replaceChildren(
        ...scenario.opportunities.map((item, index) => {
            const row = el("tr"),
                title = el("td");
            title.append(el("strong", item.title), el("small", item.sector));
            row.append(title);
            for (const key of ["cost", "value", "risk"]) {
                const cell = el("td"),
                    input = el("input");
                input.type = "number";
                input.value = item[key];
                input.min = key === "cost" ? "1" : "0";
                input.max = key === "risk" ? "10000" : "1000000";
                input.step = "1";
                input.required = true;
                input.setAttribute("aria-label", `${item.title}: ${key}`);
                input.dataset.index = index;
                input.dataset.field = key;
                cell.append(input);
                row.append(cell);
            }
            return row;
        }),
    );
}
function inputScenario() {
    const next = structuredClone(scenario);
    next.budget = Number($("scenario-budget").value);
    next.risk_limit = Number($("scenario-risk").value);
    all("#opportunity-inputs input").forEach((input) => {
        next.opportunities[Number(input.dataset.index)][input.dataset.field] =
            Number(input.value);
    });
    return validateScenario(next);
}
async function work(kind) {
    stopWork();
    const worker = new Worker(new URL("./worker.mjs", import.meta.url), {
        type: "module",
    });
    const current = revision;
    $(kind === "architect" ? "stop-architect" : "stop-analysis").hidden = false;
    $(kind === "architect" ? "run-architect" : "analyse").disabled = true;
    return new Promise((resolve, reject) => {
        activeWorker = { worker, reject };
        worker.onmessage = ({ data }) => {
            if (activeWorker?.worker !== worker) return;
            worker.terminate();
            activeWorker = null;
            $("stop-analysis").hidden = true;
            $("stop-architect").hidden = true;
            $("analyse").disabled = false;
            $("run-architect").disabled = false;
            if (data.error) reject(new Error(data.error));
            else if (current !== revision)
                reject(new Error("Inputs changed. Run the new scenario."));
            else resolve(data.result);
        };
        worker.onerror = () => {
            if (activeWorker?.worker !== worker) return;
            stopWork();
            status(
                "The calculation worker could not load. Reload the page and retry.",
                true,
            );
        };
        worker.postMessage({ kind, scenario });
    });
}
async function analyse() {
    const next = inputScenario();
    invalidate();
    scenario = next;
    $("scenario-json").value = JSON.stringify(scenario, null, 2);
    status(
        "Comparing every feasible portfolio and coordinating the selected work…",
    );
    analysis = await work("analysis");
    genome = analysis.selected.length ? makeGenome(analysis) : null;
    renderInsight();
    renderPlan();
    renderMarket();
    updateGates();
    status(
        genome
            ? `${scenario.title}: ${analysis.selected.length} projects selected; ${analysis.portfolio.evidence.examined_subsets} portfolios compared. Ready to inspect.`
            : "No project fits these limits. Increase the budget or risk allowance and try again.",
    );
}
async function chooseScenario(value) {
    scenario = validateScenario(value);
    invalidate();
    renderInputs();
    showStep("insight", false);
    await analyse();
}
function renderInsight() {
    const totals = analysis.portfolio.evidence.totals;
    metrics("portfolio-metrics", [
        ["Assumed benefit", num(totals.value), scenario.unit],
        [
            "Budget used",
            `${totals.cost} / ${scenario.budget}`,
            "planning credits",
        ],
        [
            "Risk used",
            `${totals.risk} / ${scenario.risk_limit}`,
            `${analysis.selected.length} selected projects`,
        ],
    ]);
    const { svg, x, y } = chart("frontier-chart", {
        xmax: Math.max(...scenario.opportunities.map((p) => p.cost)) * 1.15,
        ymax: Math.max(...scenario.opportunities.map((p) => p.value)) * 1.15,
        xlabel: "COST",
        ylabel: "ASSUMED BENEFIT",
    });
    scenario.opportunities.forEach((item, i) => {
        const selected = analysis.selected.some((s) => s.id === item.id);
        const circle = svgEl("circle", {
            cx: x(item.cost),
            cy: y(item.value),
            r: selected ? 9 : 6,
            fill: selected ? palette[0] : "#617688",
            "fill-opacity": selected ? 0.9 : 0.55,
        });
        circle.append(
            svgEl(
                "title",
                {},
                `${item.title}: cost ${item.cost}, benefit ${item.value}, risk ${item.risk}; ${selected ? "selected" : "not selected"}`,
            ),
        );
        svg.append(
            circle,
            svgEl(
                "text",
                { x: x(item.cost) + 12, y: y(item.value) - 9 },
                i + 1,
            ),
        );
    });
    $("portfolio-selection").replaceChildren(
        ...scenario.opportunities.map((item, i) => {
            const row = el("div", undefined, "selection-row"),
                copy = el("div");
            copy.append(
                el(
                    "strong",
                    `${String(i + 1).padStart(2, "0")} · ${item.title}`,
                ),
                el(
                    "small",
                    `${item.cost} cost · ${item.value} assumed benefit · ${item.risk} risk`,
                ),
            );
            row.append(
                copy,
                el(
                    "span",
                    analysis.selected.some((s) => s.id === item.id)
                        ? "SELECTED ↗"
                        : "—",
                ),
            );
            return row;
        }),
    );
    $("insight-results").hidden = false;
}
function renderPlan() {
    $("seed-name").textContent = genome
        ? scenario.title
        : "Run Insight to prepare your seed.";
    $("seed-detail").textContent = genome
        ? `${analysis.selected.length} projects · ${analysis.schedule.evidence.operations.length} tasks · one reproducible plan`
        : "Your encrypted capsule will contain the complete scenario and native missions.";
    $("genome-preview").textContent = genome
        ? JSON.stringify(genome, null, 2)
        : "No computed plan yet.";
    if (!genome) {
        [
            "schedule-metrics",
            "gantt-chart",
            "task-list",
            "council-checks",
        ].forEach((id) => $(id).replaceChildren());
        $("reservoir").replaceChildren(
            el("span", "VALUE RESERVOIR", "eyebrow"),
            el("h3", "Complete settlement to inspect the reservoir."),
            el(
                "p",
                "Unspent escrow and the modeled treasury remain visible. Workers’ payouts are not automatically recycled.",
            ),
        );
        return;
    }
    const evidence = analysis.schedule.evidence;
    metrics("schedule-metrics", [
        ["Completion", evidence.makespan, "scenario time units"],
        [
            "Operations",
            evidence.operations.length,
            "research → delivery → verification",
        ],
        [
            "Orders compared",
            evidence.examined_orders,
            "best within job-priority policy",
        ],
    ]);
    const w = 650,
        h = 240,
        left = 100,
        width = 526,
        svg = svgEl("svg", { viewBox: `0 0 ${w} ${h}`, "aria-hidden": "true" });
    for (let i = 0; i <= 5; i++) {
        const xx = left + (width * i) / 5;
        svg.append(
            svgEl("line", {
                x1: xx,
                x2: xx,
                y1: 25,
                y2: 193,
                class: "gridline",
            }),
            svgEl(
                "text",
                { x: xx, y: 217, "text-anchor": "middle" },
                num((evidence.makespan * i) / 5),
            ),
        );
    }
    ["research", "delivery", "verification"].forEach((name, lane) => {
        const yy = 35 + lane * 57;
        svg.append(
            svgEl(
                "text",
                { x: left - 12, y: yy + 20, "text-anchor": "end" },
                name,
            ),
        );
        evidence.operations
            .filter((op) => op.machine === name)
            .forEach((op) => {
                const idx = analysis.selected.findIndex((p) => p.id === op.job),
                    item = analysis.selected[idx];
                const rect = svgEl("rect", {
                    x: left + (op.start / evidence.makespan) * width,
                    y: yy,
                    width:
                        ((op.end - op.start) / evidence.makespan) * width - 1,
                    height: 32,
                    rx: 3,
                    fill: palette[idx],
                });
                rect.append(
                    svgEl(
                        "title",
                        {},
                        `${item.title}: ${name}, ${op.start}–${op.end}`,
                    ),
                );
                svg.append(rect);
            });
    });
    $("gantt-chart").replaceChildren(svg);
    $("task-list").replaceChildren(
        ...analysis.selected.map((item, i) => {
            const row = el("div", undefined, "selection-row"),
                copy = el("div");
            copy.append(
                el("strong", `${i + 1}. ${item.title}`),
                el(
                    "small",
                    `Research ${item.effort[0]} → Delivery ${item.effort[1]} → Verification ${item.effort[2]}`,
                ),
            );
            const color = svgEl("svg", {
                width: 14,
                height: 14,
                viewBox: "0 0 14 14",
                "aria-hidden": "true",
            });
            color.append(
                svgEl("circle", { cx: 7, cy: 7, r: 5, fill: palette[i] }),
            );
            row.append(copy, color);
            return row;
        }),
    );
    $("council-checks").replaceChildren(
        ...councilChecks(analysis).map((check) => {
            const card = el(
                "div",
                undefined,
                `check-card${check.passed ? "" : " fail"}`,
            );
            card.append(
                el("span", check.passed ? "✓" : "×", "check-icon"),
                el("h3", check.title),
                el("p", check.detail),
            );
            return card;
        }),
    );
}
function renderMarket() {
    const lots = Number($("market-lots").value);
    try {
        $("market-quote").textContent = curveQuote({
            supply,
            lots,
            base: "1",
            slope: "0.25",
        }).amount;
    } catch {
        $("market-quote").textContent = "Check lots";
    }
    const max = Math.max(
        40,
        supply +
            (Number.isSafeInteger(lots) && lots > 0
                ? Math.min(lots, 1000000)
                : 25),
    );
    const { svg, x, y } = chart("curve-chart", {
        xmax: max,
        ymax: (1 + 0.25 * max) * 1.15,
        xlabel: "OUTSTANDING LOTS",
        ylabel: "NEXT LOT PRICE",
    });
    path(
        svg,
        [
            [x(0), y(1)],
            [x(max), y(1 + 0.25 * max)],
        ],
        palette[2],
    );
    if (supply) {
        const area = svgEl("path", {
            d: `M${x(0)} ${y(0)} L${x(0)} ${y(1)} L${x(supply)} ${y(1 + 0.25 * supply)} L${x(supply)} ${y(0)} Z`,
            fill: "#f6ca8522",
        });
        svg.prepend(area);
        svg.append(
            svgEl("circle", {
                cx: x(supply),
                cy: y(1 + 0.25 * supply),
                r: 6,
                fill: palette[2],
            }),
        );
    }
    metrics("market-metrics", [
        ["Funded", tokenDecimal(reserve), "modeled $AGIALPHA in reserve"],
        [
            "Plan cost",
            genome ? analysis.portfolio.evidence.totals.cost : "—",
            "planning credits mapped 1:1 in this sandbox",
        ],
        ["Lots issued", num(supply), "one modeled funder"],
    ]);
}
function requirePlan() {
    if (!genome)
        throw new Error("Run Insight with a feasible portfolio first.");
}
function trade(direction) {
    requirePlan();
    if (!capsule) throw new Error("Seal the Nova-Seed first.");
    if (settlement)
        throw new Error(
            "This mission is settled. Reset it to explore another funding path.",
        );
    const q = curveQuote({
        supply,
        lots: Number($("market-lots").value),
        base: "1",
        slope: "0.25",
        direction,
    });
    const amount = BigInt(q.units);
    if (direction === "sell" && amount > reserve)
        throw new Error("The modeled reserve cannot cover this redemption.");
    reserve += direction === "buy" ? amount : -amount;
    supply = q.next_supply;
    renderMarket();
    updateGates();
    status(
        `${direction === "buy" ? "Funded" : "Redeemed"} ${q.amount} modeled $AGIALPHA. Reserve is ${tokenDecimal(reserve)}.`,
    );
}
async function report() {
    if (!settlement) throw new Error("Complete modeled settlement first.");
    const result = {
        schema: "agialpha.ascension.report.v1",
        mode: "protocol_simulation",
        scenario,
        analysis,
        seed_commitment: capsule.commitment,
        funding: {
            lots: supply,
            deposited: tokenDecimal(reserve),
            curve: "1 + 0.25 × supply",
        },
        checks: councilChecks(analysis),
        operator_review: "accepted in browser",
        settlement,
        limits: [
            "Scenario benefits are user assumptions, not measured gains.",
            "Funding and settlement are simulated; no wallet transaction occurred.",
            "This digest detects accidental changes; it is not a trusted signature or independent validation.",
        ],
    };
    return { ...result, sha256: await hashObject(result) };
}
function renderSettlement() {
    metrics("ledger-metrics", [
        ["Burned", settlement.burned, "1% of gross project payouts"],
        [
            "Minted",
            settlement.minted,
            "actor + treasury; combined cap enforced",
        ],
        [
            "Balance check",
            settlement.conservation ? "Exact ✓" : "Failed",
            "escrow + workers + treasury = supply",
        ],
    ]);
    $("ledger-flow").replaceChildren();
    for (const [title, amount] of [
        ["ESCROW DEPOSIT", tokenDecimal(reserve)],
        ["→", ""],
        ["WORKERS", settlement.workers],
        ["TREASURY", settlement.treasury],
    ]) {
        const node = el(
            "div",
            undefined,
            title === "→" ? "flow-arrow" : "flow-box",
        );
        if (title === "→") node.textContent = "→";
        else node.append(el("small", title), el("strong", amount));
        $("ledger-flow").append(node);
    }
    table(
        "ledger-table",
        ["Project", "Gross", "Burn", "Worker", "Treasury mint"],
        settlement.events.map((e) => [
            scenario.opportunities.find((p) => p.id === e.id).title,
            e.gross,
            e.burn,
            e.worker,
            e.treasury_mint,
        ]),
    );
    $("settlement-results").hidden = false;
    $("settlement-status").textContent =
        `${settlement.settled_jobs} jobs settled exactly once. ${settlement.escrow} remains in escrow.`;
    $("reservoir").replaceChildren(
        el("span", "VALUE RESERVOIR", "eyebrow"),
        el(
            "h3",
            `${settlement.escrow} unspent escrow · ${settlement.treasury} treasury`,
        ),
        el(
            "p",
            "These modeled balances are available to inspect when choosing a new cycle. Selecting a policy below starts a fresh scenario; no funds transfer automatically.",
        ),
    );
}
function renderPolicies() {
    const { svg, x, y } = chart("architect-chart", {
        xmax: Math.max(...policies.map((p) => p.cost)) * 1.15,
        ymax: Math.max(...policies.map((p) => p.value)) * 1.15,
        xlabel: "COST",
        ylabel: "ASSUMED BENEFIT",
    });
    policies.forEach((p) => {
        const dot = svgEl("circle", {
            cx: x(p.cost),
            cy: y(p.value),
            r: p.frontier ? 7 : 4,
            fill: p.frontier ? palette[0] : "#617688",
            "fill-opacity": 0.75,
        });
        dot.append(
            svgEl(
                "title",
                {},
                `${p.id}: cost ${p.cost}, value ${p.value}, risk ${p.risk}, duration ${p.duration}`,
            ),
        );
        svg.append(dot);
    });
    $("policy-list").replaceChildren(
        ...policies.map((p) => {
            const card = el(
                "div",
                undefined,
                `policy-card${p.frontier ? " frontier" : ""}`,
            );
            card.append(
                el("h4", `${p.frontier ? "◇ Frontier · " : ""}${p.id}`),
                el("p", `Budget ${p.budget} · risk allowance ${p.risk_limit}`),
                el(
                    "p",
                    `Benefit ${p.value} · cost ${p.cost} · risk ${p.risk} · duration ${p.duration}`,
                ),
            );
            const button = el(
                "button",
                "Use this policy ↗",
                "button secondary",
            );
            button.dataset.policy = p.id;
            card.append(button);
            return card;
        }),
    );
    $("architect-results").hidden = false;
}
function renderGovernance() {
    const kind = $("game-kind").value,
        mix = Number($("initial-mix").value) / 100;
    $("mix-value").textContent = `${num(mix * 100)}%`;
    $("hawk-inputs").hidden = kind !== "hawk";
    let history, names, note;
    if (kind === "hawk") {
        const V = Number($("hawk-value").value),
            C = Number($("hawk-cost").value),
            result = hawkDove(V, C, mix);
        history = result.history;
        names = ["Hawk", "Dove"];
        note = `dx/dt = x(1−x)(V−Cx)/2. ${result.interior ? `The interior equilibrium is V/C = ${num(result.equilibrium * 100)}% hawks.` : "With V ≥ C, the attracting boundary is all hawks."} The plotted endpoint is ${num(history.at(-1).mix[0] * 100)}%.`;
    } else if (kind === "rps") {
        history = evolveStrategies(
            [
                [0, -1, 1],
                [1, 0, -1],
                [-1, 1, 0],
            ],
            [mix, (1 - mix) * 0.4, (1 - mix) * 0.6],
        );
        names = ["Rock", "Paper", "Scissors"];
        note =
            "This zero-sum game cycles around its interior equilibrium. Average payoff remains zero; the dynamics do not guarantee convergence or increasing welfare.";
    } else {
        history = evolveStrategies(
            [
                [1, 0],
                [0, 1],
            ],
            [mix, 1 - mix],
        );
        names = ["Strategy A", "Strategy B"];
        note =
            "Two attracting outcomes, one coordination problem. Initial shares below 50% favor B; above 50% favor A. This demonstrates why a universal unique equilibrium cannot be assumed.";
    }
    const { svg, x, y } = chart("strategy-chart", {
        xmax: history.at(-1).t,
        ymax: 100,
        xlabel: "MODEL TIME",
        ylabel: "POPULATION SHARE (%)",
    });
    names.forEach((name, i) => {
        path(
            svg,
            history.map((p) => [x(p.t), y(p.mix[i] * 100)]),
            palette[i],
        );
        const label = svgEl("text", { x: 350 + i * 95, y: 12 }, name);
        label.setAttribute("fill", palette[i]);
        svg.append(label);
    });
    $("strategy-note").textContent = note;
    const additional = Number($("mitigation").value) / 100;
    $("mitigation-value").textContent =
        `${num(additional * 100)} percentage points`;
    const audit = riskAudit(
        PAPER_RISKS.map((r) => ({
            ...r,
            stake: Math.min(1, r.stake + additional),
            formal: Math.min(1, r.formal + additional),
            fuzz: Math.min(1, r.fuzz + additional),
        })),
        Number($("risk-threshold").value),
    );
    $("risk-chart").replaceChildren(
        ...audit.rows.map((r) => {
            const row = el("div", undefined, "risk-row"),
                bar = svgEl("svg", {
                    viewBox: "0 0 100 12",
                    preserveAspectRatio: "none",
                    "aria-hidden": "true",
                });
            bar.append(
                svgEl("rect", {
                    x: 0,
                    y: 0,
                    width: (r.residual / 0.2) * 100,
                    height: 12,
                    fill: palette[2],
                    rx: 2,
                }),
            );
            row.append(
                el("span", `${r.id} · ${r.title}`),
                bar,
                el("b", r.residual.toFixed(5)),
            );
            return row;
        }),
    );
    $("risk-conclusion").textContent =
        `Aggregate ${audit.aggregate.toFixed(6)} · threshold ${audit.threshold} · ${audit.admitted ? "within the modeled gate" : "exceeds the modeled gate"}.`;
    $("risk-conclusion").classList.toggle("failed", !audit.admitted);
    const risk = actionRisk(
        Number($("per-action").value),
        Number($("action-count").value),
    );
    metrics("action-risk", [
        [
            "Expected failures",
            num(risk.expected_failures),
            "sum of per-action expectations",
        ],
        [
            "At least one",
            `${num(risk.independent_probability * 100, 6)}%`,
            "if failures are independent",
        ],
        [
            "Required p ≤",
            risk.union_budget_per_action.toExponential(2),
            "sufficient union-bound budget for 0.1%",
        ],
    ]);
    const severity = Number($("fault-severity").value);
    $("severity-value").textContent = `${num(severity / 100)}%`;
    const stake = stakeDecision({
        stake: $("stake-amount").value,
        minimum: "10",
        severity,
        attested: $("identity-attested").checked,
        name: $("stake-name").value,
    });
    $("stake-result").textContent =
        `${stake.eligible ? "Eligible at admission" : "Not eligible at admission"}. Modeled slash: ${stake.slash}. Remaining stake: ${stake.remaining}. Eligibility must be checked again after a slash.`;
    const ballot = quadraticBallot([Number($("proposal-votes").value)], 100),
        days = Number($("upgrade-days").value);
    const upgrade = upgradeStatus({
        queued_at: 0,
        now: days * 86400,
        approved: $("governance-approved").checked && ballot.admitted,
        policy_valid: $("policy-valid").checked,
    });
    $("days-value").textContent = `Day ${days}`;
    $("governance-result").textContent =
        `Ballot cost ${ballot.spent}/100 credits: ${ballot.admitted ? "within budget" : "rejected"}. ${upgrade.executable ? "All modeled gates pass; the upgrade may execute." : `Upgrade blocked. ${Math.ceil(upgrade.seconds_remaining / 86400)} days remain; approval and policy checks are also required.`}`;
    $("governance-result").classList.toggle("failed", !upgrade.executable);
}

all("[data-step]").forEach((button) =>
    button.addEventListener("click", () => showStep(button.dataset.step)),
);
all("[data-next]").forEach((button) =>
    button.addEventListener("click", () => showStep(button.dataset.next)),
);
$("scenario-form").addEventListener(
    "submit",
    guarded(async (event) => {
        event.preventDefault();
        await analyse();
    }),
);
$("scenario-form").addEventListener("input", (event) => {
    if (event.target.id === "scenario-json") return;
    invalidate();
    status(
        "Inputs changed. Discover the portfolio again to refresh the plan, funding and review.",
    );
});
$("apply-scenario").addEventListener(
    "click",
    guarded(async () => {
        if ($("scenario-json").value.length > 150000)
            throw new Error("Scenario exceeds 150 KB.");
        await chooseScenario(JSON.parse($("scenario-json").value));
    }),
);
$("scenario-import").addEventListener(
    "change",
    guarded(async (event) => {
        try {
            await chooseScenario(await readFile(event.target.files[0], 150000));
        } finally {
            event.target.value = "";
        }
    }),
);
$("download-scenario").addEventListener(
    "click",
    guarded(() => download("ascension-scenario.json", inputScenario())),
);
$("reset-lab").addEventListener(
    "click",
    guarded(() =>
        chooseScenario(scenarios.find((s) => s.id === scenario.id) || scenario),
    ),
);
$("stop-analysis").addEventListener("click", stopWork);
$("stop-architect").addEventListener("click", stopWork);
$("seal-form").addEventListener(
    "submit",
    guarded(async (event) => {
        event.preventDefault();
        requirePlan();
        if (cryptoBusy) return;
        if (supply || settlement)
            throw new Error(
                "This seed is already funded. Reset the mission before resealing it.",
            );
        const current = revision,
            payload = genome,
            phrase = $("seed-passphrase").value;
        cryptoBusy = true;
        updateGates();
        $("seed-status").textContent =
            "Deriving an encryption key and sealing the genome…";
        try {
            const sealed = await sealSeed(payload, phrase);
            if (revision !== current)
                throw new Error(
                    "The plan changed during encryption. Seal the new plan.",
                );
            capsule = sealed;
            $("seed-status").textContent =
                `Sealed. Commitment ${capsule.commitment.slice(0, 20)}… Download the capsule and keep the passphrase separately.`;
            status(
                "Nova-Seed sealed on this device. Your FusionPlan is ready for the funding model.",
            );
        } finally {
            cryptoBusy = false;
            $("seed-passphrase").value = "";
            updateGates();
        }
    }),
);
$("download-seed").addEventListener(
    "click",
    guarded(() => {
        if (!capsule) throw new Error("Seal a seed first.");
        download("nova-seed.sealed.json", capsule);
    }),
);
$("recover-form").addEventListener(
    "submit",
    guarded(async (event) => {
        event.preventDefault();
        recovered = null;
        $("restore-plan").hidden = true;
        $("recovered-genome").hidden = true;
        $("recovery-status").textContent =
            "Authenticating and decrypting the capsule…";
        const phrase = $("recovery-passphrase").value;
        try {
            recovered = await openSeed(
                await readFile($("seed-import").files[0]),
                phrase,
            );
            validateScenario(recovered.scenario);
            $("recovered-genome").textContent = JSON.stringify(
                recovered,
                null,
                2,
            );
            $("recovered-genome").hidden = false;
            $("recovery-status").textContent =
                "Authenticated and recovered. Inspect the genome, then restore its scenario to recompute the plan.";
            $("restore-plan").hidden = false;
        } catch (error) {
            $("recovery-status").textContent = error.message;
            throw error;
        } finally {
            $("recovery-passphrase").value = "";
        }
    }),
);
$("restore-plan").addEventListener(
    "click",
    guarded(async () => {
        if (!recovered) throw new Error("Recover a seed first.");
        await chooseScenario(recovered.scenario);
        // A user may explore another panel while the real worker is running.
        if (activeStep === "insight") showStep("insight");
    }),
);
$("market-lots").addEventListener("input", renderMarket);
$("market-form").addEventListener(
    "submit",
    guarded((event) => {
        event.preventDefault();
        trade("buy");
    }),
);
$("sell-lots").addEventListener(
    "click",
    guarded(() => trade("sell")),
);
all("[data-mission]").forEach((button) =>
    button.addEventListener(
        "click",
        guarded(() => {
            requirePlan();
            download(
                `ascension-${button.dataset.mission}.json`,
                analysis.missions[button.dataset.mission],
            );
        }),
    ),
);
$("settlement-form").addEventListener(
    "submit",
    guarded((event) => {
        event.preventDefault();
        requirePlan();
        if (!capsule || settlement || !$("operator-approval").checked)
            throw new Error(
                "A sealed, unspent mission and your explicit review are required.",
            );
        if (
            reserve <
            tokenUnits(String(analysis.portfolio.evidence.totals.cost))
        )
            throw new Error("Fund the selected plan before settlement.");
        settlement = runSettlement(analysis, {
            deposit: tokenDecimal(reserve),
            certified_value: $("certified-value").value,
            emission_cap: $("emission-cap").value,
        });
        renderSettlement();
        updateGates();
        status(
            "Modeled settlement complete. Exact token conservation passed; the full evidence is ready to export.",
        );
    }),
);
$("download-report").addEventListener(
    "click",
    guarded(async () => download("ascension-evidence.json", await report())),
);
$("download-brief").addEventListener(
    "click",
    guarded(async () => {
        const r = await report();
        const lines = [
            `# ${scenario.title}`,
            "",
            scenario.goal,
            "",
            "Protocol simulation with user-supplied assumptions.",
            "",
            "## Selected projects",
            "",
            ...analysis.selected.map(
                (p) =>
                    `- ${p.title}: cost ${p.cost}, assumed benefit ${p.value}, risk ${p.risk}.`,
            ),
            "",
            "## Settlement",
            "",
            `Deposit: ${r.funding.deposited}; worker payouts: ${settlement.workers}; burn: ${settlement.burned}; treasury: ${settlement.treasury}; unspent escrow: ${settlement.escrow}.`,
            `Combined mint: ${settlement.minted}. Token conservation: passed.`,
            "",
            `Seed commitment: ${capsule.commitment}`,
            "",
            `Evidence JSON SHA-256: ${r.sha256}`,
            "",
            "## Limits",
            "",
            ...r.limits.map((s) => `- ${s}`),
            "",
        ];
        download(
            "ascension-mission-brief.md",
            lines.join("\n"),
            "text/markdown",
        );
    }),
);
$("run-architect").addEventListener(
    "click",
    guarded(async () => {
        scenario = inputScenario();
        $("architect-status").textContent =
            "Comparing 20 budget and risk policies…";
        policies = await work("architect");
        renderPolicies();
        updateGates();
        $("architect-status").textContent =
            `20 policies compared. ${policies.filter((p) => p.frontier).length} are not dominated across cost, benefit, risk and duration.`;
    }),
);
$("policy-list").addEventListener(
    "click",
    guarded(async (event) => {
        const button = event.target.closest("[data-policy]");
        if (!button) return;
        const policy = policies.find((p) => p.id === button.dataset.policy);
        await chooseScenario({
            ...scenario,
            budget: policy.budget,
            risk_limit: policy.risk_limit,
        });
        // Completion must not undo a navigation choice made after this request.
        if (activeStep === "insight") showStep("insight");
        status(
            "New policy applied. The portfolio was recomputed; seed, funding and review start a fresh cycle.",
        );
    }),
);
all(
    '[data-panel="governance"] input, [data-panel="governance"] select',
).forEach((input) =>
    input.addEventListener("input", guarded(renderGovernance)),
);

try {
    const response = await fetch(new URL("./scenarios.json", import.meta.url));
    if (!response.ok)
        throw new Error(
            "The scenario library could not load. Reload to try again.",
        );
    scenarios = (await response.json()).map(validateScenario);
    $("case-picker").replaceChildren(
        ...scenarios.map((item, i) => {
            const button = el("button", undefined, "case-card");
            button.dataset.case = item.id;
            button.setAttribute("aria-pressed", "false");
            button.append(
                el("span", `MISSION / 0${i + 1}`, "case-no"),
                el("strong", item.title),
                el("small", item.eyebrow),
                el("span", "↗", "case-arrow"),
            );
            button.addEventListener(
                "click",
                guarded(() => chooseScenario(item)),
            );
            return button;
        }),
    );
    const target = location.hash.slice(1);
    await chooseScenario(
        scenarios.find((s) => s.id === target) || scenarios[0],
    );
    renderGovernance();
    if (all("[data-panel]").some((p) => p.dataset.panel === target))
        showStep(target);
    if ("serviceWorker" in navigator)
        navigator.serviceWorker
            .register("../service-worker.js")
            .catch(() =>
                status(
                    "The lab is ready. Offline caching is unavailable in this browser.",
                ),
            );
} catch (error) {
    status(error.message, true);
}
