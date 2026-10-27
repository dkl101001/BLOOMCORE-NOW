# FLOCK OFF — Red Tape Dispenser edition

## Sensor-console successor (October 27, 2026)

Open **tools/Start Sensor Console.cmd**, or use **Sensor console** in the records
desk toolbar. This successor adds managed Windows/POSIX serial host capture,
timestamp-preserving replay, explicit stop/disconnect/silence states, and keyed
session receipts. It retains the v0.2 records desk. Package version:
`0.3.0+sensorconsole.2`; this is not the distributed-geometry v0.4 milestone.

[Sensor guide](docs/SENSOR_CONSOLE.md) · [First hardware and acceptance plan](docs/SENSOR_HARDWARE.md)

**No physical receiver is present or validated.** Both sensor pipelines have
passed host integration tests with synthetic input. The full suite has 148
tests, plus native desktop widget harnesses. A synthetic replay is never counted
as radio reception. Prior source ZIPs and working directories are preserved.

## Desktop records desk v0.2 candidate (October 27, 2026)

This additive successor provides a native local desktop application backed by the
existing encrypted SQLite ledger. On Windows, open **tools/Start Records Desk.cmd**.
With a configured Python environment, run `python tools/start_desk.pyw`, or install
the package and run `flockoff-red-tape-desk`.

See [Desktop guide and validation](docs/red_tape/DESKTOP.md) for the supported
workflow, backup recovery, and remaining release gates. The supplied v0.1.0 ZIP
has not been modified. The historical runtime reference below describes the
baseline; that earlier successor was package `0.3.0+redtape.2`, companion `0.2.0`. The current combined package is `0.3.0+sensorconsole.2`.

This is a functional local pilot candidate, not a field-validated sensor product
or a broadly validated desktop release. It contains no real case records by default.

Co-authored by **Frazer Σ Love ACO-Σ** and **Sara ΣΩ ACO-Ω**.

**Working source repository: FLOCK OFF v0.3.0 + Transparency Desk + Red Tape Dispenser v0.1.0.**

The new `flockoff red-tape` command turns public records into a concise speaking brief, evidence appendix, twelve-question assessment, answer tracker, and an offline Town Hall view with a timer. It keeps accountability snapshots and original documents in a separate encrypted local store and produces reconstructable packet receipts. No requests are sent and nothing is published automatically.

- **[Start the Red Tape Dispenser](docs/red_tape/README.md)** — complete commands, examples, data contract, privacy boundaries, and limitations.
- Active module code: `src/flockoff_red_tape/`.
- Existing sensor runtime: `src/flockoff/`.
- New and existing tests: `TESTS/`.
- Original license: Apache-2.0, with upstream attribution preserved.

