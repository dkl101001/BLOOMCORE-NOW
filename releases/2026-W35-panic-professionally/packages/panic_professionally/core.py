# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Domain rules for emergencies that have completed the required paperwork."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    SEV1 = "SEV-1"
    SEV2 = "SEV-2"
    SEV3 = "SEV-3"
    SEV4 = "SEV-4"


class IncidentStatus(StrEnum):
    DECLARED = "declared"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


ALLOWED_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.DECLARED: {IncidentStatus.INVESTIGATING, IncidentStatus.RESOLVED},
    IncidentStatus.INVESTIGATING: {IncidentStatus.IDENTIFIED, IncidentStatus.RESOLVED},
    IncidentStatus.IDENTIFIED: {IncidentStatus.MONITORING, IncidentStatus.RESOLVED},
    IncidentStatus.MONITORING: {IncidentStatus.INVESTIGATING, IncidentStatus.RESOLVED},
    IncidentStatus.RESOLVED: set(),
}


@dataclass(frozen=True)
class Incident:
    id: str
    title: str
    severity: Severity
    status: IncidentStatus
    commander: str
    created_at: str
    updated_at: str


class InvalidTransition(ValueError):
    """Raised when somebody tries to reverse time without filing Form 88-B."""


def validate_transition(current: str, requested: str) -> IncidentStatus:
    old = IncidentStatus(current)
    new = IncidentStatus(requested)
    if old == new:
        return new
    if new not in ALLOWED_TRANSITIONS[old]:
        raise InvalidTransition(
            f"cannot move incident from {old.value!r} to {new.value!r}; "
            "causality remains temporarily unionized"
        )
    return new


def validate_severity(value: str) -> Severity:
    try:
        return Severity(value.upper())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in Severity)
        raise ValueError(f"severity must be one of: {allowed}") from exc
