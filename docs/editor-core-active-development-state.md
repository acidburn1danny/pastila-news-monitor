# Editor Core active development state

This document identifies the single active Editor Core development baseline.
It does not create an execution, adjudication, qualification, certification, or
promotion authority.

## Active baseline

`ACTIVE_EDITOR_DEVELOPMENT_STATE` is the evaluated checkpoint 8 from the
targeted continuation round:

- parent adapter content identity: `8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f`;
- parent checkpoint identity: `6925fca8c5b6c9e94e96255cb21ec9442aff5d0ac2f7bd0f2038ce45475a7dd1`;
- dataset manifest identity: `cbcf7a90ff55b56b5499ce4967a54118b3d99c57c105d7645fada6ad54392b8e`;
- training configuration identity: `934bc1dcd02f2eb23e98e4ef371e2fd89eb9d7b921eb0554cec8e51cc561f975`;
- training corpus identity: `c1ee2f4a6c0561eba52ef7a437a885568cf8fd2b53956b0c3a05c309ca0fad4a`;
- 64 new targeted examples, 64 replay anchors, and a separate 32-case
  independent holdout;
- training receipt identity: `bde0363562a699e79603c857fa18015d7cf0a5a26d26d25a032ec7dfc508b2db`;
- selected checkpoint identity: `00ee968941f8cba8ea47534d441c272c7a3120f9076953aa552f67e302a0ceef`;
- selected adapter content identity: `50b292f9cfdfb2f44dcc8bb9ef811ea367c78db505e4adc2c62e851e6060d3a4`;
- independent holdout result: 32/32 structurally valid and 20/32 exact target,
  compared with 12/32 for the parent;
- checkpoint 16 also scored 20/32 and changed only responses that remained
  mismatches, so checkpoint 8 is retained as the smaller effective update.

The next development step is semantic failure mining on separate development
evidence for epistemic calibration, transition no-new-facts behavior, and
unsupported material claims. The independent holdout remains excluded from
training labels. This experimental selection is not a promotion or release.

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
