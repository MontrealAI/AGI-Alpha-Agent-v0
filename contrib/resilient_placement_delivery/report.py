# SPDX-License-Identifier: Apache-2.0
"""Publish a content-bound named plan after independent finite verification."""

from __future__ import annotations

import csv
import base64
import hashlib
import html
import io
import json
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.successor.flywheel_experiments import verify_placement
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest

from .schema import PlacementBrief, parse_brief


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _cell(value: str | int) -> str | int:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def checked_delivery(brief: PlacementBrief, execution: dict[str, Any]) -> dict[str, Any]:
    """Check the exact named scope, artifact and independent numerical answer.

    Receipt consistency is not cryptographic authentication of an imported journal.
    The runner separately verifies its retained authoritative Journal.
    """
    if len(canonical(execution)) > 1_000_000:
        raise ValueError("execution receipt exceeds the delivery frame")
    mission = execution.get("mission", {})
    if (
        execution.get("status") != "delivered-awaiting-independent-acceptance-and-costs"
        or type(execution.get("actions")) is not int
        or execution["actions"] < 1
        or mission.get("mission_id") != brief.brief_id
        or mission.get("beneficiary") != brief.beneficiary
        or mission.get("inputs", {}).get("problem") != brief.problem.model_dump()
        or mission.get("inputs", {}).get("placement_brief_digest")
        != digest("commercial-placement-brief", brief.model_dump())
    ):
        raise ValueError("delivery receipt does not bind the exact executed named brief")
    if (
        mission.get("mode") != "hybrid"
        or mission.get("components", {}).get("model") != "simulated"
        or mission.get("components", {}).get("tools") != "executed-local"
        or execution.get("profile", {}).get("model_id") != "scripted-protocol-fixture/v1"
    ):
        raise ValueError("this research pack supports only the explicitly scripted hybrid configuration")
    result = execution.get("result", {})
    artifacts = result.get("artifacts", [])
    if not isinstance(artifacts, list) or len(artifacts) != 1 or not isinstance(artifacts[0], dict):
        raise ValueError("delivery requires exactly one unchanged placement-result artifact")
    artifact = artifacts[0]
    content = artifact.get("content", {})
    if (
        not isinstance(content, dict)
        or artifact.get("kind") != "placement-result"
        or artifact.get("digest") != digest("placement-artifact", content)
        or content.get("problem") != brief.problem.model_dump()
        or content.get("outcome") != result.get("deliverable")
    ):
        raise ValueError("delivered artifact differs from its bound problem, digest or answer")
    outcome = content.get("outcome")
    if not isinstance(outcome, dict) or outcome.get("status") not in {"optimal", "infeasible"}:
        raise ValueError("an incomplete or malformed answer cannot become an accepted decision pack")
    verification = verify_placement(brief.problem, outcome)
    if verification["accepted_finite_result"] is not True:
        raise ValueError("delivery fails independent exhaustive acceptance")
    observed = False
    for item in execution.get("history", []):
        if not isinstance(item, dict) or item.get("type") != "function_call_output":
            continue
        try:
            observation = json.loads(item.get("output", ""))
        except (ValueError, TypeError):
            continue
        observed = observed or observation == content
    if not observed:
        raise ValueError("delivery has no matching saved tool observation")
    return {"outcome": outcome, "verification": verification, "artifact_digest": artifact["digest"]}


