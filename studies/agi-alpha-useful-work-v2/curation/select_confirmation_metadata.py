# SPDX-License-Identifier: Apache-2.0
"""Select historical versions from metadata before reading candidate bodies."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
from pip._vendor.packaging.markers import default_environment
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "discovery/release-metadata"
CUTOFF = "2026-10-26T14:33:37Z"
BASELINE = {"starlette": "1.7.0", "pydantic": "2.13.5"}
EXPOSED = {
    "starlette": {
        "0.36.3": "v1 exact source and executed historical integration wheel",
        "0.37.2": "v1 executed known-remedy integration wheel",
    },
    "pydantic": {"2.14.1": "v1 native import/runtime and bundled wheel; also proposed development version"},
}
SUPPORT = {"anyio": "4.15.1", "annotated-types": "0.8.0", "typing-extensions": "4.16.0",
           "typing-inspection": "0.4.4"}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load(name: str) -> dict:
    return json.loads((META / name).read_text())


def active_requirements(info: dict) -> list[Requirement]:
    env = default_environment()
    env.update(python_version="3.12", python_full_version="3.12.14", platform_system="Linux",
               sys_platform="linux", platform_machine="x86_64", extra="")
    return [r for text in info.get("requires_dist", []) if (r := Requirement(text)).marker is None or r.marker.evaluate(env)]


def main() -> None:
    out = ROOT / "discovery/confirmation-metadata-v1.json"
    if out.exists():
        raise ValueError("SELECTION_ALREADY_RECORDED")
    cutoff = datetime.datetime.fromisoformat(CUTOFF.replace("Z", "+00:00"))
    projects = {name: load(name + "-project.json") for name in BASELINE}
    latest = {name: data["info"]["version"] for name, data in projects.items()}
    constraints = {"starlette": [], "pydantic": [Requirement("pydantic>=2.11,<3")]}
    for filename in ("fastapi-0.141.1.json", "pydantic-settings-2.15.0.json"):
        for requirement in active_requirements(load(filename)["info"]):
            if requirement.name in constraints:
                constraints[requirement.name].append(requirement)
    audit, selected, versions = [], {}, {}
    for name, data in projects.items():
        eligible = []
        for version, files in data["releases"].items():
            reasons = []
            try:
                parsed = Version(version)
            except InvalidVersion:
                audit.append({"package": name, "version": version, "eligible": False, "reasons": ["invalid_pep440"]})
                continue
            if parsed.is_prerelease or parsed.is_devrelease:
                reasons.append("prerelease_or_dev")
            if parsed.major != {"starlette": 1, "pydantic": 2}[name]:
                reasons.append("outside_declared_primary_major")
            if not files:
                reasons.append("no_published_files")
            usable = []
            for f in files:
                if not f["upload_time_iso_8601"]:
                    continue
                when = datetime.datetime.fromisoformat(f["upload_time_iso_8601"].replace("Z", "+00:00"))
                if (not f["yanked"] and f["packagetype"] == "bdist_wheel" and when <= cutoff
                        and (not f["requires_python"] or "3.12.14" in SpecifierSet(f["requires_python"]))):
                    usable.append(f)
            if not usable:
                reasons.append("no_non_yanked_python312_wheel_before_cutoff")
            if any(parsed not in requirement.specifier for requirement in constraints[name]):
                reasons.append("outside_current_profile_dependency_constraints")
            if version in EXPOSED[name]:
                reasons.append("v1_source_or_runtime_exposure")
            if version == BASELINE[name]:
                reasons.append("development_incumbent_version")
            if version == latest[name]:
                reasons.append("development_proposed_latest_version")
            row = {"package": name, "version": version, "eligible": not reasons, "reasons": reasons,
                   "first_file_upload": min((f["upload_time_iso_8601"] for f in files), default=None),
                   "source_or_runtime_exposure": EXPOSED[name].get(version), "eligible_wheel_files": len(usable)}
            audit.append(row)
            if not reasons:
                eligible.append(version)
        chosen = sorted(eligible, key=Version, reverse=True)[:4]
        if len(chosen) != 4:
            raise ValueError("INSUFFICIENT_ELIGIBLE_VERSIONS")
        selected[name] = sorted(chosen, key=Version)
        for version in [BASELINE[name], latest[name], *selected[name]]:
            metadata = data if version == latest[name] else load(name + "-" + version + ".json")
            info = metadata["info"]
            if info["version"] != version or (info["requires_python"] and "3.12.14" not in SpecifierSet(info["requires_python"])):
                raise ValueError("VERSION_OR_PYTHON_METADATA")
            if any(Version(version) not in requirement.specifier for requirement in constraints[name]):
                raise ValueError("PROFILE_CONSTRAINT_MISMATCH")
            dependencies = []
            core = None
            for requirement in active_requirements(info):
                key = requirement.name.lower().replace("_", "-")
                if key == "pydantic-core":
                    pins = [s.version for s in requirement.specifier if s.operator == "=="]
                    if len(pins) != 1:
                        raise ValueError("CORE_EXACT_PIN_REQUIRED")
                    core = pins[0]
                    dependencies.append({"requirement": str(requirement), "resolved_version": core, "kind": "required_coupled_change"})
                elif key in SUPPORT and Version(SUPPORT[key]) in requirement.specifier:
                    dependencies.append({"requirement": str(requirement), "resolved_version": SUPPORT[key], "kind": "unchanged_native_support_version"})
                else:
                    raise ValueError("UNACCOUNTED_DIRECT_COMPONENT_DEPENDENCY: " + str(requirement))
            wheels = [f for f in metadata["urls"] if not f["yanked"] and f["packagetype"] == "bdist_wheel"
                      and f["filename"].endswith("-py3-none-any.whl")
                      and datetime.datetime.fromisoformat(f["upload_time_iso_8601"].replace("Z", "+00:00")) <= cutoff]
            if len(wheels) != 1:
                raise ValueError("UNAMBIGUOUS_PRIMARY_WHEEL_REQUIRED")
            versions[name + "==" + version] = {"package": name, "version": version,
                "metadata_url": metadata["source_url"], "raw_metadata_sha256": metadata["raw_metadata_sha256"],
                "requires_python": info["requires_python"], "requires_dist": info["requires_dist"],
                "active_direct_dependencies": dependencies, "pydantic_core": core, "wheel": wheels[0],
                "wheel_downloaded": False, "source_body_read": False, "outcome_seen": False}
    missions = []
    for package, ordered in selected.items():
        fixed = "pydantic" if package == "starlette" else "starlette"
        for index, (before, after) in enumerate(zip(ordered, ordered[1:]), 1):
            missions.append({"id": f"{package}-{index}", "cluster": package,
                             "before_version": before, "after_version": after,
                             "unchanged_other_component": {fixed: BASELINE[fixed]},
                             "trigger": "Changed released dependency version and exact wheel identity",
                             "role": "Representative historical compatibility assessment; not a paid order or actual prior Alpha adoption",
                             "adjacency": "Adjacent among eligible unexposed versions; exclusions can skip intervening releases"})
    identities = {p.name: {"sha256": sha(p.read_bytes()), "bytes": p.stat().st_size}
                  for p in sorted(META.glob("*.json"))}
    result = {"schema": "useful-work-v2-confirmation-metadata/v1", "cutoff_utc": CUTOFF,
              "selection_rule": "For each primary major, select the latest four stable PEP440 versions satisfying current-profile metadata and Python3.12 wheel availability before cutoff, after excluding all known v1 source/runtime and development versions. Compare chronological eligible neighbors.",
              "selection_made_without_candidate_source_or_outcomes": True,
              "consumer_commit": "eb07086ac42799ff45f7b1c946a2f7c514bd3bbc",
              "current_profile_reread_commit": "804e1afeb78ea48fb4807d76b336803aa0906a20",
              "native_lock_git_blob": "d450350998018b691f04fa99093d2fef68b929f0",
              "development": {"incumbent": BASELINE, "proposed_latest": latest,
                              "role": "One concrete internal native-profile refresh question, not paid demand"},
              "incoming_constraints": {name: [str(x) for x in req] for name, req in constraints.items()},
              "unchanged_support_versions": SUPPORT, "exposure_ledger": EXPOSED,
              "exposure_evidence": ["Prior companion deps/native-versions.json and deps/wheels", "Prior companion data/development/integration-example/wheels and executed three-pair replay", "Development incumbent and proposed versions excluded by design"],
              "selected_versions_ascending": selected, "primary_mission_count": len(missions), "package_clusters": 2,
              "missions": missions, "version_records": versions, "all_release_eligibility_records": audit,
              "metadata_artifact_identities": identities,
              "limitations": ["Public historical releases may have model pretraining exposure; held out only from this study's source/runtime inspection.",
                              "Common support dependencies and unchanged consumer source are legitimate reused inputs, not claimed fresh code.",
                              "Metadata compatibility is not a successful installation or behavior result; full closure and execution follow the protocol freeze.",
                              "Historical recurrence is representative; no actual customer recurrence, demand or orders are asserted.",
                              "Development and primary versions never count as extra missions merely because of repeated cases or evaluations."],
              "wheel_or_source_body_downloads": 0, "execution_outcomes_observed": 0}
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"path": str(out), "sha256": sha(out.read_bytes()), "bytes": out.stat().st_size,
                      "selected": selected, "missions": len(missions), "development": result["development"]}))


if __name__ == "__main__":
    main()
