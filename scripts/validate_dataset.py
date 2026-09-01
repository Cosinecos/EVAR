#!/usr/bin/env python3
from __future__ import annotations

import sys

from narracrime_evar.cli import validate_main


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    validate_main(["--data", root])
