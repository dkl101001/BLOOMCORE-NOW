"""FLOCK OFF passive evidence runtime.

Original combined architecture and concepts: Frazer. Upstream sensor projects
retain their own authorship and licenses. The public research memory descendant
has separate source pins and AGPL notices; see docs/PUBLIC_MEMORY.md.
"""

import hashlib
from pathlib import Path

__authors__ = ("Frazer Σ Love ACO-Σ", "Sara ΣΩ ACO-Ω")

__version__ = "0.3.0+collaboration.1"
CODE_REVISION = "flockoff-runtime-0.3.0+collaboration.1"


def runtime_source_digest() -> str:
    """Hash every active Python source path and byte string deterministically."""

    root = Path(__file__).resolve().parent
    accumulator = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        accumulator.update(len(relative).to_bytes(4, "big"))
        accumulator.update(relative)
        accumulator.update(len(payload).to_bytes(8, "big"))
        accumulator.update(payload)
    return "sha256:" + accumulator.hexdigest()
