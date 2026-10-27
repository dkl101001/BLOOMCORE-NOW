# Preregistered calibration plan

No numeric confidence/probability may be emitted before this plan is registered,
run on held-out data, and linked by a calibration receipt.

## Static location corpus

At least 200 held-out controlled trials across:

- three environment strata (open, suburban/light multipath, dense urban);
- at least two receiver/antenna placements and two route geometries;
- multiple target units/firmware generations, transmit-power regimes and days;
- single receiver, calibrated multi-RSSI receivers, and any later bearing profile
  evaluated separately;
- preregistered gross-outlier/moving-traffic blocks and censored coverage gaps.

Calibration targets for 50%, 80% and 90% regions: maximum absolute empirical
coverage error ≤0.05. The 90% region's 95% Wilson lower coverage bound must be
≥0.85. Until then, output `UNCALIBRATED` and null confidence level.

Utility gate: on informative orthogonal-pass fixtures, a second independent pass
reduces median region area by ≥25% while empirical coverage drops by ≤5
percentage points. Exact duplicate observations may not change the region.

## Signature corpus

Use immutable captures with raw-frame hashes, exact device labels, receiver/
channel/day/environment separation, ordinary same-prefix devices, wildcard-probe
controls, firmware generations and open-set unknowns. Split by physical device,
not packet. An active vendor-associated claim needs a one-sided 95% upper bound
on false-positive rate ≤1% plus documented false-negative behavior. Validation
captures cannot share measurement/training roots.

## Mobile/RID corpus

Evaluate broadcast-coordinate, RF-only and fused tracks separately. On observable
held-out traces, static/mobile false classification ≤5%; 90% trajectory envelope
must meet the same ≥0.85 Wilson lower-bound gate. Every deliberately
unobservable one-receiver scalar-RSSI trace must return `MOTION_UNRESOLVED`.

Remote ID codec testing requires all pinned upstream golden vectors plus one
million bounded mutated frames with zero crash/out-of-bounds result. Syntax,
semantics, freshness, replay suspicion, authentication and consistency require
separate confusion matrices.

## Calibration receipts

Record preregistration hash, corpus/source and measurement roots, exclusions,
random split seed, physical-device grouping, environment labels, hardware and
calibration profiles, code/parameter hashes, full metrics with intervals, and
approved claim ceiling. Failed runs remain in lineage history.

