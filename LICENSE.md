<!-- SPDX-License-Identifier: Apache-2.0 -->

# Licensing

BLOOMCORE NOW is a multi-license repository.

The repository is not licensed as a whole under one license and is not
triple-licensed at the recipient's option. Components are governed by
different licenses according to their architectural role.

## License map

| Path | License |
| --- | --- |
| `README.md`, public Markdown documentation (including `docs/faq/**` and `docs/assets/ASSET_PROVENANCE.md`), `shared/schemas/**`, release examples and `packages/receipt-schema/**` | Apache-2.0 |
| `forge_tools/**`, `shared/deterministic-tools/**`, release deterministic validators and local CLIs | MPL-2.0 |
| `shared/runtime-contracts/**`, hosted services and adaptive runtimes | AGPL-3.0-only |

The applicable license is identified by the SPDX header in a file and the
nearest parent-directory `LICENSE` file. The full standard license texts are
stored in `LICENSES/`.

A combined distribution incorporating an AGPL-covered component must comply
with the AGPL to the extent required by that license. Existing Apache and MPL
copyright, attribution, patent, notice and source-availability requirements
remain intact.

Custody, provenance, safety and architectural-boundary documents describe
lineage and intended use. They do not silently replace or modify the standard
open-source licenses.

Binary artwork such as `docs/assets/bloomcore-sigil.png` is not reclassified
merely because it appears beside Apache-2.0 documentation. Its use also does
not imply a trademark license.

