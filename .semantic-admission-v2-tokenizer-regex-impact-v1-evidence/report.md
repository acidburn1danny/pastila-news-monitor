# Semantic Admission V2 — tokenizer regex impact assessment

## Outcome

The bounded zero-inference comparison found no tokenization difference on the frozen Run 4 diagnostic contract. Loading the same local tokenizer with legacy behavior and with `fix_mistral_regex=True` produced byte-identical token-ID sequences for all 15 assessed samples.

## Coverage

- All ten exact frozen Gate F prompts for `HMCV1-SASC-01` through `HMCV1-SASC-10`.
- Canonical `PASS` and `INDETERMINATE` JSON streams.
- Two critical constrained `FAIL` prefixes used during trie prewarming.
- A Romanian sample containing diacritics, guillemets, punctuation, modal language, and semantic-admission vocabulary.

For every sample, legacy and fixed token counts, token IDs, and token-sequence SHA-256 values were identical. Difference count: zero.

## Interpretation

The Transformers warning is genuine and may matter for strings outside this bounded corpus. It does not affect the exact ten-case Run 4 Gate F prompts or the assessed constrained-language anchors. Changing tokenizer configuration now would create unnecessary identity and comparability drift without providing evidence benefit for this run.

This result does not claim global equivalence between the two tokenizer modes and does not authorize changing the frozen runner.

## Authority boundary

Both tokenizer configurations were loaded locally. No model was loaded; no inference, generation, model call, or provider call occurred. Neither runner was modified. No Run 4, runtime, curriculum, or training authority is granted.

## Recommendation

For the bounded Run 4 conformance evaluation, retain the existing frozen tokenizer behavior and runner identities. Record the regex warning as a known out-of-scope global limitation. The next step may be a separately authorized one-shot Run 4 using the same ten cases, twenty-call ceiling, durable raw ledger, no retry/repair/selection, and an unrestricted WSL execution context.
