# SPDX-License-Identifier: Apache-2.0
"""Common customer handoff, separately registered after the primary package failure."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from intake import canonical, digest, scoped_calls


def source_url(source: dict[str, Any], line: int | None = None) -> str:
    suffix = f"#L{line}" if line is not None else ""
    return f"https://github.com/{source['repository']}/blob/{source['commit']}/{source['path']}{suffix}"


def inventory(raw: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = scoped_calls(raw)
    consumer = raw["sources"][raw["consumer"]["source"]]
    record = result.get("coreRecord") or {}
    assessed = {row["id"]: row for row in record.get("calls", [])}
    rows = []
    for call in (result.get("request") or {}).get("calls", []):
        check = assessed[call["id"]]
        node = nodes[(call["line"], call["column"], call["callee"])]
        rows.append(
            {
                "id": call["id"],
                "line": call["line"],
                "column": call["column"],
                "callee": call["callee"],
                "status": check["status"],
                "mappingVerified": check.get("mappingVerified", False),
                "qualification": check.get("qualification"),
                "reason": check.get("reason"),
                "snippet": ast.get_source_segment(consumer["text"], node),
                "consumerUrl": source_url(consumer, call["line"]),
                "consumerSha256": consumer["sha256"],
                "targets": {
                    side: {
                        **call[side],
                        "url": source_url(raw["sources"][call[side]["source"]]),
                        "sha256": raw["sources"][call[side]["source"]]["sha256"],
                    }
                    for side in ("before", "after")
                },
                "beforeAccepts": check.get("beforeAccepts"),
                "afterAccepts": check.get("afterAccepts"),
                "afterSignature": check.get("afterSignature"),
                "mappingExplanation": call.get("mapping", {}).get("explanation", ""),
            }
        )
    for call in result["unresolvedIntake"]:
        node = nodes[(call["line"], call["column"], call["callee"])]
        rows.append(
            {
                "id": f"unresolved-{call['line']}-{call['column']}",
                **call,
                "status": "UNRESOLVED",
                "mappingVerified": False,
                "qualification": "Captured evidence does not establish the target relationship.",
                "snippet": ast.get_source_segment(consumer["text"], node),
                "consumerUrl": source_url(consumer, call["line"]),
                "consumerSha256": consumer["sha256"],
                "targets": {},
                "beforeAccepts": None,
                "afterAccepts": None,
                "afterSignature": None,
            }
        )
    return sorted(rows, key=lambda row: (row["line"], row["column"], row["callee"]))


def action(row: dict[str, Any], lang: str) -> str:
    name = row["callee"]
    if lang == "fr":
        if row["status"] == "BINDING_CONFLICT":
            return (
                f"Suspendre la mise à niveau pour `{name}`. Le contrat capturé accepte cet appel avant, "
                "mais le refuse après. Vérifier la cible importée, adapter les arguments à la signature ci-dessous, "
                "puis exécuter un test de régression du consommateur avec les deux versions. Aucun correctif comportemental n’est validé ici."
            )
        if row["status"] == "BINDING_PRESERVED":
            return (
                f"Aucun changement d’arguments n’est exigé par ces deux signatures pour `{name}`. "
                "Confirmer la cible importée et tester ce chemin du consommateur avec les deux versions; "
                "la liaison seule ne justifie pas une mise en production."
            )
        return (
            f"Décision suspendue pour `{name}`. Identifier la cible effective et les arguments développés ou liés, "
            "puis exécuter un test isolé de ce chemin avec les versions avant et après; conserver les valeurs, "
            "types et exceptions observés. Le motif ci-dessous précise la preuve manquante."
        )
    if row["status"] == "BINDING_CONFLICT":
        return (
            f"Hold this upgrade for `{name}`. The captured before contract accepts this call; the after contract rejects it. "
            "Confirm the imported target, revise the arguments against the signature below, and run a consumer regression "
            "test under both versions. No behavioral patch is validated here."
        )
    if row["status"] == "BINDING_PRESERVED":
        return (
            f"These two signatures require no argument change for `{name}`. Confirm the imported target and test this "
            "consumer path under both versions; binding alone does not justify production approval."
        )
    return (
        f"Hold the decision for `{name}`. Identify the actual target and expanded or bound arguments, then run an "
        "isolated test of this consumer path under both versions, recording values, types and exceptions. "
        "The reason below identifies the missing evidence."
    )


def markdown(raw: dict[str, Any], result: dict[str, Any], rows: list[dict[str, Any]], lang: str) -> str:
    fr = lang == "fr"
    words = {
        "title": (
            "Décision de maintenance — contrat d’appel" if fr else "Maintenance decision — call contract"
        ),
        "scope": "Périmètre" if fr else "Scope",
        "next": "Action proposée" if fr else "Recommended action",
        "evidence": "Preuves et limites" if fr else "Evidence and limits",
        "cost": "Coût complet non identifié" if fr else "Complete cost not identified",
    }
    lines = [
        f"# AGI ALPHA · {words['title']}",
        "",
        f"**{raw['id']} · {raw['title']}**",
        "",
        f"{words['scope']}: `{', '.join(raw['consumer']['scopeSymbols'])}`; "
        f"{raw['dependency']['package']} {raw['dependency']['before']['version']} → {raw['dependency']['after']['version']}.",
        "",
        f"## {words['next']}",
        "",
        f"**{result['nextAction']}**",
        "",
        (
            "Cette revue délimite les appels à corriger ou à tester. Elle ne constitue ni une validation comportementale, "
            "ni une approbation de sécurité ou de déploiement. L’acceptation du périmètre complet est évaluée séparément."
            if fr
            else "This review identifies calls to revise or test. It is not behavioral validation, a security assessment "
            "or deployment approval. Complete scope acceptance is audited separately."
        ),
        "",
        f"## {words['evidence']}",
        "",
    ]
    for row in rows:
        lines += [
            f"### `{row['callee']}` · L{row['line']} · {row['status']}",
            "",
            action(row, lang),
            "",
            f"[{'Source consommateur' if fr else 'Consumer source'}]({row['consumerUrl']}) · SHA-256 `{row['consumerSha256']}`",
            "",
            "```python",
            row["snippet"] or "",
            "```",
            "",
        ]
        reason = row.get("reason") or row.get("qualification")
        if reason:
            lines += [f"{'Limite conservée' if fr else 'Retained qualification'}: {reason}", ""]
        for side, target in row["targets"].items():
            lines += [f"- {side}: [`{target['symbol']}`]({target['url']}) · SHA-256 `{target['sha256']}`"]
        lines += [""]
        if row["afterSignature"]:
            lines += [
                f"{'Signature après' if fr else 'After signature'}: `"
                + ", ".join(
                    f"{p['name']} ({p['kind']}{', required' if p['required'] else ', optional'})"
                    for p in row["afterSignature"]["parameters"]
                )
                + "`",
                "",
            ]
    lines += [
        f"## {words['cost']}",
        "",
        (
            "Les ressources locales mesurées figurent dans le reçu. Les frais d’inférence, de préparation, de vérification humaine, "
            "d’intégration et d’entretien ne sont pas tous disponibles; le coût complet demeure inconnu. Aucun encaissement réel."
            if fr
            else "Measured local resources are in the receipt. Inference, preparation, human review, integration and upkeep "
            "charges are not all available; complete cost remains unknown. Actual collections are zero."
        ),
        "",
        "[Captured input](raw-task.json) · [Decision record](decision-record.json) · [Call inventory](call-inventory.json) · "
        "[Cost record](costs.json) · [Execution result](result.json) · [Receipt](receipt.json)",
        "",
        (
            "Autorité : HOLD; aucune autorité opérateur; règlement non connecté. Les recommandations exigent la décision du mainteneur."
            if fr
            else "Authority: HOLD; no operator authority; settlement disconnected. Recommendations require the maintainer’s decision."
        ),
        "",
    ]
    return "\n".join(lines)


def write_package(out: Path, raw: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    rows = inventory(raw, result)
    costs = {
        "schema": "agi-alpha-complete-delivery-cost/v1",
        "mission": raw["id"],
        "arm": result["arm"],
        "actualCollectionsUsd": 0,
        "marginalUsd": None,
        "recurringUsd": None,
        "fullyLoadedUsd": None,
        "currentSessionModelStage": result["arm"] in ("A", "B"),
        "runtimeModelCallsWithinRecordedProcess": 0,
        "unknowns": [
            "source acquisition and authoring",
            "current-session extraction inference and billing",
            "discovery and failed candidate construction",
            "verification and corrections",
            "integration and packaging",
            "future upkeep",
            "residual operator and customer effort",
        ],
        "allocation": "Construction belongs once to the retained asset; it is not also booked as each mission’s recurring cost.",
        "noWageConversion": True,
        "completeCostsIdentified": False,
    }
    files = {
        "raw-task.json": raw,
        "call-inventory.json": rows,
        "costs.json": costs,
        "decision-record.json": result.get("coreRecord")
        or {"available": False, "reason": "All selected calls remain unresolved at intake."},
    }
    for name, value in files.items():
        (out / name).write_bytes(canonical(value))
    for lang in ("en", "fr"):
        (out / f"report-{lang}.md").write_text(markdown(raw, result, rows, lang))
    return {
        "schema": "agi-alpha-customer-handoff/v2",
        "callCount": len(rows),
        "inventorySha256": digest(rows),
        "bilingual": True,
        "completeScopeAccepted": None,
        "customerAcceptance": "unknown",
        "sourceScope": raw["consumer"],
        "completeCostsIdentified": False,
        "productionApproved": False,
    }
