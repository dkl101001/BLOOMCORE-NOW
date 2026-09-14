#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export PYTHONPATH="$ROOT/packages"
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

python3 -m pledge_receipt scaffold "$ROOT/examples/policy-v1.md" \
  --title "Example Agent Conduct Draft" \
  --issuer "BLOOMCORE NOW synthetic fixture" \
  --version "scaffold" \
  --url "https://example.invalid/agent-conduct-v1" \
  --json "$OUT/scaffold.json"

python3 -m pledge_receipt audit "$ROOT/examples/complete.packet.json" \
  --source "$ROOT/examples/complete-policy.md" \
  --json "$OUT/audit.json" --markdown "$OUT/audit.md" >/dev/null

python3 -m pledge_receipt diff \
  "$ROOT/examples/version-1.packet.json" \
  "$ROOT/examples/version-2.packet.json" \
  --advisory --json "$OUT/diff.json" --markdown "$OUT/diff.md" >/dev/null

python3 -m pledge_receipt verify "$OUT/audit.json"
python3 -m pledge_receipt verify "$OUT/diff.json"

python3 - "$OUT/audit.json" "$OUT/diff.json" <<'PY'
# SPDX-License-Identifier: Apache-2.0
import json, sys
audit = json.load(open(sys.argv[1], encoding="utf-8"))
diff = json.load(open(sys.argv[2], encoding="utf-8"))
print("AUDIT", audit["summary"])
print("DIFF", diff["summary"])
PY
