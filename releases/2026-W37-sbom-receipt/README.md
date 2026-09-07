<!-- SPDX-License-Identifier: Apache-2.0 -->

# BLOOMCORE SBOM RECEIPT v0.1.0

> Drop in CycloneDX JSON. See what the new CISA profile can—and cannot—prove.

State: **Φ — RELEASE_CANDIDATE_NOT_SHIPPED**

BLOOMCORE SBOM RECEIPT is a dependency-free local CLI that inspects CycloneDX
JSON against a bounded structural interpretation of CISA's July 29, 2026 SBOM
minimum elements. It keeps four outcomes separate:

- `present` — a recognized field contains a non-placeholder value;
- `explicit_unknown` — the value says `UNKNOWN`, `NOASSERTION`, `not known` or
  `undetermined`;
- `missing` — the mapped field has no value;
- `not_machine_verifiable` — the requirement needs process or organizational
  evidence outside one SBOM file.

## One-minute demo

From this release directory:

```bash
sh examples/demo.sh
```

Or inspect your own CycloneDX 1.4–1.7 JSON:

```bash
export PYTHONPATH="$PWD/packages"
python -m sbom_receipt check bom.cdx.json \
  --json /tmp/sbom-receipt.json \
  --markdown /tmp/sbom-receipt.md
python -m sbom_receipt verify /tmp/sbom-receipt.json
```

`check` returns `1` when structural gaps exist, `2` for invalid input or unsafe
overwrite, and `0` when no mapped structural fields are missing. Use
`--advisory` when a gap receipt should not fail a pipeline.

## What it inspects

- document author, signature, timestamp, format, format version, generation
  context, generator name/version and SBOM version;
- component name, version, producer, external identifier, hash value/algorithm,
  license and dependency-graph membership;
- six process practices that are deliberately held at
  `not_machine_verifiable`.

The input never leaves the machine. The runtime makes no network requests and
has no third-party dependencies. JSON and Markdown outputs are deterministic;
the JSON receipt carries a self-hash and source-file SHA-256.

## Boundary

This is a structural inspection aid—not an official CISA tool and not a legal,
regulatory or procurement compliance determination. Presence does not establish
accuracy, completeness, provenance, signature validity, license meaning or
artifact-hash correspondence. See [scope and limitations](docs/SCOPE_AND_LIMITATIONS.md),
[the profile mapping](docs/PROFILE_MAPPING.md), and [the threat model](docs/THREAT_MODEL.md).

## Test

```bash
python -m unittest discover -s tests -v
```

Python 3.11–3.13 is supported.

## License map

The CLI package and tests are MPL-2.0. Documentation, contracts, examples,
evidence and release metadata are Apache-2.0. See `LICENSE_MAP.md` and `NOTICE`.

