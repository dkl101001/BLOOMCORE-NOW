<!-- SPDX-License-Identifier: Apache-2.0 -->

# CISA 2026 Structural Profile Mapping

Source: CISA, *2026 Minimum Elements for a Software Bill of Materials*, July
29, 2026. The [source PDF](https://media.defense.gov/2026/Jul/29/2003971159/-1/-1/1/CSI_2026_cisa_sbom_minimum_elements_508c.PDF)
replaces the 2021 NTIA baseline.

This mapping is a bounded implementation interpretation for CycloneDX JSON,
not an official CISA conformance profile.

## Document-level fields

| Element | CycloneDX JSON path |
|---|---|
| SBOM author | `metadata.authors` or `metadata.manufacturer` |
| SBOM author signature | `signature` |
| Timestamp | `metadata.timestamp` |
| Data format name | `bomFormat` |
| Data format version | `specVersion` |
| Generation context | `metadata.lifecycles` |
| Tool name and version | `metadata.tools` component/service or legacy tool records |
| SBOM version | `version` |

## Per-component fields

| Element | CycloneDX JSON path |
|---|---|
| Component name | `name` |
| Component version | `version` |
| Component producer | `supplier`, `manufacturer`, `authors`, legacy `author`, or `publisher` |
| Component identifier | `purl`, `cpe`, `swid`, `omniborId`, or `swhid` |
| Hash value and algorithm | `hashes[*].content` and `hashes[*].alg` |
| Component license | `licenses[*].license`, `licenses[*].expression` |
| Dependency relationship | component `bom-ref` represented by `dependencies[*].ref` |

## Process-practice fields

Generation frequency, generation depth/coverage, known-unknown handling,
distribution/delivery, access control and accommodation of updates are emitted
as `not_machine_verifiable`. A single document can contain related evidence,
but its own contents cannot prove the surrounding organizational practice.

The CycloneDX schema is authoritative for CycloneDX syntax. Its current JSON
schemas document the fields used here: https://cyclonedx.org/schema/bom-1.6.schema.json

