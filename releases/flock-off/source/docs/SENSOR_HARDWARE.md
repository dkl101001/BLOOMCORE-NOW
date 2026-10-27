# First receiver and measurable acceptance

Checked against primary project/manufacturer documentation on October 27, 2026.
No hardware has been purchased, flashed, opened, or tested for this candidate.

## First integration target

Start with a **Seeed Studio XIAO ESP32-S3**, its compatible antenna, and a USB
**data** cable. This is the directly documented Flock-You board/build target.
An enclosure is useful for handling; the buzzer is optional for host ingestion.
Consult the [manufacturer's board guide](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/)
for power, antenna and USB details. Do not substitute a similarly named board
without checking its firmware target and USB behavior.

The [Flock-You upstream](https://github.com/colonelpanichacks/flock-you) describes
USB JSON output and a 2.4 GHz Wi-Fi receiver, with the documented default scanning
channels 11/6/1. The project's claims are upstream assertions, not validation
performed here. Record the exact commit, build environment, configuration and
firmware binary hash used; do not silently replace the pinned candidate's
assumptions with a moving upstream branch.

The first test can run without GPS: prove that serial records reach the host and
that ordinary-device controls do not become unjustified identity claims. Add a
pose source only after reception works. A USB GNSS puck generally supplies NMEA;
this console needs a separately implemented and validated NMEA-to-pose-NDJSON
bridge before that puck is useful for localization. Do not buy an expensive
location/direction-finding setup on the strength of the current software tests.

## Remote ID is a separate integration

[OpenDroneID's Android receiver](https://github.com/opendroneid/receiver-android)
is an external reference for Bluetooth/Wi-Fi Remote ID reception. Its
[supported-phone notes](https://github.com/opendroneid/receiver-android/blob/master/supported-smartphones.md)
must be checked for a particular phone and transport. The current FLOCK OFF host
accepts decoded Remote ID NDJSON; it does not automatically ingest that Android
app and does not include its radio decoder. An exact export/USB bridge remains
to be selected, implemented and tested. Do not claim all BLE/Wi-Fi transports
from one successful message or buy a phone based solely on this document.

## Acceptance sequence

1. **Record the assembly:** exact board, antenna, firmware commit/binary hash,
   configured channels, baud, OS, USB driver, host version and test conditions.
2. **Bench the USB path:** verify framing, boot behavior and field meanings;
   unplug/reconnect and confirm the host produces a failed/stopped session rather
   than continuing a fictitious healthy capture. Inspect DTR/RTS reset behavior.
3. **Audit receive-only operation:** independently measure the assembled
   receiver's emissions in an appropriate controlled setup. Host read-only code
   alone does not establish an over-air receive-only device.
4. **Collect labeled controls:** consenting/owned ordinary devices and independently
   established target examples. Record target/control labels separately from
   detector output. Include no-signal, shared-prefix and nonmatching frames.
5. **Report measured error:** count hits, misses and false candidate matches per
   stated test condition. No observation is not an absence claim when channel
   coverage, power, timing or receiver continuity is incomplete.
6. **Validate pose before localization:** independently compare position/time
   accuracy, prove receiver-ID pairing, and collect explicit passes with useful
   spatial diversity. Keep observer routes private. Do not turn an uncalibrated
   support region into a precise location or confidence percentage.
7. **Exercise custody and recovery:** stop, verify the receipt with the external
   key, reopen the database, decrypt retained poses, and recover an independent
   copy. Power-loss/disk-full behavior requires further testing before deployment.

Only after measured receipts exist should an exact hardware/firmware profile be
considered for BENCH_VERIFIED or FIELD_VERIFIED. Those labels are not set by this
console, by a source pin, or by passing synthetic tests.
