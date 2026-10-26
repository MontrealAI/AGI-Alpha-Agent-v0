# SPDX-License-Identifier: Apache-2.0
"""Render the customer result from its checked source record, without reconstruction."""

from __future__ import annotations

import copy
import html
import io
import json
import time
import zipfile
from pathlib import Path
from typing import Any

from .core import STAGES, canonical, sha

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORDS = {
    "en": {
        "title": "Your upgrade decision",
        "action": "Next action",
        "unknown": "Unknown",
        "scope": "What this establishes",
        "cost": "Complete monetary cost: unknown",
        "evidence": "Source evidence",
        "limits": "What remains unresolved",
        "calls": "Selected calls",
        "basis": "Argument binding only. Review behavior and security before changing a deployed dependency.",
        "HOLD_UPDATE_AND_TEST": "Hold the dependency-only update. Reproduce this specific conflict; review the upstream fix and test the complete dependency set.",
        "REVIEW_UNRESOLVED_SCOPE": "Resolve the stated source or dispatch gap and run the relevant integration check before deciding.",
        "RUN_BEHAVIOR_AND_SECURITY_CHECKS": "The selected argument bindings are preserved. Run behavior and security checks before deciding on the update.",
        "BINDING_CONFLICT": "The selected call shape is accepted by the earlier declaration and rejected by the proposed declaration.",
        "BINDING_PRESERVED": "The selected call shape binds to both captured declarations.",
        "UNRESOLVED": "This selected call remains unresolved.",
        "historical": "Historical sources and recorded evidence; these pins are not current production recommendations.",
        "conditional": "The call-to-declaration target is supplied, and its runtime identity remains unproved.",
        "direct": "Direct source import checked, subject to standard import behavior and no monkeypatching.",
    },
    "fr": {
        "title": "Votre décision de mise à niveau",
        "action": "Prochaine action",
        "unknown": "Inconnu",
        "scope": "Ce qui est établi",
        "cost": "Coût monétaire complet : inconnu",
        "evidence": "Sources vérifiables",
        "limits": "Ce qui reste non résolu",
        "calls": "Appels sélectionnés",
        "basis": "Liaison des arguments seulement. Vérifiez le comportement et la sécurité avant toute modification d'une dépendance déployée.",
        "HOLD_UPDATE_AND_TEST": "Suspendez la mise à niveau de cette dépendance seule. Reproduisez ce conflit précis, examinez la correction amont et testez l'ensemble des dépendances.",
        "REVIEW_UNRESOLVED_SCOPE": "Résolvez le manque de source ou de résolution de l'appel, puis exécutez le test d'intégration pertinent avant de décider.",
        "RUN_BEHAVIOR_AND_SECURITY_CHECKS": "La liaison des arguments sélectionnés est préservée. Vérifiez le comportement et la sécurité avant de décider de la mise à niveau.",
        "BINDING_CONFLICT": "La forme de cet appel est acceptée par la déclaration précédente et refusée par la déclaration proposée.",
        "BINDING_PRESERVED": "La forme de cet appel est acceptée par les deux déclarations capturées.",
        "UNRESOLVED": "Cet appel sélectionné reste non résolu.",
        "historical": "Sources historiques et résultats consignés ; ces versions ne sont pas des recommandations de production actuelles.",
        "conditional": "La cible de l'appel est déclarée ; son identité à l'exécution reste non démontrée.",
        "direct": "Importation directe vérifiée dans la source, sous réserve d'un import standard sans modification à l'exécution.",
    },
}


def fact(value: int | None, basis: str, reference: str) -> dict[str, Any]:
    return {"value": value, "basis": basis, "reference": reference}


