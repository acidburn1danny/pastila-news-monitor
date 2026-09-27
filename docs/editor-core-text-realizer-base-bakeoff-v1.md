# EDITOR text-realizer base-model bake-off v1

## Scope

This development diagnostic compares the existing R2/Ministral control with two
text-only challengers: Qwen3-8B with thinking disabled and Qwen2.5-7B-Instruct.
It evaluates the model only as a non-authoritative realizer behind the published
source-bound ledger, verifier, and deterministic extractive fallback.

The same 48 feasibility cases, source authority, factual-setup contract, prompt
payload, proposal schema, verifier, fallback, metrics, and deterministic decoding
apply to every arm. Native chat templates are model-specific and must be hash-pinned
before any real execution.

The Qwen challengers must use the same backend, bit width, and quantization recipe.
R2 remains in its authoritative existing runtime, so the first-round claim concerns
the deployable model/runtime package rather than base weights alone. Any winner must
reproduce its direction at reference or higher precision before a pivot decision.

## Interpretation

The first round excludes Gemma 3 and Qwen3.5 because their multimodal runtime would
confound the initial text-only comparison. Expansion proceeds to Qwen3-14B first,
then to multimodal challengers only if neither initial challenger passes and the
observed failure is compatible with insufficient model capacity.

Native structured-output adherence is measured without grammar-constrained decoding.
All proposals then pass through the same source-bound verifier and fallback. Human
blind review is required for functional Romanian and usable realization gain;
machine scoring cannot select a parent.

This fixture boundary grants no authority to download or load models, run inference,
create an optimizer, train, select a parent, promote, release, access historical
holdouts, or clean the repository. Successor training remains suspended and R2
step-9 remains the baseline.
