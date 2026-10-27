# Negative-control fixtures

- `ordinary_shared_prefix.json` demonstrates that a prefix-only Tier 2 source
  assertion cannot satisfy the candidate Tier 4 pattern and cannot produce a
  vendor claim.
- `five_osm_mirrors.json` encodes five derivative renderings of one OSM object
  plus one independent municipal assertion.
- `osm_revision_history.json` proves two version-addressable revisions retain a
  single stable OSM object root and cannot be counted as independent observers.
- `malformed_remote_id.json` requires a malformed Remote ID state with no
  invented aircraft/operator position.

These are deterministic logic controls, not empirical false-positive-rate data.
Empirical signature activation requires the corpus in `CALIBRATION_PLAN.md`.
