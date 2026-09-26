// SPDX-License-Identifier: Apache-2.0
import {
    SECTORS,
    DEFAULT_CONFIG,
    validateScenario,
    validateConfig,
    allocateEnvelope,
    quadrillionsToDollars,
    compareArchitectures,
    searchArchitectures,
    proofGates,
    buildEvidence,
    verifyEvidence,
    buildDossier,
    emptyChronicle,
    appendChronicle,
    verifyChronicle,
    exportWorkspace,
    restoreWorkspace,
} from "./engine.mjs";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const clone = (value) => structuredClone(value);
const node = (tag, text = "", className = "") => {
    const el = document.createElement(tag);
    el.textContent = text;
    if (className) el.className = className;
    return el;
};
const svgNode = (tag, attributes, text = "") => {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attributes))
        el.setAttribute(key, String(value));
    el.textContent = text;
    return el;
};
const status = (message, error = false) => {
    $("#atlas-status").textContent = message;
    $("#atlas-status").dataset.error = String(error);
};
const money = (value) => "$" + BigInt(value).toLocaleString("en-US");
function compactMoney(value) {
    const amount = BigInt(value);
    for (const [unit, scale] of [
        ["Q", 1000000000000000n],
        ["T", 1000000000000n],
        ["B", 1000000000n],
        ["M", 1000000n],
    ]) {
        if (amount >= scale)
            return (
                "$" +
                String((amount * 100n) / scale)
                    .replace(/(\d{2})$/, ".$1")
                    .replace(/\.00$/, "") +
                unit
            );
    }
    return money(value);
}
const descriptions = [
    "Power is the first constraint—and a frontier for useful coordination.",
    "Turn scarce compute into timely, reviewable work.",
    "Make discovery reproducible enough to build upon.",
    "Put better evidence before consequential decisions.",
    "Find the physical building blocks of a better system.",
    "Connect capable machines with accountable human control.",
    "Measure the full cost before claiming the return.",
    "Make planetary consequences visible in the calculation.",
    "Design a firm around useful work and independent checks.",
    "Coordinate the systems that every other frontier depends on.",
    "Turn knowledge into demonstrated, transferable capability.",
    "Make incentives, authority and failure domains explicit.",
];
const glyphs = ["↯", "⌘", "✧", "+", "◇", "⌬", "↗", "◌", "⧉", "⌗", "◈", "⊙"];
// Deliberately composed positions, not scores. The underlying allocation is in the ledger.
const positions = [
    [25, 20],
    [62, 13],
    [82, 30],
    [76, 65],
    [56, 82],
    [33, 82],
    [14, 62],
    [13, 37],
    [43, 18],
    [83, 48],
    [34, 58],
    [61, 61],
];
let library = [];
const customScenarios = new Map();
let scenario;
let config = clone(DEFAULT_CONFIG);
let comparison;
let selectedSector = "Energy";
let selectedClaim = null;
let chronicle = emptyChronicle();
let evidence = null;
let search = null;
let dirty = false;
let envelopeDirty = false;
let revision = 0;
let busy = false;

