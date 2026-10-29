# SPDX-License-Identifier: Apache-2.0
"""Native narrow registration checks; no candidate execution or model calls."""
import argparse

import pytest

from alpha_factory_v1.core.runtime.invention_automation import operator


def test_narrow_commands_parse_without_precursor_engine() -> None:
    parser = argparse.ArgumentParser()
    operator.add_commands(parser.add_subparsers(dest="command", required=True))
    args = parser.parse_args(["invention", "critic-resume", "--output", "retained"])
    assert args.command == "invention"
    assert args.invention_command == "critic-resume"
    assert str(args.output) == "retained"
    with pytest.raises(SystemExit):
        parser.parse_args(["invention", "run", "unqualified-money-request.json"])


def test_native_parser_registers_invention() -> None:
    from alpha_factory_v1.core.runtime.cli import parser

    args = parser().parse_args(["invention", "critic-resume", "--output", "retained"])
    assert args.command == "invention"
