# SPDX-License-Identifier: Apache-2.0
import argparse, base64, contextlib, hashlib, importlib.util, io, json, os, pathlib, socket, sys, time, traceback

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
    from IPython.terminal.interactiveshell import TerminalInteractiveShell
    shell = TerminalInteractiveShell.instance()
    # TerminalInteractiveShell implements enable_gui, including inline's no-GUI
    # mode. Enable notebook MIME types so the native inline formatter is tested.
    shell.display_formatter.active_types = ["text/plain", "text/html", "image/png", "image/svg+xml", "application/json"]
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
    plot_states = []
    rendered_plots = []
    cell_context = {"index": None}
    plot_dir = output_path.with_suffix("")
    import matplotlib.pyplot as plt

    def inspect_figures_before_inline_flush():
        # Registered before the notebook enables inline; this observer runs
        # before inline's native flush callback without altering figure state.
        for number in plt.get_fignums():
            fig = plt.figure(number)
            plot_states.append({
                "cell": cell_context["index"], "figure": number,
                "axes": [{"bounds": list(ax.get_position().bounds),
                          "lines": len(ax.lines), "collections": len(ax.collections),
                          "images": len(ax.images), "texts": len(ax.texts),
                          "xlabel": ax.get_xlabel(), "ylabel": ax.get_ylabel(),
                          "title": ax.get_title()} for ax in fig.axes]
            })

    shell.events.register("post_execute", inspect_figures_before_inline_flush)
    original_publish = shell.display_pub.publish

    def observe_published_image(data, metadata=None, **kwargs):
        if "image/png" in data:
            blob = data["image/png"]
            blob = base64.b64decode(blob) if isinstance(blob, str) else blob
            from PIL import Image
            with Image.open(io.BytesIO(blob)) as im:
                dimensions = list(im.size)
            plot_dir.mkdir(parents=True, exist_ok=True)
            target = plot_dir / ("cell-%02d-plot-%02d.png" % (cell_context["index"], len(rendered_plots)+1))
            target.write_bytes(blob)
            rendered_plots.append({"cell": cell_context["index"], "path": str(target),
                                   "sha256": hashlib.sha256(blob).hexdigest(),
                                   "dimensions": dimensions, "bytes": len(blob)})
        return original_publish(data, metadata=metadata, **kwargs)

    shell.display_pub.publish = observe_published_image

    def reject_network(self, address):
        denied.append(repr(address))
        raise RuntimeError("Independent acceptance forbids outbound runtime sockets")

    old_connect = socket.socket.connect
    old_connect_ex = socket.socket.connect_ex
    socket.socket.connect = reject_network
    socket.socket.connect_ex = reject_network
    try:
        for index, cell in enumerate(notebook["cells"]):
            cell_context["index"] = index
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
    # These additional expectations enforce the original inline cell boundaries.
    # They correct a discovered handoff defect; the frozen numeric tests above
    # are unchanged and their counts remain separate from graphical checks.
    expected_plot_axes = {
        "03.02-Data-Indexing-and-Selection": {},
        "03.05-Hierarchical-Indexing": {},
        "05.02-Introducing-Scikit-Learn": {1:20,4:1,13:1,18:1,20:3,22:100,26:2,30:1,31:100},
        "05.03-Hyperparameters-and-Model-Validation": {11:1,12:1,13:1,14:1,15:1,16:2,20:1},
        "03.06-Concat-And-Append": {},
        "05.04-Feature-Engineering": {9:1,10:1,12:1}
    }.get(args.case)
    graphical = []
    if expected_plot_axes is not None:
        expected_cells = list(expected_plot_axes)
        graphical = [
            {"name": "exact_native_inline_figure_cells", "pass": [r["cell"] for r in rendered_plots] == expected_cells,
             "expected": expected_cells, "observed": [r["cell"] for r in rendered_plots]},
            {"name": "independent_figure_axes_per_cell", "pass": [(r["cell"], len(r["axes"])) for r in plot_states] == list(expected_plot_axes.items()),
             "expected": list(expected_plot_axes.items()), "observed": [(r["cell"], len(r["axes"])) for r in plot_states]},
            {"name": "all_native_inline_pngs_readable", "pass": all(r["dimensions"][0] >= 200 and r["dimensions"][1] >= 150 and r["bytes"] > 1000 for r in rendered_plots)},
            {"name": "no_open_figures_left_between_cells", "pass": not plt.get_fignums()}
        ]
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
        "plot_states": plot_states, "rendered_plots": rendered_plots, "graphical_checks": graphical,
        "accepted": executed == expected_nonempty and not denied and bool(numerical) and all(row["pass"] for row in numerical) and all(row["pass"] for row in graphical),
        "elapsed_seconds": time.perf_counter() - started
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, default=convert) + "\n")
    print(json.dumps({k: report[k] for k in ["case", "nonempty_code_cells", "executed_code_cells", "accepted", "elapsed_seconds"]}))
    raise SystemExit(0 if report["accepted"] else 1)

if __name__ == "__main__":
    main()
