# SPDX-License-Identifier: Apache-2.0
"""Native recovered and retained command registration; no candidate execution."""
import argparse

import pytest

from alpha_factory_v1.core.runtime.invention_automation import operator


def test_recovered_commands_and_retained_qualification_parse() -> None:
    parser = argparse.ArgumentParser()
    operator.add_commands(parser.add_subparsers(dest="command", required=True))
    args = parser.parse_args(["invention", "critic-resume", "--output", "retained"])
    assert args.command == "invention"
    assert args.invention_command == "critic-resume"
    assert str(args.output) == "retained"
    assert parser.parse_args(["invention", "run", "request.json", "--output", "sim"]).invention_command == "run"
    with pytest.raises(ValueError, match="retired"):
        operator.handle(argparse.Namespace(invention_command="qualify"))


def test_native_parser_registers_invention() -> None:
    from alpha_factory_v1.core.runtime.cli import parser

    args = parser().parse_args(["invention", "critic-resume", "--output", "retained"])
    assert args.command == "invention"
