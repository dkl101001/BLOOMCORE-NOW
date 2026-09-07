<!-- SPDX-License-Identifier: Apache-2.0 -->

# Threat Model

| Threat | Control | Remainder |
|---|---|---|
| Malicious or malformed JSON | UTF-8 decoding, standard parser, duplicate-key and non-finite-number rejection | Memory exhaustion from very large valid JSON is not bounded in v0.1 |
| Input-triggered execution | Data-only parser; no dynamic imports, templates, shell or network | External wrappers remain outside scope |
| Output clobbering | Existing output paths are refused | User-selected new paths may be anywhere the user can write |
| Receipt alteration | Canonical JSON self-hash verification | Self-hash is file integrity, not trusted identity or signing |
| False compliance confidence | Four-state findings and repeated noncompliance boundary | Users can still misrepresent reports outside the tool |
| False hash confidence | Hash-field presence is separated from artifact correspondence | Artifact retrieval/verification is outside v0.1 |
| Private architecture leakage | Standalone deterministic rules; no private source inventory or protected runtime | Public docs necessarily reveal the bounded field mapping |

The parser does not fetch remote schemas, resolve package identifiers, inspect
artifacts or evaluate licenses. Those omissions are protective boundaries, not
implicit passes.

