#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

RELEASE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$RELEASE_ROOT/packages"
DEMO_DIR="$(mktemp -d)"
trap 'rm -rf -- "$DEMO_DIR"' EXIT
DEMO_DB="$DEMO_DIR/panic-professionally-demo.db"

python3 -m panic_professionally --db "$DEMO_DB" start \
  "Enterprise Potato has entered the load balancer" \
  --severity SEV-2 --commander "Root Jenkins"

INCIDENT_ID="$(python3 -m panic_professionally --db "$DEMO_DB" list --json | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')"
python3 -m panic_professionally --db "$DEMO_DB" status "$INCIDENT_ID" investigating
python3 -m panic_professionally --db "$DEMO_DB" update "$INCIDENT_ID" \
  "The potato is responding to health checks with strategic ambiguity"
python3 -m panic_professionally --db "$DEMO_DB" action add "$INCIDENT_ID" \
  "Remove tuber from production traffic" --owner "Chad Starch"
python3 -m panic_professionally --db "$DEMO_DB" show "$INCIDENT_ID"
python3 -m panic_professionally --db "$DEMO_DB" verify "$INCIDENT_ID"
