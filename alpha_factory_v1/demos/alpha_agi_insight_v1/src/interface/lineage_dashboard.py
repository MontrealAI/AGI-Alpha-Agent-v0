# SPDX-License-Identifier: Apache-2.0
"""Compatibility wrapper for the shared lineage dashboard."""

from alpha_factory_v1.core.interface.lineage_dashboard import *  # noqa: F403
from alpha_factory_v1.core.interface import lineage_dashboard as _lineage_dashboard

__all__ = list(_lineage_dashboard.__all__)
