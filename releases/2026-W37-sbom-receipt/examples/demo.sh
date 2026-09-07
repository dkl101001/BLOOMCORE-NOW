#!/usr/bin/env sh
# SPDX-License-Identifier: Apache-2.0
set -eu

release_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
output_dir=${1:-/tmp/bloomcore-sbom-receipt-demo}
rm -rf "$output_dir"
mkdir -p "$output_dir"

export PYTHONPATH="$release_dir/packages"
python -m sbom_receipt check "$release_dir/examples/with-gaps.cdx.json" \
  --json "$output_dir/with-gaps.json" \
  --markdown "$output_dir/with-gaps.md" \
  --advisory
python -m sbom_receipt check "$release_dir/examples/complete.cdx.json" \
  --json "$output_dir/complete.json" \
  --markdown "$output_dir/complete.md"
python -m sbom_receipt verify "$output_dir/complete.json"

printf '%s\n' "Receipts written to $output_dir"

