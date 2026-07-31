# Validation

## Responsibilities and contract

Validators cover identity/version, graph lineage/order/fingerprint, observation provenance, evidence chronology, confidence recomputation, candidate inactivity/evidence, preference/counter-evidence lineage, conflicts, supersession, decay, profile buckets/counts/fingerprint, guidance, compatibility, session fingerprint, and readiness.

## Failures and guarantees

Missing, duplicate, or orphan IDs; generated-language flags; forged confidence; invalid transitions; decayed explicit rules; canonical mutation; stale fingerprints; and readiness mismatches are rejected. Validation is deterministic and performs no mutation or I/O.
