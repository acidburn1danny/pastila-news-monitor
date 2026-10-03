# VNext Qwen3 Experimental Non-Promotable VOICE LoRA v1

This boundary trains three conservative QLoRA adapters against the frozen owner-written dataset authority at commit `1246bfc480e45f3eb1511838d230edd4f0d38367`.

The experiment is evidence-only. It does not authorize promotion, active integration, or installation. VOICE remains `DISABLED_UNTIL_PROMOTION`.

## Configuration

- Base: local Qwen3-8B, non-thinking prompt
- Quantization: NF4 double quantization, BF16 compute
- LoRA: rank 4, alpha 8, dropout 0.05, `q_proj` and `v_proj`
- Optimizer: bitsandbytes `PagedAdamW8bit`
- Seeds: 1701, 2903, 4517
- Epochs: 4; batch 1; gradient accumulation 3; learning rate `5e-5`
- Train/validation: 18/9 positive records
- Holdout: remained sealed

## Result

All three adapters trained and packaged. Validation loss was stable across seeds, but the blind deterministic quality gain did not reach the frozen `+0.50` acceptance threshold. Raw generations also required factual projection rejections. No exact training-output copy or 12-token training sequence was detected.

Terminal: `CONTINUE_EXPERIMENTAL_EVIDENCE`.

One CAR invalidated the initial run set because its executor optimizer differed from the frozen declaration. The executor was aligned to `PagedAdamW8bit`, all three seeds were retrained, and evaluation and audit were restarted from zero. Pre-CAR evidence is excluded.