def _plan(brief: PlacementBrief, outcome: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    loads = [0] * len(brief.hosts)
    for service_index, pair in enumerate(outcome["placement"] or []):
        service = brief.services[service_index]
        for replica, host_index in enumerate(pair, start=1):
            host = brief.hosts[host_index]
            loads[host_index] += service.demand
            rows.append(
                {
                    "service": service.id,
                    "replica": replica,
                    "host": host.id,
                    "failure_domain": host.failure_domain,
                    "demand": service.demand,
                    "objective_cost": service.costs[host.id],
                    "cost_unit": brief.cost_unit,
                }
            )
    hosts = [
        {
            "host": host.id,
            "failure_domain": host.failure_domain,
            "capacity": host.capacity,
            "load": loads[index] if outcome["status"] == "optimal" else None,
            "remaining": host.capacity - loads[index] if outcome["status"] == "optimal" else None,
        }
        for index, host in enumerate(brief.hosts)
    ]
    return rows, hosts


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f'<th scope="col">{html.escape(value)}</th>' for value in headers)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>" for row in rows)
    return (
        f'<div class="table-wrap" tabindex="0"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    )


def _page(brief: PlacementBrief, delivery: dict[str, Any]) -> str:
    plan = delivery["plan"]
    hosts = delivery["hosts"]
    optimal = delivery["outcome"]["status"] == "optimal"
    objective = delivery["outcome"]["cost"] if optimal else "—"
    price_usd = f"{brief.price_micro_usd // 1_000_000}.{brief.price_micro_usd % 1_000_000:06d}".rstrip("0").rstrip(".")
    plan_table = _table(
        ["Service", "Replica / Réplique", "Host / Hôte", "Failure domain / Domaine", "Demand / Demande", "Objective"],
        [[r[k] for k in ("service", "replica", "host", "failure_domain", "demand", "objective_cost")] for r in plan],
    )
    host_table = _table(
        ["Host / Hôte", "Failure domain / Domaine", "Capacity / Capacité", "Load / Charge", "Remaining / Disponible"],
        [
            ["—" if r[k] is None else r[k] for k in ("host", "failure_domain", "capacity", "load", "remaining")]
            for r in hosts
        ],
    )
    style = """
    :root{color-scheme:light;font-family:ui-sans-serif,system-ui,sans-serif;color:#12243b;background:#f4f1eb}
    *{box-sizing:border-box}body{margin:0}a{color:#005a71;text-underline-offset:.2em}a:focus-visible{outline:3px solid #be6100}
    .skip{position:absolute;left:-10000px}.skip:focus{left:1rem;top:1rem;background:white;padding:1rem;z-index:3}
    nav{display:flex;gap:1.3rem;justify-content:space-between;align-items:center;padding:1.2rem max(5vw,1rem);flex-wrap:wrap}
    nav strong{font-size:.8rem;letter-spacing:.14em}nav div{display:flex;gap:1rem}main{max-width:1140px;margin:auto;padding:1rem}
    .hero{background:#12243b;color:#fff;border-radius:24px;padding:clamp(1.5rem,5vw,4rem);margin-bottom:1.5rem}
    .eyebrow{letter-spacing:.12em;font-size:.78rem;color:#a0ded8;text-transform:uppercase}.hero h1{font-size:clamp(2rem,5vw,3.7rem);
    line-height:1.08;max-width:850px;margin:.6rem 0 1.1rem}.hero p{max-width:760px;line-height:1.65}.pill{display:inline-block;
    padding:.5rem .8rem;border:1px solid #79a9ad;border-radius:20px;font-size:.85rem}.stats{display:grid;grid-template-columns:repeat(3,1fr);
    gap:1rem;margin:1.5rem 0}.stat,section,.panel{background:#fff;border:1px solid #d9dedb;border-radius:16px;padding:1.5rem}
    .stat strong{display:block;font-size:1.9rem;overflow-wrap:anywhere}.stat span{font-size:.9rem;color:#405568}
    section{margin:1rem 0;scroll-margin-top:1rem}h2{margin-top:0;font-size:1.55rem}h3{margin-top:1.7rem}p,li{line-height:1.65}
    .notice{border-left:4px solid #ad5b00;background:#fff6e9;padding:1rem;line-height:1.65}.table-wrap{max-width:100%;overflow:auto;
    border:1px solid #dde3df;border-radius:10px}table{border-collapse:collapse;min-width:100%;font-size:.9rem}th,td{text-align:left;
    border-bottom:1px solid #e5e9e5;padding:.8rem;vertical-align:top;overflow-wrap:anywhere}th{background:#eaf2ef;white-space:nowrap}
    .downloads{display:flex;gap:.6rem;flex-wrap:wrap}.downloads a{padding:.7rem 1rem;border:1px solid #005a71;border-radius:9px}
    code{overflow-wrap:anywhere;white-space:normal;font-size:.8rem}footer{padding:2rem 1rem;line-height:1.6;color:#405568;font-size:.85rem}
    @media(max-width:650px){.stats{grid-template-columns:1fr}.hero{border-radius:16px}section{padding:1rem}th,td{padding:.6rem}}
    @media print{nav,.downloads,.skip{display:none}body{background:white}.hero{background:white;color:#12243b;border:1px solid #aaa}
    section,.stat{break-inside:avoid}.table-wrap{overflow:visible}table{font-size:9pt}}
    """
    style_hash = hashlib.sha256(style.encode()).digest()
    csp = (
        "default-src 'none'; style-src 'sha256-"
        + base64.b64encode(style_hash).decode("ascii")
        + "'; base-uri 'none'; form-action 'none'; object-src 'none'"
    )
    status_en = "Exact minimum verified" if optimal else "Infeasibility verified"
    status_fr = "Minimum exact vérifié" if optimal else "Impossibilité vérifiée"
    e = html.escape
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{e(csp, quote=True)}">
<title>{e(brief.brief_id)} — Resilient Placement Decision Pack</title><style>{style}</style></head>
<body><a class="skip" href="#report">Skip to report / Aller au rapport</a>
<nav aria-label="Report navigation"><strong>MONTREAL.AI · AGI ALPHA</strong><div><a href="#english" lang="en">English</a>
<a href="#francais" lang="fr">Français</a><a href="#files">Files / Fichiers</a></div></nav><main id="report">
<header class="hero"><div class="eyebrow">Research delivery · Livraison de recherche</div>
<h1>Place workloads with a plan you can check.</h1><p lang="fr">Répartissez vos services avec un plan vérifiable.</p>
<p>{e(brief.beneficiary)} · <strong>{e(brief.brief_id)}</strong></p>
<span class="pill">{status_en} · {status_fr}</span></header>
<div class="stats"><div class="stat"><strong>{len(brief.services)}</strong><span>Services · Two replicas each / Deux répliques</span></div>
<div class="stat"><strong>{len(brief.hosts)}</strong><span>Named hosts / Hôtes nommés</span></div>
<div class="stat"><strong>{objective}</strong><span>{e(brief.cost_unit)} · Objective / Objectif</span></div></div>
<section id="english" lang="en"><h2>Your decision pack</h2>
<p>This bounded plan assigns two replicas of each service to different declared failure domains, respecting every host capacity.
The independent exhaustive checker verifies the exact minimum objective, or proves that no feasible placement exists within this model.</p>
<p class="notice"><strong>Research acceptance, not customer acceptance.</strong> Packaging independently rechecks the numerical answer in a saved scripted-model
hybrid receipt. Execution authenticity requires the runner’s retained Journal audit. This delivery path performs no infrastructure deployment.
Capacity units, failure domains and costs are supplied assumptions;
this does not verify provider independence, recovery behavior or physical availability. Actual customer collections are USD0;
complete actual delivery and project costs remain unknown.</p>
<h3>Scope and inventory</h3><p>{e(brief.inventory_basis)}</p><p>Input authority: {e(brief.rights_basis)}</p>
<h3>Named placement</h3><p>{"Each row is one replica allocation." if optimal else "No plan is issued: the declared constraints are infeasible."}
Objective values use <strong>{e(brief.cost_unit)}</strong>; they are not the sale price or measured provider profit.</p>{plan_table}
<h3>Capacity reconciliation</h3>{host_table}<h3>Acceptance and correction</h3>
<p>{delivery["verification"]["oracle_assignments"]} candidate assignments were independently enumerated. Acceptance applies only to the
unchanged supplied scope. An incomplete search produces no accepted pack. Input corrections require a new scoped mission;
package defects require correction and a new manifest. Price hypothesis: USD{price_usd}, not an accepted offer or observed willingness to pay.
Any commercial price, turnaround, payment and refund terms require a separate agreed offer.</p>
<p>For production use, validate the inventory, units, provider dependencies, failover behavior and implementation permissions before deployment.
No frontier-performance advantage, market demand or retained Alpha is established.</p></section>
<section id="francais" lang="fr"><h2>Votre dossier de décision</h2>
<p>Ce plan borné affecte deux répliques de chaque service à des domaines de défaillance déclarés distincts, dans les limites de capacité de chaque hôte.
Le vérificateur exhaustif indépendant confirme le minimum exact de l’objectif, ou prouve l’impossibilité dans ce modèle.</p>
<p class="notice"><strong>Acceptation de recherche, sans acceptation client.</strong> Le dossier revérifie indépendamment la réponse numérique d’un reçu
hybride avec modèle scénarisé. L’authenticité de l’exécution exige l’audit du Journal conservé. Ce parcours ne réalise aucun déploiement.
Les capacités, domaines et coûts sont des hypothèses fournies;
ni l’indépendance réelle des fournisseurs ni la reprise physique ne sont validées. Encaissements clients réels : USD0;
coûts réels complets de livraison et du projet : inconnus.</p>
<h3>Périmètre et données</h3><p>{e(brief.inventory_basis)}</p><p>Autorisation des données : {e(brief.rights_basis)}</p>
<h3>Affectations nominatives</h3><p>{"Chaque ligne représente une réplique." if optimal else "Aucun plan n’est émis : les contraintes déclarées sont impossibles."}
L’objectif est exprimé en <strong>{e(brief.cost_unit)}</strong>, sans constituer le prix de vente ni un bénéfice réel.</p>{plan_table}
<h3>Vérification des capacités</h3>{host_table}<h3>Acceptation et correction</h3>
<p>{delivery["verification"]["oracle_assignments"]} affectations candidates ont été énumérées indépendamment.
L’acceptation porte uniquement sur le périmètre fourni inchangé. Une recherche incomplète ne produit aucun dossier accepté.
Toute correction des données exige une nouvelle mission; tout défaut du dossier exige une correction et un nouveau manifeste.
Hypothèse de prix : USD{price_usd}, sans offre acceptée ni volonté de payer observée.
Prix, délais, paiement et remboursement commerciaux doivent être convenus dans une offre distincte.</p>
<p>Avant tout usage en production, validez données, unités, dépendances fournisseurs, reprise et autorisations de déploiement.
Aucun avantage de modèle de pointe, demande commerciale ou Alpha conservé n’est établi.</p></section>
<section id="files"><h2>Inspect and reproduce / Examiner et reproduire</h2><div class="downloads">
<a href="plan.csv" download>Plan CSV</a><a href="delivery.json" download>Decision JSON</a>
<a href="brief.json" download>Brief / Mandat</a><a href="execution.json" download>Execution evidence</a>
<a href="manifest.json" download>SHA-256 manifest</a></div>
<p>Brief commitment / Engagement : <code>{delivery["brief_digest"]}</code></p>
<p>Artifact commitment / Artefact : <code>{delivery["artifact_digest"]}</code></p>
<p>Packaging checks imported receipt consistency; it does not authenticate an imported Journal.
The retained runner Journal provides the separate execution audit path.</p></section>
<footer>Vincent Boucher — President of MONTREAL.AI · Conceptual research prototype; AGI describes a research objective.
No financial return or transaction is asserted. / Prototype de recherche conceptuel; aucun rendement ni transaction n’est affirmé.</footer>
</main></body></html>"""


def render_pack(raw_brief: dict[str, Any], execution: dict[str, Any], output: Path) -> dict[str, Any]:
    """Create an immutable customer-readable pack, refusing overwritten outputs."""
    brief = parse_brief(raw_brief)
    checked = checked_delivery(brief, execution)
    plan, hosts = _plan(brief, checked["outcome"])
    delivery = {
        "schema_name": "resilient-placement-delivery/v1",
        "brief_id": brief.brief_id,
        "brief_digest": digest("commercial-placement-brief", brief.model_dump()),
        **checked,
        "plan": plan,
        "hosts": hosts,
        "acceptance_kind": "independent-finite-research-acceptance",
        "actual_customer_acceptance": False,
        "actual_customer_collections_micro_usd": 0,
        "actual_complete_cost_micro_usd": None,
        "model": "scripted-protocol-fixture/v1",
        "price_hypothesis_micro_usd": brief.price_micro_usd,
        "price_basis": "Hypothesis only; not an accepted commercial offer or customer willingness to pay",
        "deployment_performed": False,
        "receipt_authentication": "runner journal audit required; pack checks content consistency only",
    }
    csv_file = io.StringIO(newline="")
    writer = csv.writer(csv_file)
    writer.writerow(["service", "replica", "host", "failure_domain", "demand", "objective_cost", "cost_unit"])
    for row in plan:
        writer.writerow(
            [
                _cell(row[name])
                for name in ("service", "replica", "host", "failure_domain", "demand", "objective_cost", "cost_unit")
            ]
        )
    files = {
        "brief.json": _json(brief.model_dump()),
        "execution.json": _json(execution),
        "delivery.json": _json(delivery),
        "plan.csv": csv_file.getvalue(),
        "index.html": _page(brief, delivery),
    }
    manifest = {
        "schema_name": "resilient-placement-pack/v1",
        "brief_digest": delivery["brief_digest"],
        "files": {
            name: {"sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(), "bytes": len(value.encode("utf-8"))}
            for name, value in sorted(files.items())
        },
        "manifest_scope": "All five delivered files; manifest excludes itself",
    }
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("choose a new delivery directory; preserve earlier packs")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("Incomplete delivery; do not accept without a complete verified manifest.\n", encoding="utf-8")
    for name, value in {**files, "manifest.json": _json(manifest)}.items():
        with (output / name).open("x", encoding="utf-8", newline="") as target:
            target.write(value)
    marker.unlink()
    return {"path": str(output), "delivery": delivery, "manifest": manifest}
