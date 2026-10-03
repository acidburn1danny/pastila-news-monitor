# VNext Qwen3 VOICE Length-Stratified Sampling A1

- Verdict: `STOP_ABLATION_ACCEPTANCE_NOT_MET`
- Integrity: `PASS_0_INTEGRITY_BLOCKERS_NON_PROMOTABLE`
- Configuration: `383c63d7d8cbccb186d49914b3eed4b75d6adb9ad1f6bdbd675fec0f7c42c088`
- Sampling: `6d0688b4630bd7a5649ef36cf7dac9d8d03ad5a44ecb26213af66851d02677fa`
- Training result: `d2e6f662031f1442afc99f4dcd81b8d3ab7dbdf16a1926d404d4327234faf057`
- Evaluation: `71425e3ae010797009eec27764ff04dfcbfd9dc1a13a2150a2121043a4c099a1`
- Package manifest: `518bd823a75d9440534b59c00a6d942cebff07a49846406a128941de58c75aab`
- Audit: `0ac56d4f6e6104a30dcc98d392dbb73f29f022d117bc3ef2d936e697da13eb8a`

## Frozen intervention

- All 39 train records appear once per epoch.
- Concise/medium/long counts: `12/19/8`.
- Target optimizer-loss mass: `13/13/13`; total mass `39`.
- Weights: concise `13/12`, medium `13/19`, long `13/8`.
- Seeds: `1913`, `3203`, `4729`.

## Result

- LoRA2 mean length: `83.600333` words.
- A1 aggregate mean length: `87.222333` words.
- LoRA2 aggregate quality: `3.624444`.
- A1 aggregate quality: `3.58`.
- No A1 seed passed all frozen criteria.
- Exact/normalized memorization: `0` for all seeds.
- Final unsupported factual rate after projection: `0`; this is attributed to runtime constrained projection.
- Distribution hypothesis: `FALSIFIED_OR_INSUFFICIENT_BY_FROZEN_CRITERIA`.
- A2 explicit stopping/length-pressure objective ablation is justified only as a separately authorized experiment.

## Protected state

- Active product and canonical rollback were not modified.
- No adapter was installed; no holdout or bakeoff was exposed.
- GUI remains `ACTIVE`; VOICE remains `DISABLED_UNTIL_PROMOTION`.
