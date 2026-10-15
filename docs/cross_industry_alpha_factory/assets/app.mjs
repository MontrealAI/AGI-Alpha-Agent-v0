/* SPDX-License-Identifier: Apache-2.0 */
import { compare, validate } from "./engine.mjs";
import { parseJSON } from "./json.mjs";
import { fr, words } from "./i18n.mjs";
const $ = (id) => document.getElementById(id),
    metrics = ["benefit", "confidence", "effort", "risk"],
    original = new Map(
        [...document.querySelectorAll("[data-t]")].map((e) => [
            e,
            e.textContent,
        ])
    );
let lang =
        new URL(location.href).searchParams.get("lang") === "fr" ? "fr" : "en",
    serial = 0,
    revision = 0,
    current = null;
const w = (k) => words[lang][k] ?? k;
function node(tag, text) {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    return e;
}
function translated(tag, key) {
    const e = node(tag, w(key));
    e.dataset.w = key;
    return e;
}
function translate() {
    document.documentElement.lang = lang;
    for (const [e, text] of original)
        e.textContent = lang === "fr" ? fr[e.dataset.t] ?? text : text;
    for (const e of document.querySelectorAll("[data-w]"))
        e.textContent = w(e.dataset.w);
    $("language").textContent = lang === "fr" ? "EN" : "FR";
    $("language").setAttribute(
        "aria-label",
        lang === "fr" ? "Switch to English" : "Passer en français"
    );
    document.title =
        lang === "fr"
            ? "Intersectoriel • Comparaison des possibilités"
            : "Cross-industry • Opportunity comparison";
    for (const row of $("opportunities").children)
        row.querySelector("button").setAttribute(
            "aria-label",
            `${w("remove")} ${row.querySelector("[data-field=id]").value}`
        );
    if (current) render();
}
function field(parent, key, value, id, numeric = false) {
    const div = node("div"),
        label = translated("label", key),
        e = node(
            key === "evidence" || key === "opportunity" ? "textarea" : "input"
        );
    e.id = id;
    e.dataset.field = key;
    e.value = value;
    e.required = true;
    label.htmlFor = id;
    if (numeric) {
        e.type = "number";
        e.min = 0;
        e.max = 100;
        e.step = 1;
    } else if (key === "id") e.maxLength = 64;
    else if (key === "sector") e.maxLength = 120;
    else if (key === "opportunity") e.maxLength = 1000;
    else if (key === "evidence") e.maxLength = 10000;
    div.append(label, e);
    parent.append(div);
    return e;
}
function add(o) {
    const row = node("fieldset");
    row.className = "job-grid";
    const id = serial++;
    for (const key of ["id", "sector", "opportunity", ...metrics, "evidence"])
        field(
            row,
            key,
            key === "evidence" ? o[key].join("\n") : o[key],
            `candidate-${id}-${key}`,
            metrics.includes(key)
        );
    const remove = translated("button", "remove");
    remove.type = "button";
    remove.onclick = () => {
        row.remove();
        invalidate();
    };
    row.append(remove);
    $("opportunities").append(row);
    translate();
}
function load(input) {
    for (const group of ["weights", "constraints"]) {
        $(group).replaceChildren();
        for (const [key, value] of Object.entries(input[group]))
            field($(group), key, value, `${group}-${key}`, true);
    }
    $("opportunities").replaceChildren();
    for (const o of input.opportunities) add(o);
    translate();
}
function integer(value) {
    if (!/^(0|[1-9][0-9]*)$/.test(value))
        throw Error("Use whole-number digits without decimals or exponents");
    return Number(value);
}
function read() {
    const input = {
        schema_version: "cross-industry-input-v1",
        weights: {},
        constraints: {},
        opportunities: [],
    };
    for (const group of ["weights", "constraints"])
        for (const e of $(group).querySelectorAll("input"))
            input[group][e.dataset.field] = integer(e.value);
    input.opportunities = [...$("opportunities").children].map((row) =>
        Object.fromEntries(
            [...row.querySelectorAll("[data-field]")].map((e) => [
                e.dataset.field,
                metrics.includes(e.dataset.field)
                    ? integer(e.value)
                    : e.dataset.field === "evidence"
                    ? e.value.split("\n")
                    : e.value,
            ])
        )
    );
    return input;
}
function invalidate() {
    revision++;
    current = null;
    $("result").hidden = true;
    $("error").hidden = true;
    $("status").textContent = "";
    return revision;
}
function error(e) {
    current = null;
    $("result").hidden = true;
    $("error").hidden = false;
    $("error").textContent = `${w("error")} ${e.message}`;
    $("status").textContent = "";
}
function render() {
    if (!current) return;
    const r = current.report;
    $("summary").textContent = r.selected_id
        ? `${w("selected")}: ${r.selected_id}`
        : w("none");
    $("ranking").replaceChildren();
    for (const o of r.ranking) {
        const section = node("section");
        section.className = "panel";
        section.append(
            node(
                "h3",
                `${o.rank === null ? "—" : o.rank}. ${o.id} · ${o.sector}`
            ),
            node("p", o.opportunity),
            node(
                "p",
                `${w("score")}: ${o.score} · ${w(
                    o.eligible ? "eligible" : "excluded"
                )}`
            )
        );
        if (o.eligible)
            section.append(
                node("p", w(o.pareto_optimal ? "pareto" : "dominated"))
            );
        else
            for (const reason of o.exclusion_reasons)
                section.append(
                    node(
                        "p",
                        w(
                            reason === "risk exceeds max_risk"
                                ? "riskReason"
                                : "confidenceReason"
                        )
                    )
                );
        section.append(
            node(
                "p",
                `${w("contributions")}: ${metrics
                    .map((m) => `${w(m)} ${o.contributions[m]}`)
                    .join(" · ")}`
            )
        );
        const list = node("ul");
        for (const note of o.evidence) list.append(node("li", note));
        section.append(list);
        $("ranking").append(section);
    }
    $("raw").textContent = JSON.stringify(r, null, 2);
    $("digest").textContent = `${w("hash")}: ${r.input_sha256}\n${w(
        "downloadHash"
    )}: ${current.hash}`;
    $("result").hidden = false;
    $("status").textContent = w("ready");
}
async function compute(input, ticket) {
    const report = await compare(input),
        bytes = JSON.stringify(input, null, 2) + "\n";
    if (ticket !== revision) return;
    const hash = [
        ...new Uint8Array(
            await crypto.subtle.digest(
                "SHA-256",
                new TextEncoder().encode(bytes)
            )
        ),
    ]
        .map((n) => n.toString(16).padStart(2, "0"))
        .join("");
    if (ticket !== revision) return;
    current = { input, report, bytes, hash };
    render();
}
$("comparison").onsubmit = async (e) => {
    e.preventDefault();
    const ticket = invalidate();
    $("status").textContent = w("loading");
    try {
        await compute(read(), ticket);
    } catch (e) {
        if (ticket === revision) error(e);
    }
};
for (const type of ["input", "change"])
    $("comparison").addEventListener(type, () => {
        invalidate();
        translate();
    });
