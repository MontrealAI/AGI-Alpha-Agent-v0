# SPDX-License-Identifier: Apache-2.0
"""Render an inert, offline delivery report from actual catalog artifacts."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import io
import json
from pathlib import Path
from typing import Any

from .catalog_product import verify_package


COPY = {
    "title": ("Your catalog change set", "Votre jeu de modifications"),
    "eyebrow": ("AGI ALPHA · CHECKED CATALOG DELIVERY", "AGI ALPHA · LIVRAISON DE CATALOGUE CONTRÔLÉE"),
    "intro": (
        "Inspect the actual changes. Keep the output, exact rollback and source-bound package.",
        "Examinez les changements réels. Conservez le résultat, le retour exact et le lot lié aux sources.",
    ),
    "scope": (
        "Offline delivery report. This page displays retained artifacts; it does not execute a new order or grant authority.",
        "Rapport de livraison hors ligne. Cette page présente les artefacts conservés ; elle n’exécute aucune commande et n’accorde aucune autorité.",
    ),
    "evidence": ("Recorded independent acceptance", "Acceptation indépendante consignée"),
    "accepted": ("ACCEPTED", "ACCEPTÉ"),
    "rejected": ("REFUSED", "REFUSÉ"),
    "unknown": ("NOT SUPPLIED", "NON FOURNIE"),
    "status_note": (
        "The acceptance record is supplied evidence, bound here to the delivered output digest. This report does not authenticate its author.",
        "L’acceptation est une preuve fournie, liée ici au condensat du résultat livré. Ce rapport n’authentifie pas son auteur.",
    ),
    "generation": ("Constructed generation", "Génération construite"),
    "changes": ("Changed keys", "Clés modifiées"),
    "rows": ("Output records", "Enregistrements produits"),
    "downloads": ("Keep the complete delivery", "Conserver la livraison complète"),
    "download_note": (
        "Machine CSV preserves exact cell text, including formula-like strings. Use the separate spreadsheet-safe preview in spreadsheet software.",
        "Le CSV machine préserve le texte exact, y compris les chaînes ressemblant à des formules. Utilisez l’aperçu sécurisé dans un tableur.",
    ),
    "before": ("Original snapshot · machine CSV", "État original · CSV machine"),
    "after": ("Supplier snapshot · machine CSV", "État fournisseur · CSV machine"),
    "output": ("Updated catalog · machine CSV", "Catalogue mis à jour · CSV machine"),
    "rollback": ("Exact rollback · machine CSV", "Retour exact · CSV machine"),
    "safe": ("Spreadsheet-safe preview · CSV", "Aperçu sécurisé pour tableur · CSV"),
    "package": ("Complete checked change set · JSON", "Jeu complet de modifications contrôlé · JSON"),
    "acceptance": ("Independent acceptance record · JSON", "Preuve d’acceptation indépendante · JSON"),
    "preview": ("First twenty changes", "Vingt premiers changements"),
    "key": ("Key", "Clé"),
    "kind": ("Change", "Modification"),
    "fields": ("Fields", "Champs"),
    "old": ("Before", "Avant"),
    "new": ("After", "Après"),
    "empty": ("No record-level changes.", "Aucun changement d’enregistrement."),
    "identity": ("Exact source and output identities", "Identités exactes des sources et du résultat"),
    "limits": ("Evidence and commercial boundaries", "Limites des preuves et de la portée commerciale"),
    "limit_text": (
        "This bounded commercial probe remains on Blue Sky HOLD. Useful delivery or simulated profit does not establish a transformational flagship. All campaign buyers, orders and payments are simulated. No live service, purchase or settlement is performed by this file.",
        "Cette sonde commerciale délimitée reste sous Blue Sky HOLD. Une livraison utile ou un profit simulé n’établit pas un projet phare transformationnel. Acheteurs, commandes et paiements de la campagne sont simulés. Ce fichier n’effectue aucun service distant, achat ou règlement.",
    ),
}


def _copy(key: str, tag: str = "span", class_name: str = "") -> str:
    en, fr = COPY[key]
    return (
        f'<{tag} class="{class_name}" data-en="{html.escape(en, quote=True)}" '
        f'data-fr="{html.escape(fr, quote=True)}">{html.escape(en)}</{tag}>'
    )


def render_report(package: dict[str, Any], acceptance: dict[str, Any] | None = None) -> str:
    """Keep all supplied CSV/JSON inert, escaped and downloadable without a server."""
    before = package.get("rollback_csv")
    if not isinstance(before, str):
        raise ValueError("The package must retain its exact source snapshot.")
    verify_package(package, before)
    acceptance = acceptance or {}
    if acceptance.get("accepted") is True and acceptance.get("actual_output_sha256") != package["output_sha256"]:
        raise ValueError("Accepted evidence must bind the exact delivered output.")
    status = (
        "accepted"
        if acceptance.get("accepted") is True
        else "rejected"
        if acceptance.get("accepted") is False
        else "unknown"
    )
    package_text = json.dumps(package, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    acceptance_text = json.dumps(acceptance, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    files = [
        ("before", "before.csv", before, "text/csv"),
        ("after", "after.csv", package["after_csv"], "text/csv"),
        ("output", "output.csv", package["output_csv"], "text/csv"),
        ("rollback", "rollback.csv", before, "text/csv"),
        ("safe", "spreadsheet-safe-preview.csv", package["safe_preview_csv"], "text/csv"),
        ("package", "catalog-change-set.json", package_text, "application/json"),
        ("acceptance", "acceptance.json", acceptance_text, "application/json"),
    ]
    downloads = "".join(
        f'<a class="download" download="{name}" href="data:{mime};base64,'
        f'{base64.b64encode(raw.encode()).decode()}">{_copy(label)}<span aria-hidden="true">↓</span></a>'
        for label, name, raw, mime in files
    )
    changes = package["changes"]
    preview = "".join(
        "<tr><td>"
        + html.escape(json.dumps(change["key"], ensure_ascii=False))
        + "</td><td>"
        + html.escape(change["kind"])
        + "</td><td>"
        + html.escape(", ".join(change["fields"]))
        + "</td><td>"
        + html.escape(json.dumps(change["before"], ensure_ascii=False))
        + "</td><td>"
        + html.escape(json.dumps(change["after"], ensure_ascii=False))
        + "</td></tr>"
        for change in changes[:20]
    )
    table = (
        (
            '<div class="table-wrap"><table><thead><tr>'
            + "".join(_copy(k, "th") for k in ["key", "kind", "fields", "old", "new"])
            + "</tr></thead><tbody>"
            + preview
            + "</tbody></table></div>"
        )
        if changes
        else _copy("empty", "p")
    )
    identities = "".join(
        "<dt>" + html.escape(label) + "</dt><dd><code>" + html.escape(value) + "</code></dd>"
        for label, value in [
            ("before_sha256", package["before_sha256"]),
            ("after_sha256", package["after_sha256"]),
            ("output_sha256", package["output_sha256"]),
            ("proof_digest", package["proof_digest"]),
            ("acceptance_record_sha256", hashlib.sha256(acceptance_text.encode()).hexdigest()),
        ]
    )
    rows = len(list(csv.reader(io.StringIO(package["output_csv"])))) - 1
    stats = "".join(
        "<article>" + _copy(label, "p") + "<strong>" + str(value) + "</strong></article>"
        for label, value in [("generation", package["generation"]), ("changes", len(changes)), ("rows", rows)]
    )
    style = """
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#100f1c;color:#f1ecf8}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top right,#41335b88,transparent 60%);line-height:1.6}main,header{width:min(1040px,calc(100% - 40px));margin:auto}header{display:flex;justify-content:space-between;align-items:center;padding-block:25px;border-bottom:1px solid #a698bf33}header strong{font-size:14px;letter-spacing:.12em}.languages{display:flex;gap:8px}button{font:inherit;color:inherit;border:1px solid #a698bf77;background:#272035;padding:6px 13px;border-radius:8px;cursor:pointer}button[aria-pressed=true]{background:#edcf98;color:#231a2a}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #ffdd92;outline-offset:4px}main{padding-block:45px 60px}.eyebrow{font-size:11px;letter-spacing:.13em;color:#e4c58d}h1{font-family:Georgia,serif;font-size:clamp(34px,6vw,60px);font-weight:400;line-height:1.1;max-width:720px}h2{font-size:23px;font-weight:500}p{color:#c0b7ce}section{margin-top:34px}.intro{font-size:18px;max-width:680px}.status{padding:20px;border:1px solid #c5a97166;border-radius:12px;background:#251d31}.status strong{color:#efcf95}.fine{font-size:12px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.stats article{padding:15px 20px;background:#271f354d;border-radius:12px;border:1px solid #a698bf33}.stats strong{font-size:30px}.stats p{font-size:12px;margin:0 0 8px}.downloads{display:grid;grid-template-columns:1fr 1fr;gap:10px}.download{color:#f5e7ce;text-decoration:none;padding:14px 18px;border:1px solid #a698bf55;background:#2c233a66;border-radius:10px;display:flex;justify-content:space-between;gap:12px;font-size:13px}.download:hover{background:#4d3b59}table{width:100%;border-collapse:collapse;font-size:13px}td,th{text-align:left;padding:12px;border-bottom:1px solid #a698bf33;overflow-wrap:anywhere}th{color:#e4c58d}.table-wrap{overflow:auto}details{border-top:1px solid #a698bf44;padding-top:18px;margin-top:30px}summary{cursor:pointer;color:#e4c58d}dl{font-size:12px}dt{color:#c9bbdc;margin-top:12px}dd{margin:5px 0;overflow-wrap:anywhere}footer{margin-top:40px;border-top:1px solid #a698bf33;padding-top:18px;color:#a99cb9;font-size:12px}@media(max-width:600px){main,header{width:calc(100% - 28px)}.downloads{grid-template-columns:1fr}.stats{gap:7px}.stats article{padding:11px}.stats strong{font-size:26px}.stats p{font-size:10px}main{padding-top:28px}}
"""
    script = """
