"""Append-only SQLite evidence ledger with a separately encrypted pose table."""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes, keyed_digest, sha256_uri, without_keys
from .crypto import EncryptedRecord, FieldCipher
from .geometry import validate_region_geojson
from .receipts import verify_receipt
from .schema_guard import validate

_EVENT_SCHEMAS = {
    "adapter_health": ("adapter_health.schema.json", "health_id"),
    "community_submission": ("community_submission.schema.json", "submission_id"),
    "contradiction": ("contradiction.schema.json", "contradiction_id"),
    "event_envelope": ("event_envelope.schema.json", "event_id"),
    "measurement_lineage": ("measurement_lineage.schema.json", "measurement_lineage_id"),
    "remote_id_message": ("remote_id_message.schema.json", "message_id"),
    "mobile_track_revision": ("mobile_track.schema.json", "track_revision_id"),
    "local_alert": ("local_alert.schema.json", "local_alert_id"),
    "observation": ("observation.schema.json", "observation_id"),
    "public_evidence": ("public_evidence.schema.json", "evidence_id"),
    "publication_approval": ("publication_approval.schema.json", "approval_id"),
    "sensor_coverage": ("sensor_coverage.schema.json", "coverage_id"),
    "signature_match": ("signature_match.schema.json", "match_id"),
    "pose_association": ("pose_association.schema.json", "association_id"),
    "pass_partition": ("pass_partition.schema.json", "partition_id"),
    "evidence_receipt": ("evidence_receipt.schema.json", "receipt_id"),
    "failure_packet": ("failure_packet.schema.json", "failure_id"),
    "drift_event": ("drift_event.schema.json", "drift_id"),
    "validation_decision": ("validation_decision.schema.json", "validation_id"),
}
_SELF_HASHED_EVENT_KINDS = {
    "adapter_health", "contradiction", "measurement_lineage", "pass_partition",
    "sensor_coverage", "failure_packet", "drift_event", "validation_decision",
}


