# Live Remote ID reality loop — v0.3

v0.3 closes one receive-only mobile path:

```text
LIVE REMOTE ID RECEIVE
→ NORMALIZED MOBILE OBSERVATION
→ OBSERVER/EMITTER BASIS SEPARATION
→ MOBILE TRACK
→ NODE LEDGER
→ LOCAL ALERT
→ EVIDENCE RECEIPT
```

## Runtime boundary

FLOCK OFF does not contain a radio driver or fork an upstream receiver. The
`live-remote-id` command consumes decoded NDJSON from a local regular file,
FIFO, stdin, or character device. An exact upstream radio/driver/decoder bridge
must be supplied and identified by the operator. No socket or network client is
present in the active runtime.

The default source locks are OpenDroneID receiver-android release `v3.7.0`
(release page reports commit `60b4320`) and OpenDroneID core C revision
`ec44332f67be38035d1f9dace4ce8e0bdf3cc2c8`. They are external Apache-2.0
references; their source is not copied into FLOCK OFF. See
`docs/REMOTE_ID_SOURCE_LOCK.md`.

## Input contract

The sensor stream accepts exactly three event forms:

- `remote_id` or `remote_id_message`: one decoded Broadcast Remote ID message
  or message pack;
- `receiver_status`: explicit local adapter health/loss accounting;
- the separate pose stream accepts restricted GNSS/pose records only.

Each decoded Remote ID record should carry:

- `transport`: `bluetooth_legacy`, `bluetooth_5_long_range`, `wifi_nan`, or
  `wifi_beacon`;
- `validity`: `VALID`, `UNVERIFIED`, `INCOMPLETE`, `MALFORMED`, or
  `CONTRADICTED`;
- `sensor_boot_id` plus monotonic `source_sequence` for duplicate/loss custody;
- source observation time and uncertainty when available;
- a decoded aircraft position when the message contains one;
- the exact upstream build references supplied on the command line.

The runtime rejects duplicate JSON keys, non-finite numbers, oversized lines,
invalid coordinates, sequence reuse with different content, and unsupported
state values. An exact duplicate sequence is counted and not inserted twice.

## Basis separation

The aircraft trajectory is built only from coordinates explicitly labeled
`BROADCAST_REMOTE_ID`. Observer coordinates enter the encrypted restricted-pose
table and appear outside that vault only as pose and association references.
Observer motion is never subtracted from, added to, or silently fused with the
broadcast aircraft path.

Each track revision declares its basis. RF-only mobile observations remain a
separate future track family. v0.3 performs no Remote-ID/RF fusion.

## Claims

A valid Broadcast Remote ID record supports only the claim that a receiver
decoded an aircraft Remote ID broadcast with the recorded state. It does not
establish:

- cryptographically authenticated identity;
- compliance or noncompliance;
- ownership or operator identity;
- surveillance equipment or mission;
- a drone dock or base.

Caller-supplied authentication claims remain `NOT_CHECKED` unless a future
trust-anchor verifier produces a separate receipt. The local node classification
therefore includes `SURVEILLANCE_CAPABILITY_UNDETERMINED`, uses no probability,
and stays `PRIVATE_LOCAL`.

## Contradiction and absence

Malformed, contradicted, stale-clock, and out-of-order records are retained as
evidence states. They do not enter a clean mobile track. When two assertions
conflict, an immutable contradiction event is preserved rather than smoothing
the track.

No messages is not evidence of no aircraft or no Remote ID. A
`receiver_status` event records only the declared receiver health and explicit
loss counts; it always carries `absence_claim_permitted=false`. A negative
inference requires a separately demonstrated sensing aperture, which v0.3 does
not claim from stream continuity.

## Run

```sh
export FLOCKOFF_ROTATION_SECRET_HEX=<at-least-32-random-bytes-as-hex>
export FLOCKOFF_ROUTE_KEY_BASE64=<32-random-bytes-as-base64>

flockoff live-remote-id \
  --remote-id-input /run/flockoff/remote-id.ndjson \
  --pose-input /run/flockoff/pose.ndjson \
  --ledger /var/lib/flockoff/remote-id.sqlite3 \
  --receiver-id rid-rx-1 \
  --remote-id-receiver-build-ref v3.7.0@60b4320 \
  --remote-id-core-build-ref ec44332f67be38035d1f9dace4ce8e0bdf3cc2c8
```

The bridge that creates `/run/flockoff/remote-id.ndjson` is deployment-specific
and must be audited separately. Test keys and synthetic traces are not field
credentials or hardware validation.