This bundle uses the exact v0.3.0 source ZIP linked in the [V1.0 release body](https://github.com/dkl101001/BLOOMCORE-NOW/releases/tag/V1.0). It does not claim that the release tag's Git source tree contains FLOCK OFF. That historical input was package `0.3.0+redtape.1`. The current combined package is `0.3.0+sensorconsole.2`, not a v0.4 sensor release.

## Install and run

Python 3.12 is the verification target.

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.lock
python3 -m pip install -e .
flockoff red-tape --help
```

Use the [fictional worked example](docs/red_tape/README.md#run-the-fictional-example) to generate your first packet. Replace and verify its fictional records and meeting rules before real use.


## Existing v0.3.0 runtime reference

### FLOCK OFF

FLOCK OFF is a passive, local-first evidence runtime for surveillance awareness
and public transparency. It normalizes receive-only sensor observations,
preserves provenance, estimates uncertainty regions, and produces reproducible
evidence receipts without exposing the observer's route by default.

## Repository layout

```text
README.md              You are here
src/flockoff/           Runtime source code
TESTS/                  Unit, privacy, replay, and battle tests
SCHEMAS/                JSON Schemas and SQLite migration
SIGNATURES/             Versioned candidate signatures and controls
config/                 Runtime defaults
hardware_profiles/      Explicit receiver capability profiles
docs/                   Architecture, interfaces, privacy, and limitations
tools/                  Verification and clean-source ZIP builders
pyproject.toml           Python package metadata
LICENSE / NOTICE        Apache-2.0 license and attribution
```

## Install

Python 3.12 is the verified target.

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.lock
python3 -m pip install -e .
```

## Test

```sh
python3 -m unittest discover -s TESTS -p 'test_*.py' -v
python3 tools/verify_release.py
```

Run the test command above for the current count; the original baseline test-count claim is superseded.

## Run the live recursive Flock-You loop

The live path consumes the external receive-only Flock-You JSON stream plus a local pose stream. It does not transmit to or control observed infrastructure. See `docs/LIVE_REALITY_LOOP.md` and `config/targets.example.json`.

```sh
flockoff live-flock-you \
  --flock-you-input /dev/ttyACM0 \
  --pose-input /run/flockoff/pose.fifo \
  --targets config/my_targets.json \
  --signature SIGNATURES/candidate/flock_you_wifi_assertion_v0.1.0.json \
  --ledger /var/lib/flockoff/live.sqlite \
  --receiver-id rx-car-1 \
  --flock-you-build-ref <commit-or-build-you-actually-flashed>
```

A silent bounded traversal creates a failure packet and discovery campaign automatically. Because the upstream JSON does not prove channel-scan completeness, the reference campaign immediately records `SENSING_APERTURE_INSUFFICIENT` rather than pretending silence means absence. Compatible live detections generate local alerts; once an emitter has sufficient geometry across two explicit pose `pass_id` values, the runtime creates an RF-only support region, private node revision, and evidence receipts.

## Run the live Remote ID loop

The v0.3 path consumes a local decoded Remote ID NDJSON stream plus a separate
observer-pose stream. Radio reception/decoding stays behind the external adapter
boundary; FLOCK OFF performs normalization, custody, basis separation, tracking,
node assembly, private alerting, and receipts.

```sh
flockoff live-remote-id \
  --remote-id-input /run/flockoff/remote-id.ndjson \
  --pose-input /run/flockoff/pose.ndjson \
  --ledger /var/lib/flockoff/remote-id.sqlite3 \
  --receiver-id rid-rx-1 \
  --remote-id-receiver-build-ref v3.7.0@60b4320 \
  --remote-id-core-build-ref ec44332f67be38035d1f9dace4ce8e0bdf3cc2c8
```

See `docs/LIVE_REMOTE_ID.md` for the exact input contract and claim ceilings.

## Run the offline replay

```sh
export FLOCKOFF_ROTATION_SECRET_HEX=000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
export FLOCKOFF_ROUTE_KEY_BASE64=AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=

flockoff replay \
  --input TESTS/synthetic_traces/fixed_two_pass.jsonl \
  --signature SIGNATURES/candidate/flock_you_wifi_assertion_v0.1.0.json \
  --ledger /tmp/flockoff-ledger.sqlite \
  --output /tmp/flockoff-replay.json
```

Those values are public test keys. Generate independent secrets before handling
real observations.

## Implemented now

- live receive-only Flock-You USB/NDJSON ingestion plus pinned replay normalization
- live decoded Remote ID ingestion, typed message custody, basis-separated
  mobile-track revisions, private nodes/alerts, and receipts
- strict observation, pose, lineage, node, receipt, and export schemas
- rotating keyed identifier minimization
- encrypted restricted receiver poses
- append-only SQLite evidence and node-revision ledger
- candidate signature evaluation with explicit claim ceilings
- repeated-pass, uncalibrated, nonzero-area RF support regions
- source-lineage independence counting
- deterministic receipt verification and replay
- bounded live target windows that turn detector misses into immutable recursive discovery campaigns
- append-only discovery-campaign revision custody
- approval-gated, allowlisted, route-safe local-draft export

## Not implemented or not field-validated

There is no native radio driver or active radio control in FLOCK OFF; live v0.2
and v0.3 consume external receive-only streams. The Remote ID host loop is
implemented, but exact radio/driver/bridge combinations remain unverified until
their receive-only over-air audits pass. There is still no calibrated
Flock-specific classifier, calibrated location probability, 5 GHz generic
receiver, SDR, AoA, TDoA, or public auto-publication. See `docs/LIMITATIONS.md`.

The runtime contains no connection attempts, interference, deauthentication,
spoofing, credential capture, exploitation, device control, or transmission
capability.

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/INTERFACES.md`
- `docs/THREAT_AND_PRIVACY_MODEL.md`
- `docs/REMOTE_ID.md`
- `docs/LIVE_REMOTE_ID.md`
- `docs/REMOTE_ID_SOURCE_LOCK.md`
- `docs/LIMITATIONS.md`
- `SECURITY.md`

## License

Original FLOCK OFF material is licensed under Apache-2.0. Third-party projects,
dependencies, standards, and datasets retain their own licenses and terms. See
`LICENSE`, `NOTICE`, and `THIRD_PARTY_NOTICES/NOTICE.md`.

## v0.1.1 recursive adversarial patch

v0.1.1 adds a runtime recursive discovery state machine. A bounded detector miss
creates an immutable failure packet and a nonterminal discovery campaign rather
than an absence claim. Signature drift can reactivate discovery only after
coverage is evaluated. Vendor/product/revision/emitter separation is now explicit;
RF behavior is never inherited across a vendor family by name. See
`docs/RECURSIVE_DISCOVERY.md` and `docs/ROADMAP_v0.1.1.md`.

## v0.2 live recursive reality loop

v0.2 binds live Flock-You observations and local pose to the recursive failure machinery. A bounded real-world miss now creates coverage evidence, a failure packet, and an immutable discovery-campaign revision chain automatically. The runtime explicitly treats incomplete scan telemetry as developmental pressure rather than target absence. See `docs/LIVE_REALITY_LOOP.md`.

## v0.3 live mobile / airborne loop

v0.3 binds decoded live Remote ID and separately restricted observer pose to
immutable broadcast-basis mobile tracks. A moving track produces a private drone
node, local alert, and deterministic receipts without claiming surveillance
capability, authenticated identity, compliance, a dock, or Remote-ID/RF fusion.

## Release the Hounds

The records desk has an optional keyboard-focusable **Release the Hounds (sound)** button. Clicking plays a short synthetic bark on supported Windows audio and displays **THE HOUNDS HAVE ACKNOWLEDGED YOUR PRESENCE.** Startup is silent. Other platforms or audio failures retain the text response. Repeated clicks restart the short sound; closing the desk stops it. This control never changes cases, starts capture, or sends anything.
