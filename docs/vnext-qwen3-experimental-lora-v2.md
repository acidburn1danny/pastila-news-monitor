# VNext Qwen3 Second Experimental Non-Promotable VOICE LoRA Training & Blind Comparative Evaluation Boundary v1

## Verdict

`CONTINUE_EXPERIMENTAL_EVIDENCE` with `PASS + 0 INTEGRITY BLOCKERS`.

The second experiment is non-promotable. The expanded corpus produced stable training and packaged adapters, but did not produce a material quality gain over the matching baseline and did not improve on LoRA experiment #1 on the compatible common nine-case validation set.

## Frozen authority

- Authority commit: `8305cbaf9669c6b40d4c836a96598887dca68262`
- Dataset: `b48426314ce66a8bfb8f1e773cf171c07de0116b170dafec2a9c85228439c4e6`
- Corpus freeze: `e2f94bb1266cbe64ea48eb244d95637c4d5f1dfdb7d250b3857834c4dc445a8c`
- Config: `4abb9cde5011b0a7e84b135f82fd98f0bcbd52661ae5cd6db215bc915bd0111d`
- Training result: `e5d12db78b89dc0da845be11ab33283087a9081171e49dfb73326f2a28bba61c`
- Evaluation result: `f46d83318f0eca4e9fc5cb51d2903c171aa5ff7eff2c439b0800931393a495f2`
- Package manifest: `680e2a1a577696943d50020285c700edd89c03fe838955973a8241b8e4cc973a`
- Audit: `67361918d04950b4e8b4cab48c186c020d5d08b0f4cc15d1cd893c4603e27329`

## Frozen training configuration

The experiment uses the same conservative training configuration as experiment #1 to isolate the effect of the expanded corpus:

- seeds: `1811`, `3001`, `4621`
- LoRA: rank 4, alpha 8, dropout 0.05
- targets: `q_proj`, `v_proj`
- quantization: NF4 double quantization with BF16 compute
- epochs: 4
- learning rate: `5e-5`
- batch size: 1
- gradient accumulation: 3
- maximum length: 1024
- optimizer: `paged_adamw_8bit`
- decoding: deterministic, sampling disabled, maximum 220 new tokens

## Training and packages

| Seed | Optimizer steps | Mean train loss | Mean validation loss | Package identity |
|---|---:|---:|---:|---|
| 1811 | 52 | 2.552741 | 2.417915 | `faf2d0ae132622dae827a2d8fb750563fcb57e641fdd35366babe1fbe8d543b3` |
| 3001 | 52 | 2.539058 | 2.408984 | `faf29cb09ba20a0be0f3c5765df53011647f5ea239d13dbe9c0ea92f81e3d6ec` |
| 4621 | 52 | 2.553330 | 2.419665 | `df16d32f78adb0ca362b94b92efe012523574746788d6599d645d24ec5b373e8` |

No exact train commentary copy and no shared 12-token train span was detected.

## Blind comparative evaluation

The candidate mapping was hidden behind content-derived blind slots during deterministic rubric scoring.

Full 15-case validation means:

| Candidate | Composite | Naturalness | Restraint | Concision | Style | Non-generic | Composition | Mean words |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 3.646667 | 4.000000 | 5.000000 | 4.733333 | 2.800000 | 2.866667 | 1.933333 | 63.200 |
| LoRA2 1811 | 3.580000 | 4.000000 | 4.533333 | 4.266667 | 2.933333 | 3.266667 | 2.000000 | 81.667 |
| LoRA2 3001 | 3.673333 | 4.000000 | 4.600000 | 4.333333 | 3.066667 | 3.400000 | 2.066667 | 78.867 |
| LoRA2 4621 | 3.620000 | 4.000000 | 4.266667 | 4.133333 | 3.066667 | 3.400000 | 1.866667 | 90.267 |

LoRA #2 mean was `3.624444`, with population standard deviation `0.038232`. Directional improvement over baseline was not consistent across all three seeds.

On the compatible common nine-case set:

- LoRA #1 mean: `3.829630`
- LoRA #2 mean: `3.688889`
- LoRA #2 minus LoRA #1: `-0.140741`

## Learned behavior

The adapters consistently increased non-generic phrasing and Pastila Acida style signals. Two seeds increased sarcasm/irony markers and mechanism composition slightly.

The same adapters increased output length and reduced restraint and concision relative to baseline. The expanded corpus therefore did not eliminate the style distortion demonstrated by experiment #1.

## Runtime projection effect

Raw constrained-projection rejections:

- baseline: 1/15
- seed 1811: 1/15
- seed 3001: 1/15
- seed 4621: 2/15

Final unsupported factual claims after projection: `0`.

This final factual safety belongs to the runtime constrained-projection boundary. It is not attributed to model weights.

## CAR history

CAR-01: the experiment #1 executor required an `episode` field on every record. Contemporary Pack #3 records use family identity and may omit `episode`. The first attempt stopped before training. Its partial config was invalidated and deleted. The executor was repaired to preserve episode when present and otherwise bind family identity. The complete experiment was restarted fresh.

## Protected state

- Holdout exposure: `0`
- Qwen3 bakeoff exposure: `0`
- Active product modified: false
- Canonical rollback modified: false
- Adapter installed: false
- GUI: `ACTIVE`
- VOICE: `DISABLED_UNTIL_PROMOTION`
