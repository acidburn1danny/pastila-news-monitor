# EDITOR text-realizer model acquisition authority v1

This bounded authority freezes official immutable revisions for Qwen3-8B and
Qwen2.5-7B-Instruct, their complete snapshot inventories, Apache-2.0 licenses,
content identities, content-addressed destinations, and a matched NF4 runtime recipe.

The two snapshots contain 29 files and about 29.45 GiB. The WSL store has more than
860 GiB available. Full BF16 plus runtime overhead does not fit the 16 GiB deployment
budget; both challengers therefore use bitsandbytes NF4, double quantization, and
bfloat16 compute under the same pinned package versions. Quantization is performed
only at future model load and is not authorized here.

The future downloader streams files from the exact revisions into ineligible
`.inflight` directories, verifies LFS SHA-256 or Git blob OIDs and exact sizes, and
atomically publishes each snapshot only after full verification. A program receipt
covering both snapshots is required before bake-off eligibility. Existing final or
staging paths fail closed; no overwrite or automatic cleanup is allowed.

This checkpoint does not authorize download, model load, quantization, inference,
optimizer activity, training, historical holdout access, cleanup, parent selection,
promotion, or release. Successor training remains suspended.
