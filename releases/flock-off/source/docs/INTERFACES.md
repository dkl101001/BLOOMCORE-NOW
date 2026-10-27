# Interface contracts

## Adapter envelope

An adapter transport is bounded UTF-8 NDJSON over stdin/stdout or a Unix-domain
socket. Maximum line size is 1 MiB in the reference CLI. Duplicate JSON keys,
NaN/Infinity, invalid UTF-8, unknown event types, impossible tier/method pairs,
and unknown major schema versions are quarantined with an ingest decision. A
production adapter must provide:

- envelope schema ID/digest;
- adapter ID/version/commit and process instance;
- sensor boot ID and source sequence when available;
- host UTC receive time and monotonic receive time;
- source clock domain/uncertainty and clock-epoch ID;
- privacy-classed raw-record digest and bounded payload type (keyed HMAC in
  operational mode; ordinary SHA-256 only inside restricted research custody);
- exact hardware capability-snapshot reference;
- privacy class and transform version.

The current Flock-You source JSON lacks several of these. The host fills only
facts it can observe and writes `null`/`HOST_RECEIPT_ONLY`; it never invents a
source sequence, packet hash, source time, IE vector, or scan-completeness state.

## Observation contract

`Observation` is capture-time evidence and immutable. It references a restricted
pose rather than copying coordinates. A source-reported tier/method remains
measurement metadata. A FLOCK OFF `SignatureMatch` is a later immutable event
that references both the observation and exact signature content hash.

Identifiers default to session-scoped keyed HMAC. Raw unrelated MAC/BLE/RID
identifiers never enter operational tables. Research-raw retention is a separate
explicit mode, encrypted and excluded from publication.

## Public assertion contract

The current `public_evidence` object represents one normalized assertion from an
exact artifact—not an entire webpage as one lineage. It carries parents,
authority role, independence class, claim geometry/uncertainty, source locator,
license/terms and transform version. An importer must split a council packet's
original action from copied vendor product text.

## Node revision contract

Motion, asset-kind hypothesis, evidentiary state and lifecycle are orthogonal.
Location is null or a nonzero-area circle/ellipse/polygon/trajectory envelope.
No inferred `POINT` exists. `probabilities` must be null when calibration state
is `UNCALIBRATED`. Each revision references exact evidence, measurement/source
lineages, contradictions, parent hash, and receipt.

## Receipt contract

The canonical representation used by v0.1 is sorted-key compact UTF-8 JSON with
finite numbers. The deterministic `body` is hashed separately from an optional
timestamped/signed attestation. A release implementation must replace/confirm
this with RFC 8785 JCS across all supported languages before cross-language
receipts are accepted; numeric inputs must be quantized or declare a tolerance
class.

Node creation uses an observation-to-pose receipt per association, a spatial
receipt that binds those associations, keyed pose digests, pass partition and
RF region, and a node-assembly receipt that binds the complete node body **excluding only its own
`receipt_id`**. The final node inserts that node-assembly receipt ID, avoiding a
self-referential hash while making every other field reconstructable. Before a
receipt enters the ledger, every input reference is resolved against immutable
event, restricted-pose or prior-node custody and its claimed hash must match.
The node receipt input set must equal the node's full evidence, measurement,
contradiction and prior-revision derivation set; empty or foreign closures fail.

## Failure/backpressure contract

Every adapter eventually accounts for:

`received = accepted + duplicate + quarantined + explicitly_lost`

Storage acknowledgment occurs after a durable transaction. Disk-full, sensor
disconnect, clock reset and lost sequence intervals create health/loss events.
No negative/absence conclusion is permitted without a matching complete
coverage interval.

## v0.2 live Flock-You reality-loop contract

`flockoff live-flock-you` consumes two local receive-only streams:

1. the external Flock-You UTF-8 NDJSON stream over USB CDC, FIFO, regular file,
   or stdin; and
2. a local pose/GNSS NDJSON stream carrying observer position.

No network transport is imported by the active runtime. A live target expectation
must bind an exact `target_asset_ref`, an exact signature version, bounded entry
and exit radii, at least one source/evidence reference establishing why the
physical target is expected there, the assumption under test, and explicit next
tests if the current detector misses.

A compatible signature observed while the receiver is inside the target window
suppresses an automatic miss, but it does **not** prove that the signal came from
that exact physical target. The emitted local event therefore states
`target_identity_proven: false`.

When the observer exits a bounded target window without a compatible match, the
runtime creates a `FailurePacket` even though there is no detection observation.
The packet binds:

- restricted encrypted pose references documenting the traversal;
- target-source/evidence references establishing the prior;
- a `SensorCoverage` record documenting the receive aperture; and
- the failed assumption and next-test seed.

Current Flock-You JSON does not report channel-scan completeness. Consequently,
the reference live loop marks that coverage `PARTIAL` and automatically advances
the discovery campaign to `SENSING_APERTURE_INSUFFICIENT`. Serial continuity is
never promoted to complete RF coverage, and a miss is never promoted to an
absence claim.

The operator supplies the flashed Flock-You build/commit reference with
`--flock-you-build-ref`. The host never infers that a live external sensor is the
repository-pinned commit merely because its JSON resembles the documented
schema.

## v0.3 live Remote ID contract

`flockoff live-remote-id` consumes a decoded local Remote ID NDJSON stream and a
separate observer-pose stream. It accepts `remote_id`, `remote_id_message`, and
`receiver_status` sensor events. The upstream receiver and core build references
are operator-supplied and enter every decoder/source lock; they are not inferred
from payload shape.

`sensor_boot_id` plus `source_sequence` forms the duplicate-accounting key. An
exact duplicate is counted and ignored. Reuse with different content is
quarantined. Source time, host UTC receipt time, host monotonic time, clock epoch,
and uncertainty remain separate fields. Excess source/host skew becomes
`CLOCK_CONTRADICTED` and cannot silently enter a clean track.

Aircraft points enter only a `BROADCAST_REMOTE_ID` track. Observer poses remain
encrypted and contribute only pose-association references. A moving broadcast
track can create a private drone node and local alert, but the alert is
uncalibrated, has no probability, and structurally sets
`surveillance_capability_claim=false`.

Receiver status and explicit loss accounting never permit an absence claim.
See `docs/LIVE_REMOTE_ID.md` for the complete contract.
