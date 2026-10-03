# VNext Qwen3 VOICE A2 Explicit Stopping Experiment

- Verdict: `A2_ACCEPTANCE_NOT_MET`
- Integrity: `PASS_0_INTEGRITY_BLOCKERS_NON_PROMOTABLE`
- Published design: `0e58b1de172e151936c7d3e9060e37d601cc9286af1296fbe0453a039a70a49a`
- Config: `c094dad85ec18620b48a00d62a15dae929df4696b13fe6e8ffcebb83cd0b2176`
- Intervention: `50668b2539bb659b248040ee1b88782bf2af2ffc17e61f89f7ce550668d44878`
- Implementation: `ceb53950d4d1ba37a2a0b1af9bf2b86a40baf7c3c0f1fcb5d9d99284ff414895`
- Training: `101b21f11722677f865cb27f583bfffab45210c0f996648ed1a77535d3588939`
- Evaluation: `4ccbfc9eab2f0ffad2f40902b6b4c4dc348ac5f7500d5cca6ea53c07a8f16605`
- Package manifest: `84dff48e41cd6c890a6e274552847628c276a3075b6ec2ca943ed128c5484cdc`
- Audit: `943df87e33b424312c97ca4ccebc57b8bf1397a7131cf31d7b76f664d53b1021`

## Result

- A2 aggregate length: `72.111111` versus LoRA2 `83.6`.
- A2 aggregate quality: `3.773333` versus LoRA2 `3.624444`.
- No A2 seed passed every frozen criterion.
- Final unsupported factual rate after projection: `0`; attributed to runtime projection.
- Holdout and Qwen3 bakeoff exposure: `0`.
- No adapter installed; VOICE remains disabled.

## Causal adjudication

`EXPLICIT_EOS_PRESSURE_PARTIAL_BUT_INSUFFICIENT_AND_UNSTABLE`
