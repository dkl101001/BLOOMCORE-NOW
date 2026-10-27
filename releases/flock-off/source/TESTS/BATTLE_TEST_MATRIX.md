# Battle-test matrix

Status values: **PASS** executable now; **DESIGN PASS** structurally prevented or
documented but needs a field/fault harness; **BLOCKED** cannot honestly pass
without hardware/corpus/authority listed in the blocker.

| Scenario | Required result | Status / evidence |
|---|---|---|
| Hidden/disguised fixed node; no image | RF/public inference has no vision dependency | **PASS** — schema/runtime has no image field; synthetic replay produces RF-only polygon |
| Public pin displaced 80 m | RF-only output byte-identical; conflict retained on fusion | **DESIGN PASS** — `public_prior_used=false`; fusion implementation/calibration blocked |
| Five websites mirror one OSM node | One OSM root, not five | **PASS** — lineage unit test; municipal root yields lower count 2 |
| Ordinary hardware shares target prefix | Prefix alone cannot yield vendor claim | **PASS** — candidate gate is claim-capped `RF_PATTERN`; no active signature |
| Locally administered/random MAC | Correctly typed and HMAC-minimized | **PASS** — `82:6b:f2` test, raw MAC absent |
| Firmware invalidates old signature | Old receipt replays; new version degrades/retires | **DESIGN PASS** — immutable signature snapshot/retirement policy; drift corpus blocked |
| 2.4-only receiver misses 5 GHz | `UNSUPPORTED`, never absence | **PASS** — capability and coverage unit test |
| Severe urban multipath/moving traffic | Region stays conservative; no loudest-point collapse | **DESIGN PASS** — rank support region/no exact point; held-out multipath calibration blocked |
| One moving receiver | Movement-based uncalibrated region, not triangulation | **PASS** — `RANK_RSSI_SUPPORT` polygon |
| Two uncalibrated scalar-RSSI receivers | Compare ranks only within each receiver/pass; never claim differential RSSI | **PASS gate / BLOCKED calibration** — executable negative control; shared-calibration profile absent |
| Bearing-capable receivers | Wedge intersection + bearing uncertainty; triangulation only with ≥2 | **BLOCKED** — no bearing hardware/implementation profile |
| TDoA receivers | Same-packet timestamps and clock bound required | **PASS gate / BLOCKED hardware** — 1 µs refused, 10 ns/30 m gate allowed |
| Observer and drone both moving | Separate observer pose and basis-labeled emitter track | **PASS** — live restricted pose association and broadcast-only track points; calibrated joint tracker blocked |
| Remote ID present | `BROADCAST_REMOTE_ID`; caller authentication claim cannot become verified | **PASS** — live typed decoded message, track, node, alert and receipt path; trust-anchor verification blocked |
| Remote ID malformed | Malformed/partial state; no crash/invented position | **PASS** — live malformed evidence state produces no track; mutation corpus blocked |
| Remote ID absent | Inconclusive unless transport coverage complete/applicable | **PASS** — live health/loss event forces `absence_claim_permitted=false` |
| RID inconsistent with RF | Parallel tracks + contradiction, never silent correction | **DESIGN PASS** — RID contradiction custody implemented; RID/RF fusion remains blocked |
| Repeated endpoints near dock | `ENDPOINT_CLUSTER`, not proof | **PASS** unit test |
| Three flights/two dates + fixed root | At most `PROBABLE_DOCK_OR_BASE` | **PASS** structural test |
| Official record locates dock | `DOCUMENTED_DOCK_OR_BASE` with source root | **PASS** structural test; no real record imported |
| Raw-data seizure | Route encrypted/separate; residual DB risk explicit | **PASS column test / BLOCKED field** — full DB/WAL+keystore pending |
| Malicious/mistaken community submission | Quarantine, provenance, contradiction/retraction | **DESIGN PASS** — strict schema/policy; moderation UI not implemented |
| Route begins at home | No route, exact observation time or identifier in export | **PASS** allowlist/leak test |
| Oversized line, duplicate keys, NaN | Reject/quarantine without parser ambiguity | **PASS duplicate/NaN; line limit implemented; million-case fuzz blocked** |
| Clock jumps backward | New clock epoch; no cross-epoch TDoA/fusion | **DESIGN PASS** timing schema; live clock detector blocked |
| Power loss/write acknowledgment | No acknowledged-event loss | **BLOCKED** — 1,000 process-kill injections not run |
| Disk full/sensor unplug | Explicit health/loss gap, no false acknowledgment | **DESIGN PASS** schemas; fault injector blocked |
| Corrupt storage | Detect before inference, read-only recovery | **BLOCKED** — corruption harness not implemented |
| Offline operation | Replay/inference/receipt/export use no network | **PASS code audit and offline tests**; local UI not implemented |

Contradictions are ledger events, not score penalties to be averaged away.
