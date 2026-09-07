<!-- SPDX-License-Identifier: Apache-2.0 -->

# Scope and Limitations

## Bounded claim

Given UTF-8 CycloneDX JSON version 1.4, 1.5, 1.6 or 1.7, the tool reports
whether values exist at documented paths for a bounded mapping of CISA's 2026
SBOM minimum elements. It produces a reproducible receipt for the same input
bytes and tool version.

## Claims deliberately withheld

The tool does not claim that:

- the SBOM conforms to the complete CycloneDX schema;
- present values are accurate, complete, authentic or current;
- a signature is cryptographically valid or belongs to the asserted author;
- a component hash corresponds to a distributed or executable artifact;
- a declared license is legally correct or sufficient;
- dependency relationships capture every transitive or runtime relationship;
- process-practice requirements are satisfied;
- an organization, product or procurement submission is CISA-compliant;
- the receipt is an official CISA assessment.

Schema validation and structural profile inspection are different jobs. A
future adapter may invoke an official CycloneDX schema validator, but this v0.1
does not silently bundle or fetch one.

## Explicit unknowns

The scanner recognizes `UNKNOWN`, `NOASSERTION`, `not known` and `undetermined`
case-insensitively as explicit unknowns. It does not treat them as present facts
or collapse them into missing data. Additional ecosystem conventions require
evidence before being added.

## Component identifiers

External identifiers include purl, CPE, SWID, OmniBOR and SWHID values. A local
CycloneDX `bom-ref` is not counted as an external component identifier, though
it is used to inspect dependency-graph membership.

## Security and privacy

The tool reads local bytes, parses JSON with duplicate-key and non-finite-number
rejection, and writes only explicit output paths. It makes no network calls,
executes no input content and refuses to overwrite existing outputs.

