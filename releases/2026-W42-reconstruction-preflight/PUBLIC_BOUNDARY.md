<!-- SPDX-License-Identifier: Apache-2.0 -->

# Public/private boundary

| Surface | Disposition |
|---|---|
| Public schema, CLI, synthetic fixtures, tests, receipts, results | Included |
| Compact source names, versions, public-safe hashes, and authority class | Included |
| Full Triad/Keystone payloads | Excluded |
| Native identity-bearing state or memory | Excluded |
| Protected ECA synthesis/orchestration and proprietary scoring | Excluded |
| Credentials, private adapters, private repository paths | Excluded |
| Sensitive infrastructure or supplier vulnerability data | Excluded |
| Automatic execution, admission, governance, or publication authority | Explicitly denied |

The fixtures are synthetic. The package performs local reads only and has no networking, subprocess execution of manifest content, dynamic imports, or mutation of referenced source bytes.

