<!-- SPDX-License-Identifier: Apache-2.0 -->

# Current Problem — 2026-W37

CISA replaced the 2021 SBOM minimum-elements baseline on July 29, 2026. Teams
now need to distinguish four things that generic schema validation collapses:

- a required structural field is present;
- its value is explicitly unknown;
- it is absent;
- the requirement describes an organizational practice that one file cannot
  prove.

A JSON document can validate against CycloneDX while still omitting the new
CISA profile's author signature, generation context, generator version,
component hashes, licenses or dependency relationships. Conversely, a scanner
must not call an SBOM “compliant” merely because those fields exist.

Selected build: **BLOOMCORE SBOM RECEIPT v0.1.0** — a local, deterministic
structural witness that preserves those distinctions and stops below legal,
regulatory, procurement and semantic certification.