(()=>{'use strict';function language(value){document.documentElement.lang=value;document.title=document.querySelector('[data-en-title]').dataset[value+'Title'];document.querySelectorAll('[data-en]').forEach(el=>{el.textContent=el.dataset[value];});document.querySelectorAll('[data-language]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.language===value)));}document.querySelectorAll('[data-language]').forEach(el=>el.addEventListener('click',()=>language(el.dataset.language)));language(new URLSearchParams(location.search).get('lang')==='fr'?'fr':'en');})();
"""

    def hashed(raw: str) -> str:
        return base64.b64encode(hashlib.sha256(raw.encode()).digest()).decode()

    title_en, title_fr = COPY["title"]
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; script-src 'sha256-"
        + hashed(script)
        + "'; style-src 'sha256-"
        + hashed(style)
        + "'; base-uri 'none'; object-src 'none'; form-action 'none'\">"
        "<title>" + title_en + "</title><style>" + style + "</style></head><body><header><strong>AGI ALPHA · Ω</strong>"
        '<nav class="languages" aria-label="Language / Langue"><button type="button" data-language="en" aria-pressed="true" lang="en">EN</button>'
        '<button type="button" data-language="fr" aria-pressed="false" lang="fr">FR</button></nav></header><main data-en-title="'
        + html.escape(title_en, quote=True)
        + '" data-fr-title="'
        + html.escape(title_fr, quote=True)
        + '">'
        + _copy("eyebrow", "p", "eyebrow")
        + _copy("title", "h1")
        + _copy("intro", "p", "intro")
        + _copy("scope", "p", "fine")
        + '<section class="status">'
        + _copy("evidence", "p", "fine")
        + _copy(status, "strong")
        + _copy("status_note", "p", "fine")
        + "</section>"
        + '<section class="stats">'
        + stats
        + "</section><section>"
        + _copy("downloads", "h2")
        + _copy("download_note", "p", "fine")
        + '<div class="downloads">'
        + downloads
        + "</div></section><section>"
        + _copy("preview", "h2")
        + table
        + "</section><details><summary>"
        + _copy("identity")
        + "</summary><dl>"
        + identities
        + "</dl></details><footer>"
        + _copy("limits", "strong")
        + _copy("limit_text", "p")
        + "</footer></main><script>"
        + script
        + "</script></body></html>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Render actual checked delivery artifacts as offline EN/FR HTML.")
    parser.add_argument("package", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--acceptance", type=Path)
    args = parser.parse_args()
    package = json.loads(args.package.read_text(encoding="utf-8"))
    acceptance = json.loads(args.acceptance.read_text(encoding="utf-8")) if args.acceptance else None
    rendered = render_report(package, acceptance)
    with args.output.open("x", encoding="utf-8") as target:
        target.write(rendered)
    print(str(args.output))


if __name__ == "__main__":
    main()