def accounting(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    template = json.loads((ROOT / "examples/successor-alpha/fixtures/automated-costs-unknown.json").read_text())
    template["offeringId"] = record["missionKey"]
    stages = {s["stage"] for s in record["resources"]["stages"]}
    for scenario in template["scenarios"]:
        for operation in scenario["operations"]:
            stage = operation["stage"]
            operation["implementation"] = "implemented"
            operation["frequency"] = "attempt"
            operation["unitsPerOccurrencePpm"] = fact(
                1_000_000 if stage in stages or stage == "packaging" else None,
                "measured" if stage in stages else "estimated" if stage == "packaging" else "unknown",
                "Observed core stages; one subsequent packaging operation is planned. Recovery/interrupted attempts and parent transport are not inferred as zero.",
            )
            operation["unitCostMicros"] = fact(
                None,
                "unknown",
                "No observed provider/compute monetary invoice or defensible operation allocation is available for this offering.",
            )
        scenario["attemptsPerRequestPpm"] = fact(
            None,
            "unknown",
            "One completed observed attempt does not estimate the offering's recurring failure/retry distribution.",
        )
    events: list[dict[str, Any]] = [
        {
            "id": "mission",
            "type": "mission",
            "missionId": record["missionKey"],
            "reference": "Internal engineering packet; actual customer acceptance remains unknown.",
            "acceptance": "unknown",
        }
    ]
    for ident, kind, category, value, basis in [
        ("collected", "revenue", "collected", 0, "observed"),
        ("price", "revenue", "price", None, "unknown"),
        ("delivery", "cost", "delivery", None, "unknown"),
        ("business", "cost", "business", None, "unknown"),
        ("construction", "cost", "capability", None, "unknown"),
        ("upkeep", "cost", "maintenance", None, "unknown"),
        ("obligations", "obligation", "unpaid", None, "unknown"),
        ("reserve", "reserve", "reliability", None, "unknown"),
    ]:
        events.append(
            {
                "id": ident,
                "type": kind,
                "missionId": record["missionKey"],
                "reference": "Internal nontransactional evaluation: zero customer collections; all unsupported currency amounts remain unknown. Construction is recorded once, not charged again per mission.",
                "amountMinor": value,
                "basis": basis,
                "category": category,
            }
        )
    return template, {"schema": "alpha-shadow-ledger/v1", "currency": "USD", "events": events}


def markdown(record: dict[str, Any], language: str) -> str:
    if record.get("assessmentKind") == "native-component-contract":
        return component_markdown(record, language)
    w = WORDS[language]
    lines = [
        f"# {w['title']}",
        "",
        record["title"],
        "",
        f"**{w['action']}:** {w[record['nextAction']]}",
        "",
        w["basis"],
        "",
        f"**{w['cost']}**. {w['unknown']}: setup, integration, upkeep, authoring/inference, customer effort.",
        "",
        f"## {w['calls']}",
        "",
    ]
    for row in record["calls"]:
        lines.extend(
            [
                f"### {row['id']}",
                "",
                w[row["status"]],
                "",
                "```python",
                row.get("snippet", ""),
                "```",
                "",
                w["direct"] if row.get("mappingVerified") else w["conditional"],
                "",
            ]
        )
        if row.get("reason"):
            lines.extend([row["reason"], ""])
        for source in row["evidence"]:
            lines.append(
                f"- [{source['sourceId']} · L{source['line']}–L{source['endLine']}]({source['url']}) · SHA256 `{source['sha256']}`"
            )
        lines.append("")
    if record["recordedChecks"]:
        lines.extend(
            [
                "## " + ("Recorded execution evidence" if language == "en" else "Preuves d'exécution consignées"),
                "",
                (
                    "These checks were recorded separately and are not rerun by this source worker."
                    if language == "en"
                    else "Ces vérifications ont été consignées séparément ; cet exécuteur de sources ne les réexécute pas."
                ),
                "",
            ]
        )
        for check in record["recordedChecks"]:
            lines.extend(
                [
                    check["id"],
                    "",
                    check["method"],
                    "",
                    check["reference"],
                    "",
                    "```json",
                    json.dumps(check["result"].get("checks", check["result"]), ensure_ascii=False, indent=2),
                    "```",
                    "",
                ]
            )
    lines.extend(
        [
            f"## {w['limits']}",
            "",
            *[f"- {limit}" for limit in record["limits"]],
            "",
            w["historical"],
            "",
            "Source record: decision-record.json. Canonical cost inputs/analysis: automated-costs.json / cost-analysis.json. Nontransactional ledger: ledger.json / ledger-analysis.json.",
            "",
        ]
    )
    return "\n".join(lines)


def render_html(record: dict[str, Any]) -> str:
    if record.get("assessmentKind") == "native-component-contract":
        return component_html(record)
    blocks = []
    for lang in ("en", "fr"):
        w = WORDS[lang]
        calls = []
        for row in record["calls"]:
            links = "".join(
                f'<li><a rel="noreferrer" href="{html.escape(s["url"], quote=True)}">{html.escape(s["sourceId"])} · L{s["line"]}–L{s["endLine"]}</a><br><small>SHA256 {s["sha256"]}</small></li>'
                for s in row["evidence"]
            )
            calls.append(
                f'<article><h3>{html.escape(row["id"])}</h3><p>{w[row["status"]]}</p><pre>{html.escape(row.get("snippet", ""))}</pre><p>{w["direct"] if row.get("mappingVerified") else w["conditional"]}</p><p>{html.escape(row.get("reason") or "")}</p><ul>{links}</ul></article>'
            )
        limits = "".join(f"<li>{html.escape(value)}</li>" for value in record["limits"])
        stored = ""
        for check in record["recordedChecks"]:
            heading = (
                "Recorded execution evidence — not rerun by this source worker"
                if lang == "en"
                else "Preuves d'exécution consignées — non réexécutées par cet exécuteur"
            )
            stored += f'<article><h3>{heading}</h3><p>{html.escape(check["method"])}</p><details><summary>{html.escape(check["id"])}</summary><pre>{html.escape(json.dumps(check["result"].get("checks", check["result"]), ensure_ascii=False, indent=2))}</pre><small>{html.escape(check["reference"])}</small></details></article>'
        blocks.append(
            f'<section lang="{lang}" {"hidden" if lang == "fr" else ""}><p class="eyebrow">AGI ALPHA · {w["title"]}</p><h1>{html.escape(record["title"])}</h1><p class="action">{w[record["nextAction"]]}</p><p>{w["basis"]}</p><p class="cost">{w["cost"]}</p><h2>{w["calls"]}</h2>{"".join(calls)}{stored}<h2>{w["limits"]}</h2><ul>{limits}</ul><p>{w["historical"]}</p></section>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>AGI ALPHA · Upgrade decision</title><style>body{font:17px/1.55 system-ui;background:#110c23;color:#f5f0ff;margin:0}main{max-width:900px;margin:auto;padding:28px}h1{font-size:clamp(30px,6vw,48px);line-height:1.12}.eyebrow{color:#c2aaff}article{background:#211635;padding:22px;margin:22px 0;border-radius:18px}pre{overflow:auto;font-size:14px;padding:16px;background:#120e20}a{color:#c9b4ff}small{overflow-wrap:anywhere}.action{border-left:4px solid #b6efb1;padding:18px;background:#1b2b27}.cost{color:#ffd79e}button{padding:12px 20px;color:inherit;background:#392354;border:1px solid #b697eb;border-radius:10px}li{margin-bottom:10px}[hidden]{display:none}</style></head><body><main><button id="lang" type="button">Français</button>'
        + "".join(blocks)
        + '<footer><p>decision-record.json · automated-costs.json · ledger.json · checksums.json</p><p>Engineering acceptance is separate from customer acceptance, approved operation and production adoption.</p></footer></main><script>document.getElementById("lang").onclick=()=>{let fr=document.documentElement.lang==="en";document.documentElement.lang=fr?"fr":"en";for(let e of document.querySelectorAll("section[lang]"))e.hidden=e.lang!==document.documentElement.lang;document.getElementById("lang").textContent=fr?"English":"Français"}</script></body></html>'
    )


def package(
    record: dict[str, Any],
    pack: dict[str, Any],
    cost_record: dict[str, Any],
    ledger: dict[str, Any],
    analysis: dict[str, Any],
    *,
    notices: bytes,
) -> bytes:
    started, cpu = time.perf_counter_ns(), time.process_time_ns()
    files = {
        "report.en.md": markdown(record, "en").encode(),
        "report.fr.md": markdown(record, "fr").encode(),
        "report.html": render_html(record).encode(),
        "source-pack.json": canonical(pack),
        "automated-costs.json": canonical(cost_record),
        "cost-analysis.json": canonical(analysis["accounting"]),
        "ledger.json": canonical(ledger),
        "ledger-analysis.json": canonical(analysis["ledger"]),
        "NOTICES.md": notices,
        "capability.json": (HERE / "CAPABILITY.json").read_bytes(),
        "workload.json": (HERE / "WORKLOAD.json").read_bytes(),
        "README.md": b"Open report.html for English/French. Inspect decision-record.json and source-pack.json for exact claims and sources. Full currency costs remain unknown. This is a bounded source-contract assessment, not performed dependency upgrade, production authority or proof of payback. Preserve original records on rerun.\n",
    }
    record = copy.deepcopy(record)
    if "implementation" in record:
        files["implementation.json"] = canonical(record["implementation"])
    if record.get("assessmentKind") == "native-component-contract":
        for name, item in pack["files"].items():
            files["research/" + name] = item["text"].encode()
    record["resources"]["stages"].append(
        {
            "stage": "packaging",
            "status": "completed",
            "wallNs": time.perf_counter_ns() - started,
            "cpuNs": time.process_time_ns() - cpu,
            "basis": "measured",
            "scope": "Rendering/encoding payloads; final compression, parent transport, journal and delivery overhead remain outside this observation, not zero.",
        }
    )
    files["decision-record.json"] = canonical(record)
    files["checksums.json"] = canonical({name: sha(raw) for name, raw in sorted(files.items())})
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    result = stream.getvalue()
    if len(result) > 500_000:
        raise ValueError("complete customer package exceeds installed output bound")
    return result


def component_markdown(record: dict[str, Any], language: str) -> str:
    fr = language == "fr"
    decision = record["componentDecision"]
    regression = record["nextAction"] == "HOLD_COMPONENT_AND_INVESTIGATE"
    lines = [
        "# " + ("Votre décision de mise à niveau" if fr else "Your dependency-upgrade decision"),
        "",
        (
            "**Conservez le verrou actuel de l'application native. Ces preuves des composants peuvent servir à la qualification complète suivante.**"
            if fr
            else "**Keep the current native application lock. Advance this component evidence to full application qualification.**"
        ),
        "",
        (
            "Les 61 exigences déclarées ont réussi avant et après le changement. Le chemin FastAPI d'origine et le délai réel de 15 secondes ont été vérifiés dans les observations consignées par le chercheur."
            if fr
            else "All 61 declared requirements passed before and after the change. The original FastAPI import bridge and actual 15-second timeout were exercised in the writer's recorded observations."
        ),
        "",
        (
            "Ce produit revérifie les observations consignées. Il n'exécute pas le code des composants ni l'application."
            if fr
            else "This product rechecks the saved observations. It does not execute the consumer components or application."
        ),
        "",
        "## " + ("Versions examinées" if fr else "Examined versions"),
        "",
        "| " + ("Dépendance | Avant | Après |" if fr else "Dependency | Before | After |"),
        "|---|---|---|",
    ]
    for name in decision["before_versions"]:
        lines.append(f"| {name} | {decision['before_versions'][name]} | {decision['after_versions'][name]} |")
    lines.extend(["", "## " + ("Ce qui est établi" if fr else "What is established"), ""])
    properties = (
        [
            "Encadrement et taille des requêtes, origine, déconnexion, délai d'expiration réel et octets transmis.",
            "En-têtes de sécurité déclarés.",
            "Validation stricte et sérialisation complète des entrées Mission, Review et Control sélectionnées.",
        ]
        if fr
        else decision["accepted_properties"]
    )
    if regression:
        properties = [
            (
                "La référence satisfait le contrat ; le profil proposé présente au moins un écart requis."
                if fr
                else "The baseline satisfies the contract; the proposed profile has at least one required behavior mismatch."
            )
        ]
    lines.extend("- " + text for text in properties)
    lines.extend(["", "## " + ("Votre prochaine action" if fr else "Your next action"), ""])
    actions = (
        [
            "Décider si cette mise à niveau est nécessaire.",
            "Réconcilier et qualifier l'ensemble des dépendances et plateformes de l'application.",
            "Faire exécuter les contrôles autorisés d'authentification, de persistance et de mission complète.",
            "Obtenir la revue des responsables et les contrôles requis avant toute adoption.",
        ]
        if fr
        else decision["remaining_customer_work"]
    )
    if regression:
        actions = (
            [
                "Conserver le verrou de l'application native et ne pas adopter ce profil proposé.",
                "Reproduire les cas en écart avec les sources et versions exactes du dossier.",
                "Examiner la cause, puis requalifier toute correction avant la revue des responsables.",
            ]
            if fr
            else [
                "Keep the native application lock and do not adopt this proposed tuple.",
                "Reproduce the mismatching cases with the exact captured sources and versions.",
                "Investigate the cause and requalify a remedy before owner review.",
            ]
        )
    lines.extend(f"{i}. {text}" for i, text in enumerate(actions, 1))
    lines.extend(
        [
            "",
            "## " + ("Preuves et limites" if fr else "Evidence and limits"),
            "",
            (
                "Un seul dossier interne de développement, pas 61 clients ni une preuve universelle. L'acceptation par un client et l'adoption opérationnelle ne sont pas établies."
                if fr
                else "One internal development work package, not 61 customers or a universal proof. Customer acceptance and operational adoption are unestablished."
            ),
            "",
        ]
    )
    lines.extend(f"- [Source {i}]({url})" for i, url in enumerate(decision["source_urls"], 1))
    lines.extend(
        [
            "",
            (
                "research/ contient les fichiers originaux et leur manifeste. componentChecks dans decision-record.json conserve la nouvelle revérification. Aucun original n'est réécrit."
                if fr
                else "research/ contains all original files and their manifest. componentChecks in decision-record.json preserves this new recheck. No original is rewritten."
            ),
            "",
            "## " + ("Coût complet" if fr else "Complete cost"),
            "",
            (
                "Coûts monétaires marginal, récurrent et complet : inconnus. Prix et minutes client/opérateur : inconnus. Paiements clients observés : zéro. Surplus disponible : inconnu. Les ressources mesurées, les échecs et les coûts non mesurés restent distincts."
                if fr
                else "Marginal, recurring and fully loaded currency costs: unknown. Price and customer/operator minutes: unknown. Observed customer collections: zero. Available surplus: unknown. Measured resources, failed attempts and unmeasured costs remain distinct."
            ),
            "",
            "automated-costs.json · cost-analysis.json · ledger.json · ledger-analysis.json · checksums.json",
            "",
        ]
    )
    if regression:
        lines[2] = (
            "**Suspendez cette mise à niveau. Conservez le verrou actuel de l'application native et examinez les écarts des composants.**"
            if fr
            else "**Hold this refresh. Keep the current native application lock and investigate the component mismatches.**"
        )
        lines[4] = (
            "Un comportement requis diffère dans le profil proposé ; les preuves restent limitées à ce contrat."
            if fr
            else "A required behavior mismatches in the proposed profile; this evidence remains limited to the exact component contract."
        )
        lines.append("Cas en écart : " if fr else "Mismatching cases: ")
        lines.extend(
            row["id"] for row in record["componentChecks"][1]["result"]["cases"] if row["status"] == "BEHAVIOR_MISMATCH"
        )
    return "\n".join(lines)


def component_html(record: dict[str, Any]) -> str:
    decision = record["componentDecision"]
    regression = record["nextAction"] == "HOLD_COMPONENT_AND_INVESTIGATE"
    required = decision["coverage"]["requirements"]
    before_pass = record["componentChecks"][0]["result"]["counts"]["PASS"]
    after_pass = record["componentChecks"][1]["result"]["counts"]["PASS"]
    sections = []
    for language in ("en", "fr"):
        fr = language == "fr"
        heading = "Votre prochaine mise à niveau, avec ses preuves." if fr else "Your next upgrade, with the evidence."
        action = (
            "Conservez le verrou actuel. Passez ces preuves à la qualification complète de l'application."
            if fr
            else "Keep the current lock. Advance this evidence to full application qualification."
        )
        if regression:
            action = (
                "Suspendez cette mise à niveau. Conservez le verrou natif et examinez les écarts."
                if fr
                else "Hold this refresh. Keep the native lock and investigate the mismatches."
            )
        steps = (
            (
                [
                    "Conserver le verrou natif et ne pas adopter ce profil proposé.",
                    "Reproduire et examiner les cas en écart avec les sources exactes.",
                    "Requalifier toute correction et obtenir la revue des responsables.",
                ]
                if fr
                else [
                    "Keep the native lock and do not adopt this proposed tuple.",
                    "Reproduce and investigate the mismatches against the exact sources.",
                    "Requalify a remedy and obtain owner review.",
                ]
            )
            if regression
            else (
                [
                    "Réconcilier le verrou complet et les plateformes prises en charge.",
                    "Faire exécuter les contrôles autorisés d'authentification, de persistance et de mission complète.",
                    "Obtenir la revue des responsables et les contrôles requis avant l'adoption.",
                ]
                if fr
                else [
                    "Reconcile the complete lock and supported platforms.",
                    "Run authorized authentication, persistence and complete mission checks.",
                    "Obtain owner review and required acceptance before adoption.",
                ]
            )
        )
        next_steps_html = "<ol>" + "".join("<li>" + html.escape(text) + "</li>" for text in steps) + "</ol>"
        rows = "".join(
            f'<tr><td>{html.escape(name)}</td><td>{html.escape(before)}</td><td>{html.escape(decision["after_versions"][name])}</td></tr>'
            for name, before in decision["before_versions"].items()
        )
        requirements = "".join(
            f'<tr><td>{html.escape(row["id"])}</td><td>{row["status"]}</td></tr>'
            for row in record["componentChecks"][1]["result"]["cases"]
        )
        sources = "".join(
            f'<li><a href="{html.escape(url, quote=True)}" rel="noreferrer">{html.escape(url.rsplit("/", 1)[-1])}</a></li>'
            for url in decision["source_urls"]
        )
        sections.append(
            f"""<section lang="{language}" {"hidden" if fr else ""}><p class="eyebrow">AGI ALPHA · {"EXAMEN DE DÉPENDANCES" if fr else "DEPENDENCY REVIEW"}</p><h1>{heading}</h1><p class="action">{action}</p><div class="stats"><article><strong>{before_pass} / {required}</strong><span>{"Exigences avant" if fr else "Requirements before"}</span></article><article><strong>{after_pass} / {required}</strong><span>{"Exigences après" if fr else "Requirements after"}</span></article><article><strong>{"Inconnu" if fr else "Unknown"}</strong><span>{"Coût monétaire complet" if fr else "Full monetary cost"}</span></article></div><p>{("Des comportements requis diffèrent dans le profil proposé. Consultez les cas en écart ci-dessous." if fr else "Required behavior mismatches in the proposed profile. Inspect the cases below.") if regression else "Le chemin d'importation FastAPI d'origine et le délai réel de 15 secondes ont été conservés dans les observations du chercheur. Ce produit revérifie ces observations sans réexécuter les composants." if fr else "The writer's observations preserve the original FastAPI import bridge and actual 15-second timeout. This product rechecks those observations without re-executing the consumer."}</p><h2>{"Le changement examiné" if fr else "The examined change"}</h2><table><thead><tr><th>{"Dépendance" if fr else "Dependency"}</th><th>{"Avant" if fr else "Before"}</th><th>{"Après" if fr else "After"}</th></tr></thead><tbody>{rows}</tbody></table><h2>{"Votre prochaine action" if fr else "Your next action"}</h2>{next_steps_html}<details><summary>{"Les 61 exigences et leurs résultats" if fr else "All 61 requirements and outcomes"}</summary><table><thead><tr><th>{"Exigence" if fr else "Requirement"}</th><th>{"Après" if fr else "After"}</th></tr></thead><tbody>{requirements}</tbody></table></details><h2>{"Sources et limites" if fr else "Sources and limits"}</h2><ul>{sources}</ul><p>{"Un seul dossier interne de développement. Aucun résultat sur l'authentification, la persistance, l'application entière, la sécurité des dépendances ou la production. Les fichiers d'origine et leurs empreintes sont inclus." if fr else "One internal development work package. No authentication, persistence, whole-application, dependency-security or production result. All original files and their hashes are included."}</p><p class="cost">{"Coûts marginal, récurrent et complet, prix et temps client/opérateur : inconnus. Paiements clients : zéro. Surplus disponible : inconnu." if fr else "Marginal, recurring and fully loaded costs, price and customer/operator time: unknown. Customer collections: zero. Available surplus: unknown."}</p></section>"""
        )
    return (
        """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>AGI ALPHA · Dependency decision</title><style>body{font:17px/1.6 system-ui;background:#100b21;color:#f6f1ff;margin:0}main{max-width:940px;margin:auto;padding:28px}h1{font-size:clamp(32px,6vw,54px);line-height:1.13;max-width:760px}.eyebrow{color:#c6a6ff;letter-spacing:.1em;font-size:13px}.action{padding:24px;background:#20352d;border:1px solid #75bb93;border-radius:16px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:26px 0}.stats article{background:#261c3c;padding:20px;border-radius:14px}.stats strong{display:block;font-size:27px}.stats span{font-size:14px;color:#d1c3e7}table{border-collapse:collapse;width:100%;font-size:14px;overflow-wrap:anywhere}td,th{text-align:left;border-bottom:1px solid #463955;padding:11px}a{color:#cdb5ff}button{padding:12px 20px;color:inherit;background:#392354;border:1px solid #aa8cdb;border-radius:10px}details{padding:18px;background:#20172f;border-radius:14px;margin:24px 0}summary{cursor:pointer}.cost{color:#fbd49c}[hidden]{display:none}@media(max-width:620px){main{padding:18px}.stats{grid-template-columns:1fr}.stats article{padding:12px}td,th{padding:8px}}</style></head><body><main><button id="lang" type="button">Français</button>"""
        + "".join(sections)
        + """<footer><p>decision-record.json · research/ · automated-costs.json · ledger.json · checksums.json</p></footer></main><script>document.getElementById('lang').onclick=()=>{const fr=document.documentElement.lang==='en';document.documentElement.lang=fr?'fr':'en';for(const s of document.querySelectorAll('section[lang]'))s.hidden=s.lang!==document.documentElement.lang;document.getElementById('lang').textContent=fr?'English':'Français'}</script></body></html>"""
    )
