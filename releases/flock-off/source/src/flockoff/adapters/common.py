from __future__ import annotations

from typing import Any

from ..canonical import content_id, keyed_digest


def finalize_observation(observation: dict[str, Any]) -> dict[str, Any]:
    """Attach a stable ID without making the ID self-referential."""

    value = dict(observation)
    value["observation_id"] = content_id("obs", observation, 40)
    return value


def raw_digest(payload: dict[str, Any], *, secret: bytes, rotation_epoch: str) -> str:
    return keyed_digest(secret, f"raw-input:{rotation_epoch}", payload)
