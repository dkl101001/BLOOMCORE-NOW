# Schema set v1.x

All canonical schemas use JSON Schema Draft 2020-12, strict outer objects and
content-addressed IDs. Adapter extension fields are an explicit schema
allowlist; downstream algorithms cannot consume a newly proposed extension
without a schema and extractor version.

Core invariants:

- observations and later derivations are different immutable objects;
- routes live in restricted pose objects; observations carry references only;
- absence claims require a complete coverage reference;
- uncalibrated classification/location probabilities are null;
- inferred location geometry is never a point;
- Remote ID parsing/authentication/consistency are distinct;
- node motion, asset kind, evidence and lifecycle are orthogonal;
- receipts hash a deterministic body separately from attestation;
- raw observation objects are not public-export objects.
- public projection requires an exact-request approval artifact and is limited
  to a route-free `LOCAL_DRAFT`.

Where a non-receipt event carries `content_hash`, the digest is computed from
the canonical object with that one field omitted. Receipt hashing instead uses
the explicitly separate `body` and is never self-referential.

The included fail-closed validator covers every keyword used by these schemas
and is exercised by the test suite. A release gate still requires a second,
standards-complete Draft 2020-12 validator across all positive/negative fixtures.

`remote_id_message` is implemented for decoded upstream records in v0.3.
`remote_id_snapshot` remains `DESIGN_ONLY`; the runtime does not claim raw-frame
decoding, full message-set completeness, conformance certification, or
authentication. `mobile_track` and `local_alert` keep broadcast basis and claim
ceilings explicit.

`migrations/0001_initial.sql` creates immutable ledger, node-revision, source-edge and encrypted-pose tables. `migrations/0002_recursive_live_campaigns.sql` adds immutable discovery-campaign revision custody. Migrations are append-only, declared in the manifest, checksummed, and applied in order; old evidence is never rewritten in place.

v0.1.1 adds recursive failure, discovery, drift, validation-decision and
surveillance-asset schemas. Unresolved campaigns require a next test; detector
misses and drift events explicitly forbid absence inference; RF behavior cannot
inherit across vendor product/revision boundaries.


v0.2 adds `target_expectation` for bounded live target traversals and corrects failure-packet evidence so a true detector miss may carry zero detection observations when it is bound instead to coverage/context evidence. Live target priors must retain source references; public target coordinates are never injected into RF-only localization.

v0.3 adds typed decoded Remote ID message events, immutable mobile-track
revisions, and private local-alert objects. Observer poses remain encrypted and
are represented in tracks only by association references.