class EvidenceLedger:
    def __init__(
        self, path: Path, migration_sql: Path, cipher: FieldCipher, *,
        evidence_digest_secret: bytes,
    ):
        self.path = path
        self.cipher = cipher
        if len(evidence_digest_secret) < 32:
            raise ValueError("evidence digest secret must be at least 32 bytes")
        self.evidence_digest_secret = evidence_digest_secret
        self.schema_root = migration_sql.resolve().parents[1]
        self.connection = sqlite3.connect(path)
        try:
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.execute("PRAGMA journal_mode = WAL")
            self.connection.execute("PRAGMA synchronous = FULL")
            self._apply_migration(migration_sql)
            self._apply_remaining_declared_migrations(migration_sql)
        except Exception:
            self.connection.close()
            raise

    @staticmethod
    def _now() -> str:
        return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")

    def _schema(self, name: str) -> dict[str, Any]:
        return json.loads((self.schema_root / name).read_text(encoding="utf-8"))


    def _apply_remaining_declared_migrations(self, migration_sql: Path) -> None:
        """Apply later append-only migrations declared after the bootstrap migration."""

        manifest_path = self.schema_root / "migration_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        declared = [self.schema_root / item["path"] for item in manifest["migrations"]]
        bootstrap = migration_sql.resolve()
        try:
            index = [item.resolve() for item in declared].index(bootstrap)
        except ValueError as exc:
            raise ValueError("bootstrap migration is not declared in the migration manifest") from exc
        for path in declared[index + 1:]:
            self._apply_migration(path)

    def _migration_id(self, migration_sql: Path) -> str:
        manifest_path = self.schema_root / "migration_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        relative = migration_sql.resolve().relative_to(self.schema_root.resolve()).as_posix()
        matches = [item["id"] for item in manifest["migrations"] if item["path"] == relative]
        if len(matches) != 1:
            raise ValueError(f"migration {relative!r} is not uniquely declared in the manifest")
        return str(matches[0])

    @staticmethod
    def _migration_statements(sql: str) -> list[str]:
        """Split SQLite statements without breaking trigger bodies or strings."""

        statements: list[str] = []
        buffer: list[str] = []
        for character in sql:
            buffer.append(character)
            if character == ";" and sqlite3.complete_statement("".join(buffer)):
                statement = "".join(buffer).strip()
                if statement:
                    statements.append(statement)
                buffer = []
        trailing = "".join(buffer).strip()
        if trailing:
            raise ValueError("migration SQL has an incomplete trailing statement")
        if not statements:
            raise ValueError("migration SQL contains no complete statement")
        return statements

    def _apply_migration(self, migration_sql: Path) -> None:
        sql = migration_sql.read_text(encoding="utf-8")
        sql_hash = sha256_uri(sql.encode("utf-8"))
        migration_id = self._migration_id(migration_sql)
        table_exists = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        existing = None
        if table_exists:
            existing = self.connection.execute(
                "SELECT sql_sha256 FROM schema_migrations WHERE migration_id = ?",
                (migration_id,),
            ).fetchone()
            if existing is not None and existing[0] != sql_hash:
                raise RuntimeError(
                    f"migration checksum mismatch for {migration_id}: "
                    f"ledger has {existing[0]}, package has {sql_hash}"
                )
            if existing is not None:
                return

        # executescript() implicitly commits pending work, so execute complete
        # SQLite statements individually inside our transaction. The SQLite
        # authorizer rejects transaction/savepoint opcodes regardless of case,
        # comments, line layout or quoting; only this host may commit/rollback.
        statements = self._migration_statements(sql)
        blocked_actions = {sqlite3.SQLITE_TRANSACTION}
        if hasattr(sqlite3, "SQLITE_SAVEPOINT"):
            blocked_actions.add(sqlite3.SQLITE_SAVEPOINT)

        def migration_authorizer(
            action: int, _arg1: str | None, _arg2: str | None,
            _database: str | None, _trigger: str | None,
        ) -> int:
            if action in blocked_actions:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.set_authorizer(migration_authorizer)
            for statement in statements:
                self.connection.execute(statement)
            self.connection.set_authorizer(None)
            self.connection.execute(
                "INSERT INTO schema_migrations VALUES (?, ?, ?)",
                (migration_id, sql_hash, self._now()),
            )
            self.connection.commit()
        except Exception:
            self.connection.set_authorizer(None)
            if self.connection.in_transaction:
                self.connection.rollback()
            raise
        recorded = self.connection.execute(
            "SELECT sql_sha256 FROM schema_migrations WHERE migration_id = ?",
            (migration_id,),
        ).fetchone()
        if recorded is None or recorded[0] != sql_hash:
            raise RuntimeError(f"migration custody was not recorded atomically for {migration_id}")

    def _resolve_input_hash(self, input_ref: str) -> str:
        candidates = [
            row[0] for row in self.connection.execute(
                "SELECT content_hash FROM ledger_events WHERE event_id = ?",
                (input_ref,),
            ).fetchall()
        ]
        candidates.extend(
            row[0] for row in self.connection.execute(
                "SELECT content_hash FROM restricted_pose_ciphertexts WHERE pose_id = ?",
                (input_ref,),
            ).fetchall()
        )
        if ":revision:" in input_ref:
            node_id, revision_text = input_ref.rsplit(":revision:", 1)
            if revision_text.isdigit():
                candidates.extend(
                    row[0] for row in self.connection.execute(
                        "SELECT content_hash FROM node_revisions WHERE node_id = ? AND revision = ?",
                        (node_id, int(revision_text)),
                    ).fetchall()
                )
        if not candidates:
            raise ValueError(f"receipt has unresolved input reference {input_ref!r}")
        if len(candidates) != 1:
            raise ValueError(f"receipt input reference is ambiguous {input_ref!r}")
        return candidates[0]

    def _verify_receipt_input_closure(self, receipt: dict[str, Any]) -> None:
        refs = receipt["body"]["input_refs"]
        hashes = receipt["body"]["input_hashes"]
        if len(refs) != len(hashes):
            raise ValueError("receipt input references and hashes are not parallel")
        for input_ref, claimed_hash in zip(refs, hashes, strict=True):
            actual_hash = self._resolve_input_hash(input_ref)
            if claimed_hash != actual_hash:
                raise ValueError(f"receipt input hash mismatch for {input_ref!r}")

    def append_event(self, kind: str, event_id: str, value: dict[str, Any]) -> str:
        if kind not in _EVENT_SCHEMAS:
            raise ValueError(f"unsupported ledger event kind {kind!r}")
        schema_name, id_field = _EVENT_SCHEMAS[kind]
        validate(value, self._schema(schema_name))
        if value.get(id_field) != event_id:
            raise ValueError(f"{kind} event ID does not match {id_field}")
        if kind == "evidence_receipt":
            if not verify_receipt(value):
                raise ValueError("invalid evidence receipt")
            self._verify_receipt_input_closure(value)
        if kind in _SELF_HASHED_EVENT_KINDS:
            expected = sha256_uri(without_keys(value, "content_hash"))
            if value["content_hash"] != expected:
                raise ValueError(f"{kind} content hash mismatch")
        raw = canonical_bytes(value)
        digest = sha256_uri(raw)
        with self.connection:
            self.connection.execute(
                "INSERT INTO ledger_events VALUES (?, ?, ?, ?, ?)",
                (kind, event_id, raw.decode("utf-8"), digest, self._now()),
            )
        return digest

    def _event_exists(self, event_id: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM ledger_events WHERE event_id = ? LIMIT 1", (event_id,)
        ).fetchone() is not None

    def append_node_revision(self, value: dict[str, Any]) -> str:
        validate(value, self._schema("node_estimate.schema.json"))
        if value.get("location") is not None:
            validate_region_geojson(value["location"]["geojson"])
        node_id = value["node_id"]
        revision = int(value["revision"])
        if revision == 1:
            if self.connection.execute(
                "SELECT 1 FROM node_revisions WHERE node_id = ? LIMIT 1", (node_id,)
            ).fetchone() is not None:
                raise ValueError("revision 1 cannot follow an existing node revision")
        else:
            previous = self.connection.execute(
                "SELECT content_hash FROM node_revisions WHERE node_id = ? AND revision = ?",
                (node_id, revision - 1),
            ).fetchone()
            if previous is None:
                raise ValueError("previous node revision is missing")
            if value["parent_revision_hash"] != previous[0]:
                raise ValueError("parent revision hash does not match the immutable predecessor")
        unresolved = [
            ref for ref in [
                *value["evidence_refs"], *value["contradiction_refs"],
                *value["measurement_lineages"],
            ]
            if not self._event_exists(ref)
        ]
        if unresolved:
            raise ValueError(f"node revision has unresolved evidence references: {unresolved}")
        receipt = self.get_event("evidence_receipt", value["receipt_id"])
        expected_subject = f"{node_id}:revision:{revision}"
        if receipt["body"]["subject_ref"] != expected_subject:
            raise ValueError("node receipt subject does not match revision")
        if receipt["body"]["algorithm"]["name"] != "node_revision_assembler":
            raise ValueError("node receipt was not produced by the node assembler")
        expected_inputs = set(value["evidence_refs"])
        expected_inputs.update(value["measurement_lineages"])
        expected_inputs.update(value["contradiction_refs"])
        if revision > 1:
            expected_inputs.add(f"{node_id}:revision:{revision - 1}")
        if set(receipt["body"]["input_refs"]) != expected_inputs:
            raise ValueError("node receipt does not bind the complete derivation graph")
        if receipt["body"]["output_hash"] != sha256_uri(without_keys(value, "receipt_id")):
            raise ValueError("node receipt output hash does not bind the revision body")
        raw = canonical_bytes(value)
        digest = sha256_uri(raw)
        with self.connection:
            self.connection.execute(
                "INSERT INTO node_revisions VALUES (?, ?, ?, ?, ?)",
                (node_id, revision, raw.decode(), digest, self._now()),
            )
        return digest

    def append_discovery_campaign_revision(self, value: dict[str, Any]) -> str:
        """Persist one immutable revision of a recursive discovery campaign."""

        validate(value, self._schema("discovery_campaign.schema.json"))
        campaign_id = value["campaign_id"]
        revision = int(value["revision"] )
        expected_hash = sha256_uri(without_keys(value, "content_hash"))
        if value["content_hash"] != expected_hash:
            raise ValueError("discovery campaign content hash mismatch")
        if revision == 1:
            if value["parent_campaign_hash"] is not None:
                raise ValueError("first discovery campaign revision cannot have a parent hash")
            if self.connection.execute(
                "SELECT 1 FROM discovery_campaign_revisions WHERE campaign_id = ? LIMIT 1",
                (campaign_id,),
            ).fetchone() is not None:
                raise ValueError("revision 1 cannot follow an existing discovery campaign")
        else:
            previous = self.connection.execute(
                "SELECT content_hash FROM discovery_campaign_revisions WHERE campaign_id = ? AND revision = ?",
                (campaign_id, revision - 1),
            ).fetchone()
            if previous is None:
                raise ValueError("previous discovery campaign revision is missing")
            if value["parent_campaign_hash"] != previous[0]:
                raise ValueError("discovery campaign parent hash does not match predecessor")
        if not self._event_exists(value["origin_failure_ref"]):
            raise ValueError("discovery campaign origin failure is not in immutable custody")
        raw = canonical_bytes(value)
        lineage_hash = value["content_hash"]
        with self.connection:
            self.connection.execute(
                "INSERT INTO discovery_campaign_revisions VALUES (?, ?, ?, ?, ?)",
                (campaign_id, revision, raw.decode("utf-8"), lineage_hash, self._now()),
            )
        return lineage_hash

    def get_discovery_campaign_revision(self, campaign_id: str, revision: int) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT canonical_json FROM discovery_campaign_revisions WHERE campaign_id = ? AND revision = ?",
            (campaign_id, revision),
        ).fetchone()
        if row is None:
            raise KeyError((campaign_id, revision))
        return json.loads(row[0])

    def append_restricted_pose(self, pose: dict[str, Any]) -> str:
        validate(pose, self._schema("receiver_pose.schema.json"))
        pose_id = pose["pose_id"]
        content_hash = keyed_digest(
            self.evidence_digest_secret, "restricted-pose-receipt", pose
        )
        record = self.cipher.encrypt(pose, pose_id)
        with self.connection:
            self.connection.execute(
                "INSERT INTO restricted_pose_ciphertexts VALUES (?, ?, ?, ?, ?, ?)",
                (pose_id, record.key_id, record.nonce, record.ciphertext, content_hash, self._now()),
            )
        return content_hash

    def read_restricted_pose(self, pose_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT key_id, nonce, ciphertext, content_hash "
            "FROM restricted_pose_ciphertexts WHERE pose_id = ?",
            (pose_id,),
        ).fetchone()
        if row is None:
            raise KeyError(pose_id)
        plaintext = self.cipher.decrypt(EncryptedRecord(row[0], row[1], row[2]), pose_id)
        pose = json.loads(plaintext)
        expected = keyed_digest(
            self.evidence_digest_secret, "restricted-pose-receipt", pose
        )
        if row[3] != expected:
            raise RuntimeError("restricted pose evidence digest mismatch")
        return pose

    def get_event(self, kind: str, event_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT canonical_json FROM ledger_events WHERE event_kind = ? AND event_id = ?",
            (kind, event_id),
        ).fetchone()
        if row is None:
            raise KeyError((kind, event_id))
        return json.loads(row[0])

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "EvidenceLedger":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
