# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
"""Wrapper script forwarding to :mod:`alpha_factory_v1.edge_runner`."""
from alpha_factory_v1.edge_runner import main
from src.utils.config import init_config

if __name__ == "__main__":
    init_config()
    main()
