# SPDX-License-Identifier: Apache-2.0
"""Create a realistic synthetic incident and export reviewable evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RELEASE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RELEASE_ROOT / "packages"))

from panic_professionally.store import PanicStore  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("panic-professionally-demo"),
        help="directory for the synthetic database and exports",
    )
    args = parser.parse_args(argv)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    database = output_dir / "synthetic-incident.db"
    if database.exists():
        parser.error(f"refusing to overwrite existing demo database: {database}")

    with PanicStore(database) as store:
        incident = store.start_incident(
            "Checkout API returns intermittent 503s after regional rollout",
            "SEV-2",
            "Incident Commander",
        )
        incident_id = incident["id"]
        store.transition(incident_id, "investigating", "Incident Commander")
        store.append_event(
            incident_id,
            "Error rate rose from 0.2% to 18% in us-east during the rollout window",
            "observation",
            "Telemetry Lead",
        )
        rollback = store.add_action(
            incident_id,
            "Pause rollout and preserve deployment metadata",
            "Release Lead",
        )
        store.add_action(
            incident_id,
            "Compare timeout configuration with the previous stable release",
            "Service Owner",
        )
        store.complete_action(rollback["id"], "Release Lead")
        store.transition(incident_id, "identified", "Incident Commander")
        store.append_event(
            incident_id,
            "An invalid upstream timeout was isolated to synthetic release 2026.09.30.2",
            "finding",
            "Service Owner",
        )
        store.transition(incident_id, "monitoring", "Incident Commander")
        store.append_event(
            incident_id,
            "Rollback remained stable for 20 minutes; error rate returned below 0.3%",
            "validation",
            "Telemetry Lead",
        )

        markdown_path = output_dir / "incident.md"
        json_path = output_dir / "incident.json"
        markdown_path.write_text(store.export_markdown(incident_id), encoding="utf-8")
        json_path.write_text(store.export_json(incident_id), encoding="utf-8")
        verification = store.verify_receipts(incident_id)

    result = {
        "synthetic_data": True,
        "incident_id": incident_id,
        "database": str(database),
        "markdown_export": str(markdown_path),
        "json_export": str(json_path),
        "receipt_verification": verification,
    }
    print(json.dumps(result, indent=2))
    return 0 if verification["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
