<!-- SPDX-License-Identifier: Apache-2.0 -->

# Threat model

| Threat | Control | Residual limitation |
|---|---|---|
| Role collapse or a fourth authority | Exact three-role vocabulary and count | Correct labels do not prove semantic correctness |
| Filename substituted for authority | SHA-256 binding between role and source record | SHA-256 proves bytes, not truth |
| Adapter self-promotion | Exact authority mapping | Human review remains necessary |
| Companion scope expansion | Single named DSK aperture | Research quality remains outside this tool |
| Path traversal or source overwrite | Relative-path containment and new-directory-only output | Local readers still need OS permissions |
| Receipt/report tampering | Canonical receipt self-hash plus artifact hashes | A valid receipt witnesses only declared checks |
| Evidence-free completion | Closed-with-evidence invariant and bounded claim vocabulary | Evidence relevance still needs review |
| Contradiction erasure | Required pre-transform, rejected readings and remainder | Preservation is structural, not interpretive resolution |
| Parser ambiguity | Duplicate-key and non-finite-number rejection | JSON text normalization is not retained |

There is no network client, shell bridge, plugin loader, secret reader, or
native-state mutation path in v0.1.0.
