from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
from statistics import median

COUNTED_STATUSES = {"operator_attested", "source_verifiable", "third_party_verified"}
VERIFIED_STATUSES = {"source_verifiable", "third_party_verified"}
REQUIRED_SCALE_CATEGORIES = {
    "product", "usage", "customer_discovery", "design_partner", "pilot",
    "benchmark", "commercial", "independent_validation", "fair_value_support", "governance",
}

@dataclass(frozen=True)
class EvidenceSummary:
    total_items: int
    counted_items: int
    verified_items: int
    placeholder_items: int
    categories_present: list[str]
    required_categories_missing: list[str]
    public_scale_claim_allowed: bool
    state: str


def load_json_files(root: Path, patterns: list[str]) -> list[dict]:
    items: list[dict] = []
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                item = json.loads(path.read_text(encoding="utf-8"))
                item["_path"] = path.relative_to(root).as_posix()
                items.append(item)
    return items


def summarize_evidence(items: list[dict]) -> EvidenceSummary:
    counted = [i for i in items if i.get("evidence_status") in COUNTED_STATUSES]
    verified = [i for i in items if i.get("evidence_status") in VERIFIED_STATUSES]
    placeholders = [i for i in items if i.get("evidence_status") == "example_placeholder"]
    categories = sorted({i.get("category") for i in verified if i.get("category")})
    missing = sorted(REQUIRED_SCALE_CATEGORIES - set(categories))
    fair_value_verified = "fair_value_support" in categories
    independent_verified = "independent_validation" in categories
    commercial_verified = "commercial" in categories
    public_allowed = not missing and fair_value_verified and independent_verified and commercial_verified
    if public_allowed:
        state = "strategic_scale_evidence_candidate"
    elif len(categories) >= 5 and independent_verified:
        state = "validated_evidence_candidate"
    elif counted:
        state = "emerging_evidence_operator_attested"
    else:
        state = "infrastructure_ready_market_evidence_pending"
    return EvidenceSummary(
        total_items=len(items), counted_items=len(counted), verified_items=len(verified),
        placeholder_items=len(placeholders), categories_present=categories,
        required_categories_missing=missing, public_scale_claim_allowed=public_allowed, state=state,
    )


def proof_velocity(events: list[dict]) -> dict:
    counted = [e for e in events if e.get("evidence_status") in COUNTED_STATUSES]
    hours_to_docket = []
    hours_to_validation = []
    reuse = 0
    for item in counted:
        metrics = item.get("metrics", {})
        if metrics.get("capability_reused"):
            reuse += 1
        start = metrics.get("mission_started_at")
        docket = metrics.get("evidence_docket_created_at")
        validation = metrics.get("validator_report_created_at")
        try:
            if start and docket:
                hours_to_docket.append((datetime.fromisoformat(docket) - datetime.fromisoformat(start)).total_seconds()/3600)
            if docket and validation:
                hours_to_validation.append((datetime.fromisoformat(validation) - datetime.fromisoformat(docket)).total_seconds()/3600)
        except Exception:
            continue
    return {
        "counted_events": len(counted),
        "capability_reuse_events": reuse,
        "median_hours_to_docket": median(hours_to_docket) if hours_to_docket else None,
        "median_hours_to_validation": median(hours_to_validation) if hours_to_validation else None,
    }
