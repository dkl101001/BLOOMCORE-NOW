# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Source-checkout launcher for the installed dashboard implementation."""

from __future__ import annotations

import sys
from pathlib import Path

RELEASE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RELEASE_ROOT / "packages"))

from panic_professionally.dashboard import INDEX, handler_factory, main  # noqa: E402,F401


if __name__ == "__main__":
    raise SystemExit(main())
