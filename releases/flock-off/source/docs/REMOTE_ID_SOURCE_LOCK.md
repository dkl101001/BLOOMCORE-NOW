# Remote ID source lock — audited 2026-08-23

This record separates protocol/legal authority, upstream implementation, and
FLOCK OFF field claims.

## Authorities and upstreams

| Source | Pin/date | Authority | License/custody | Disposition |
|---|---|---|---|---|
| [14 CFR Part 89](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-89) | current text accessed 2026-08-23 | U.S. Remote ID rule and required broadcast elements | U.S. government legal record; cited, not copied | research/semantic authority |
| [FAA Remote ID overview](https://www.faa.gov/uas/getting_started/remote_id) | accessed 2026-08-23 | FAA operational overview distinguishing standard Remote ID, broadcast modules, and FRIAs | U.S. government page; cited, not copied | research-only |
| [ASTM F3411-22a](https://store.astm.org/f3411-22.html) | F3411-22/22a family; accessed 2026-08-23 | message formats, transport methods, and minimum performance standard | copyrighted paid standard; no text copied | required external standard; not redistributed |
| [OpenDroneID receiver-android](https://github.com/opendroneid/receiver-android/releases/tag/v3.7.0) | tag `v3.7.0`; release page reports `60b4320`; 2026-07-24 | example receiver for Bluetooth, Wi-Fi NAN, and Wi-Fi Beacon | Apache-2.0; authors/contributors retained; no source copied | external adapter reference |
| [OpenDroneID core C](https://github.com/opendroneid/opendroneid-core-c) | `ec44332f67be38035d1f9dace4ce8e0bdf3cc2c8`; 2026-08-01 | encode/decode implementation for ASTM/ASD-STAN message structures | Apache-2.0; authors/contributors retained; no source copied | external decoder reference |

The OpenDroneID draft-specification repository explicitly warns that its early
draft documents are not compliant with the final standard, so it is not treated
as protocol authority: <https://github.com/opendroneid/specs>.

## Claims adopted by v0.3

- The FAA describes Remote ID as identification and location information
  broadcast from a drone and receivable by other parties.
- 14 CFR §§ 89.305 and 89.315 distinguish standard-aircraft and broadcast-module
  message elements; FLOCK OFF therefore does not collapse control-station and
  takeoff-location semantics.
- 14 CFR Part 89 requires non-proprietary broadcast using spectrum compatible
  with personal wireless devices; FLOCK OFF nevertheless claims only the exact
  transport reported by its bound receiver.
- OpenDroneID receiver-android supports multiple broadcast transports, but its
  own hardware notes show receiver/driver capability varies by device. A source
  build pin is not a hardware coverage receipt.

## Unresolved custody and field gaps

- The exact external NDJSON bridge and radio hardware are deployment choices;
  neither is vendored or falsely declared field-verified here.
- The receiver release page exposes tag `v3.7.0` and abbreviated commit
  `60b4320`; deployments must record the actual full build revision they use.
- FLOCK OFF has no licensed ASTM text in the repository and makes no standards-
  conformance certification claim.
- No v0.3 hardware/transport has completed the required shielded receive-only
  audit. The host loop is executable; the radio aperture remains declared, not
  bench- or field-verified.
