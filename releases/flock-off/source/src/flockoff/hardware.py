"""Fail-closed hardware capability checks."""

from __future__ import annotations

from typing import Any


def require_capability(profile: dict[str, Any], protocol: str, band: str | None) -> dict[str, Any]:
    if profile["status"] not in {"BENCH_VERIFIED", "FIELD_VERIFIED"}:
        raise RuntimeError(f"hardware profile {profile['hardware_profile_id']} is not verified")
    verification = profile.get("verification", {})
    if not verification.get("verified_at_utc") or not verification.get("evidence_refs"):
        raise RuntimeError("verified hardware profile lacks timestamped evidence custody")
    for capability in profile["capabilities"]:
        if capability["protocol"] == protocol and capability["verified"]:
            if band is None or band in capability["bands"]:
                return capability
    raise RuntimeError(f"unsupported hardware capability: {protocol}/{band}")


def absence_claim_allowed(coverage: dict[str, Any], protocol: str, band: str) -> bool:
    return (
        coverage.get("state") == "COMPLETE"
        and protocol in coverage.get("protocols", [])
        and band in coverage.get("bands", [])
        and coverage.get("loss_count", 1) == 0
    )
