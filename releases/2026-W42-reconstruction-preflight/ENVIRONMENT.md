<!-- SPDX-License-Identifier: Apache-2.0 -->

# Deterministic environment

- Python: 3.11 or newer
- Runtime dependencies: none beyond the standard library
- Network: not used
- Input encoding: UTF-8 JSON
- Canonicalization: sorted JSON object keys, compact separators, UTF-8, trailing newline
- Hash: SHA-256
- Randomness: none
- Clock: excluded from evaluation and receipt hot paths

The build was tested under the environment recorded in `evidence/TEST_RESULTS.md`. Receipts contain no timestamps, host paths, process IDs, or random identifiers.