function download(name, value) {
    const url = URL.createObjectURL(
        new Blob([JSON.stringify(value, null, 2) + "\n"], {
            type: "application/json",
        }),
    );
    const link = node("a");
    link.href = url;
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function readFile(input) {
    const file = input.files[0];
    if (!file) throw new Error("Choose a JSON file.");
    if (file.size > 250000)
        throw new Error("Choose a JSON document smaller than 250 KB.");
    try {
        return JSON.parse(await file.text());
    } finally {
        input.value = "";
    }
}
async function action(operation) {
    if (busy) return;
    busy = true;
    $("#atlas").setAttribute("aria-busy", "true");
    try {
        await operation();
    } catch (error) {
        status(error.message, true);
    } finally {
        busy = false;
        $("#atlas").removeAttribute("aria-busy");
    }
}
function table(headers, rows) {
    const result = node("table");
    const head = node("thead");
    const tr = node("tr");
    for (const header of headers) {
        const th = node("th", header);
        th.scope = "col";
        tr.append(th);
    }
    head.append(tr);
    result.append(head);
    const body = node("tbody");
    for (const values of rows) {
        const row = node("tr");
        for (const value of values) row.append(node("td", String(value)));
        body.append(row);
    }
    result.append(body);
    return result;
}
function openView(view, focus = true) {
    for (const button of $$("[data-view]")) {
        if (button.dataset.view === view)
            button.setAttribute("aria-current", "page");
        else button.removeAttribute("aria-current");
    }
    for (const panel of $$("[data-panel]"))
        panel.hidden = panel.dataset.panel !== view;
    if (focus) {
        const heading = $(`[data-panel="${view}"] h2`);
        heading.tabIndex = -1;
        heading.focus({ preventScroll: true });
        heading.scrollIntoView({ behavior: "auto", block: "start" });
    }
}
function invalidate(message) {
    revision += 1;
    evidence = null;
    search = null;
    $("#search-results").hidden = true;
    $("#review-panel").hidden = true;
    $("#download-proof").disabled = true;
    $("#build-proof").disabled = dirty || envelopeDirty;
    renderGates();
    if (message) status(message);
}
function readConfig() {
    return validateConfig(
        Object.fromEntries(
            Object.keys(DEFAULT_CONFIG).map((key) => [
                key,
                Number($("#" + key).value),
            ]),
        ),
    );
}
function writeConfig() {
    for (const [key, value] of Object.entries(config))
        $("#" + key).value = value;
}
function updateComparison() {
    comparison = compareArchitectures(scenario, config);
    dirty = false;
    search = null;
    $("#search-results").hidden = true;
    invalidate();
    renderComparison();
}
function useScenario(value) {
    scenario = validateScenario(value);
    config = clone(DEFAULT_CONFIG);
    dirty = false;
    envelopeDirty = false;
    selectedSector = scenario.claims[0].sector;
    selectedClaim = scenario.claims[0].id;
    $("#scenario-question").textContent = scenario.question;
    const dollars = BigInt(scenario.envelope_usd);
    $("#envelope").value =
        dollars % 1000000000000n === 0n
            ? String(dollars / 1000000000000000n) +
              (dollars % 1000000000000000n
                  ? "." +
                    String(
                        (dollars % 1000000000000000n) / 1000000000000n,
                    ).padStart(3, "0")
                  : "")
            : "";
    $("#envelope").placeholder = "Custom · see exact ledger";
    $("#claim-sector").value = "all";
    $("#claim-search").value = "";
    $("#claim-form").hidden = true;
    writeConfig();
    updateComparison();
    renderMap();
    renderClaims();
    status(
        `${scenario.title} is ready. Explore a frontier, compare the architecture, then replay its evidence.`,
    );
}
function renderMap() {
    const focused = document.activeElement?.classList.contains("sector-node")
        ? document.activeElement.getAttribute("aria-label")
        : null;
    const allocations = allocateEnvelope(
        scenario.envelope_usd,
        scenario.weights_bps,
    );
    $("#sector-nodes").replaceChildren();
    $("#sector-links").replaceChildren();
    positions.forEach(([x, y], i) => {
        for (const target of [
            [50, 50],
            positions[(i + 1) % positions.length],
        ]) {
            const line = svgNode("line", {
                x1: x * 8,
                y1: y * 5.3,
                x2: target[0] * 8,
                y2: target[1] * 5.3,
                class: SECTORS[i] === selectedSector ? "selected-line" : "",
            });
            $("#sector-links").append(line);
        }
        const button = node(
            "button",
            "",
            "sector-node" + (SECTORS[i] === selectedSector ? " selected" : ""),
        );
        button.style.left = x + "%";
        button.style.top = y + "%";
        button.setAttribute(
            "aria-pressed",
            String(SECTORS[i] === selectedSector),
        );
        button.setAttribute("aria-label", `Explore ${SECTORS[i]}`);
        button.append(node("span", "", "node-dot"), node("span", SECTORS[i]));
        button.addEventListener("click", () => {
            selectedSector = SECTORS[i];
            renderMap();
            status(
                `${selectedSector} selected. Its allocation and open claims are shown beside the map.`,
            );
        });
        $("#sector-nodes").append(button);
    });
    const index = SECTORS.indexOf(selectedSector);
    const allocation = allocations[index];
    const claims = scenario.claims.filter(
        (claim) => claim.sector === selectedSector,
    );
    $("#sector-number").textContent =
        `FRONTIER ${String(index + 1).padStart(2, "0")} / 12`;
    $("#sector-title").textContent = selectedSector;
    $("#sector-glyph").textContent = glyphs[index];
    $("#sector-description").textContent = descriptions[index];
    $("#sector-amount").textContent = compactMoney(allocation.scenario_usd);
    $("#sector-amount").title = money(allocation.scenario_usd);
    $("#sector-share").textContent = allocation.weight_bps / 100 + "%";
    $("#sector-claims-count").textContent = String(claims.length);
    $("#sector-claims").replaceChildren(
        ...(claims.length
            ? claims.map((claim) => node("p", claim.title))
            : [
                  node(
                      "p",
                      "An open frontier. Add a falsifiable hypothesis to begin.",
                  ),
              ]),
    );
    $("#envelope-label").textContent = compactMoney(
        scenario.envelope_usd,
    ).replace(/Q$/, " quadrillion");
    $("#allocation-table").replaceChildren(
        table(
            ["Frontier", "Weight", "Illustrative allocation · USD"],
            [
                ...allocations.map((row) => [
                    row.sector,
                    row.weight_bps / 100 + "%",
                    money(row.scenario_usd),
                ]),
                ["Conserved total", "100%", money(scenario.envelope_usd)],
            ],
        ),
    );
    if (focused)
        $$(".sector-node")
            .find((button) => button.getAttribute("aria-label") === focused)
            ?.focus({ preventScroll: true });
}
function renderComparison() {
    const split = $("#split").value;
    const result = comparison[split];
    const before = result.baseline.metrics,
        after = result.candidate.metrics;
    const metrics = [
        [
            "Useful, on-time outputs",
            before.useful,
            after.useful,
            "Valid ground truth + quorum + operator + deadline",
        ],
        [
            "Invalid outputs accepted",
            before.unsafe_accepts,
            after.unsafe_accepts,
            "Negative controls · lower is better",
        ],
        [
            "Credits reserved",
            before.reserved_credits,
            after.reserved_credits,
            `${after.remaining_credits} credits remain in the candidate budget`,
        ],
    ];
    $("#comparison-cards").replaceChildren(
        ...metrics.map(([label, oldValue, newValue, caption]) => {
            const card = node("div", "", "metric");
            const value = node("strong");
            value.append(
                node("small", `${oldValue} → `),
                document.createTextNode(String(newValue)),
            );
            card.append(node("span", label), value, node("p", caption));
            return card;
        }),
    );
    const gain = after.useful - before.useful;
    const traceMax = Math.max(
        config.horizon,
        ...result.candidate.rows.map((row) =>
            row.end === null ? 0 : row.end - row.arrival,
        ),
    );
    $("#comparison-explanation").textContent =
        `${gain >= 0 ? "+" : ""}${gain} useful outputs versus the two-agent baseline on ${split}. ${after.rejected_invalid} invalid cases rejected; ${after.missed_valid} valid cases missed their deadline or were blocked. These are model results on synthetic fixtures.`;
    $("#timeline-caption").textContent =
        `${after.tasks} tasks · ${config.horizon}-minute horizon · ${traceMax}-minute scale`;
    $("#task-timeline").replaceChildren(
        ...result.candidate.rows.map((row) => {
            const el = node("div", "", "task-trace");
            el.dataset.good = String(row.status === "accepted" && row.valid);
            el.dataset.status = row.status;
            el.title = `${row.id}: ${row.status}; ${row.end ?? "no"} completion minute`;
            const meter = node("meter");
            meter.min = 0;
            meter.max = traceMax;
            meter.value = row.end === null ? 0 : row.end - row.arrival;
            meter.setAttribute(
                "aria-label",
                `${row.id}, ${row.status}, ${row.end === null ? "not completed" : `${row.end - row.arrival} minutes from arrival`}`,
            );
            el.append(
                node("span", row.id),
                meter,
                node("b", row.status === "accepted" && row.valid ? "●" : "○"),
            );
            return el;
        }),
    );
    $("#task-table").replaceChildren(
        table(
            [
                "Task",
                "Truth",
                "Arrival",
                "Execution",
                "Review done",
                "Decision",
                "Deadline",
                "Reviewer groups / votes",
                "Credits",
                "Result",
            ],
            result.candidate.rows.map((row) => [
                row.id,
                row.valid ? "valid" : "invalid",
                row.arrival,
                row.start === null ? "—" : `${row.start}–${row.execution_end}`,
                row.review_end ?? "—",
                row.end ?? "—",
                row.due,
                row.reviewers
                    .map(
                        (reviewer) =>
                            `g${reviewer.group}:${reviewer.vote ? "yes" : "no"}`,
                    )
                    .join(", ") || "—",
                row.cost,
                row.status,
            ]),
        ),
    );
    renderGates();
}
function renderGates() {
    if (!comparison) return;
    const gates = [
        ...proofGates(comparison),
        {
            id: "replay",
            label: "Current-input replay",
            passed: Boolean(evidence) && !dirty && !envelopeDirty,
            detail: evidence
                ? `Recomputed bundle ${evidence.digest.slice(0, 16)}…`
                : "Build and replay evidence after the latest input change.",
        },
    ];
    $("#proof-gates").replaceChildren(
        ...gates.map((gate) => {
            const item = node("div", "", "proof-gate");
            item.dataset.passed = String(gate.passed);
            const content = node("div");
            content.append(node("strong", gate.label), node("p", gate.detail));
            item.append(
                node("span", gate.passed ? "✓" : "○", "gate-indicator"),
                content,
            );
            return item;
        }),
    );
}
function renderSearch() {
    $("#search-results").hidden = false;
    const chart = $("#frontier-chart");
    chart.replaceChildren();
    const costs = search.candidates.map((row) => row.training.reserved_credits);
    const min = Math.min(...costs) - 10,
        max = Math.max(...costs) + 10;
    const best = Math.max(
        ...search.candidates.map((row) => row.training.useful),
        1,
    );
    chart.append(
        svgNode("line", { x1: 48, y1: 218, x2: 675, y2: 218, class: "axis" }),
        svgNode("line", { x1: 48, y1: 20, x2: 48, y2: 218, class: "axis" }),
        svgNode("text", { x: 290, y: 252 }, "Reserved planning credits →"),
        svgNode("text", { x: 48, y: 12 }, "Useful training outputs ↑"),
    );
    for (const row of search.candidates) {
        const selected = row === search.candidates[0];
        const dot = svgNode("circle", {
            cx:
                48 +
                ((row.training.reserved_credits - min) / (max - min)) * 615,
            cy: 218 - (row.training.useful / best) * 185,
            r: selected ? 7 : 5,
            class: selected ? "selected-point" : "frontier-point",
        });
        dot.append(
            svgNode(
                "title",
                {},
                `${row.config.agents} agents / ${row.config.validators} validators: ${row.training.useful} useful outputs, ${row.training.reserved_credits} credits${selected ? "; selected" : ""}`,
            ),
        );
        chart.append(dot);
    }
    chart.append(
        svgNode("text", { x: 48, y: 235 }, String(min)),
        svgNode("text", { x: 640, y: 235 }, String(max)),
    );
    const chosen = search.selected;
    $("#search-explanation").textContent =
        `Selected on training: ${chosen.agents} agents and ${chosen.validators} validators; ${search.candidates[0].training.useful} useful outputs. Held-out evaluation: ${search.evaluation.holdout.candidate.metrics.useful} useful outputs. The table includes all ${search.candidates.length} candidates; ${search.frontier.length} lie on the useful-output/cost frontier. Repeated tuning can overfit these public fixtures.`;
    $("#search-table").replaceChildren(
        table(
            [
                "Agents",
                "Validators / groups",
                "Useful · training",
                "Unsafe accepts",
                "Credits",
                "Median latency",
                "Frontier",
            ],
            search.candidates.map((row) => [
                row.config.agents,
                row.config.validators,
                row.training.useful,
                row.training.unsafe_accepts,
                row.training.reserved_credits,
                row.training.median_latency ?? "—",
                search.frontier.includes(row) ? "yes" : "no",
            ]),
        ),
    );
}
function filteredClaims() {
    const query = $("#claim-search").value.trim().toLowerCase();
    const sector = $("#claim-sector").value;
    return scenario.claims.filter(
        (claim) =>
            (sector === "all" || claim.sector === sector) &&
            [claim.title, claim.hypothesis, claim.metric, claim.evidence_needed]
                .join(" ")
                .toLowerCase()
                .includes(query),
    );
}
function renderClaims() {
    const focused = document.activeElement?.classList.contains("claim-card");
    const claims = filteredClaims();
    if (!claims.some((claim) => claim.id === selectedClaim))
        selectedClaim = claims[0]?.id ?? null;
    $("#claim-list").replaceChildren(
        ...claims.map((claim) => {
            const button = node("button", "", "claim-card");
            button.setAttribute(
                "aria-pressed",
                String(claim.id === selectedClaim),
            );
            button.append(
                node("span", claim.sector),
                node("strong", claim.title),
                node("small", "OPEN CLAIM · EVIDENCE REQUIRED"),
            );
            button.addEventListener("click", () => {
                selectedClaim = claim.id;
                renderClaims();
                status(
                    `Inspecting ${claim.title}: references, acceptance criteria and proof debt are shown in the dossier.`,
                );
            });
            return button;
        }),
    );
    if (focused)
        $(".claim-card[aria-pressed='true']")?.focus({ preventScroll: true });
    const dossier = $("#claim-dossier");
    dossier.replaceChildren();
    if (!claims.length) {
        $("#claim-list").append(
            node(
                "p",
                "No claims match. Choose all frontiers, clear the search, or add your own hypothesis.",
            ),
        );
        dossier.append(
            node("h3", "An open frontier."),
            node("p", "Make the next possibility specific enough to test."),
        );
        return;
    }
    const claim = scenario.claims.find((item) => item.id === selectedClaim);
    const data = buildDossier(scenario, config);
    const topology = node("div", "", "topology");
    topology.setAttribute("aria-label", "Typed claim relationships");
    topology.append(
        node("span", `SECTOR / ${claim.sector}`),
        node("span", "→ CLAIM"),
        node("span", `→ ${claim.source_ids.length} REFERENCES`),
        node("span", "→ PROOF DEBT"),
    );
    dossier.append(
        node("p", "CLAIM DOSSIER / EXTERNAL EVIDENCE REQUIRED", "eyebrow"),
        node("h3", claim.title),
        topology,
        node("p", claim.hypothesis),
    );
    for (const [label, text] of [
        ["Observable metric", claim.metric],
        ["Acceptance criterion", claim.target],
    ])
        dossier.append(node("h4", label), node("p", text));
    dossier.append(
        node("h4", "What would resolve the proof debt?"),
        node("p", claim.evidence_needed, "evidence-needed"),
        node("h4", "Sources · references, not independent verification"),
    );
    for (const id of claim.source_ids) {
        const source = scenario.sources.find((item) => item.id === id);
        const card = node("div", "", "source-card");
        card.append(
            node("strong", source.title),
            node("small", source.kind),
            node("p", source.text),
        );
        if (source.url) {
            const link = node("a", "Open the source ↗");
            link.href = source.url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            card.append(link);
        }
        dossier.append(card);
    }
    const actions = node("div", "", "button-row");
    const brief = node("button", "Export validation brief ↓", "button ink");
    brief.addEventListener("click", () =>
        download(
            `proof-${claim.id}.json`,
            data.briefs.find((item) => item.claim_id === claim.id),
        ),
    );
    const mission = node(
        "button",
        "Export native research mission ↓",
        "text-button",
    );
    mission.id = "download-mission";
    mission.addEventListener("click", () =>
        download(
            `mission-${claim.id}.json`,
            data.missions[scenario.claims.indexOf(claim)],
        ),
    );
    actions.append(brief, mission);
    dossier.append(actions);
}
async function renderChronicle() {
    const verified = await verifyChronicle(chronicle);
    $("#chronicle-count").textContent =
        `${verified.active.length} active modeled ${verified.active.length === 1 ? "capability" : "capabilities"}`;
    const events = $("#chronicle-events");
    events.replaceChildren();
    if (!chronicle.events.length) {
        events.append(
            node(
                "p",
                "No capabilities promoted yet. Run a comparison, replay the evidence, then record your review.",
            ),
        );
        return;
    }
    for (const event of chronicle.events) {
        const row = node("div", "", "chronicle-event");
        const content = node("div");
        const active = verified.active.includes(event.digest);
        content.append(
            node(
                "strong",
                `${event.action === "promote" ? "MODELED CAPABILITY RECORDED" : "CAPABILITY REVOKED"}${event.action === "promote" && !active ? " · INACTIVE" : ""}`,
            ),
            node("p", event.note),
            node("small", `SHA-256 ${event.hash}`),
        );
        row.append(
            node("span", String(event.sequence).padStart(2, "0")),
            content,
        );
        if (event.action === "promote" && active) {
            const actions = node("div", "", "chronicle-actions");
            const reuse = node(
                "button",
                "Reuse reviewed design",
                "small-button",
            );
            reuse.addEventListener("click", () =>
                action(() => {
                    if (envelopeDirty)
                        throw new Error(
                            "Apply the pending envelope before reusing a design.",
                        );
                    const saved = chronicle.bundles[event.digest].config;
                    config = validateConfig({
                        ...readConfig(),
                        agents: saved.agents,
                        validators: saved.validators,
                        groups: saved.groups,
                        quorum: saved.quorum,
                    });
                    writeConfig();
                    updateComparison();
                    openView("agency");
                    status(
                        "Reviewed architecture reused. Your current budget, horizon, operator capacity and fault test remain in force. Fresh evidence is required for these inputs.",
                    );
                }),
            );
            const revoke = node("button", "Revoke capability", "small-button");
            revoke.addEventListener("click", () =>
                action(async () => {
                    chronicle = await appendChronicle(chronicle, {
                        action: "revoke",
                        digest: event.digest,
                        note: "Operator revoked this local modeled capability; original evidence remains in history.",
                    });
                    await renderChronicle();
                    status(
                        "Capability revoked. Its evidence and original review remain in the Chronicle.",
                    );
                }),
            );
            actions.append(reuse, revoke);
            row.append(actions);
        }
        events.append(row);
    }
}
function demandCurrent() {
    if (dirty || envelopeDirty)
        throw new Error(
            "Apply the pending scenario or architecture inputs before using evidence or exporting the workspace.",
        );
}

async function initialize() {
    const response = await fetch(new URL("./scenarios.json", import.meta.url));
    if (!response.ok)
        throw new Error(
            "The scenario library could not be loaded. Refresh after reconnecting.",
        );
    library = (await response.json()).map(validateScenario);
    for (const item of library) {
        const option = node("option", item.title);
        option.value = item.id;
        $("#scenario-picker").append(option);
    }
    for (const sector of SECTORS)
        for (const select of [$("#claim-sector"), $("#new-sector")]) {
            const option = node("option", sector);
            option.value = sector;
            select.append(option);
        }
    useScenario(library[0]);
    await renderChronicle();
    $$("[data-view]").forEach((button) =>
        button.addEventListener("click", () => openView(button.dataset.view)),
    );
    $$("[data-open]").forEach((button) =>
        button.addEventListener("click", () => openView(button.dataset.open)),
    );
    $("#guide-toggle").addEventListener("click", () => {
        const panel = $("#field-notes");
        panel.hidden = !panel.hidden;
        $("#guide-toggle").setAttribute("aria-expanded", String(!panel.hidden));
    });
    $("#scenario-picker").addEventListener("change", () => {
        const key = $("#scenario-picker").value;
        const choice =
            library.find((item) => item.id === key) || customScenarios.get(key);
        if (choice) useScenario(choice);
    });
    $("#reveal-next").addEventListener("click", () => {
        selectedSector =
            SECTORS[(SECTORS.indexOf(selectedSector) + 1) % SECTORS.length];
        renderMap();
        status(`Now exploring ${selectedSector}.`);
    });
    $("#inspect-claims").addEventListener("click", () => {
        $("#claim-sector").value = selectedSector;
        $("#claim-search").value = "";
        renderClaims();
        openView("ontology");
    });
    $("#envelope").addEventListener("input", () => {
        envelopeDirty = true;
        invalidate(
            "Envelope edit pending. Reallocate to apply it; earlier evidence is no longer current.",
        );
    });
    $("#envelope-form").addEventListener("submit", (event) => {
        event.preventDefault();
        action(() => {
            const next = {
                ...scenario,
                envelope_usd: quadrillionsToDollars($("#envelope").value),
            };
            scenario = validateScenario(next);
            envelopeDirty = false;
            invalidate();
            renderMap();
            status(
                "The envelope was reallocated exactly. No economic claim was validated by this change.",
            );
        });
    });
    $("#architecture-form").addEventListener("input", () => {
        dirty = true;
        invalidate(
            "Architecture edits pending. Run the comparison to apply them; earlier evidence is no longer current.",
        );
    });
    $("#architecture-form").addEventListener("submit", (event) => {
        event.preventDefault();
        action(() => {
            if (envelopeDirty)
                throw new Error("Reallocate the pending envelope first.");
            config = readConfig();
            updateComparison();
            status(
                "Comparison recomputed. Inspect the holdout and failed checks before building evidence.",
            );
        });
    });
    $("#split").addEventListener("change", renderComparison);
    $("#search-architectures").addEventListener("click", () =>
        action(() => {
            if (envelopeDirty)
                throw new Error("Reallocate the pending envelope first.");
            search = searchArchitectures(scenario, readConfig());
            renderSearch();
            status(
                "18 architectures compared on training; the selected architecture was then evaluated on holdout. Apply it to continue.",
            );
        }),
    );
    $("#apply-search").addEventListener("click", () =>
        action(() => {
            if (!search) throw new Error("Run architecture search first.");
            config = clone(search.selected);
            writeConfig();
            updateComparison();
            status(
                "Selected architecture applied. Build fresh evidence to record a capability.",
            );
        }),
    );
    $("#build-proof").addEventListener("click", () =>
        action(async () => {
            demandCurrent();
            const before = revision;
            const candidate = await buildEvidence(scenario, config);
            const result = await verifyEvidence(candidate, {
                scenario,
                config,
            });
            if (before !== revision)
                throw new Error(
                    "Inputs changed during replay. Build evidence again.",
                );
            evidence = candidate;
            $("#download-proof").disabled = false;
            $("#review-panel").hidden = !result.passed;
            $("#review-note").value = "";
            $("#proof-summary").textContent =
                `All local model gates and exact-input replay passed. Bundle ${evidence.digest.slice(0, 24)}… The economic claims still require external evidence.`;
            renderGates();
            status(
                result.passed
                    ? "Evidence replay passed. Review the result before recording a modeled capability."
                    : "Evidence replay matched, but one or more model gates failed. Promotion remains blocked.",
                !result.passed,
            );
        }),
    );
    $("#download-proof").addEventListener("click", () =>
        action(() => {
            demandCurrent();
            if (!evidence) throw new Error("Build evidence first.");
            download(`insight-${scenario.id}-evidence.json`, evidence);
        }),
    );
    $("#proof-import").addEventListener("change", () =>
        action(async () => {
            demandCurrent();
            const before = revision;
            const bundle = await readFile($("#proof-import"));
            const verified = await verifyEvidence(bundle, { scenario, config });
            if (before !== revision)
                throw new Error("Inputs changed during verification.");
            status(
                verified.passed
                    ? "Imported bundle replayed against the current inputs and passed every model gate."
                    : "Imported bundle replayed, but failed model gates prevent promotion.",
                !verified.passed,
            );
        }),
    );
    $("#promote").addEventListener("click", () =>
        action(async () => {
            demandCurrent();
            if (!evidence) throw new Error("Build current evidence first.");
            const before = revision;
            const next = await appendChronicle(
                chronicle,
                {
                    action: "promote",
                    bundle: evidence,
                    note: $("#review-note").value,
                },
                { scenario, config },
            );
            if (before !== revision)
                throw new Error(
                    "Inputs changed during promotion. Nothing was recorded.",
                );
            chronicle = next;
            await renderChronicle();
            status(
                "Modeled capability recorded with your review. Save the expedition to preserve it.",
            );
        }),
    );
    $("#claim-search").addEventListener("input", renderClaims);
    $("#claim-sector").addEventListener("change", renderClaims);
    $("#new-claim").addEventListener("click", () => {
        $("#claim-form").hidden = false;
        $("#new-sector").value =
            $("#claim-sector").value === "all"
                ? selectedSector
                : $("#claim-sector").value;
        $("#claim-form input").focus();
    });
    $("#cancel-claim").addEventListener("click", () => {
        $("#claim-form").hidden = true;
        $("#new-claim").focus();
    });
    $("#claim-form").addEventListener("submit", (event) => {
        event.preventDefault();
        action(() => {
            let i = 1;
            while (
                scenario.claims.some((claim) => claim.id === `operator-${i}`)
            )
                i++;
            const claim = {
                id: `operator-${i}`,
                source_ids: scenario.sources
                    .map((source) => source.id)
                    .slice(0, 8),
                ...Object.fromEntries(new FormData(event.target)),
            };
            scenario = validateScenario({
                ...scenario,
                claims: [...scenario.claims, claim],
            });
            selectedClaim = claim.id;
            selectedSector = claim.sector;
            $("#claim-search").value = "";
            $("#claim-sector").value = "all";
            $("#claim-form").reset();
            $("#claim-form").hidden = true;
            invalidate();
            renderMap();
            renderClaims();
            status(
                "Hypothesis added with an explicit test and proof debt. Download inputs to edit its sources or workload.",
            );
        });
    });
    $("#download-dossier").addEventListener("click", () =>
        action(() => {
            demandCurrent();
            download(
                `insight-${scenario.id}-dossier.json`,
                buildDossier(scenario, config),
            );
            status(
                "Dossier exported with the typed graph, validation briefs and native research missions.",
            );
        }),
    );
    $("#download-inputs").addEventListener("click", () =>
        action(() => {
            demandCurrent();
            download(`insight-${scenario.id}-inputs.json`, scenario);
        }),
    );
    $("#scenario-import").addEventListener("change", () =>
        action(async () => {
            const value = validateScenario(
                await readFile($("#scenario-import")),
            );
            useScenario(value);
            let option = $("#scenario-picker option[value='imported']");
            if (!option) {
                option = node("option");
                option.value = "imported";
                $("#scenario-picker").append(option);
            }
            option.textContent = `Imported: ${value.title}`;
            customScenarios.set("imported", clone(value));
            $("#scenario-picker").value = "imported";
            status(
                "Scenario imported and validated. Existing Chronicle history was preserved.",
            );
        }),
    );
    $("#save-workspace").addEventListener("click", () =>
        action(async () => {
            demandCurrent();
            const before = revision;
            const saved = await exportWorkspace(scenario, config, chronicle);
            if (before !== revision)
                throw new Error("Inputs changed during export. Save again.");
            download(`insight-${scenario.id}-recovery.json`, saved);
            status(
                "Recovery file saved with inputs, architecture, review history and replayable evidence. It is plain JSON; keep sensitive source text private.",
            );
        }),
    );
    $("#workspace-import").addEventListener("change", () =>
        action(async () => {
            const recovered = await restoreWorkspace(
                await readFile($("#workspace-import")),
            );
            useScenario(recovered.scenario);
            config = recovered.config;
            chronicle = recovered.chronicle;
            writeConfig();
            updateComparison();
            await renderChronicle();
            let option = $("#scenario-picker option[value='restored']");
            if (!option) {
                option = node("option");
                option.value = "restored";
                $("#scenario-picker").append(option);
            }
            option.textContent = `Restored: ${scenario.title}`;
            customScenarios.set("restored", clone(scenario));
            $("#scenario-picker").value = "restored";
            status(
                "Expedition restored. Every promoted capability was independently recomputed and the history chain verified.",
            );
        }),
    );
    $("#reset-atlas").addEventListener("click", () => {
        const original =
            library.find((item) => item.id === scenario.id) || library[0];
        useScenario(original);
        $("#scenario-picker").value = original.id;
        status(
            "Current scenario reset. Chronicle history remains intact; export it for recovery.",
        );
    });
    if ("serviceWorker" in navigator) {
        const projectRoot = new URL("../../", import.meta.url);
        navigator.serviceWorker
            .register(new URL("service-worker.js", projectRoot), {
                scope: projectRoot.pathname,
            })
            .catch(() =>
                status(
                    "The Atlas is ready. Offline caching is unavailable in this browser; download a recovery file to preserve your work.",
                ),
            );
    }
    document.documentElement.dataset.atlasReady = "true";
    if (["#agency", "#ontology"].includes(location.hash))
        openView(location.hash.slice(1), false);
}
initialize().catch((error) =>
    status(`Atlas could not start: ${error.message}`, true),
);