$("add").onclick = () => {
    if ($("opportunities").children.length >= 100) return;
    invalidate();
    let n = 1;
    const ids = [...$("opportunities").querySelectorAll("[data-field=id]")].map(
        (e) => e.value
    );
    while (ids.includes("candidate-" + n)) n++;
    add({
        id: "candidate-" + n,
        sector: lang === "fr" ? "Secteur à préciser" : "Sector to specify",
        opportunity:
            lang === "fr" ? "Possibilité à évaluer" : "Opportunity to assess",
        benefit: 50,
        confidence: 50,
        effort: 50,
        risk: 50,
        evidence: [
            lang === "fr"
                ? "Hypothèse non vérifiée à remplacer"
                : "Unverified assumption to replace",
        ],
    });
};
async function restore() {
    const ticket = invalidate();
    $("import").value = "";
    try {
        const response = await fetch("assets/example.json");
        if (!response.ok) throw Error("Example unavailable");
        const input = parseJSON(await response.text());
        if (ticket !== revision) return;
        validate(input);
        load(input);
    } catch (e) {
        if (ticket === revision) error(e);
    }
}
$("reset").onclick = restore;
$("import").onchange = async () => {
    const ticket = invalidate(),
        file = $("import").files[0];
    if (!file) return;
    try {
        if (file.size > 1048576) throw Error("1 MiB maximum");
        let input = parseJSON(
            new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(
                await file.arrayBuffer()
            ),
            true,
            ["report"]
        );
        if (ticket !== revision) return;
        if (input?.schema_version === "cross-industry-browser-evidence-v1") {
            if (
                Object.keys(input).sort().join("|") !==
                [
                    "schema_version",
                    "input",
                    "report",
                    "downloadedInputSha256",
                    "hashScope",
                ]
                    .sort()
                    .join("|")
            )
                throw Error("Unknown evidence fields");
            input = input.input;
        }
        if (input?.schema === "cross-industry-notebook-evidence-v1") {
            if (Object.keys(input).sort().join("|") !== "input|report|schema")
                throw Error("Unknown notebook evidence fields");
            input = input.input;
        }
        validate(input);
        load(input);
        await compute(input, ticket);
    } catch (e) {
        if (ticket === revision) error(e);
    } finally {
        if ($("import").files[0] === file) $("import").value = "";
    }
};
$("language").onclick = () => {
    lang = lang === "fr" ? "en" : "fr";
    translate();
    const u = new URL(location.href);
    u.searchParams.set("lang", lang);
    history.replaceState(null, "", u);
};
function download(bytes, name) {
    const u = URL.createObjectURL(
            new Blob([bytes], { type: "application/json" })
        ),
        a = node("a");
    a.href = u;
    a.download = name;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(u), 1000);
}
$("download").onclick = () => {
    if (current) download(current.bytes, "cross-industry-input.json");
};
$("evidence").onclick = () => {
    if (current)
        download(
            JSON.stringify(
                {
                    schema_version: "cross-industry-browser-evidence-v1",
                    input: current.input,
                    report: current.report,
                    downloadedInputSha256: current.hash,
                    hashScope: "Exact UTF-8 bytes of cross-industry-input.json",
                },
                null,
                2
            ) + "\n",
            "cross-industry-evidence.json"
        );
};
translate();
restore();
