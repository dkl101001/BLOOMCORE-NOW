# Frozen runtime architecture

## Build decision

FLOCK OFF v0.3 is one offline host process plus replaceable, least-privileged
receive-only adapter processes. The working reference is Python 3.12 with one
runtime dependency (`cryptography` 46.0.0), SQLite append-only storage, strict
JSON contracts, deterministic derivations, and an allowlist-only export path.
There is no cloud service, network client, transmitter, vision dependency,
device-control surface, general ML model, or embedded third-party sensor code.

```text
EXTERNAL RECEIVE-ONLY SENSORS / OFFLINE PUBLIC SNAPSHOTS
                            │
                    bounded NDJSON
                            ▼
                 INGEST + PRIVACY FIREWALL
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
MINIMIZED IMMUTABLE EVENTS             ENCRYPTED ROUTE VAULT
Observation · Coverage · Assertion       Pose · sensitive raw research
        │                                       │
        └───────────────────┬───────────────────┘
                            ▼
                 DETERMINISTIC DERIVATIONS
 Match · Association · RF support region · RID message · Track · Conflict
                            │
                            ▼
                    REVISIONED NODE LEDGER
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   LOCAL ALERTS       EVIDENCE RECEIPTS    REVIEWED EXPORT
                                             (opt-in)
```

The fixed-infrastructure logical flow remains:

`SENSORS → NORMALIZED OBSERVATIONS → SIGNATURE MATCHES → SPATIAL INFERENCE → NODE LEDGER → ALERTS / RECEIPTS / OPT-IN PUBLICATION`

The v0.3 mobile path is:

`REMOTE ID RECEIVE → MOBILE OBSERVATION → BASIS SEPARATION → MOBILE TRACK → NODE LEDGER → LOCAL ALERT → RECEIPT`

The public-record path enters as immutable assertions and priors, never as
sensor observations. An RF-only region is computed and receipted before any
public prior can be fused. A changed public pin therefore cannot change the
RF-only output hash.

## Component boundaries

| Boundary | Accepts | Emits | Must never do |
|---|---|---|---|
| Sensor adapter | External serial/pcap/decoded replay from one pinned capability profile | Bounded event envelopes and coverage/health events | Transmit, associate, authenticate, probe, scan-request, control, exploit, or silently drop input |
| Public snapshot importer | Offline immutable snapshot + source custody record | Artifact and assertion events with derivation edges | Fetch during field capture; count mirrors as independent; infer installation from permit alone |
| Privacy firewall | Untrusted adapter event | Strict normalized event and identifier-vault action | Persist unrelated raw identifiers in operational tables; copy observer coordinates into observations |
| Route vault | Pose events + field key | AES-256-GCM ciphertext and content hash | Store key in database/log; export poses; claim protection on rooted/unlocked host |
| Event ledger | Schema-valid immutable events | Content-addressed lookups | Update/delete acknowledged evidence; hide corruption or disk-full loss |
| Signature matcher | Observation + immutable signature snapshot | Separate explainable match event | Mutate observation; exceed signature claim ceiling; output probability when uncalibrated |
| Static inference | Pose associations + observations + coverage | RF-only nonzero-area support region + diagnostics | Emit exact inferred point; call RSSI “triangulation”; fuse public prior invisibly |
| Mobile/RID estimator | Typed messages or separately derived RF regions | Basis-labeled tracks and contradictions | Merge broadcast/RF tracks silently; treat parsed ID as authenticated; prove dock from endpoints |
| Node ledger | Derived events, public assertions, contradictions | Append-only node revisions | Smooth contradictions away; reuse stale evidence without marking it |
| Receipt engine | Exact refs/hashes, code and source locks | Deterministic body/hash; optional separate attestation | Include wall time in deterministic body; self-hash recursively |
| Publication projector | Review-eligible node revisions/public assertions + exact local approval artifact | Allowlisted route-free `LOCAL_DRAFT` | Serialize internal observation/association refs, route, exact observation times, raw/pseudonymous IDs or RID operator/takeoff positions; emit a published state |

## Active runtime versus lineage archive

The active runtime contains only original FLOCK OFF code, schemas, fixtures and
the `cryptography` dependency. Flock-You, OpenDroneID, DeFlock, Kismet and other
projects remain upstream references or external adapters at exact commits. The
lineage archive preserves the original seed, rejected alternatives,
contradictions, and decision receipts. Nothing in the archive is importable by
the active Python package path.

## Static inference freeze

The implemented baseline is a deterministic local-plane grid with
within-receiver/within-pass RSSI-order consistency. It collapses packet
multiplicity to the median for each receiver/pass/pose block, expands the region
by pose accuracy, is insensitive to absolute RSSI-to-distance conversion, and returns an uncalibrated polygon. It is a
baseline replay oracle—not a calibrated production likelihood. The next
calibration implementation may add robust Student-t path-loss nuisance
parameters, pass tempering, censored non-detections, outlier mixtures and
adaptive boundary expansion behind the same `spatial_estimate` interface.

One moving receiver is movement-based localization. Uncalibrated scalar-RSSI
receivers are not directly compared; differential RSSI requires a shared
calibration receipt. Two or more calibrated bearings can be called
triangulation. TDoA requires same-packet hardware timestamps plus a clock-error
receipt satisfying the configured physical bound.

## Mobile and dock freeze

Remote-ID broadcast coordinates, RF-only regions and any later fused track are
separate artifacts with separate hashes. A single-receiver scalar RSSI series
defaults to `MOTION_UNRESOLVED`. Missing updates must widen a future calibrated
state envelope.

Dock/base ladder:

1. repeated endpoints → `ENDPOINT_CLUSTER`;
2. endpoint evidence with bias review → `POSSIBLE_BASE` (review state);
3. ≥3 distinct flights on ≥2 dates, overlapping endpoint regions, plus an
   independent fixed-RF or original documentary lineage →
   `PROBABLE_DOCK_OR_BASE`;
4. primary/official record explicitly locating the base →
   `DOCUMENTED_DOCK_OR_BASE`.

There is no endpoint-only “confirmed dock” state.
