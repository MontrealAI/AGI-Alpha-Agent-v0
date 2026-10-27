# SPDX-License-Identifier: Apache-2.0
import argparse, ast, contextlib, hashlib, importlib.util, importlib.metadata, io, json, os, platform, socket, time, traceback
from pathlib import Path


def convert(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    return str(value)


def run(path, output, checks=None, case=None):
    raw = path.read_bytes()
    doc = json.loads(raw)
    os.environ["MPLBACKEND"] = "Agg"
    import numpy as np
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    np.random.seed(20261027)
    ns = {"__name__": "__capsule__"}
    rows, denied, figs = [], [], []
    output.parent.mkdir(parents=True, exist_ok=True)

    def no_network(self, address):
        denied.append(str(address))
        raise RuntimeError("Network access is outside the offline capsule contract")

    old, old_ex = socket.socket.connect, socket.socket.connect_ex
    socket.socket.connect = no_network
    socket.socket.connect_ex = no_network
    started = time.perf_counter()
    for index, cell in enumerate(doc["cells"]):
        code = "".join(cell["source"])
        if cell["cell_type"] != "code" or not code.strip():
            continue
        stdout, stderr = io.StringIO(), io.StringIO()
        error, value, cell_figs = None, None, []
        t = time.perf_counter()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = code.replace("%matplotlib inline", "import matplotlib; matplotlib.use('Agg')")
                tree = ast.parse(code)
                last = tree.body[-1] if tree.body else None
                if isinstance(last, ast.Expr):
                    tree.body = tree.body[:-1]
                    exec(compile(tree, str(path), "exec"), ns)
                    value = eval(compile(ast.Expression(last.value), str(path), "eval"), ns)
                    if value is not None:
                        print(repr(value))
                        if hasattr(value, "_repr_html_"):
                            value._repr_html_()
                else:
                    exec(compile(tree, str(path), "exec"), ns)
                for num in plt.get_fignums():
                    fp = output.parent / (output.stem + f"-cell-{index:03d}-figure-{num}.png")
                    plt.figure(num).savefig(fp, dpi=120, bbox_inches="tight")
                    cell_figs.append(fp.name)
                    figs.append(fp.name)
                plt.close("all")
        except Exception as exc:
            error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        rows.append(
            {
                "cell": index,
                "upstream_cell_index": cell["metadata"].get("upstream_cell_index"),
                "source_sha256": hashlib.sha256("".join(cell["source"]).encode()).hexdigest(),
                "status": "error" if error else "executed",
                "elapsed_seconds": time.perf_counter() - t,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                "error": error,
                "figures": cell_figs,
            }
        )
        if error:
            break
    numerical = []
    if checks and not any(row["error"] for row in rows):
        try:
            spec = importlib.util.spec_from_file_location("checks", checks)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            numerical = mod.check(case or path.parent.name, ns)
        except Exception as exc:
            numerical = [{"name": "checker", "pass": False, "error": str(exc)}]
    socket.socket.connect, socket.socket.connect_ex = old, old_ex
    output.parent.mkdir(parents=True, exist_ok=True)
    versions = {"python": platform.python_version()}
    for package in ["numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "seaborn", "ipython"]:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    count = sum(c["cell_type"] == "code" and bool("".join(c["source"]).strip()) for c in doc["cells"])
    completed = sum(row["status"] == "executed" for row in rows)
    report = {
        "schema": "capsule-execution/v1",
        "case": case or path.stem,
        "path": str(path),
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "expected_cells": count,
        "completed_cells": completed,
        "all_cells_completed": completed == count,
        "checks": numerical,
        "accepted": completed == count and not denied and bool(numerical) and all(x["pass"] for x in numerical),
        "network_attempts": denied,
        "versions": versions,
        "elapsed_seconds": time.perf_counter() - started,
        "cells": rows,
        "figures": figs,
        "cost": {
            "provider_bill": None,
            "actual_total_usd": None,
            "status": "unknown; elapsed execution excludes model deliberation and acquisition",
        },
    }
    output.write_text(json.dumps(report, indent=2, default=convert) + "\n")
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "case",
                    "completed_cells",
                    "expected_cells",
                    "all_cells_completed",
                    "accepted",
                    "elapsed_seconds",
                ]
            }
        )
    )
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("notebook", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--checks", type=Path)
    ap.add_argument("--case")
    a = ap.parse_args()
    r = run(a.notebook, a.output, a.checks, a.case)
    raise SystemExit(0 if r["all_cells_completed"] and (not a.checks or r["accepted"]) else 1)
