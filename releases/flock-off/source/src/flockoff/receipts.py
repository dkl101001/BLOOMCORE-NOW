"""Deterministic receipt bodies separated from mutable attestations."""

from __future__ import annotations

from typing import Any

from .canonical import content_id, sha256_uri


def make_receipt(
    *,
    subject_ref: str,
    input_refs: list[str],
    input_hashes: list[str],
    algorithm_name: str,
    algorithm_version: str,
    parameters: dict[str, Any],
    output: Any,
    source_locks: list[dict[str, Any]],
    code_revision: str,
    code_digest: str,
) -> dict[str, Any]:
    if len(input_refs) != len(input_hashes):
        raise ValueError("input refs and hashes must be parallel")
    if len(input_refs) != len(set(input_refs)):
        raise ValueError("duplicate receipt input reference")
    paired = sorted(zip(input_refs, input_hashes, strict=True))
    body = {
        "receipt_version": "1.0.0",
        "subject_ref": subject_ref,
        "input_refs": [item[0] for item in paired],
        "input_hashes": [item[1] for item in paired],
        "algorithm": {"name": algorithm_name, "version": algorithm_version},
        "parameters": parameters,
        "parameters_hash": sha256_uri(parameters),
        "output_hash": sha256_uri(output),
        "source_locks": sorted(source_locks, key=lambda item: (item["source_id"], item["revision"])),
        "code_revision": code_revision,
        "code_digest": code_digest,
    }
    receipt_hash = sha256_uri(body)
    return {
        "schema_version": "1.0.0",
        "receipt_id": "receipt_" + receipt_hash.split(":", 1)[1][:40],
        "receipt_hash": receipt_hash,
        "body": body,
        "attestation": None,
    }


def verify_receipt(receipt: dict[str, Any]) -> bool:
    try:
        body = receipt["body"]
        refs = body["input_refs"]
        hashes = body["input_hashes"]
        digest = sha256_uri(body)
        paired = list(zip(refs, hashes, strict=True))
        return (
            len(refs) == len(set(refs))
            and paired == sorted(paired)
            and digest == receipt["receipt_hash"]
            and receipt["receipt_id"] == "receipt_" + digest.split(":", 1)[1][:40]
            and body.get("parameters_hash") == sha256_uri(body.get("parameters"))
        )
    except (KeyError, TypeError, ValueError):
        return False
