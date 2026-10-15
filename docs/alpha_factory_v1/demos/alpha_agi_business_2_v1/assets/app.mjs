import { evaluate, validate, canonical } from "./engine.mjs";
import { parseJSON } from "./json.mjs";
import { messages } from "./i18n.mjs";
const $ = (id) => document.getElementById(id);
let lang = "en",
    revision = 0,
    report = null,
    lastInput = null,
    serial = 0;
const t = (k) => messages[lang][k] || k;
const numeric = new Set([
    "effortHours",
    "maxProjects",
    "minSupportingSources",
    "baseline",
    "current",
    "valuePoints",
]);
function element(tag, text) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    return el;
}
function field(parent, key, value, options) {
    const wrap = element("div"),
        label = element("label");
    label.dataset.t = key;
    label.textContent = t(key);
    const control = element(options ? "select" : "input");
    control.id = "field-" + ++serial;
    control.dataset.key = key;
    label.htmlFor = control.id;
    if (options)
        for (const option of options) {
            const el = element("option", t(option));
            el.value = option;
            el.dataset.t = option;
            control.append(el);
        }
    else {
        control.type = "text";
        if (numeric.has(key)) control.inputMode = "numeric";
    }
    control.value = value;
    wrap.append(label, control);
    parent.append(wrap);
    return control;
}
function row(collection, data) {
    const card = element("fieldset");
    card.className = "business-row";
    card.dataset.collection = collection;
    const legend = element("legend", data.id);
    card.append(legend);
    const fields = element("div");
    fields.className = "pair";
    for (const [key, value] of Object.entries(data))
        field(
            fields,
            key,
            Array.isArray(value) ? value.join(", ") : value,
            key === "direction" ? ["increase", "decrease"] : undefined
        );
    card.append(fields);
    const remove = element("button", t("remove"));
    remove.type = "button";
    remove.dataset.t = "remove";
    remove.className = "quiet";
    remove.addEventListener("click", () => {
        card.remove();
        invalidate();
    });
    card.append(remove);
    card.addEventListener("input", () => {
        legend.textContent = card.querySelector('[data-key="id"]').value;
        remove.setAttribute(
            "aria-label",
            t("remove") + " " + legend.textContent
        );
    });
    remove.setAttribute("aria-label", t("remove") + " " + data.id);
    $(collection).append(card);
}
function fill(s) {
    validate(s);
    $("metadata").replaceChildren();
    $("policy").replaceChildren();
    field($("metadata"), "id", s.id);
    field($("metadata"), "kind", s.provenance.kind, [
        "constructed",
        "supplied",
    ]);
    field($("metadata"), "note", s.provenance.note);
    for (const [k, v] of Object.entries(s.policy)) field($("policy"), k, v);
    for (const collection of ["observations", "opportunities"]) {
        $(collection).replaceChildren();
        s[collection].forEach((r) => row(collection, r));
    }
}
function integer(raw) {
    if (!/^(?:0|[1-9][0-9]*)$/.test(raw))
        throw Error("Whole decimal integer required");
    const n = Number(raw);
    if (!Number.isSafeInteger(n)) throw Error("Integer too large");
    return n;
}
function values(container) {
    const out = {};
    for (const el of container.querySelectorAll("[data-key]")) {
        const key = el.dataset.key;
        out[key] = numeric.has(key)
            ? integer(el.value)
            : key === "evidenceIds"
            ? el.value.split(",").map((s) => s.trim())
            : el.value;
    }
    return out;
}
function bounded(input) {
    validate(input);
    if (new TextEncoder().encode(canonical(input)).length > 128000)
        throw Error("Input exceeds 128000 bytes");
    return input;
}
function read() {
    const m = values($("metadata"));
    return bounded({
        schema: "agialpha.business2.input.v1",
        id: m.id,
        provenance: { kind: m.kind, note: m.note },
        policy: values($("policy")),
        observations: [...$("observations").children].map(values),
        opportunities: [...$("opportunities").children].map(values),
    });
}
function invalidate() {
    revision++;
    report = null;
    lastInput = null;
    $("result").hidden = true;
    $("evidence").disabled = true;
    $("download").disabled = true;
    $("error").hidden = true;
    $("status").textContent = t("changed");
}
function render() {
    if (!report) return;
    const p = report.plan;
    $("summary").textContent =
        (p.selectedIds.join(", ") || t("empty")) +
        " · " +
        p.totalValuePoints +
        " " +
        t("points") +
        " · " +
        p.totalEffortHours +
        " " +
        t("hours") +
        " · " +
        p.remainingEffortHours +
        " " +
        t("remaining");
    $("review").replaceChildren();
    for (const r of report.research.observations) {
        const card = element("article");
        card.className = "report-card";
        card.append(
            element("h3", r.id + " · " + r.metric),
            element(
                "p",
                r.baseline +
                    " → " +
                    r.current +
                    " " +
                    r.unit +
                    " · " +
                    t("delta") +
                    ": " +
                    r.delta
            ),
            element(
                "p",
                t(r.supports ? "supports" : "noSupport") + " · " + r.source
            )
        );
        $("review").append(card);
    }
    $("portfolio").replaceChildren();
    for (const r of report.research.opportunities) {
        const card = element("article");
        card.className = "report-card";
        card.append(
            element("h3", r.title + " · " + t(r.reason)),
            element(
                "p",
                r.valuePoints +
                    " " +
                    t("points") +
                    " · " +
                    r.effortHours +
                    " " +
                    t("hours")
            ),
            element(
                "p",
                t("sources") + ": " + (r.supportingSources.join(" · ") || "0")
            )
        );
        $("portfolio").append(card);
    }
    $("raw").textContent = JSON.stringify(report, null, 2);
    $("digest").textContent =
        "SHA-256 input: " +
        report.inputDigest +
        " · report: " +
        report.reportDigest;
    $("result").hidden = false;
    $("evidence").disabled = false;
    $("download").disabled = false;
}
async function run() {
    invalidate();
    const own = revision;
    $("status").textContent = t("pending");
    try {
        const input = structuredClone(read());
        const result = await evaluate(input);
        if (own !== revision) return;
        lastInput = input;
        report = result;
        render();
        $("status").textContent = t("ready");
    } catch {
        if (own !== revision) return;
        $("error").textContent = t("invalid");
        $("error").hidden = false;
        $("status").textContent = "";
    }
}
function translate() {
    document.documentElement.lang = lang;
    for (const el of document.querySelectorAll("[data-t]"))
        el.textContent = t(el.dataset.t);
    $("language").textContent = lang === "en" ? "FR" : "EN";
    $("language").setAttribute(
        "aria-label",
        lang === "en" ? "Passer en français" : "Switch to English"
    );
    for (const card of document.querySelectorAll(".business-row"))
        card.querySelector("button").setAttribute(
            "aria-label",
            t("remove") + " " + card.querySelector('[data-key="id"]').value
        );
    if (!$("error").hidden) $("error").textContent = t("invalid");
    $("status").textContent = t(report ? "ready" : "changed");
    render();
}
$("language").onclick = () => {
    lang = lang === "en" ? "fr" : "en";
    translate();
};
$("workspace").addEventListener("input", invalidate);
$("workspace").addEventListener("change", invalidate);
$("workspace").onsubmit = (e) => {
    e.preventDefault();
    run();
};
const example = parseJSON(await (await fetch("assets/example.json")).text());
$("reset").onclick = () => {
    invalidate();
    fill(example);
    run();
};
$("addObservation").onclick = () => {
    if ($("observations").children.length >= 64) return;
    row("observations", {
        id: "observation-" + ++serial,
        source: "",
        metric: "",
        unit: "",
        baseline: 0,
        current: 0,
        direction: "increase",
    });
    invalidate();
};
$("addOpportunity").onclick = () => {
    if ($("opportunities").children.length >= 16) return;
    row("opportunities", {
        id: "project-" + ++serial,
        title: "",
        effortHours: 1,
        valuePoints: 0,
        evidenceIds: [],
    });
    invalidate();
};
$("import").onchange = async () => {
    const file = $("import").files[0];
    if (!file) return;
    invalidate();
    const own = revision;
    try {
        if (file.size > 1048576) throw Error("Too large");
        const parsed = parseJSON(
            new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(
                await file.arrayBuffer()
            ),
            true,
            1048576
        );
        let input = parsed;
        if (
            parsed &&
            [
                "agialpha.business2.evidence.v1",
                "agialpha.business2.notebook-evidence.v1",
            ].includes(parsed.schema)
        ) {
            if (Object.keys(parsed).sort().join("|") !== "input|report|schema")
                throw Error("Unknown evidence fields");
            input = parsed.input;
        } else if (file.size > 128000) throw Error("Input exceeds byte limit");
        bounded(input);
        if (own !== revision) return;
        fill(input);
        await run();
    } catch {
        if (own === revision) {
            $("error").hidden = false;
            $("error").textContent = t("invalid");
        }
    } finally {
        if ($("import").files[0] === file) $("import").value = "";
    }
};
function download(value, name) {
    const url = URL.createObjectURL(
        new Blob([JSON.stringify(value)], {
            type: "application/json",
        })
    );
    const a = element("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("download").onclick = () => {
    if (lastInput && report) download(lastInput, "observations.json");
};
$("evidence").onclick = () => {
    if (lastInput && report)
        download(
            {
                schema: "agialpha.business2.evidence.v1",
                input: lastInput,
                report,
            },
            "business2-report.json"
        );
};
fill(example);
await run();
