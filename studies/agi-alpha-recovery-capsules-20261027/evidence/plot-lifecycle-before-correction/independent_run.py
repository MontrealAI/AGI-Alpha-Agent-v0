# SPDX-License-Identifier: Apache-2.0
import argparse, contextlib, hashlib, importlib.util, io, json, os, pathlib, socket, sys, time, traceback

def convert(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, pathlib.Path):
        return str(value)
    return repr(value)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("notebook")
    parser.add_argument("--case", required=True)
    parser.add_argument("--checks", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    notebook_path = pathlib.Path(args.notebook).resolve()
    checks_path = pathlib.Path(args.checks).resolve()
    output_path = pathlib.Path(args.output).resolve()
    original_bytes = notebook_path.read_bytes()
    notebook = json.loads(original_bytes)
    os.environ["MPLBACKEND"] = "Agg"
    sys.path.insert(0, str(notebook_path.parent))
    import numpy as np
    np.random.seed(20261027)
    from IPython.core.interactiveshell import InteractiveShell
    shell = InteractiveShell.instance()
    display_errors = []
    original_showtraceback = shell.showtraceback
    def observed_showtraceback(*args, **kwargs):
        error_tuple = args[0] if args and isinstance(args[0], tuple) else sys.exc_info()
        error = error_tuple[1] if len(error_tuple) > 1 else None
        display_errors.append({"type": type(error).__name__, "error": str(error)})
        return original_showtraceback(*args, **kwargs)
    shell.showtraceback = observed_showtraceback
    started = time.perf_counter()
    rows = []
    denied = []

    def reject_network(self, address):
        denied.append(repr(address))
        raise RuntimeError("Independent acceptance forbids outbound runtime sockets")

    old_connect = socket.socket.connect
    old_connect_ex = socket.socket.connect_ex
    socket.socket.connect = reject_network
    socket.socket.connect_ex = reject_network
    try:
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] != "code":
                continue
            source = cell.get("source", "")
            source = "".join(source) if isinstance(source, list) else source
            if not source.strip():
                rows.append({"index": index, "status": "empty", "source_sha256": hashlib.sha256(source.encode()).hexdigest()})
                continue
            stdout, stderr = io.StringIO(), io.StringIO()
            t = time.perf_counter()
            error_count_before = len(display_errors)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = shell.run_cell(source, store_history=False)
            error = result.error_before_exec or result.error_in_exec
            if error is None and len(display_errors) > error_count_before:
                error = RuntimeError("IPython display formatting failed: " + repr(display_errors[error_count_before:]))
            rows.append({
                "index": index, "status": "failed" if error else "executed",
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "elapsed_seconds": time.perf_counter() - t,
                "stdout": stdout.getvalue(), "stderr": stderr.getvalue(),
                "error_type": type(error).__name__ if error else None,
                "error": str(error) if error else None
            })
            if error:
                break
        spec = importlib.util.spec_from_file_location("independent_case_checks", checks_path)
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        numerical = checker.check(args.case, shell.user_ns)
    except Exception as error:
        numerical = [{"name": "checker_execution", "pass": False, "observed": str(error), "traceback": traceback.format_exc()}]
    finally:
        socket.socket.connect = old_connect
        socket.socket.connect_ex = old_connect_ex
    expected_nonempty = sum(c["cell_type"] == "code" and bool(("".join(c.get("source", ""))).strip()) for c in notebook["cells"])
    executed = sum(row["status"] == "executed" for row in rows)
    report = {
        "schema": "independent-notebook-acceptance/v1", "case": args.case,
        "notebook": str(notebook_path), "sha256": hashlib.sha256(original_bytes).hexdigest(),
        "checker_sha256": hashlib.sha256(checks_path.read_bytes()).hexdigest(),
        "nonempty_code_cells": expected_nonempty, "executed_code_cells": executed,
        "all_cells_completed": executed == expected_nonempty,
        "outbound_attempts": denied, "cells": rows, "checks": numerical,
        "display_errors": display_errors,
        "accepted": executed == expected_nonempty and not denied and bool(numerical) and all(row["pass"] for row in numerical),
        "elapsed_seconds": time.perf_counter() - started
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, default=convert) + "\n")
    print(json.dumps({k: report[k] for k in ["case", "nonempty_code_cells", "executed_code_cells", "accepted", "elapsed_seconds"]}))
    raise SystemExit(0 if report["accepted"] else 1)

if __name__ == "__main__":
    main()
