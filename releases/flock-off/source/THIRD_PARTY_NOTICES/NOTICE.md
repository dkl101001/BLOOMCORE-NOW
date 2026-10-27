# Third-party notices and custody

## Current combined successor

The required Windows CPython 3.12 runtime wheel inventory, exact artifact hashes,
dependency graph and upstream-declared licenses are recorded in sbom.cdx.json and
DEPENDENCY_ARTIFACTS.json. Upstream license and notice texts extracted from those
exact wheels are retained under licenses/. Dependency binaries are not bundled in
the source ZIP. Optional serial/receiver firmware remains separately identified.
The older environment discussion below is historical and does not override this
current inventory (in particular cffi is now 2.1.1).

The public BLOOMCORE geometry source is bundled with its original AGPL-3.0-only
notices. Exact source pin and adaptation: ../docs/THIRD_PARTY_PUBLIC_MEMORY.md.
The combined application is AGPL-3.0-only; original Apache components retain
their notices and permissions. See ../docs/LICENSE_MAP.md.

## Included runtime dependency

### Optional serial host dependency: pyserial 3.5

- Project: <https://github.com/pyserial/pyserial>
- Author: Chris Liechti and contributors
- License: BSD (upstream license: <https://github.com/pyserial/pyserial/blob/v3.5/LICENSE.txt>)
- Use: local COM/POSIX serial reads and device enumeration in the managed sensor console.
- Installed only in the candidate's local `.venv`; no dependency source or binary
  is redistributed in the source ZIP. Network serial URL handlers are not used.

### cryptography 46.0.0

- Project: <https://github.com/pyca/cryptography>
- Authors: The Python Cryptographic Authority and individual contributors
- License expression: Apache-2.0 OR BSD-3-Clause
- Use: AES-256-GCM for restricted route records
- Transitive packages in audited environment: `cffi` 1.17.1 (MIT; Armin
  Rigo/Maciej Fijalkowski and contributors) and `pycparser` 2.23 (BSD-3-Clause;
  Eli Bendersky and contributors)

Target-platform wheel/source hashes and full license-text bundling remain a
release gate. This package records notice metadata but does not vendor the
dependency or its license files.

## External upstream adapters and references—not included

- **Flock-You** — Colonel Panic and contributors; repository MIT notice; exact
  pin `7e969663eade07833603bad86cb156338e895583`. No source or binary copied.
  Pre-license contribution custody must be clarified before redistribution.
- **OpenDroneID core C / Android receiver** — OpenDroneID contributors;
  Apache-2.0; core pin `ec44332f67be38035d1f9dace4ce8e0bdf3cc2c8`
  and receiver release tag `v3.7.0` (release page reports `60b4320`). No source
  copied. Deployments must record the exact receiver/bridge build actually used.
- **DeFlock** — William Freeman/FoggedLens and contributors; legacy repository
  MIT; app AGPL-3.0 at the recorded pin. No source copied.
- **OpenStreetMap data** — © OpenStreetMap contributors, ODbL 1.0. No OSM
  snapshot bundled.
- **Flock Safety legal pages** — © 2026 Flock Safety / Flock Group Inc.; site
  states all rights reserved. Product Specific Terms, Customer InfoSec Addendum,
  and Part 91 Operational Agreement are cited as mutable vendor
  contract-source evidence only; no page bytes are bundled and no customer
  applicability or redistribution permission is inferred.
- **libiio** — Analog Devices and contributors; pin
  `4e3cfe61fb93698926f96faa7f6cce77abcece4b`; LGPL-2.1-or-later library,
  GPL-2.0-or-later tests/examples, and certain MIT-licensed files. Future
  external IMU-adapter research only; no source or binary copied.
- Candidate and rejected research components are not copied into this clean
  source repository. Their audit archive is distributed separately.

Repository references do not transfer upstream authorship to FLOCK OFF. FLOCK
OFF does not rename, fork or claim original authorship of those projects.

## FLOCK OFF custody

Concept originator: **Frazer**. The public name is **FLOCK OFF**, with no forced
acronym expansion. The combined source-lineage model, passive-adapter
architecture, host evidence ledger, uncertainty/publication design and
originating concepts remain attributed to the originator. Original FLOCK OFF
repository material is licensed under Apache-2.0 as stated in root `LICENSE`
and `NOTICE`. That grant does not relicense any material listed above.

The bundled `flockoff_red_tape/resources/bark.wav` is an original deterministic synthesized noise/tone sound generated for this release, licensed Apache-2.0 with the component; it contains no recording or third-party audio.
