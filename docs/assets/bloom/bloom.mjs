// SPDX-License-Identifier: Apache-2.0
import { canonicalJSON } from "../ascension/crypto.mjs";
import {
    PLAYBOOKS,
    makeSeed,
    compile,
    newWorkspace,
    executeJob,
    acceptReturn,
    recordReview,
    inspectWorkspace,
    promote,
    appendEvent,
    nextMission,
    exportDossier,
    serialize,
    parse,
} from "./engine.mjs";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const node = (tag, text = "", className = "") => {
    const el = document.createElement(tag);
    el.textContent = text;
    if (className) el.className = className;
    return el;
};
const fmt = (value) =>
    Number(value).toLocaleString("en-US", { maximumFractionDigits: 4 });
const status = (message, error = false) => {
    $("#bloom-status").textContent = message;
    $("#bloom-status").dataset.error = String(error);
};
const ROOT = new URL("../../", import.meta.url);
const STORAGE = "agialpha-proof-bloom-v1";
const PIN_STORAGE = "agialpha-proof-bloom-pins-v1";
let playbooks,
    workspace,
    plan,
    inspection,
    pins = [],
    selected = "nova",
    dirty = false,
    busy = false;

function view(name) {
    $$("[data-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.panel !== name;
    });
    $$("[data-view]").forEach((button) => {
        if (button.dataset.view === name)
            button.setAttribute("aria-current", "page");
        else button.removeAttribute("aria-current");
    });
}

function controls() {
    const locked = dirty || busy || !!inspection?.blocked;
    for (const id of [
        "run-all",
        "run-job",
        "download-dossier",
        "download-mission",
        "download-spec",
    ])
        $("#" + id).disabled = locked;
    $("#save-review").disabled =
        locked || !workspace?.bundles[$("#job-picker").value];
    $("#download-bundle").disabled =
        locked || !workspace?.bundles[$("#job-picker").value];
    $("#promote").disabled =
        locked ||
        !inspection?.docket?.promotable ||
        workspace.history.some(
            (event) =>
                event.type === "promote" &&
                event.payload.seed &&
                canonicalJSON(event.payload.seed) ===
                    canonicalJSON(workspace.seed),
        );
    $("#compile-seed").disabled = busy;
    $("#bloom").setAttribute("aria-busy", String(busy));
}

