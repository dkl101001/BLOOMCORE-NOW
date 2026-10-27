"""Semantic checks that JSON Schema cannot fully express for GeoJSON regions."""

from __future__ import annotations

from typing import Any


def _ring_area(ring: list[list[float]]) -> float:
    return abs(sum(
        ring[index][0] * ring[(index + 1) % len(ring)][1]
        - ring[(index + 1) % len(ring)][0] * ring[index][1]
        for index in range(len(ring))
    )) / 2


def validate_region_geojson(geojson: dict[str, Any]) -> None:
    geometry_type = geojson.get("type")
    polygons = [geojson.get("coordinates")] if geometry_type == "Polygon" else geojson.get("coordinates")
    if geometry_type not in {"Polygon", "MultiPolygon"} or not isinstance(polygons, list):
        raise ValueError("inferred region must be Polygon or MultiPolygon")
    positive_area = False
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise ValueError("region polygon must contain a ring")
        for ring in polygon:
            if not isinstance(ring, list) or len(ring) < 4:
                raise ValueError("region ring must contain at least four coordinates")
            if ring[0] != ring[-1]:
                raise ValueError("region ring must be closed")
            for coordinate in ring:
                if not isinstance(coordinate, list) or len(coordinate) < 2:
                    raise ValueError("invalid region coordinate")
                longitude, latitude = coordinate[:2]
                if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
                    raise ValueError("region coordinate out of range")
            positive_area |= _ring_area(ring) > 0
    if not positive_area:
        raise ValueError("inferred region must have nonzero area")
