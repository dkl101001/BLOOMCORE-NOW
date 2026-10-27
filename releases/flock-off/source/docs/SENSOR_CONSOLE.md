# Sensor console: working host, hardware validation pending

This candidate adds Windows/POSIX serial host ingestion, separate replay mode,
managed session storage and a native operator console. It retains the records
desk; its toolbar can open the sensor console. The earlier v0.2 source directory
and ZIP are preserved unchanged.

## Start

On this Windows machine, double-click `tools/Start Sensor Console.cmd`.
The candidate has a local `.venv` with pyserial 3.5 installed. The launcher uses
it first. The source ZIP excludes that environment, private sessions and keys.

On another machine, install Python 3.12+ with Tk, create a virtual environment,
install `requirements.lock` plus `pyserial==3.5`, then install this package or run
`python tools/start_sensors.pyw`. The installed command is `flockoff-sensors`.
Serial support is an optional dependency: `pip install ".[serial]"`.

Use this console for the managed capture workflow. The original
`live-flock-you`/`live-remote-id` CLI transport remains a legacy interface and does
not acquire the console's session receipt, cancellation or preflight behavior.

## Without hardware

1. Click **Load synthetic fixture**. This explicitly selects REPLAY, records a
   synthetic build label and loads timestamped sensor/pose fixtures.
2. Click **Preflight**, then **Start session**. Choose a private output parent and
   a new external key filename. The key must be outside the new session folder.
3. Watch candidate matches, evidence records and completion status. The worker
   writes a real SQLite ledger using the existing normalization/inference path.
4. Click **Verify saved session**, select its directory and original external key.
   This checks receipt authentication, file hashes, database integrity, encrypted
   configuration and the decryption/custody hashes of retained observer poses.

This exercises software against invented input. It is not live RF reception and
does not upgrade any hardware profile to bench- or field-verified.

## With a compatible receiver

Set LIVE_SERIAL, select the decoded protocol, and enter `serial:COM3` (or the
actual COM port shown by **List serial devices**). POSIX endpoints use
`serial:/dev/ttyACM0`. Enter the actual flashed firmware/build, receiver ID and
baud rate. Remote ID also requires the actual decoder build. Flock-You requires
a hash-verified signature JSON; the bundled candidate is under
`SIGNATURES/candidate/`.

The host only calls serial open/read/close. It disables software and hardware
flow control and requests deasserted DTR/RTS before opening. Drivers may still
pulse control lines; inspect this on the physical receiver. Nothing here proves
the receiver firmware is receive-only over the air. No firmware flashing, radio
configuration commands, socket serial URLs or active RF operations are included.

Observer pose is optional. A separate pose port must already emit the documented
NDJSON pose format. **Raw NMEA/GPSD is not supported by this console.** With no
pose feed, Flock-You observations and candidate matches can be retained, but RF
localization cannot run. Remote ID broadcast positions remain distinct from
observer position. Never substitute the expected target coordinates for observer
pose. The host never invents a pose or a pass boundary.

Two explicit pose `pass_id` values and sufficient geometry are required for the
existing Flock-You region estimate. Those estimates remain uncalibrated. Targets
are optional; when used, their file must contain independently supported target
expectations. The example target coordinates are not real deployment facts.

## Replay format

Every replay record must have a timestamp with a timezone. Both input files must
be ordered by time. Pose records use `observed_at_utc`. Remote ID records may use
that field directly. Flock-You or status events without source time use:

```json
{"received_at_utc":"2026-10-27T12:00:00Z","payload":{"event":"config"}}
```

This timestamp must come from the original capture, not a guessed clock.
The host merges files by recorded time, taking pose first at equal timestamps.
It rejects missing/out-of-order timestamps rather than restamping historical
input as current. Malformed replay framing fails the session. Invalid decoded
records with usable framing are counted as quarantined; raw input is not copied
into diagnostics.

## Health, limits and recovery

- CONNECTED means a serial device opened. SILENT means no complete record arrived
  for the silence interval. Neither proves RF coverage or target absence.
- Device errors stop the session. Reconnect requires an explicit new session;
  the host does not silently reconnect under an unchanged capture identity.
- Stop cancels bounded serial reads, closes readers and the worker's database,
  and seals a STOPPED receipt. The default session bounds are 10,000 input
  records and one hour; reaching a bound reports LIMIT_REACHED.
- A finite input with no accepted sensor records is NO_USABLE_SENSOR_RECORDS.
  Rejected decoded records produce COMPLETED_WITH_REJECTIONS. Failure is FAILED,
  never a successful negative detection result.
- Reader queues are bounded with backpressure. This bounds host queued memory,
  but does not prove the receiver or OS buffer dropped nothing. UI preview may
  skip messages if it cannot keep up; the private event log is written first.
- A process crash can leave `started.json` without `receipt.json`. Treat that
  session as incomplete. Do not manufacture a successful closeout. Preserve the
  directory/key for recovery; automatic crash repair is not implemented.

Each new directory contains a normalized evidence ledger, encrypted capture
configuration, minimal diagnostic log, start marker and final receipt. Raw
capture bytes are not archived. The receipt uses an **HMAC**, not a public-key
signature or independent witness: it authenticates the listed files to the
separate secret. It cannot prove radio truth, who operated the receiver, or
prevent a holder of that secret from producing different receipts.

Windows session directories get current-user inheritable ACLs; observer poses
and config use authenticated encryption. The entire SQLite database is **not**
encrypted. Normalized observations and metadata remain readable to an account
that can access it. Use appropriate protected storage for real field work.
Keep session directories and external keys backed up separately. Verification
can distinguish matching bytes and decryptability from a successful capture.

## What has been tested

The full suite passes **143 tests**, including twenty new transport/session
tests: fragmented UTF-8, line-size limits, URL refusal, silent serial reads,
disconnects, bounded-queue cancellation, pyserial configuration, timestamped
replay merge, both evidence pipelines, wrong keys, file tampering, missing input,
failed sessions, stop, record limits, and diagnostic minimization.

`tools/check_sensors.py` runs the real Tk controls and worker, loads the synthetic
fixture, checks candidate-match presentation, persists a node and verifies the
session. `tools/check_desktop.py` checks the retained records desk.

No serial ports were enumerated on the current host during this run. Physical
USB/driver behavior, actual reception, receiver emissions, RF range, calibration,
clock accuracy, loss accounting and field identification accuracy are NOT RUN.
Window capture returned a blank image despite an exposed native window tree;
visual layout/accessibility has not been certified by that tool.

See [Hardware and first field test](SENSOR_HARDWARE.md) for the remaining physical
steps. No SDR, 5 GHz capture, direction finding or Remote ID radio decoder was
implemented by adding this console.