function download(value, filename, canonical = false) {
    const url = URL.createObjectURL(
        new Blob([canonical ? canonicalJSON(value) : serialize(value)], {
            type: "application/json",
        }),
    );
    const link = node("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function readFile(input) {
    const file = input.files[0];
    if (!file) throw new Error("Select a JSON file.");
    if (file.size > 250000) throw new Error("Import exceeds 250 KB.");
    return parse(await file.text());
}

function saveLocal() {
    try {
        localStorage.setItem(STORAGE, serialize(workspace));
        $("#storage-state").textContent =
            "Saved on this device. Download a recovery file before clearing browser data.";
    } catch {
        $("#storage-state").textContent =
            "This browser cannot save locally. Download a recovery file to keep your work.";
    }
}

async function commit(next) {
    const verified = await inspectWorkspace(next, pins);
    const compiled = await compile(next.seed);
    workspace = next;
    inspection = verified;
    plan = compiled;
    saveLocal();
    render();
}

async function action(fn) {
    if (busy) return;
    busy = true;
    controls();
    // Let the busy indicator paint before bounded CPU work begins.
    await new Promise((resolve) => requestAnimationFrame(resolve));
    try {
        await fn();
    } catch (error) {
        status(error.message || "This action could not be completed.", true);
    } finally {
        busy = false;
        controls();
    }
}

function editable(seed) {
    selected = seed.playbook;
    $("#objective").value = seed.objective;
    $("#claim").value = seed.claim;
    $("#shock").value = seed.shock;
    $("#mission-json").value = JSON.stringify(seed.mission, null, 2);
    renderPlaybook();
}

function renderPlaybook() {
    const book = playbooks[selected];
    $("#playbook-edition").textContent = book.edition;
    $("#seed-title").textContent = book.name;
    $("#playbook-description").textContent = book.description;
    $$("[data-experience]").forEach((button) =>
        button.setAttribute(
            "aria-pressed",
            String(button.dataset.experience === selected),
        ),
    );
    let kind = "";
    try {
        kind = JSON.parse($("#mission-json").value).work.kind;
    } catch {
        /* Editor may be incomplete. */
    }
    $("#stress-description").textContent =
        {
            allocation:
                "Raise all costs. Keep the budget and value assumptions fixed.",
            schedule:
                "Raise operation durations. Preserve machine and precedence constraints.",
            forecast:
                "Shock the holdout. Keep all training observations unchanged.",
            research:
                "Reverse the source order. Verify exact quotations again; the percentage has no effect on this probe.",
        }[kind] || "Choose valid bounded inputs to see the stress rule.";
}

function markDirty() {
    dirty = true;
    controls();
    renderPlaybook();
    status(
        "Inputs changed. Compile fresh jobs before executing, exporting or reviewing evidence.",
    );
}

function renderJobs() {
    const grid = $("#job-grid");
    grid.replaceChildren();
    plan.jobs.forEach((job, i) => {
        const row = inspection.docket?.rows[i];
        const card = node("article", "", "job-card");
        const top = node("div", "", "job-top");
        top.append(node("span", `0${i + 1}`, "job-number"));
        const badge = node(
            "span",
            row?.accepted
                ? "ACCEPTED"
                : row?.replay
                  ? "AWAITING REVIEW"
                  : "PROOF DEBT",
            "badge",
        );
        badge.dataset.pass = String(!!row?.accepted);
        top.append(badge);
        card.append(
            top,
            node("h4", job.title),
            node("p", job.acceptance),
            node("small", job.worker_role, "fine"),
        );
        const button = node("button", "Inspect job & evidence ↗");
        button.addEventListener("click", () => {
            $("#job-picker").value = job.id;
            view("docket");
            renderResult();
            $("#job-picker").focus();
        });
        card.append(button);
        grid.append(card);
    });
}

function renderGates() {
    $("#gate-grid").replaceChildren();
    for (const gate of inspection.docket?.gates || []) {
        const card = node("article", "", "gate-card");
        const top = node("div", "", "gate-top");
        const badge = node("span", gate.passed ? "PASS" : "HOLD", "badge");
        badge.dataset.pass = String(gate.passed);
        top.append(node("span", gate.id, "eyebrow"), badge);
        card.append(top, node("h4", gate.name), node("p", gate.rule));
        $("#gate-grid").append(card);
    }
}

function renderResult() {
    const id = $("#job-picker").value;
    const bundle = workspace.bundles[id];
    const row = inspection.docket?.rows.find((item) => item.id === id);
    const area = $("#result-view");
    area.replaceChildren();
    $("#review-summary").textContent = workspace.reviews[id]
        ? `${workspace.reviews[id].decision.toUpperCase()} · ${workspace.reviews[id].reviewer}: ${workspace.reviews[id].note}`
        : "No review recorded for this returned artifact.";
    if (!bundle) {
        const empty = node("div", "", "empty-evidence");
        empty.append(
            node("span", "α", "empty-mark"),
            node("h4", "Evidence is earned here."),
            node(
                "p",
                "Run this job or return a ProofBundle. Its result will be replayed against the exact inputs.",
                "fine",
            ),
        );
        area.append(empty);
        controls();
        return;
    }
    const result = bundle.result;
    const heading = node("div", "", "result-header");
    heading.append(
        node("h4", result.method),
        node("p", result.summary, "fine"),
    );
    area.append(heading);
    if (row?.measurement) {
        const { candidate, baseline, delta, metric, direction } =
            row.measurement;
        const metrics = node("div", "", "measurement");
        for (const [value, name] of [
            [candidate, "Candidate"],
            [baseline, "Declared baseline"],
        ]) {
            const cell = node("div", "", "measure");
            cell.append(
                node("strong", fmt(value)),
                node("small", `${name} · ${metric}`),
            );
            metrics.append(cell);
        }
        area.append(
            metrics,
            node(
                "p",
                `${delta > 0 ? "+" : ""}${fmt(delta)} advantage · ${direction} is better`,
                "delta",
            ),
        );
    }
    const table = node("table", "", "result-table");
    const caption = node("caption", "Computed evidence for the selected job");
    const head = node("thead"),
        tr = node("tr");
    result.headers.forEach((header) => {
        const th = node("th", header);
        th.scope = "col";
        tr.append(th);
    });
    head.append(tr);
    const body = node("tbody");
    result.rows.forEach((values) => {
        const line = node("tr");
        values.forEach((value) =>
            line.append(
                node(
                    "td",
                    typeof value === "number" ? fmt(value) : String(value),
                ),
            ),
        );
        body.append(line);
    });
    table.append(caption, head, body);
    const scroll = node("div", "", "table-scroll");
    scroll.tabIndex = 0;
    scroll.setAttribute("role", "region");
    scroll.setAttribute("aria-label", "Scrollable evidence table");
    scroll.append(table);
    area.append(scroll, node("p", result.limits, "limit-box"));
    const origin =
        bundle.origin.type === "native"
            ? "Native signed approval attached; result above computed by the local bounded engine."
            : bundle.origin.type === "reuse"
              ? "Exact reviewed benchmark reused from an active Chronicle capability; it was replayed for verification."
              : "Executed by the local bounded engine; no external worker identity is asserted.";
    area.append(node("p", origin, "fine"));
    const details = node("details");
    details.append(
        node("summary", "Inspect complete ProofBundle & replay inputs"),
        node(
            "pre",
            serialize({ job: plan.jobs.find((job) => job.id === id), bundle }),
            "result-code",
        ),
    );
    area.append(details);
    controls();
}

function renderChronicle() {
    const list = $("#chronicle-list");
    list.replaceChildren();
    const promotions = workspace.history.filter(
        (event) => event.type === "promote",
    );
    if (!promotions.length) {
        const empty = node("div", "", "empty-chronicle");
        empty.append(
            node("p", "CHRONICLE / HOLD", "eyebrow"),
            node("h4", "A place for what survives."),
            node(
                "p",
                "Complete the proof jobs and accepted reviews. Your first scoped capability will appear here.",
                "fine",
            ),
        );
        list.append(empty);
    }
    promotions.forEach((event, i) => {
        const active = inspection.active.has(event.digest);
        const card = node("article", "", "chronicle-card");
        const info = node("div");
        const badge = node(
            "span",
            active
                ? "ACTIVE · BOUNDED CAPABILITY"
                : "REVOKED · INCLUDING DEPENDENT LINEAGE",
            "badge",
        );
        badge.dataset.pass = String(active);
        info.append(
            node(
                "p",
                `CAPABILITY ${String(i + 1).padStart(2, "0")} / ${event.payload.seed.mission.work.kind.toUpperCase()}`,
                "eyebrow",
            ),
            node("h4", event.payload.seed.objective),
            badge,
            node("p", event.digest, "hash"),
        );
        const debt = event.payload.seed.parents.length
            ? `${event.payload.seed.parents.length} active foundation required.`
            : "Independent foundation.";
        info.append(
            node(
                "p",
                debt +
                    " Scope: replayed computation on these exact supplied inputs.",
                "fine",
            ),
        );
        const actions = node("div");
        const next = node("button", "Seed the next mission ↗", "button ink");
        next.disabled = !active || dirty;
        next.addEventListener("click", () =>
            action(async () => {
                const nextState = await nextMission(
                    workspace,
                    event.digest,
                    pins,
                );
                await commit(nextState);
                editable(workspace.seed);
                dirty = false;
                view("seed");
                status(
                    "Future mission seeded. One exact benchmark reused; source and stress jobs need fresh evidence and all three need review.",
                );
            }),
        );
        actions.append(next);
        const reason = node("textarea");
        reason.rows = 2;
        reason.maxLength = 1000;
        reason.id = `revoke-reason-${i}`;
        reason.placeholder = "Why should this capability be withdrawn?";
        const label = node("label", "Revocation reason");
        label.htmlFor = reason.id;
        label.className = "fine";
        const revoke = node(
            "button",
            "Revoke capability & dependents",
            "button light",
        );
        revoke.disabled = !active;
        revoke.addEventListener("click", () =>
            action(async () => {
                await commit(
                    await appendEvent(
                        workspace,
                        "revoke",
                        { capability: event.digest, reason: reason.value },
                        pins,
                    ),
                );
                status(
                    "Capability revoked. Every descendant is now closed; the immutable event history remains available.",
                );
            }),
        );
        actions.append(label, reason, revoke);
        card.append(info, actions);
        list.append(card);
    });
    const reused = Object.values(workspace.bundles).filter(
        (bundle) => bundle.origin.type === "reuse",
    ).length;
    $("#reused-count").textContent = reused;
    $("#fresh-count").textContent = 3 - reused;
}

function render() {
    const docket = inspection.docket;
    const accepted = docket?.rows.filter((row) => row.accepted).length || 0;
    $("#debt-count").textContent = `${3 - accepted} open jobs`;
    $("#memory-count").textContent = `${inspection.active.size} active`;
    const recorded = [...inspection.active.values()].some(
        (entry) => canonicalJSON(entry.seed) === canonicalJSON(workspace.seed),
    );
    $("#gate-state").textContent = recorded
        ? "Recorded in Chronicle"
        : docket?.promotable
          ? "Eligible for promotion"
          : "Chronicle HOLD";
    $("#claim-state").textContent = "Unproven vision";
    $("#promotion-reason").textContent =
        inspection.blocked ||
        (docket?.promotable
            ? "The bounded capability passed every gate. The visionary claim remains unproven."
            : "Complete accepted reviews and positive benchmark and stress results. Failed gates keep Chronicle on HOLD.");
    renderJobs();
    renderGates();
    renderResult();
    renderChronicle();
    controls();
}

function bind() {
    $("#start-fresh").addEventListener("click", () =>
        action(async () => {
            await inspectWorkspace(workspace, pins);
            download(workspace, "proof-bloom-previous-workspace.json");
            const { schema, ...input } = workspace.seed;
            await commit(newWorkspace(makeSeed({ ...input, parents: [] })));
            editable(workspace.seed);
            dirty = false;
            render();
            view("seed");
            status(
                "Previous workspace downloaded. A separate fresh workspace is ready to compile and run.",
            );
        }),
    );
    $("#pin-key").addEventListener("click", () =>
        action(async () => {
            const key = $("#trusted-key").value.trim().toLowerCase();
            if (!/^[a-f0-9]{64}$/.test(key))
                throw new Error(
                    "Enter the independently obtained 64-character public key.",
                );
            pins = [...new Set([...pins, key])];
            try {
                localStorage.setItem(PIN_STORAGE, JSON.stringify(pins));
            } catch {
                /* Session trust remains available. */
            }
            status(
                "Agent key pinned on this device. You can now verify its signed returns or restore its recovery file.",
            );
        }),
    );
    $("#guide-toggle").addEventListener("click", () => {
        const opening = $("#guide").hidden;
        $("#guide").hidden = !opening;
        $("#guide-toggle").setAttribute("aria-expanded", String(opening));
    });
    $$("[data-view]").forEach((button) =>
        button.addEventListener("click", () => view(button.dataset.view)),
    );
    $$("[data-experience]").forEach((button) =>
        button.addEventListener("click", () => {
            const id = button.dataset.experience;
            editable({ ...playbooks[id], playbook: id, shock: 20 });
            view("seed");
            markDirty();
        }),
    );
    for (const id of ["objective", "claim", "shock", "mission-json"])
        $("#" + id).addEventListener("input", markDirty);
    $("#compile-seed").addEventListener("click", () =>
        action(async () => {
            const seed = makeSeed({
                playbook: selected,
                objective: $("#objective").value,
                claim: $("#claim").value,
                mission: parse($("#mission-json").value),
                shock: Number($("#shock").value),
                parents: [],
            });
            const next = { ...newWorkspace(seed), history: workspace.history };
            await commit(next);
            dirty = false;
            render();
            status(
                "Three proof jobs compiled. Run them to produce evidence; Chronicle remains on HOLD.",
            );
        }),
    );
    $("#run-all").addEventListener("click", () =>
        action(async () => {
            let next = workspace;
            for (const job of plan.jobs) {
                if (!next.bundles[job.id]) {
                    const bundle = await executeJob(
                        next.seed,
                        job.id,
                        { type: "browser" },
                        pins,
                        inspection.active,
                    );
                    next = await acceptReturn(next, bundle, pins);
                }
            }
            await commit(next);
            view("docket");
            status(
                "Pending jobs executed and replayed. Inspect each result and record an explicit reviewer decision.",
            );
        }),
    );
    $("#run-job").addEventListener("click", () =>
        action(async () => {
            const bundle = await executeJob(
                workspace.seed,
                $("#job-picker").value,
                { type: "browser" },
                pins,
                inspection.active,
            );
            await commit(await acceptReturn(workspace, bundle, pins));
            status(
                "Job executed and replayed. Any previous review of this return was cleared.",
            );
        }),
    );
    $("#job-picker").addEventListener("change", () => {
        $("#review-note").value = "";
        renderResult();
    });
    $("#save-review").addEventListener("click", () =>
        action(async () => {
            await commit(
                await recordReview(
                    workspace,
                    $("#job-picker").value,
                    $("#review-decision").value,
                    $("#reviewer").value,
                    $("#review-note").value,
                    pins,
                ),
            );
            status(
                "Exact returned artifact reviewed. The promotion gate was recomputed from evidence and decisions.",
            );
        }),
    );
    $("#promote").addEventListener("click", () =>
        action(async () => {
            await commit(await promote(workspace, pins));
            view("chronicle");
            status(
                "Reviewed bounded capability recorded in Chronicle. Its visionary and financial claims remain unproven.",
            );
        }),
    );
    $("#download-mission").addEventListener("click", () =>
        download(
            plan.jobs.find((job) => job.id === $("#job-picker").value).mission,
            `${$("#job-picker").value}-mission.json`,
        ),
    );
    $("#download-spec").addEventListener("click", () =>
        download(
            plan.jobs.find((job) => job.id === $("#job-picker").value),
            `${$("#job-picker").value}-job-spec.json`,
            true,
        ),
    );
    $("#download-bundle").addEventListener("click", () =>
        download(
            workspace.bundles[$("#job-picker").value],
            `${$("#job-picker").value}-proofbundle.json`,
        ),
    );
    $("#download-dossier").addEventListener("click", () =>
        action(async () =>
            download(
                await exportDossier(workspace, pins),
                "proof-bloom-dossier.json",
            ),
        ),
    );
    $("#save-workspace").addEventListener("click", () =>
        action(async () => {
            await inspectWorkspace(workspace, pins);
            download(workspace, "proof-bloom-recovery.json");
        }),
    );
    for (const id of [
        "mission-import",
        "bundle-import",
        "native-import",
        "workspace-import",
    ]) {
        $("#" + id).addEventListener("change", () =>
            action(async () => {
                const input = $("#" + id);
                try {
                    const value = await readFile(input);
                    if (id === "mission-import") {
                        $("#mission-json").value = serialize(value);
                        markDirty();
                    } else if (id === "workspace-import") {
                        await commit(value);
                        editable(workspace.seed);
                        dirty = false;
                        render();
                        status(
                            "Recovery restored. Every Chronicle promotion, return and reviewer binding was replayed.",
                        );
                    } else {
                        if (dirty)
                            throw new Error(
                                "Compile the changed inputs before returning evidence.",
                            );
                        let bundle = value;
                        if (id === "native-import") {
                            const key = $("#trusted-key")
                                .value.trim()
                                .toLowerCase();
                            if (!/^[a-f0-9]{64}$/.test(key))
                                throw new Error(
                                    "Enter the independently obtained agent public key first.",
                                );
                            const candidatePins = [...new Set([...pins, key])];
                            bundle = await executeJob(
                                workspace.seed,
                                $("#job-picker").value,
                                { type: "native", artifact: value },
                                candidatePins,
                                inspection.active,
                            );
                            // Trust is granted by this separate input; it is never inferred from an imported receipt or recovery.
                            pins = candidatePins;
                            try {
                                localStorage.setItem(
                                    PIN_STORAGE,
                                    JSON.stringify(pins),
                                );
                            } catch {
                                /* Session pin still works. */
                            }
                        }
                        const next = await acceptReturn(
                            workspace,
                            bundle,
                            pins,
                        );
                        await commit(next);
                        $("#job-picker").value = bundle.job_id;
                        renderResult();
                        status(
                            "Return verified against its exact job inputs. A fresh local review is required.",
                        );
                    }
                } finally {
                    input.value = "";
                }
            }),
        );
    }
}

async function start() {
    const response = await fetch(new URL("playbooks.json", import.meta.url));
    if (!response.ok)
        throw new Error(
            "Could not load the guided experiences. Reload when online.",
        );
    playbooks = await response.json();
    const requested = new URL(location.href).searchParams.get("experience");
    selected = PLAYBOOKS.includes(requested) ? requested : "nova";
    const book = playbooks[selected];
    workspace = newWorkspace(
        makeSeed({
            playbook: selected,
            objective: book.objective,
            claim: book.claim,
            mission: book.mission,
            shock: 20,
            parents: [],
        }),
    );
    let message =
        "Choose a mission, then compile and run the proof jobs. Your vision stays a claim until evidence earns a bounded capability.";
    try {
        const savedPins = JSON.parse(localStorage.getItem(PIN_STORAGE) || "[]");
        if (
            Array.isArray(savedPins) &&
            savedPins.every((key) => /^[a-f0-9]{64}$/.test(key))
        )
            pins = savedPins;
        const saved = localStorage.getItem(STORAGE);
        if (saved && !requested) {
            const recovered = parse(saved);
            await inspectWorkspace(recovered, pins);
            workspace = recovered;
            message =
                "Your saved workspace was restored and its evidence replayed.";
        }
    } catch (error) {
        message = `Saved workspace was not restored: ${error.message}. Your stored copy has not been overwritten; export or inspect it before saving new work.`;
    }
    plan = await compile(workspace.seed);
    inspection = await inspectWorkspace(workspace, pins);
    editable(workspace.seed);
    bind();
    render();
    status(message);
    document.documentElement.dataset.bloomReady = "true";
    if ("serviceWorker" in navigator)
        navigator.serviceWorker
            .register(new URL("service-worker.js", ROOT), {
                scope: ROOT.pathname,
            })
            .catch(() =>
                status(
                    "Workspace ready. Offline caching is unavailable in this browser.",
                ),
            );
}

start().catch((error) => {
    busy = false;
    $("#bloom").setAttribute("aria-busy", "false");
    status(error.message, true);
});
