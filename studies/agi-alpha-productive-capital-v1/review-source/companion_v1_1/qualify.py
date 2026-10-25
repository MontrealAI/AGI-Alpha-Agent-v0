# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy, hashlib, json, random, resource, shutil, subprocess, time
from pathlib import Path
from check import check

ROOT = Path(__file__).resolve().parents[1]


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def call(request):
    start = time.perf_counter()
    p = subprocess.run(
        [shutil.which("node"), str(ROOT / "companion_v1_1/cli.mjs")],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        timeout=30,
    )
    r = json.loads(p.stdout)
    r["whole_process_wall_ms"] = (time.perf_counter() - start) * 1000
    return r


def qualify(development=False):
    target = ROOT / "outputs" / ("correction-development" if development else "correction-confirmation")
    if target.exists() and not development:
        raise SystemExit("CORRECTIVE_CONFIRMATION_ALREADY_EXISTS")
    target.mkdir(exist_ok=True)
    seed = 919 if development else 202610252919
    rng = random.Random(seed)
    frozen = ROOT / "protocol/experiment-v11-FREEZE.json"
    binding = hashlib.sha256(frozen.read_bytes()).hexdigest() if frozen.exists() else "0" * 64
    base = json.loads((ROOT / "data/development.json").read_text())
    base["id"] = "CORRECTION-DEV" if development else "CORRECTION-HELDOUT-" + str(rng.randrange(100000, 999999))
    base["task"]["id"] = base["id"]
    base["title"] = "Release evidence correction qualification"
    for j in base["task"]["jobs"]:
        j["duration"] = rng.randrange(1, 5)
    dump(target / "base-input.json", base)
    rows = []
    for arm in ["full_rebuild", "flywheel", "conventional_cache"]:
        initial = call({"project": base, "options": {"arm": arm, "sourceHash": binding}})
        dump(target / f"{arm}-initial.json", initial)
        if not initial["ok"]:
            raise RuntimeError(initial)
        previous = initial["result"]["state"]
        initial_check = check(base, initial["result"])
        rows.append({"case": "initial", "arm": arm, **initial_check})
        for kind in [
            "path-only",
            "source-url-only",
            "original-digest-only",
            "remove-leaf",
            "remove-parent",
            "fresh-content",
            "changed-provenance-and-dependency",
        ]:
            p = copy.deepcopy(base)
            p["cycle"] = 2
            p["task"]["id"] = base["task"]["id"] + "-changed"
            suffix = str(rng.randrange(100000, 999999))
            if kind == "path-only":
                p["components"][0]["path"] = "renamed/" + suffix + "/" + p["components"][0]["path"]
            elif kind == "source-url-only":
                p["components"][0]["source_url"] += "?revision=" + suffix
            elif kind == "original-digest-only":
                p["components"][0]["source_sha256"] = hashlib.sha256(suffix.encode()).hexdigest()
            elif kind == "remove-leaf":
                p["components"].pop()
            elif kind == "remove-parent":
                removed = p["components"].pop(1)["id"]
                for c in p["components"]:
                    c["deps"] = [d for d in c["deps"] if d != removed]
            elif kind == "fresh-content":
                p["components"][0]["content"] += "\n// independently generated confirmation mutation " + suffix + "\n"
            else:
                p["components"][-1]["source_url"] += "?revision=" + suffix
                p["components"][-1]["deps"] = []
            construct = call({"operation": "construct", "project": p, "previous": previous})
            child = construct["result"]["child"]
            r = call(
                {
                    "project": p,
                    "options": {
                        "arm": arm,
                        "previous": previous,
                        "child": child if arm == "flywheel" else None,
                        "sourceHash": binding,
                    },
                }
            )
            receipt = (
                check(p, r["result"], previous)
                if r["ok"]
                else {"accepted": False, "checks": 0, "failures": [r["error"]]}
            )
            name = f"{arm}-{kind}"
            dump(target / (name + "-input.json"), p)
            dump(target / (name + "-construction.json"), construct)
            dump(target / (name + "-execution.json"), r)
            dump(target / (name + "-acceptance.json"), receipt)
            rows.append({"case": kind, "arm": arm, **receipt})
            if arm == "flywheel" and kind == "fresh-content":
                nextp = copy.deepcopy(p)
                nextp["cycle"] = 3
                nextp["components"][-1]["path"] = "next/" + suffix + "/" + nextp["components"][-1]["path"]
                continued = call(
                    {
                        "project": nextp,
                        "options": {
                            "arm": arm,
                            "previous": r["result"]["state"],
                            "child": child,
                            "sourceHash": binding,
                        },
                    }
                )
                continued_check = (
                    check(nextp, continued["result"], r["result"]["state"])
                    if continued["ok"]
                    else {"accepted": False, "checks": 0, "failures": [continued["error"]]}
                )
                dump(
                    target / "child-second-use.json",
                    {"input": nextp, "execution": continued, "acceptance": continued_check},
                )
                rows.append({"case": "child-second-use", "arm": arm, **continued_check})
        if arm == "flywheel":
            x = copy.deepcopy(base)
            x["id"] = "UNRELATED-" + str(rng.randrange(1000, 9999))
            x["cycle"] = 2
            a = call({"project": x, "options": {"arm": arm, "previous": previous, "sourceHash": binding}})
            rows.append(
                {
                    "case": "cross-project-parent-refusal",
                    "arm": arm,
                    "accepted": not a["ok"] and a.get("error") == "PARENT_PROJECT_BINDING",
                    "error": a.get("error"),
                    "checks": 1,
                }
            )
            dump(target / "cross-project-parent.json", a)
            wrong = call({"operation": "construct", "project": x})
            targetp = copy.deepcopy(base)
            targetp["cycle"] = 2
            b = call(
                {
                    "project": targetp,
                    "options": {
                        "arm": arm,
                        "previous": previous,
                        "child": wrong["result"]["child"],
                        "sourceHash": binding,
                    },
                }
            )
            rows.append(
                {
                    "case": "unrelated-child-origin-refusal",
                    "arm": arm,
                    "accepted": not b["ok"] and b.get("error") == "CHILD_ORIGIN_BINDING",
                    "error": b.get("error"),
                    "checks": 1,
                }
            )
            dump(target / "unrelated-child-origin.json", b)
            right = call({"operation": "construct", "project": targetp, "previous": previous})
            bad = copy.deepcopy(right["result"]["child"])
            bad["parent_digest"] = "a" * 64
            c = call(
                {"project": targetp, "options": {"arm": arm, "previous": previous, "child": bad, "sourceHash": binding}}
            )
            rows.append(
                {
                    "case": "tampered-child-refusal",
                    "arm": arm,
                    "accepted": not c["ok"],
                    "error": c.get("error"),
                    "checks": 1,
                }
            )
            dump(target / "tampered-child.json", c)
    report = {
        "schema": "correction-qualification/v1.1",
        "development": development,
        "seed": seed,
        "case_count": len(rows),
        "accepted": sum(r["accepted"] for r in rows),
        "checks": sum(r["checks"] for r in rows),
        "cases": rows,
        "scope": "Corrective engineering confirmation generated after separate v1.1 freeze. Not a fresh replication of primary timing study. Ordinary output and same-custody independent Python oracle; no production authorization.",
    }
    dump(target / "summary.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    import sys

    qualify("--development" in sys.argv)
