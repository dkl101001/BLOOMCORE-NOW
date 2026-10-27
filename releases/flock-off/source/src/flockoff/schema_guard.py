"""Small fail-closed validator for the schema features used by this package.

Production deployments may additionally use a full Draft 2020-12 validator.
This module deliberately supports only the keywords present in SCHEMAS and
raises on any unsupported keyword that could affect instance validation.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


class ValidationError(ValueError):
    pass


_ANNOTATIONS = {"$schema", "$id", "title", "description", "default"}
_SUPPORTED = {
    "type", "required", "properties", "additionalProperties", "items",
    "minItems", "maxItems", "uniqueItems", "minLength", "maxLength",
    "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "enum", "const", "anyOf", "oneOf", "allOf", "if", "then", "else",
    "format", "minProperties", "maxProperties", "propertyNames",
}


def _is_type(value: Any, expected: str) -> bool:
    return {
        "null": value is None,
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
    }.get(expected, False)


def _probe(instance: Any, schema: dict[str, Any]) -> bool:
    try:
        validate(instance, schema)
        return True
    except ValidationError:
        return False


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> None:
    unknown = set(schema) - _ANNOTATIONS - _SUPPORTED
    if unknown:
        raise ValidationError(f"{path}: unsupported schema keywords {sorted(unknown)}")

    if "type" in schema:
        expected = schema["type"]
        choices = expected if isinstance(expected, list) else [expected]
        if not any(_is_type(instance, choice) for choice in choices):
            raise ValidationError(f"{path}: expected type {choices}, got {type(instance).__name__}")

    if "const" in schema and instance != schema["const"]:
        raise ValidationError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise ValidationError(f"{path}: value is not in enum")

    if "anyOf" in schema and not any(_probe(instance, branch) for branch in schema["anyOf"]):
        raise ValidationError(f"{path}: no anyOf branch matched")
    if "oneOf" in schema and sum(_probe(instance, branch) for branch in schema["oneOf"]) != 1:
        raise ValidationError(f"{path}: exactly one oneOf branch must match")
    for branch in schema.get("allOf", []):
        validate(instance, branch, path)
    if "if" in schema:
        selected = schema.get("then") if _probe(instance, schema["if"]) else schema.get("else")
        if selected is not None:
            validate(instance, selected, path)

    if isinstance(instance, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in instance]
        if missing:
            raise ValidationError(f"{path}: missing required keys {missing}")
        props = schema.get("properties", {})
        for key, value in instance.items():
            if key in props:
                validate(value, props[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                raise ValidationError(f"{path}: additional property {key!r}")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate(value, schema["additionalProperties"], f"{path}.{key}")
        if len(instance) < schema.get("minProperties", 0):
            raise ValidationError(f"{path}: too few properties")
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            raise ValidationError(f"{path}: too many properties")
        if isinstance(schema.get("propertyNames"), dict):
            for key in instance:
                validate(key, schema["propertyNames"], f"{path}.<property-name>")

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise ValidationError(f"{path}: too few items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise ValidationError(f"{path}: too many items")
        if schema.get("uniqueItems"):
            serialized = [json.dumps(x, sort_keys=True, allow_nan=False) for x in instance]
            if len(serialized) != len(set(serialized)):
                raise ValidationError(f"{path}: duplicate array items")
        if isinstance(schema.get("items"), dict):
            for index, value in enumerate(instance):
                validate(value, schema["items"], f"{path}[{index}]")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise ValidationError(f"{path}: string too short")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            raise ValidationError(f"{path}: string too long")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise ValidationError(f"{path}: pattern mismatch")
        if schema.get("format") == "date-time":
            try:
                parsed = dt.datetime.fromisoformat(instance.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError
            except ValueError as exc:
                raise ValidationError(f"{path}: invalid timezone-aware date-time") from exc

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise ValidationError(f"{path}: below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise ValidationError(f"{path}: above maximum")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            raise ValidationError(f"{path}: below exclusive minimum")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            raise ValidationError(f"{path}: above exclusive maximum")


def validate_file(instance_path: Path, schema_path: Path) -> None:
    validate(json.loads(instance_path.read_text()), json.loads(schema_path.read_text()))


def check_schema_supported(schema: dict[str, Any], path: str = "$") -> None:
    """Fail if a schema uses a keyword the bundled validator cannot enforce."""

    unknown = set(schema) - _ANNOTATIONS - _SUPPORTED
    if unknown:
        raise ValidationError(f"{path}: unsupported schema keywords {sorted(unknown)}")
    if "pattern" in schema:
        try:
            re.compile(schema["pattern"])
        except re.error as exc:
            raise ValidationError(f"{path}: invalid regular expression") from exc
    for name, child in schema.get("properties", {}).items():
        check_schema_supported(child, f"{path}.properties.{name}")
    for name in ("additionalProperties", "items", "propertyNames", "if", "then", "else"):
        child = schema.get(name)
        if isinstance(child, dict):
            check_schema_supported(child, f"{path}.{name}")
    for name in ("anyOf", "oneOf", "allOf"):
        for index, child in enumerate(schema.get(name, [])):
            check_schema_supported(child, f"{path}.{name}[{index}]")
