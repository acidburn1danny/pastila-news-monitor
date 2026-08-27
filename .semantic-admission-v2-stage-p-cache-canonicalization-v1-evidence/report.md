# Stage P trie-cache canonicalization V1

The candidate changes only the Stage P trie cache key. While the DFA is inside a required JSON string, `string_characters` is reduced to two semantic states: zero and nonzero. Zero remains distinct because closing an empty required string is invalid. All other DFA fields remain unchanged.

Synthetic testing compared the generic baseline and candidate allowed-token sets at every character prefix across 30 seeded ledgers, plus invalid root, enum, and trailing-byte streams. The incremental tracker and candidate projector were also composed through an evaluation-only callback controller. No divergence occurred.

The frozen 131,072-token tokenizer comparison covered six ledger shapes, 54 deterministic prefixes, and targeted string lengths 0/1/2/8/64/256/400. Allowed sets were identical. Across the six shapes, projection time fell from 81.236051 to 44.092913 seconds, approximately 1.84×. For repeated nonempty states in one free-string field, baseline projection required 31.561109 seconds while the canonicalized cache required 0.000399 seconds, approximately 79,100×. Empty-string behavior remained distinct and unchanged.

This is not an end-to-end speedup claim. First cache misses and non-string states remain costly, and the controller is not connected to the WSL runner. No model, provider, prompt, schema, timeout, tokenizer identity, or runtime changed.

Recommended next step: separately version and bind an instrumented runner integration using this controller, then perform zero-inference tokenizer construction/equivalence and durable-lifecycle preflight. Stop again before any model call or Case 01 diagnostic.
