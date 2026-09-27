# VNext Minimal Source-Bound Verifier Closed-Evidence Calibration v1

## Terminal result

- Status: `PASS_WITH_EVIDENCE_LIMITATIONS`
- Decision: `REVISE_BEFORE_ACTIVE_INTEGRATION`
- Closed-evidence input identity: `9169c1f3267fae81ed9b2c78c32e1d833a5d5b63bd045dce55f3259b0f88d8ba`
- Result identity: `22d0680c03b48260d065cbaf060e1b6e5df844ee5e8ffff4aa0bea55c20a47c5`
- Closed rows: 48
- Inference, model load, optimizer, and training: none
- Active VNext integration: none
- Legacy dependency count: 0

The calibration uses the frozen blind-review R2 output selected through the per-case mapping, its locked human score receipt, and the associated full content-addressed SourcePacket. It does not recreate missing payloads.

## Verdict distribution

- `PASS_PROVEN`: 45/48 (93.75%)
- `FAIL_PROVEN`: 0/48
- `UNPROVEN`: 3/48 (6.25%)

All three `UNPROVEN` rows are `CHRONOLOGY_UPDATE` cases without any hard source anchor that the deliberately minimal verifier can prove. They use the source-preserving fallback. There are no abstentions because each complete SourcePacket fits the bounded one-to-three-sentence fallback.

## Human evidence and error measurement

The locked blind review labels every selected R2 output `PASS` for factual safety and factual sufficiency. Consequently:

- demonstrated true R2 failures in this closed final-output cohort: 0;
- verifier false rejections (`FAIL_PROVEN` against human `PASS`): 0;
- observed verifier misses: 0;
- verifier miss rate: **not estimable**, because the cohort contains no human-negative R2 output.

Zero observed misses must not be interpreted as demonstrated sensitivity.

## Previous V0 comparison

The prior V0 diagnostic routed 18/48 cases to fallback (37.5%). This calibration routes 3/48 to fallback (6.25%) and 0/48 to abstention, an observed difference of -15 cases or -31.25 percentage points.

This is not a causal paired improvement: none of the 48 frozen blind-review R2 output hashes equals the corresponding prior V0 output hash. Every per-case change is therefore classified `EVIDENCE_INSUFFICIENT_DIFFERENT_OUTPUT_BYTES`. The calibration does not relabel any prior V0 failure or rejection.

## Domain results

- Numeric: 7 `PASS_PROVEN`, 0 fail, 0 unproven.
- Actor/entity: 8 `PASS_PROVEN`, 0 fail, 0 unproven.
- Qualification/status: 21 `PASS_PROVEN`, 0 fail, 0 unproven.
- Other: 9 `PASS_PROVEN`, 3 `UNPROVEN` chronology cases.

These positive-only results measure compatibility and conservatism on reviewed-safe outputs. They do not measure failure-detection sensitivity for the three domains.

## Integration conclusion

The evidence does not yet authorize active V0 integration. The verifier demonstrates a low conservative fallback rate on reviewed-safe final outputs, but closed evidence cannot estimate its miss rate. The missing evidence is a content-preserved, source-bound set of original R2 outputs containing independently adjudicated factual failures. Raw pre-fallback payloads from the earlier V0 and bake-off routes were not retained and cannot be reconstructed retrospectively.
