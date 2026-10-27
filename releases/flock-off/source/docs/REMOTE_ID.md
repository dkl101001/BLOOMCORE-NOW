# Remote ID reception architecture

v0.3 implements the host-side live decoded Remote ID evidence path. Radio
reception and frame decoding remain external adapters; the active FLOCK OFF
runtime consumes their local NDJSON output and contains no network or radio-
transmission code.

## Semantic boundaries

Remote ID is an evidence surface, not an authority. The runtime preserves these
separations:

- observer pose versus emitter-reported aircraft position;
- Broadcast Remote ID trajectory versus RF-inferred trajectory;
- decoded syntax versus semantic consistency;
- message presence versus cryptographic authentication;
- aircraft observation versus surveillance-capability classification;
- repeated endpoint evidence versus dock/base proof.

Standard Remote ID control-station location and broadcast-module takeoff
location are not interchangeable. v0.3 validates a supplied restricted
operator/takeoff position and discards it at the privacy firewall because a
separately encrypted Remote ID operator-location vault is not implemented.

## Implemented objects

One accepted decoded record can produce:

1. a minimized normalized observation;
2. a typed `remote_id_message` event with decoder/source locks;
3. an optional restricted observer-pose association;
4. an immutable `mobile_track` revision labeled `BROADCAST_REMOTE_ID`;
5. after measured movement, a private node revision;
6. a private local alert explicitly carrying
   `surveillance_capability_claim=false`;
7. deterministic receipts for message typing, association, tracking, node
   assembly, and alerting.

Track points contain only emitter-broadcast coordinates. Observer coordinates
remain encrypted in restricted pose custody and are referenced only by pose
association IDs.

## Invalid, missing, and contradictory evidence

`MALFORMED`, `INCOMPLETE`, `UNVERIFIED`, and `CONTRADICTED` are retained states,
not score penalties. Malformed or contradicted records do not enter a clean
track. Out-of-order time and source-clock contradictions create immutable
contradiction evidence rather than rewriting previous points.

Receiver health and explicit loss counts do not establish absence. v0.3 does
not infer “no aircraft,” “radio silent,” or “noncompliant” from a quiet stream.

## Authentication and identity

`parsed` never means `authenticated` or truthful. Caller-supplied authentication
claims are reduced to `NOT_CHECKED`; only a future independently verified trust-
anchor receipt may introduce an authenticated state. Raw UAS identifiers are
replaced with rotation-scoped keyed hashes in operational data.

## Deferred work

`remote_id_snapshot` remains design-only. v0.3 does not yet implement raw-frame
decoding, full message-set freshness assembly, authentication verification,
Remote-ID/RF fusion, calibrated joint motion estimation, or dock/base inference
inside the live loop. Those functions cannot be implied by the existence of a
decoded message stream.

See `docs/LIVE_REMOTE_ID.md` for the executable contract and
`docs/REMOTE_ID_SOURCE_LOCK.md` for current source custody.
