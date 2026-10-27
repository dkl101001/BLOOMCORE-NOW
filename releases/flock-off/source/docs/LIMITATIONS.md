# Current limitations and activation gates

The sensor-console successor adds a Windows/POSIX serial transport and managed
session workflow described in [SENSOR_CONSOLE.md](SENSOR_CONSOLE.md). Host tests
pass, but no physical receiver or over-air validation has been performed. Raw
NMEA conversion, Remote ID radio decoding and complete scan-coverage telemetry
remain external/unimplemented. The remaining field gates below still apply.

The checked-in code is a verified local-first reference runtime with live external Flock-You ingestion. It is not yet a fully field-validated multi-band sensor product.

The following capabilities remain disabled or unclaimed:

- verified Flock-specific probability or model attribution, pending a labeled
  target and ordinary-device control corpus;
- live Flock-You USB/NDJSON ingestion is implemented with rotating identifier minimization, encrypted pose custody, bounded target windows, recursive miss handling, and two-pass private node assembly; field hardware/firmware combinations still require deployment-specific validation and the host does not claim complete scan coverage from stream continuity;
- generic unknown-emitter capture and 5 GHz coverage, pending exact hardware and
  driver bindings;
- the live decoded Remote ID host loop and typed-message/track/node/alert
  receipts are implemented; exact BLE/Wi-Fi radio, driver, and decoder-bridge
  combinations remain `DECLARED`, not bench/field verified, pending
  per-transport receive-only audits and licensed standards custody;
- calibrated localization probabilities, calibrated mobile/static classification, AoA,
  and TDoA, pending controlled corpora and capable calibrated hardware;
- full database/WAL encryption and OS-keystore binding;
- public combined datasets or automatic publication, pending source-license,
  privacy, moderation, and redistribution review;
- target-platform dependency hashes, power-loss testing, corruption injection,
  disk-full recovery, and cross-platform reproducible builds.

Where a gate is open, the runtime fails closed or emits an uncalibrated,
inconclusive, or disabled state.
