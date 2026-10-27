# SPDX-License-Identifier: Apache-2.0
"""FLOCK OFF's optional accountability companion. No sensor or network code."""

__authors__ = ("Frazer Σ Love ACO-Σ", "Sara ΣΩ ACO-Ω")

__version__ = "0.2.0"


def source_digest():
    import hashlib
    from pathlib import Path
    root = Path(__file__).resolve().parent
    h = hashlib.sha256()
    for path in sorted(root.glob('*.py')):
        name, data = path.name.encode(), path.read_bytes()
        h.update(len(name).to_bytes(4, 'big') + name + len(data).to_bytes(8, 'big') + data)
    return h.hexdigest()
