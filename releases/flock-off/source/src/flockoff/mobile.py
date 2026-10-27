"""Mobile-node state and dock/base claim gates."""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Any

from .inference import EARTH_RADIUS_M


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    x = (lon2 - lon1) * math.cos((lat1 + lat2) / 2)
    y = lat2 - lat1
    return EARTH_RADIUS_M * math.hypot(x, y)


@dataclass(frozen=True)
class TrackPoint:
    observed_at_utc: str
    latitude: float
    longitude: float
    horizontal_accuracy_m: float | None
    evidence_basis: str


class MobileTrack:
    """Keep broadcast-coordinate and RF-inferred tracks semantically distinct."""

    def __init__(self, track_id: str, basis: str):
        if basis not in {"BROADCAST_REMOTE_ID", "RF_INFERRED"}:
            raise ValueError("invalid track evidence basis")
        self.track_id = track_id
        self.basis = basis
        self.points: list[TrackPoint] = []

    def add(self, point: TrackPoint) -> None:
        if point.evidence_basis != self.basis:
            raise ValueError("track basis cannot be silently fused")
        timestamp = dt.datetime.fromisoformat(point.observed_at_utc.replace("Z", "+00:00"))
        if self.points:
            previous = dt.datetime.fromisoformat(self.points[-1].observed_at_utc.replace("Z", "+00:00"))
            if timestamp <= previous:
                raise ValueError("track times must increase")
        self.points.append(point)

    def state(self) -> str:
        if len(self.points) < 2:
            return "MOTION_UNRESOLVED"
        displacement = _distance_m(
            (self.points[0].latitude, self.points[0].longitude),
            (self.points[-1].latitude, self.points[-1].longitude),
        )
        accuracy = sum((item.horizontal_accuracy_m or 50.0) for item in self.points) / len(self.points)
        return "MOBILE" if displacement > max(30.0, accuracy * 2) else "MOTION_UNRESOLVED"

    def as_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "evidence_basis": self.basis,
            "motion_state": self.state(),
            "points": [item.__dict__ for item in self.points],
            "calibration_state": "UNCALIBRATED",
            "confidence_level": None,
        }


def dock_hypothesis(
    endpoints: list[dict[str, Any]], *, independent_fixed_evidence: bool,
    official_document_ref: str | None = None,
) -> str:
    """Enforce the dock/base evidence ladder structurally."""

    if official_document_ref:
        return "DOCUMENTED_DOCK_OR_BASE"
    if len(endpoints) < 2:
        return "INSUFFICIENT_ENDPOINTS"
    dates = {str(item["observed_at_utc"])[:10] for item in endpoints}
    flights = {str(item["flight_id"]) for item in endpoints}
    center = (
        sum(float(item["latitude"]) for item in endpoints) / len(endpoints),
        sum(float(item["longitude"]) for item in endpoints) / len(endpoints),
    )
    spread = max(_distance_m(center, (float(item["latitude"]), float(item["longitude"]))) for item in endpoints)
    if len(flights) >= 3 and len(dates) >= 2 and spread <= 75 and independent_fixed_evidence:
        return "PROBABLE_DOCK_OR_BASE"
    return "ENDPOINT_CLUSTER"

