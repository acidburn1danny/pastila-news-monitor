# Gate-F constrained-decoding design and feasibility

Prompt-only remediation is exhausted for the tested Gate-F/model identity. This design keeps generation bounded instead of repairing its output: Transformers' existing `prefix_allowed_tokens_fn` interface will call a custom deterministic character-state machine that admits only token pieces extendable to a frozen-schema Gate-F JSON object.

The exact runtime environment has Transformers 5.15 and native prefix-constrained decoding; no additional grammar package is installed or required. The 131,072-token vocabulary contains 107 opening-brace tokens and six fence-starting tokens with no overlap. All canonical Gate-F response classes round-trip exactly through the tokenizer. A first-step constraint can therefore exclude every Markdown-fence start while retaining valid JSON starts.

The state machine must enforce root framing, fixed keys, allowed decisions/codes/statuses, PASS/non-PASS invariants, JSON escaping, confidence range, record and character bounds, and EOS only after a complete object. An empty token set is an evaluator failure and must never fall back to unconstrained decoding. The unchanged strict parser remains an independent post-generation check.

The tokenizer emitted its known Mistral-regex compatibility warning under the same settings used by the frozen runtime. This design does not silently enable `fix_mistral_regex`, because doing so would change tokenization identity. Implementation must bind the current tokenizer identity first; any regex correction requires separate compatibility evidence and authority.

Feasibility is established, but runtime performance and complete DFA correctness are not. The next bounded step is evaluation-only DFA/token-projection implementation with property tests and exhaustive tokenizer-only projection checks. No model/provider call, prompt modification, runtime activation, or Run 3 authority is warranted yet.
