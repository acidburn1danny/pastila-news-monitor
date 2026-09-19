# Editor Core active development state

This document identifies the single active Editor Core development baseline.
It does not create an execution, adjudication, qualification, certification, or
promotion authority.

## Active baseline

`ACTIVE_EDITOR_DEVELOPMENT_STATE` is the targeted continuation round introduced
by Git commit `635cc160e2b54e468ba9654f50e4da4de18ca31f`:

- parent adapter content identity: `8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f`;
- parent checkpoint identity: `6925fca8c5b6c9e94e96255cb21ec9442aff5d0ac2f7bd0f2038ce45475a7dd1`;
- dataset manifest identity: `cbcf7a90ff55b56b5499ce4967a54118b3d99c57c105d7645fada6ad54392b8e`;
- training configuration identity: `934bc1dcd02f2eb23e98e4ef371e2fd89eb9d7b921eb0554cec8e51cc561f975`;
- training corpus identity: `c1ee2f4a6c0561eba52ef7a437a885568cf8fd2b53956b0c3a05c309ca0fad4a`;
- 64 new targeted examples, 64 replay anchors, and a separate 32-case
  independent holdout;
- training and optimizer activity: not performed.

The next development step is construction and zero-step validation of a
training launcher bound to these published inputs. Starting training remains a
separate owner action.

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
