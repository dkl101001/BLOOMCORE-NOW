# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""SQLite persistence and deterministic event receipts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from .core import IncidentStatus, validate_severity, validate_transition

GENESIS_HASH = "0" * 64


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def event_hash(payload: dict[str, Any], previous_hash: str) -> str:
    envelope = {"payload": payload, "previous_hash": previous_hash}
    return hashlib.sha256(canonical_json(envelope).encode("utf-8")).hexdigest()


class PanicStore:
    def __init__(self, path: str | Path = "panic-professionally.db") -> None:
        self.path = Path(path)
        if self.path != Path(":memory:"):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.path))
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "PanicStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connection:
            yield self._connection

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                commander TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
                occurred_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                message TEXT NOT NULL,
                actor TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                receipt_hash TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS actions (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                owner TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_incident
                ON events(incident_id, sequence);
            CREATE INDEX IF NOT EXISTS idx_actions_incident
                ON actions(incident_id, status);
            """
        )

    def start_incident(
        self, title: str, severity: str = "SEV-3", commander: str = "Nobody In Particular"
    ) -> dict[str, Any]:
        title = title.strip()
        if not title:
            raise ValueError("incident title cannot be empty; even confusion needs a noun")
        sev = validate_severity(severity)
        incident_id = f"PP-{uuid.uuid4().hex[:8].upper()}"
        now = utc_now()
        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    incident_id,
                    title,
                    sev.value,
                    IncidentStatus.DECLARED.value,
                    commander.strip() or "Nobody In Particular",
                    now,
                    now,
                ),
            )
            self._append_event(
                connection,
                incident_id,
                "declaration",
                f"Incident declared: {title}",
                commander,
                occurred_at=now,
            )
        return self.get_incident(incident_id)

    def append_event(
        self, incident_id: str, message: str, kind: str = "observation", actor: str = "operator"
    ) -> dict[str, Any]:
        message = message.strip()
        if not message:
            raise ValueError("event message cannot be empty")
        with self._transaction() as connection:
            self._require_incident(connection, incident_id)
            event = self._append_event(connection, incident_id, kind, message, actor)
            connection.execute(
                "UPDATE incidents SET updated_at = ? WHERE id = ?",
                (event["occurred_at"], incident_id),
            )
        return event

    def transition(self, incident_id: str, status: str, actor: str = "operator") -> dict[str, Any]:
        with self._transaction() as connection:
            incident = self._require_incident(connection, incident_id)
            requested = validate_transition(incident["status"], status)
            if requested.value == incident["status"]:
                return dict(incident)
            now = utc_now()
            connection.execute(
                "UPDATE incidents SET status = ?, updated_at = ? WHERE id = ?",
                (requested.value, now, incident_id),
            )
            self._append_event(
                connection,
                incident_id,
                "status",
                f"Status changed from {incident['status']} to {requested.value}",
                actor,
                occurred_at=now,
            )
        return self.get_incident(incident_id)

    def add_action(
        self, incident_id: str, title: str, owner: str = "The Moon"
    ) -> dict[str, Any]:
        title = title.strip()
        if not title:
            raise ValueError("action title cannot be empty")
        action_id = f"ACT-{uuid.uuid4().hex[:8].upper()}"
        now = utc_now()
        with self._transaction() as connection:
            self._require_incident(connection, incident_id)
            connection.execute(
                "INSERT INTO actions VALUES (?, ?, ?, ?, 'open', ?, NULL)",
                (action_id, incident_id, title, owner.strip() or "The Moon", now),
            )
            self._append_event(
                connection,
                incident_id,
                "action",
                f"Action assigned: {title} [{action_id}]",
                owner,
                occurred_at=now,
            )
        return self.get_action(action_id)

    def complete_action(self, action_id: str, actor: str = "operator") -> dict[str, Any]:
        with self._transaction() as connection:
            row = connection.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
            if row is None:
                raise KeyError(f"action not found: {action_id}")
            if row["status"] == "done":
                return dict(row)
            now = utc_now()
            connection.execute(
                "UPDATE actions SET status = 'done', completed_at = ? WHERE id = ?",
                (now, action_id),
            )
            self._append_event(
                connection,
                row["incident_id"],
                "action",
                f"Action completed: {row['title']} [{action_id}]",
                actor,
                occurred_at=now,
            )
            connection.execute(
                "UPDATE incidents SET updated_at = ? WHERE id = ?",
                (now, row["incident_id"]),
            )
        return self.get_action(action_id)

    def get_action(self, action_id: str) -> dict[str, Any]:
        row = self._connection.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
        if row is None:
            raise KeyError(f"action not found: {action_id}")
        return dict(row)

    def get_incident(self, incident_id: str) -> dict[str, Any]:
        row = self._connection.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        if row is None:
            raise KeyError(f"incident not found: {incident_id}")
        incident = dict(row)
        incident["events"] = [
            dict(item)
            for item in self._connection.execute(
                "SELECT * FROM events WHERE incident_id = ? ORDER BY sequence", (incident_id,)
            )
        ]
        incident["actions"] = [
            dict(item)
            for item in self._connection.execute(
                "SELECT * FROM actions WHERE incident_id = ? ORDER BY created_at, id",
                (incident_id,),
            )
        ]
        verification = self.verify_receipts(incident_id)
        incident["receipt_verification"] = verification
        return incident

    def list_incidents(self, include_resolved: bool = True) -> list[dict[str, Any]]:
        query = "SELECT * FROM incidents"
        parameters: tuple[str, ...] = ()
        if not include_resolved:
            query += " WHERE status != ?"
            parameters = (IncidentStatus.RESOLVED.value,)
        query += " ORDER BY updated_at DESC, id"
        return [dict(row) for row in self._connection.execute(query, parameters)]

    def verify_receipts(self, incident_id: str) -> dict[str, Any]:
        rows = self._connection.execute(
            "SELECT * FROM events WHERE incident_id = ? ORDER BY sequence", (incident_id,)
        ).fetchall()
        previous_hash = GENESIS_HASH
        failures: list[int] = []
        for row in rows:
            payload = self._event_payload(row)
            expected = event_hash(payload, previous_hash)
            if row["previous_hash"] != previous_hash or row["receipt_hash"] != expected:
                failures.append(row["sequence"])
            previous_hash = row["receipt_hash"]
        return {
            "valid": not failures,
            "events_checked": len(rows),
            "failed_sequences": failures,
            "head_hash": previous_hash,
        }

    def export_json(self, incident_id: str) -> str:
        return json.dumps(self.get_incident(incident_id), indent=2, ensure_ascii=False) + "\n"

    def export_markdown(self, incident_id: str) -> str:
        incident = self.get_incident(incident_id)
        verification = incident["receipt_verification"]
        lines = [
            "<!-- SPDX-License-Identifier: Apache-2.0 -->",
            "",
            f"# {incident['id']} — {incident['title']}",
            "",
            f"- Severity: **{incident['severity']}**",
            f"- Status: **{incident['status']}**",
            f"- Incident commander: **{incident['commander']}**",
            f"- Opened: `{incident['created_at']}`",
            f"- Updated: `{incident['updated_at']}`",
            f"- Receipt chain: **{'VALID' if verification['valid'] else 'INVALID'}**",
            f"- Chain head: `{verification['head_hash']}`",
            "",
            "## Timeline",
            "",
        ]
        for event in incident["events"]:
            lines.append(
                f"- `{event['occurred_at']}` **{event['kind']}** — {event['message']} "
                f"_({event['actor']}; `{event['receipt_hash'][:12]}`)_"
            )
        lines.extend(["", "## Actions", ""])
        if incident["actions"]:
            for action in incident["actions"]:
                marker = "x" if action["status"] == "done" else " "
                lines.append(
                    f"- [{marker}] {action['title']} — **{action['owner']}** (`{action['id']}`)"
                )
        else:
            lines.append("- No actions recorded. The incident may be entirely conceptual.")
        return "\n".join(lines) + "\n"

    def _append_event(
        self,
        connection: sqlite3.Connection,
        incident_id: str,
        kind: str,
        message: str,
        actor: str,
        occurred_at: str | None = None,
    ) -> dict[str, Any]:
        previous = connection.execute(
            "SELECT receipt_hash FROM events WHERE incident_id = ? ORDER BY sequence DESC LIMIT 1",
            (incident_id,),
        ).fetchone()
        previous_hash = previous["receipt_hash"] if previous else GENESIS_HASH
        payload = {
            "incident_id": incident_id,
            "occurred_at": occurred_at or utc_now(),
            "kind": kind.strip() or "observation",
            "message": message.strip(),
            "actor": actor.strip() or "operator",
        }
        receipt = event_hash(payload, previous_hash)
        cursor = connection.execute(
            """INSERT INTO events
               (incident_id, occurred_at, kind, message, actor, previous_hash, receipt_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                payload["incident_id"],
                payload["occurred_at"],
                payload["kind"],
                payload["message"],
                payload["actor"],
                previous_hash,
                receipt,
            ),
        )
        return {
            "sequence": cursor.lastrowid,
            **payload,
            "previous_hash": previous_hash,
            "receipt_hash": receipt,
        }

    @staticmethod
    def _event_payload(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "incident_id": row["incident_id"],
            "occurred_at": row["occurred_at"],
            "kind": row["kind"],
            "message": row["message"],
            "actor": row["actor"],
        }

    @staticmethod
    def _require_incident(connection: sqlite3.Connection, incident_id: str) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        if row is None:
            raise KeyError(f"incident not found: {incident_id}")
        return row
