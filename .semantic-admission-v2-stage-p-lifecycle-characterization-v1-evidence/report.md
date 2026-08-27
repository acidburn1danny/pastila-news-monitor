# Stage P durable lifecycle and callback characterization

The timeout-surviving lifecycle boundary is implemented as append-only, exclusively created, fsynced event records outside temporary directories. Host records include request/runner identities, PID, timeout, and observed termination. Runner records cover tokenizer, trie, model, prompt, generation, heartbeat, terminal EOS, response persistence, and exceptions. Heartbeats quarantine partial output and constraint progress. A synthetic child timeout verified that lifecycle evidence survives termination without invoking WSL, a tokenizer, a model, or a provider.

The clean real-tokenizer characterization used six ledger shapes and nine fixed checkpoints per shape. Across 54 valid prefix comparisons, the incremental tracker and full replay had zero state or allowed-token divergences. Three invalid classes failed at the same prefix with the same reason. Every canonical ledger reached terminal EOS.

The measurements revise the causal diagnosis. Full DFA replay consumed 2.160827 seconds; incremental tracking consumed 0.499653 seconds; token-trie projection consumed 65.110097 seconds. Projection represented approximately 96.1% of measured callback work. Incremental tracking reduces processed characters by about 4.53× and is correct on the measured contract, but cannot plausibly solve the timeout alone.

The likely projection defect is excessive cache-key specificity in free strings. `string_characters` changes on every character although allowed continuations depend only on whether the required string is empty or nonempty. This creates repeated trie traversals across a 221,961-node trie. That diagnosis must still be proven with exact allowed-set equivalence before changing the cache.

Three unsuccessful profiler attempts are preserved: one was stopped after an assistant misunderstanding of a prior sleep event; exhaustive and 129-checkpoint methods then proved impractically slow. Only the completed nine-checkpoint stratified result is accepted.

Recommended next step: a zero-inference Stage-P-specific trie-cache canonicalization candidate plus the equivalent incremental tracker. Prove zero allowed-set divergence on randomized prefixes and the real tokenizer, quantify speedup, freeze, and stop before any model call. Do not increase the runtime timeout or rerun the proof yet.
