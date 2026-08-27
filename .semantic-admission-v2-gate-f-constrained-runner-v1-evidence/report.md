# Gate-F constrained evaluation runner V1

A separate evaluation-only WSL runner now integrates the frozen Gate-F DFA and optimized trie through Transformers `prefix_allowed_tokens_fn`. The existing Core V1.2 runner remains byte-unchanged and has no constraint imports or prefix-decoding hook.

The constrained runner is bound by source hash. Its `--preflight-only` lifecycle imports only the tokenizer and native prefix-constraint API, builds the 221,961-node trie, prewarms all three distinct nullable-string grammar states in 2.094703 seconds total, validates canonical terminal streams, proves fences impossible at the root, and proves EOS is exclusive to terminal state. Model libraries were not imported; loading and generation flags remained false.

The separate host executor validates the runner identity and accepts only responses explicitly marked `constraint_active: true`, then projects the original two-field executor result. The host preflight constructed this executor but used a forbidden executor for adapter request construction; invocation count remained zero. The V2.3 prompt and unchanged payload hashes match their frozen identities, and future one-shot output targets are empty.

No model/provider call, inference authority, runtime authority, training authority, or Run 3 authority was issued. The runner is ready only for a separately authorized one-call quarantined Gate-F constrained response-contract probe.
