# SPDX-License-Identifier: Apache-2.0
"""Run the bounded OMNI smart-city simulation from its documented module."""

from .omni_factory_demo import main
from alpha_factory_v1.utils.disclaimer import print_disclaimer

if __name__ == "__main__":
    print_disclaimer()
    main()
