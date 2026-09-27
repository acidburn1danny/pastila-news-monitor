# EDITOR R2 Factorized Fact-Plan Closed-Evidence Evaluation v1

## Verdict

`PASS + 0 BLOCKERS` for the deterministic evaluation itself.

Terminal experimental decision: `STOP_FACTORIZED_DIRECTION_V1`.

This result is development research only. It does not select a parent, access a historical holdout, authorize promotion, or establish naturalistic transfer. R2 step-9 remains the development parent.

Result identity: `64b0bc96ee58e53b6f8afcbb35c38a3d8183326fd3c7141e8fd326f0efcae899`.

## Evidence closure

- Nine terminal PASS slots were verified: I0, I1, and I2 for seeds `161803`, `271828`, and `314159`.
- Each terminal slot contains the same ordered 48-case inventory.
- The evaluation binds hashes for all nine observation bundles, all nine terminal receipts, the failure receipt, the 48 cases, 48 oracle plans, and the frozen evaluation contract.
- I3 has one terminal failure at `I3_R2_PLAN_TO_R2_SETUP__seed_161803`; no partial I3 observation or terminal bundle exists and the remaining I3 slots were not run.
- No inference, slot rerun, optimizer operation, or training was performed by this evaluation.

## I2 oracle-plan realization versus I0 one-pass R2

All three seeds are byte-behaviorally stable and produce the same direction: `MIXED_WITH_MATERIAL_REGRESSION`.

Per seed, over the same 48 cases:

| Metric | I0 | I2 | I2 − I0 |
|---|---:|---:|---:|
| Contract `text` extractable | 18 | 17 | -1 |
| Fully contract-valid | 16 | 16 | 0 |
| Factual-safety pass | 8 | 9 | +1 |
| Sufficiency pass | 0 | 6 | +6 |
| Required-fact hits | 63 / 192 | 52 / 192 | -11 |
| Numeric hits | 25 / 80 | 18 / 80 | -7 |
| Qualification/status hits | 19 / 87 | 28 / 87 | +9 |
| Target-content token hits | 242 / 955 | 270 / 955 | +28 |
| Novel-actor cases | 2 | 0 | -2 |

Case-level ordering gives I2 9 wins, I0 4 wins, and 35 ties per seed. That count is insufficient to claim an oracle-plan advantage because I2 simultaneously loses required facts, numbers, and one additional contract-extractable output. The oracle intervention helps some sufficiency, qualification, and actor-fidelity cases, but does not improve factuality, sufficiency, and safety jointly without material regression.

## I1 oracle-plan scoreability

R2 assigns a finite teacher-forced likelihood to all 48 oracle plans in all three seeds, with 48/48 exact plan-identity matches per seed.

- Mean NLL: `0.8861507823069891`
- Median NLL: `0.9027715027332306`
- Minimum NLL: `0.7259894013404846`
- Maximum NLL: `1.0588217973709106`
- Development mean NLL: `0.8267173419396082`
- Replay mean NLL: `0.9455842226743698`

This demonstrates operational representability and scoreability under teacher forcing. It does not demonstrate that R2 can construct valid plans autonomously, and NLL alone is not a semantic-validity verdict.

## Bottleneck diagnosis

The evidence identifies plan-to-text realization and output-contract adherence as active bottlenecks: supplying the oracle plan does not yield a clean, non-regressive improvement over one-pass R2. Plan construction may also be defective, but its causal contribution cannot be estimated from I3 because I3 terminated on its first case and produced no eligible plan/output bundle.

The dominant supported diagnosis is therefore:

`PLAN_TO_TEXT_REALIZATION_AND_CONTRACT_ADHERENCE; PLAN_CONSTRUCTION_EFFECT_NOT_IDENTIFIABLE_FROM_I3`.

## I3 interpretation

The closed failure receipt proves a terminal slot-execution failure for the first I3 seed and proves that no partial eligible evidence was admitted. The receipt does not contain the invalid payload or a case-level structural diagnosis. Consequently, I3 is evidence that the current generated-plan path is not executable as closed, but it is not enough by itself to attribute the failure uniquely to JSON decoding.

Because I2 lacks a safe net advantage, a successor whose only change is structural JSON decoding for I3 is not justified. Structural decoding could make plan generation executable, but the existing evidence says that even an oracle plan does not reliably solve realization.

## Decision

The factorized direction in its current R2 plan → R2 setup form is closed. The positive evidence retained is narrow:

- oracle plans are teacher-force scoreable;
- oracle conditioning improves qualification/status coverage, target-content overlap, and a subset of sufficiency outcomes;
- the result is perfectly stable across the three deterministic seeds.

The negative evidence is decisive for this design:

- no joint factuality/sufficiency/safety advantage;
- material required-fact and numeric losses;
- no improvement in full contract validity;
- I3 cannot provide a plan-construction contrast.

## Exact next owner action

Create a publication-safe checkpoint containing exactly the deterministic scorer, this result artifact, this report, and the dedicated test. Reproduce the result identity byte-exact and run the dedicated tests plus a fresh adversarial audit. Do not build a structural-decoding successor or start another experiment in that checkpoint task.
