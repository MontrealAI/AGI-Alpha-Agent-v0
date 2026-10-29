# SPDX-License-Identifier: Apache-2.0
"""Source-bound objections for the installed dimensional-screening grammar.

Only inert source spans and syntactic proof obligations are inspected here.
No candidate program, document instruction, or model-provided test is run.
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from ..structural_transfer.contracts import bounded, digest, exact_keys, text
from . import specification as spec
from .evidence_contracts import CriticFinding, Experiment, Objection, SourceLocation

SCHEMA = "agialpha/critic-context/v1"
SOURCE_LABELS = {
    ("high_side_voltage", "voltage"): frozenset(("high-side voltage", "high side voltage")),
    ("voltage", "voltage"): frozenset(("voltage", "high-side voltage", "high side voltage")),
    ("rated_power", "apparent_power"): frozenset(("rated power", "rated apparent power")),
    ("power", "apparent_power"): frozenset(("rated power", "apparent power", "rated apparent power")),
    ("apparent_power", "apparent_power"): frozenset(("apparent power", "rated apparent power")),
    ("frequency", "frequency"): frozenset(("frequency", "rated frequency")),
}
POSITIVE_LITERAL = (
    r"[ \t]*(?:(?:[:=][ \t]*)|(?:(?:is|of|requirement)[ \t]+))?"
    r"(?:(?:less[ \t]+than|greater[ \t]+than|at[ \t]+most|at[ \t]+least)[ \t]+)?"
    r"([0-9]+(?:\.[0-9]+)?)[ \t]*([A-Za-z]+)(?![\w])"
)


def validate_context(request: dict[str, Any], context: dict[str, Any]) -> None:
    spec.validate_request(request)
    bounded(context)
    exact_keys(context, {"schema", "requirements", "sources", "bindings"})
    if context["schema"] != SCHEMA or set(context["requirements"]) != set(request["requirements"]):
        raise ValueError("context must bind the complete declared task")
    for field, item in context["requirements"].items():
        exact_keys(item, {"dimension", "authority", "labels", "location"})
        if item["authority"] != "declared-task" or item["dimension"] != request["requirements"][field]:
            raise ValueError("source documents cannot change task authority")
        text(item["location"])
        if type(item["labels"]) is not list or not 1 <= len(item["labels"]) <= 4:
            raise ValueError("bounded registered field labels required")
        for label in item["labels"]:
            text(label, 80)
            if label.casefold() not in SOURCE_LABELS.get((field, item["dimension"]), frozenset()):
                raise ValueError("source field label has no declared extraction semantics")
    if type(context["sources"]) is not list or len(context["sources"]) != len(request["sources"]):
        raise ValueError("complete retrieval provenance required")
    sources = {s["id"]: s for s in request["sources"]}
    seen = set()
    for source in context["sources"]:
        exact_keys(source, {"id", "sha256", "version", "retrieved_utc", "method", "url"})
        if source["id"] in seen or source["id"] not in sources:
            raise ValueError("duplicate or unknown source provenance")
        seen.add(source["id"])
        original = sources[source["id"]]
        if source["sha256"] != original["sha256"] or source["url"] != original["url"]:
            raise ValueError("source identity mismatch")
        for key in ["version", "retrieved_utc", "method"]:
            text(source[key])
    if type(context["bindings"]) is not list or len(context["bindings"]) > 384:
        raise ValueError("bounded source association list required")
    records = {r["id"]: r for r in request["records"]}
    seen_bindings = set()
    for link in context["bindings"]:
        exact_keys(link, {"record_id", "field", "source_id", "start", "end"})
        identity = (link["record_id"], link["field"])
        if identity in seen_bindings or link["record_id"] not in records:
            raise ValueError("duplicate or unknown source association")
        seen_bindings.add(identity)
        record = records[link["record_id"]]
        if link["field"] not in record["fields"] or link["source_id"] != record["source_id"]:
            raise ValueError("source association record mismatch")
        excerpt = sources[link["source_id"]]["excerpt"]
        if any(type(link[k]) is not int for k in ["start", "end"]) or not 0 <= link["start"] < link["end"] <= len(
            excerpt
        ):
            raise ValueError("exact bounded character span required")


def bound_literal(request: dict[str, Any], context: dict[str, Any], link: dict[str, Any]) -> tuple[bool, str]:
    record = next(r for r in request["records"] if r["id"] == link["record_id"])
    source = next(s for s in request["sources"] if s["id"] == link["source_id"])
    field = link["field"]
    span = source["excerpt"][link["start"] : link["end"]]
    if any(separator in span for separator in [";", "\n", "\r"]):
        return False, "span crosses a clause boundary"
    labels = context["requirements"][field]["labels"]
    supported = SOURCE_LABELS.get((field, request["requirements"][field]), frozenset())
    if any(type(label) is not str or label.casefold() not in supported for label in labels):
        return False, "source field label has no declared extraction semantics"
    matches = [
        match
        for label in labels
        for match in re.finditer(r"(?<![\w])" + re.escape(label) + r"(?![\w])", span, re.IGNORECASE)
    ]
    if len(matches) != 1:
        return False, "source span lacks one unambiguous registered field label"
    if span[: matches[0].start()].strip():
        return False, "source span lacks an anchored positive field assertion"
    preceding = source["excerpt"][: link["start"] + matches[0].start()]
    if re.search(r"(?:\A|[;.!?\r\n])[ \t]*\Z", preceding) is None:
        return False, "source span is not attributable after clipping its clause prefix"
    tail = span[matches[0].end() :]
    for other, item in context["requirements"].items():
        if other != field and any(re.search(re.escape(label), tail, re.IGNORECASE) for label in item["labels"]):
            return False, "another field intervenes before the quantity"
    literal = re.match(POSITIVE_LITERAL, tail, re.IGNORECASE)
    reading = record["fields"][field]
    if (
        literal is None
        or literal.group(2) != reading["unit"]
        or Fraction(literal.group(1)) != Fraction(reading["value"])
    ):
        return False, "positive source bridge or its exact quantity/unit does not match the record"
    return True, "anchored registered field and positive lexical bridge bind the literal quantity/unit"


def investigate(request: dict[str, Any], context: dict[str, Any], provenance: dict[str, Any]) -> CriticFinding:
    validate_context(request, context)
    candidate_hash = digest(request["baseline"])
    limits = [
        "One exposed source provenance unit; synthetic neighbors are engineering controls.",
        "Only frozen lexical field association and syntactic dimensional dominance are investigated.",
        "No candidate execution, engineering suitability, physical harm or economic effect is established.",
    ]
    try:
        spec.dominance(request["baseline"], request["requirements"], request["budget"])
    except ValueError as error:
        if str(error) != "unguarded CONSISTENT path":
            return CriticFinding(
                candidate_hash,
                (),
                "No supported consequential objection; candidate proof is unresolved.",
                (*limits, "Inconclusive structural proof: " + str(error)),
                provenance,
            )
    else:
        return CriticFinding(
            candidate_hash,
            (),
            "No dimensional guard defect established within the declared static search.",
            tuple(limits),
            provenance,
        )
    links = {(b["record_id"], b["field"]): b for b in context["bindings"]}
    objections = []
    for record in request["records"]:
        for field, reading in record["fields"].items():
            if spec.UNITS.get(reading["unit"]) == request["requirements"][field]:
                continue
            link = links.get((record["id"], field))
            if link is None:
                limits.append("Unbound annotation excluded: " + record["id"] + "/" + field)
                continue
            valid, reason = bound_literal(request, context, link)
            if not valid:
                limits.append("Source association unresolved: " + record["id"] + "/" + field + ": " + reason)
                continue
            index, source = next((i, s) for i, s in enumerate(request["sources"]) if s["id"] == link["source_id"])
            witness = {**link, "value": reading["value"], "unit": reading["unit"]}
            ident = "dimension-" + digest(witness)[:16]
            experiment = Experiment(
                "test-" + ident,
                "static-dimension-dominance",
                "This source-bound mismatch has an unguarded CONSISTENT path under the declared dimensional contract.",
                "Exact source association and independent missing dimensional dominance are both reproduced.",
                "Association is contradicted or every CONSISTENT path is guarded; retract this objection.",
                ("Runtime outputs and actual downstream harm remain untested.",),
                {"cpu_ns": "UNKNOWN", "wall_ns": "UNKNOWN", "external_cash_paid": 0},
            )
            objections.append(
                Objection(
                    ident,
                    candidate_hash,
                    "dimensional-source-admission",
                    field,
                    "CONSISTENT requires an observed field of dimension " + request["requirements"][field] + ".",
                    SourceLocation(
                        source["id"], f"/sources/{index}/excerpt#chars={link['start']}:{link['end']}", source["sha256"]
                    ),
                    witness,
                    "Incompatible dimension can pass this static specification screen.",
                    "The source-associated annotation violates the required dimension and acceptance lacks a dominating guard.",
                    experiment,
                    (
                        "A field/span mismatch refutes source association.",
                        "A guarded candidate refutes the alleged acceptance-path defect.",
                    ),
                    "The transcript may contain a typo. Intended replacement, spoken wording and operational harm are unknown.",
                    (
                        "Source typo or extraction error; no silent relabeling is authorized.",
                        "Screening may be only one component of a stronger workflow.",
                    ),
                    (
                        "Docker-isolated dynamic paired execution",
                        "Admitted operating cohort and complete cost evidence",
                    ),
                    provenance,
                    2,
                    3,
                )
            )
    objections.sort(key=lambda o: (-o.evidence_strength, -o.severity, o.id))
    return CriticFinding(
        candidate_hash,
        tuple(objections),
        None if objections else "No supported consequential source-bound objection emerged.",
        tuple(limits),
        provenance,
    )
