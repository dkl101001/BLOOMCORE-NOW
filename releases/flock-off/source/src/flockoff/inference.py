"""Deterministic, uncalibrated support-region localization baselines."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any

from .canonical import sha256_uri

EARTH_RADIUS_M = 6_371_008.8
ALGORITHM_VERSION = "rank-grid-0.2.0"
LOCAL_PLANE_MAX_SPAN_DEG = 0.25


@dataclass(frozen=True)
class Sample:
    latitude: float
    longitude: float
    rssi_dbm: float
    receiver_id: str
    pass_id: str
    horizontal_accuracy_m: float = 0.0


def _spatial_blocks(samples: list[Sample]) -> list[Sample]:
    """Collapse packet multiplicity into one robust value per receiver/pass/pose.

    A burst of identical packets is evidence of reception, not new spatial
    geometry.  Coordinates are rounded only to make serialized replay noise at
    the centimetre scale deterministic; the original first coordinate is kept.
    """

    groups: dict[tuple[str, str, float, float], list[Sample]] = {}
    for item in samples:
        if item.horizontal_accuracy_m < 0:
            raise ValueError("horizontal accuracy cannot be negative")
        key = (item.receiver_id, item.pass_id, round(item.latitude, 7), round(item.longitude, 7))
        groups.setdefault(key, []).append(item)
    collapsed = []
    for key in sorted(groups):
        group = groups[key]
        first = group[0]
        collapsed.append(Sample(
            latitude=first.latitude,
            longitude=first.longitude,
            rssi_dbm=float(statistics.median(item.rssi_dbm for item in group)),
            receiver_id=first.receiver_id,
            pass_id=first.pass_id,
            horizontal_accuracy_m=max(item.horizontal_accuracy_m for item in group),
        ))
    return collapsed


def _origin(samples: list[Sample]) -> tuple[float, float]:
    return (
        sum(item.latitude for item in samples) / len(samples),
        sum(item.longitude for item in samples) / len(samples),
    )


def _xy(latitude: float, longitude: float, origin: tuple[float, float]) -> tuple[float, float]:
    lat0, lon0 = map(math.radians, origin)
    x = math.radians(longitude) - lon0
    y = math.radians(latitude) - lat0
    return EARTH_RADIUS_M * x * math.cos(lat0), EARTH_RADIUS_M * y


def _ll(x: float, y: float, origin: tuple[float, float]) -> tuple[float, float]:
    lat0, lon0 = map(math.radians, origin)
    return (
        math.degrees(lat0 + y / EARTH_RADIUS_M),
        math.degrees(lon0 + x / (EARTH_RADIUS_M * math.cos(lat0))),
    )


def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    unique = sorted(set(points))
    if len(unique) <= 1:
        return unique

    def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def _polygon_area(points: list[tuple[float, float]]) -> float:
    return abs(sum(
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points))
    )) / 2


def _expanded_hull(points: list[tuple[float, float]], pad: float) -> list[tuple[float, float]]:
    expanded: list[tuple[float, float]] = []
    for x, y in points:
        expanded.extend([(x - pad, y - pad), (x - pad, y + pad), (x + pad, y - pad), (x + pad, y + pad)])
    return _convex_hull(expanded)


def _rank_score(candidate: tuple[float, float], positioned: list[tuple[Sample, float, float]]) -> tuple[float, int]:
    score = 0.0
    comparisons = 0
    by_pass: dict[tuple[str, str], list[tuple[Sample, float, float]]] = {}
    for item in positioned:
        by_pass.setdefault((item[0].receiver_id, item[0].pass_id), []).append(item)
    for pass_samples in by_pass.values():
        for index, (left, lx, ly) in enumerate(pass_samples):
            for right, rx, ry in pass_samples[index + 1:]:
                delta = left.rssi_dbm - right.rssi_dbm
                if abs(delta) < 3.0:
                    continue
                left_distance = math.hypot(candidate[0] - lx, candidate[1] - ly)
                right_distance = math.hypot(candidate[0] - rx, candidate[1] - ry)
                expected = left_distance < right_distance
                observed = delta > 0
                comparisons += 1
                if expected != observed:
                    score += min(2.0, abs(delta) / 6.0)
    return score, comparisons


def localize_static(samples: list[Sample], *, grid_step_m: float = 10.0, margin_m: float = 120.0) -> dict[str, Any]:
    """Return a conservative RF-only region, never an exact point.

    This rank baseline deliberately reports UNCALIBRATED. It does not interpret
    RSSI as distance and duplicate packet counts do not create new geometry.
    """

    if len(samples) < 4:
        raise ValueError("at least four positioned observations are required")
    if grid_step_m <= 0 or margin_m <= 0:
        raise ValueError("grid settings must be positive")
    raw_sample_count = len(samples)
    blocks = _spatial_blocks(samples)
    if len(blocks) < 4:
        raise ValueError("at least four independent spatial blocks are required")
    latitude_span = max(item.latitude for item in blocks) - min(item.latitude for item in blocks)
    longitude_span = max(item.longitude for item in blocks) - min(item.longitude for item in blocks)
    if latitude_span > LOCAL_PLANE_MAX_SPAN_DEG or longitude_span > LOCAL_PLANE_MAX_SPAN_DEG:
        raise ValueError("observations exceed the local-plane extent limit")
    origin = _origin(blocks)
    if abs(origin[0]) > 85:
        raise ValueError("local-plane baseline is disabled near the poles")
    positioned = [(item, *_xy(item.latitude, item.longitude, origin)) for item in blocks]
    unique_positions = {(round(x, 2), round(y, 2)) for _, x, y in positioned}
    if len(unique_positions) < 3:
        raise ValueError("observations do not provide spatial diversity")
    xs, ys = [item[1] for item in positioned], [item[2] for item in positioned]
    max_pose_accuracy_m = max(item.horizontal_accuracy_m for item in blocks)
    search_margin_m = margin_m + max_pose_accuracy_m
    min_x, max_x = min(xs) - search_margin_m, max(xs) + search_margin_m
    min_y, max_y = min(ys) - search_margin_m, max(ys) + search_margin_m
    width, height = max_x - min_x, max_y - min_y
    cell_count = max(1, math.ceil(width / grid_step_m) * math.ceil(height / grid_step_m))
    if cell_count > 50_000:
        grid_step_m = math.sqrt(width * height / 50_000)

    scored: list[tuple[float, float, float, int]] = []
    x = min_x
    while x <= max_x + 1e-9:
        y = min_y
        while y <= max_y + 1e-9:
            score, comparisons = _rank_score((x, y), positioned)
            scored.append((score, x, y, comparisons))
            y += grid_step_m
        x += grid_step_m
    comparable = max(item[3] for item in scored)
    if comparable < 2:
        raise ValueError("RSSI ordering is insufficient for localization")
    best = min(item[0] for item in scored)
    tolerance = max(1.0, comparable * 0.08)
    support = [(x, y) for score, x, y, _ in scored if score <= best + tolerance]
    hull_xy = _expanded_hull(support, grid_step_m / 2 + max_pose_accuracy_m)
    if len(hull_xy) < 3 or _polygon_area(hull_xy) <= 0:
        raise RuntimeError("support region collapsed unexpectedly")
    coordinates = []
    for x, y in hull_xy:
        lat, lon = _ll(x, y, origin)
        coordinates.append([round(lon, 7), round(lat, 7)])
    coordinates.append(coordinates[0])
    receiver_count = len({item.receiver_id for item in blocks})
    return {
        "geometry_type": "POLYGON",
        "geojson": {"type": "Polygon", "coordinates": [coordinates]},
        "calibration_state": "UNCALIBRATED",
        "confidence_level": None,
        "area_m2": round(_polygon_area(hull_xy), 1),
        "method": "RANK_RSSI_SUPPORT",
        "diagnostics": {
            "algorithm_version": ALGORITHM_VERSION,
            "input_hash": sha256_uri([item.__dict__ for item in samples]),
            "input_sample_count": raw_sample_count,
            "spatial_block_count": len(blocks),
            "comparisons": comparable,
            "receiver_count": receiver_count,
            "cross_receiver_comparisons": False,
            "max_pose_accuracy_m": round(max_pose_accuracy_m, 4),
            "local_plane_max_span_deg": LOCAL_PLANE_MAX_SPAN_DEG,
            "support_cell_count": len(support),
            "grid_step_m": round(grid_step_m, 4),
            "public_prior_used": False,
        },
    }


def require_tdoa_timing(clock_error_p95_seconds: float, target_resolution_m: float) -> None:
    max_error = target_resolution_m / (2 * 299_792_458.0)
    if clock_error_p95_seconds > max_error:
        raise RuntimeError(
            f"TDoA disabled: p95 clock error {clock_error_p95_seconds:.3e}s exceeds {max_error:.3e}s"
        )
