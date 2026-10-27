# Live Flock-You reality loop — v0.2

## Purpose

Make the v0.1.1 recursive machinery touch a real receive-only Flock-You stream.
The live loop has two valid outcomes when traversing an independently established
target region:

```text
compatible signature observed
  -> normalized observation
  -> signature match
  -> local alert
  -> positioned emitter evidence
  -> two explicit passes + sufficient spatial diversity
  -> RF-only support region
  -> private node revision
  -> spatial + node evidence receipts

no compatible signature observed
  -> bounded traversal evidence
  -> sensor coverage evidence
  -> FAILURE_PACKET
  -> DISCOVERY_CAMPAIGN/HUNTING
  -> SENSING_APERTURE_INSUFFICIENT when coverage cannot be proven complete
  -> explicit next tests
```

Neither branch proves that a nearby RF emitter is the exact mapped target without
additional localization/corroboration.

## Why a miss has no observation

A detector miss is the absence of a matching detection **inside a bounded test**.
Requiring a detection observation to represent a miss was an ontology error in
v0.1.1. v0.2 permits `observation_refs=[]` when the failure is instead bound to
coverage and/or contextual evidence. In live operation the contextual evidence
contains restricted pose references and the independent source references that
establish the target prior.

## Coverage honesty

The upstream Flock-You JSON stream currently provides detections/configuration,
not proof that every intended Wi-Fi channel was actually observed throughout a
target window. Therefore the live reference path cannot declare complete RF
coverage merely because USB remained connected.

The first recursion from a silent target window is intentionally:

`HUNTING -> SENSING_APERTURE_INSUFFICIENT`

This is not a dead end. It is the executable instruction to improve the receive
aperture or telemetry and repeat the target/control capture.

## Local streams

The Flock-You source can be a USB CDC path such as `/dev/ttyACM0`, a FIFO, a
regular NDJSON capture, or stdin. The pose source is separate local NDJSON. The
reference runtime imports no network stack.

Pose records contain at minimum:

```json
{
  "receiver_id": "rx-car-1",
  "observed_at_utc": "2026-08-23T16:00:00Z",
  "latitude": 36.0,
  "longitude": -86.0,
  "horizontal_accuracy_m": 4.0,
  "clock_uncertainty_ms": 20.0,
  "source": "GNSS",
  "pass_id": "northbound-pass-1"
}
```

Routes are stored only in the encrypted restricted-pose table. Failure and
campaign objects reference opaque pose IDs; public export remains separate and
approval-gated.

## Example

```sh
flockoff live-flock-you \
  --flock-you-input /dev/ttyACM0 \
  --pose-input /run/flockoff/pose.fifo \
  --targets config/my_targets.json \
  --signature SIGNATURES/candidate/flock_you_wifi_assertion_v0.1.0.json \
  --ledger /var/lib/flockoff/live.sqlite \
  --receiver-id rx-car-1 \
  --flock-you-build-ref 7e969663eade07833603bad86cb156338e895583
```

The target file format is shown in `config/targets.example.json`. The evidence
reference and coordinates in that example are placeholders and must be replaced
with locally justified values.

## Deliberate limitations

- This path does not make current Flock-You scan coverage complete.
- It does not equate a compatible hit in a geofence with exact target identity.
- It does not infer absence from silence.
- Live static node assembly requires at least two explicit pose `pass_id` values; the runtime does not invent pass boundaries from RSSI.
- RF-only localization never consumes the public target coordinate prior.
- It does not create calibrated probability.
- It does not yet bind automatic live signature drift to target-specific prior
  match history; the v0.1.1 drift engine remains available and requires adequate
  coverage before confirmed drift.
- It does not add 5 GHz, cellular, SDR, BLE, Remote ID, AoA, TDoA, or active
  interaction with observed infrastructure.
