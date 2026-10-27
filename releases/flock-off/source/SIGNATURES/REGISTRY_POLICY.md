# Signature registry policy

Signatures are immutable snapshots. A correction creates a new version; old
receipts continue to reference the old content hash. `CANDIDATE` entries can
only explain feature agreement and cannot produce a calibrated probability.

Activation requires a fully specified extractor, immutable positive and
negative datasets, training-lineage accounting, leave-one-device-out testing,
expiry rules, and a preregistered local claim ceiling. A `VENDOR_ASSOCIATED`
signature additionally requires a one-sided 95% false-positive upper bound of
at most 1% on held-out controls. No signature alone establishes a public node,
operator, intent, illegality, or exposure.

Immediate degradation or retirement triggers include firmware drift, a newly
documented ordinary-device collision, extractor changes, receiver-domain shift,
expired last-confirmed dates, and broken provenance. Contradictions stay linked
to every affected version.

