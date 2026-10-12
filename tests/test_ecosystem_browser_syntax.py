# SPDX-License-Identifier: Apache-2.0
"""Parse the real JavaScript probes before sending them to browser acceptance."""
from __future__ import annotations

import ast
from pathlib import Path
import shutil
import subprocess

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/validate_ecosystem.py"


def browser_expressions() -> list[tuple[int, str]]:
    """Read literal probes and named string constants without importing Playwright."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    constants = {
        target.id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    expressions = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "inspect":
            expression = node.args[1]
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "add_init_script":
            expression = node.args[0]
        else:
            continue
        if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
            expressions.append((node.lineno, expression.value))
        elif isinstance(expression, ast.Name) and expression.id in constants:
            expressions.append((node.lineno, constants[expression.id]))
        else:
            # The one non-static probe injects the separately supplied axe library.
            assert isinstance(expression, ast.BinOp) and isinstance(expression.left, ast.Name)
            assert expression.left.id == "axe_source", f"Unvalidated JavaScript probe at line {node.lineno}"
    return expressions


EXPRESSIONS = browser_expressions()


@pytest.mark.parametrize(("line", "expression"), EXPRESSIONS, ids=[f"line-{line}" for line, _ in EXPRESSIONS])
def test_injected_browser_javascript_has_valid_syntax(line: int, expression: str) -> None:
    node = shutil.which("node")
    assert node is not None, "The contributor Node runtime is required to validate browser acceptance probes"
    result = subprocess.run([node, "--check"], input=expression, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, f"{SOURCE.name}:{line}\n{result.stderr}"


def test_control_measurement_is_included_in_browser_syntax_validation() -> None:
    assert any(
        "querySelectorAll" in expression and "getBoundingClientRect" in expression for _, expression in EXPRESSIONS
    )
