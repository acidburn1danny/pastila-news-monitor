# Editor Core active development state

This document identifies the single active Editor Core development baseline.
It does not create an execution, adjudication, qualification, certification, or
promotion authority.

## Active baseline

`ACTIVE_EDITOR_DEVELOPMENT_STATE` is the evaluated R2 step-9 checkpoint from
the second targeted continuation round:

- R1 development-parent adapter identity: `50b292f9cfdfb2f44dcc8bb9ef811ea367c78db505e4adc2c62e851e6060d3a4`;
- R2 dataset manifest identity: `ad4a58a6179ae7857d3d6db508a1e82432914027d2c32f3b178854508ff44bb8`;
- R2 training configuration identity: `eb71032c79f9ba6769ac00915bd4316fdfa865d06d248bbfccfcfd94bcc7e1d6`;
- R2 training corpus identity: `9c99425dc9c2ce1f69f2694177b8698892a8e1cc8ed67b5e7fe910d6e56ce072`;
- 36 new targeted examples, 36 replay anchors, and a separate 18-case
  independent holdout;
- R2 training receipt identity: `b348be512d66766612c2adf3f98fa5f511123997664ff3a19557ab0a3f4928a6`;
- selected checkpoint identity: `96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be`;
- selected adapter content identity: `c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02`;
- frozen R2 holdout: 18/18 structurally valid for both candidates;
- blinded semantic review: R2 passed 12/18 and R1 passed 8/18; R2 won six
  transition cases, R1 won two epistemic cases, six cases passed for both, and
  four epistemic cases failed for both.

Subsequent independent evaluations rejected R3, R4, and R5 for
development-parent selection. The R5 result is recorded in
`docs/artifacts/editor-core-v10-v12-targeted-r5-semantic-result.json`: R5
produced no semantic improvement on its frozen holdout and weakened
attribution wording in two changed responses. R2 step-9 therefore remains
the single development parent. Any next training round requires fresh,
disjoint development evidence; frozen holdout targets remain evaluation-only.
This development-parent state is not a promotion or release.

## Scope separation

The repository retains four asset classes outside the active baseline:

1. reproducibility artifacts for retained model lineage;
2. independent development, shadow, and holdout evaluation corpora;
3. immutable historical attempt and evaluation evidence;
4. recovery artifacts required by published recovery contracts.

These retained classes remain available for their documented purposes. Their
presence does not make them active training inputs or a newer ML parent.

## Hygiene closure

The project hygiene pass removed only reproducible caches and verified duplicate
materializations. It did not remove or modify source, model lineage, datasets,
holdouts, immutable evidence, or recovery objects. Local machine paths and
machine-specific storage inventories are deliberately excluded from this public
closure record.
