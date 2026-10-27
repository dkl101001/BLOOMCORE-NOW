# Release and capability acceptance gates

Unchecked gates are explicit blockers, not deferred claims.

- [x] Seed ZIP integrity: all 30 manifest entries matched exact byte counts and
  SHA-256 values; every JSON/JSONL parsed.
- [x] Active runtime contains no vendored upstream sensor code.
- [x] Repository dependencies/candidates have exact commit, license,
  attribution, authority, lineage and disposition records.
- [ ] Mutable web/public artifacts have imported byte snapshots and SHA-256.
- [x] Original FLOCK OFF license is frozen as Apache-2.0 with root `LICENSE`,
  `NOTICE`, package metadata, SBOM declaration and custody matrix.
- [ ] Target-platform dependency wheel hashes, full third-party license texts
  and complete file-level SBOM/notices are frozen.
- [x] Canonical objects reject unknown outer properties; positive replay examples
  pass the included validator; intended negative calibration example fails.
- [ ] A second standards-complete Draft 2020-12 validator and negative corpus
  pass on every schema.
- [x] Five mirrors plus one independent municipal source count as two roots.
- [x] Location output is a nonzero-area region with null uncalibrated confidence.
- [x] Raw unrelated identifiers are HMAC-minimized; pose is not copied into
  observation; public bundle excludes route and identifiers.
- [x] Remote ID broadcast and RF-only observations/tracks are distinct.
- [x] Every example node is reconstructable through evidence refs, exact
  signature hash, algorithm/source locks and deterministic receipt.
- [x] Active code contains no connection, interference, deauthentication,
  spoofing, credential, exploitation, device-control or transmitter capability.
- [x] Sixty-eight unit/battle tests pass in the audited environment.
- [x] Live decoded Remote ID produces typed message, basis-separated track,
  private mobile node, local alert, and deterministic receipt custody.
- [ ] Receive-only 30-minute shielded over-air audit passes for each live
  transport with zero attributable transmissions.
- [ ] One-million-record ingest accounting/fuzz corpus passes with zero silent
  drops and byte-identical ten-run output.
- [ ] Static/signature/mobile calibration gates in `CALIBRATION_PLAN.md` pass.
- [ ] 1,000 randomized power-cut kills lose zero acknowledged events; 100
  corruption injections are detected before inference; disk-full/unplug always
  emits health/loss state.
- [ ] Full database/WAL encryption, OS-keystore custody and field recovery are
  bound and audited.
- [ ] Two clean target-platform builds produce identical release artifacts,
  SBOMs, schema digests and test receipts, or every nondeterministic file is
  resolved as a blocker.

Capability activation is narrower than package release. A release may ship a
disabled interface, but UI/config cannot imply the capability works.
