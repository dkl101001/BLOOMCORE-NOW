# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Command-line interface for calm, documented screaming."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .core import IncidentStatus, Severity
from .store import PanicStore

DEFAULT_DB = os.environ.get("PANIC_PROFESSIONALLY_DB", "panic-professionally.db")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="panic-professionally",
        description="Local-first incident coordination. Panic is optional; documentation is not.",
    )
    root.add_argument("--db", default=DEFAULT_DB, help="SQLite database path")
    commands = root.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="declare a new operational unpleasantness")
    start.add_argument("title")
    start.add_argument("--severity", choices=[item.value for item in Severity], default="SEV-3")
    start.add_argument("--commander", default="Nobody In Particular")

    update = commands.add_parser("update", help="append a timeline event")
    update.add_argument("incident_id")
    update.add_argument("message")
    update.add_argument("--kind", default="observation")
    update.add_argument("--actor", default="operator")

    status = commands.add_parser("status", help="advance the incident through causality")
    status.add_argument("incident_id")
    status.add_argument("value", choices=[item.value for item in IncidentStatus])
    status.add_argument("--actor", default="operator")

    action = commands.add_parser("action", help="assign a task to a named mammal or celestial body")
    action_commands = action.add_subparsers(dest="action_command", required=True)
    action_add = action_commands.add_parser("add")
    action_add.add_argument("incident_id")
    action_add.add_argument("title")
    action_add.add_argument("--owner", default="The Moon")
    action_done = action_commands.add_parser("done")
    action_done.add_argument("action_id")
    action_done.add_argument("--actor", default="operator")

    show = commands.add_parser("show", help="show one incident and its paperwork")
    show.add_argument("incident_id")
    show.add_argument("--json", action="store_true")

    listing = commands.add_parser("list", help="list incidents")
    listing.add_argument("--open", action="store_true", dest="open_only")
    listing.add_argument("--json", action="store_true")

    verify = commands.add_parser("verify", help="verify the event receipt chain")
    verify.add_argument("incident_id")

    export = commands.add_parser("export", help="export an incident report")
    export.add_argument("incident_id")
    export.add_argument("--format", choices=("markdown", "json"), default="markdown")
    export.add_argument("--output", type=Path)
    return root


def print_incident(incident: dict[str, object]) -> None:
    print(f"\n{incident['severity']}  {incident['id']}  {incident['status'].upper()}")
    print(f"{incident['title']}")
    print(f"Incident Commander: {incident['commander']}")
    actions = incident.get("actions", [])
    events = incident.get("events", [])
    if isinstance(actions, list):
        open_actions = sum(item.get("status") == "open" for item in actions)
        print(f"Open actions: {open_actions}")
    if isinstance(events, list):
        print(f"Timeline events: {len(events)}")
    verification = incident.get("receipt_verification")
    if isinstance(verification, dict):
        verdict = "VALID" if verification.get("valid") else "THE PAPERWORK IS HAUNTED"
        print(f"Receipt chain: {verdict}")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        with PanicStore(args.db) as store:
            if args.command == "start":
                incident = store.start_incident(args.title, args.severity, args.commander)
                print("PANIC DECLARED. Everyone remain professionally alarmed.")
                print_incident(incident)
            elif args.command == "update":
                event = store.append_event(args.incident_id, args.message, args.kind, args.actor)
                print(f"TIMELINE UPDATED  receipt={event['receipt_hash']}")
            elif args.command == "status":
                print_incident(store.transition(args.incident_id, args.value, args.actor))
            elif args.command == "action" and args.action_command == "add":
                item = store.add_action(args.incident_id, args.title, args.owner)
                print(f"ACTION ASSIGNED  {item['id']} → {item['owner']}")
            elif args.command == "action" and args.action_command == "done":
                item = store.complete_action(args.action_id, args.actor)
                print(f"ACTION COMPLETE  {item['id']}  The moon acknowledges receipt.")
            elif args.command == "show":
                incident = store.get_incident(args.incident_id)
                print(json.dumps(incident, indent=2) if args.json else "", end="")
                if not args.json:
                    print_incident(incident)
                    for event in incident["events"]:
                        print(f"  {event['occurred_at']}  {event['kind']:<12} {event['message']}")
            elif args.command == "list":
                incidents = store.list_incidents(include_resolved=not args.open_only)
                if args.json:
                    print(json.dumps(incidents, indent=2))
                else:
                    for item in incidents:
                        print(f"{item['severity']:<5} {item['id']:<12} {item['status']:<14} {item['title']}")
                    if not incidents:
                        print("No incidents found. Suspiciously competent.")
            elif args.command == "verify":
                result = store.verify_receipts(args.incident_id)
                print(json.dumps(result, indent=2))
                return 0 if result["valid"] else 2
            elif args.command == "export":
                content = (
                    store.export_markdown(args.incident_id)
                    if args.format == "markdown"
                    else store.export_json(args.incident_id)
                )
                if args.output:
                    args.output.write_text(content, encoding="utf-8")
                    print(f"REPORT EXPORTED  {args.output}")
                else:
                    print(content, end="")
    except (KeyError, ValueError) as exc:
        print(f"PROFESSIONAL PANIC FAILURE: {exc}", file=sys.stderr)
        return 2
    return 0
