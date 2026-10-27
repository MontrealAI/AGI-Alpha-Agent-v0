# SPDX-License-Identifier: Apache-2.0
"""Assemble common public inputs; no instrument or protected answers are copied."""

from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
OPPORTUNITY = HERE.parent


def main() -> None:
    case = HERE / "public_case"
    case.mkdir(exist_ok=True)
    target = case / "sources"
    target.mkdir(exist_ok=True)
    h4 = OPPORTUNITY / "discovery/science/source_checkout/petab_select/test_cases/0009/petab"
    boehm = HERE / "public_sources/boehm/problems/Boehm_JProteomeRes2014/v1"
    for name, source in (("h4", h4), ("boehm", boehm)):
        shutil.copytree(source, target / name, dirs_exist_ok=True)
    shutil.copy2(h4.parent / "model_space.tsv", target / "h4/model_space.tsv")
    shutil.copy2(OPPORTUNITY / "discovery/science/source_checkout/petab_select/LICENSE", target / "H4_LICENSE")
    shutil.copy2(HERE / "public_sources/boehm/LICENSE", target / "BOEHM_LICENSE")
    requests = {
        "packet_version": 1,
        "missions": [
            {"id": "equilibrium", "type": "stationary_qualification", "source": "h4"},
            {
                "id": "unsupported_clock",
                "type": "clock_witness",
                "source": "h4",
                "normalized_time": 1.25,
                "alternative_clock_scales": [0.5, 3.0],
            },
            {
                "id": "calibrated_clock",
                "type": "calibrated_relaxation",
                "source": "h4",
                "calibration": {
                    "evidence_id": "HYPOTHETICAL-CLOCK-01",
                    "evidence_kind": "assumed",
                    "scale_per_physical_unit": [0.4, 1.6],
                    "physical_unit": "minute",
                },
            },
            {
                "id": "new_mission",
                "type": "inheritance_boundary",
                "source": "boehm",
                "inherited_source": "h4",
                "contrast_times": [5.0, 10.0],
            },
        ],
    }
    (case / "requests.json").write_text(json.dumps(requests, indent=2) + "\n")
    manifest = {}
    for path in sorted(target.rglob("*")):
        if path.is_file():
            manifest[str(path.relative_to(case))] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
    (case / "SOURCE_FILES.json").write_text(
        json.dumps(
            {
                "h4_commit": "7b1a1528cee614e72f17eb82338472e7ba91d8de",
                "boehm_commit": "c44d5ede9bf979db5aa8ae4e94fc31fba9776675",
                "files": manifest,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"public_files": len(manifest), "missions": 4, "source_families": 2}))


if __name__ == "__main__":
    main()
