# Stage P V3 Case 01 probe

Exactly one evaluation-only Stage P call was executed for frozen `HMCV1-SASC-01`. Stage C was neither constructed nor called. There were no retries, repairs, or selections.

The infrastructure path succeeded. The WSL process exited normally after approximately 77.7 seconds, the runner reached terminal EOS after 460 generated tokens, and it persisted a 1,462-byte constrained JSON ledger. Tokenizer loading took about 5.49 seconds, trie construction 0.66 seconds, prewarm 0.02 seconds, model loading 14.43 seconds, and generation 52.66 seconds. All 28 heartbeats used incremental tracking with zero rebuilds.

The ledger passed its strict JSON/Pydantic schema but failed exact source-membership validation. Entry P1 used the factual summary as `candidate_span`; that text is not a span of the commentary candidate. P2's commentary span and all supplied authority spans passed membership. The output declared `INDETERMINATE`, but source membership is independently mandatory, so the result is `FAIL_CLOSED_STAGE_P_SOURCE_MEMBERSHIP`.

The initial one-shot receipt groups provider and post-provider validation exceptions and therefore states that no raw output was captured. The byte-exact raw file proves otherwise and is preserved unchanged. This validated analysis records the distinction rather than rewriting the original receipt. The generic Core trace also retained initial phase flags; the 46 append-only durable lifecycle files are the authoritative phase record.

All output remains quarantined evaluation evidence with no Stage C, proof-rerun, runtime, production, curriculum, or training authority.

Recommended next step: design-only analysis of the Stage P source-membership failure and the two evidence-reporting discrepancies. Do not run Case 10 or Stage C until a bounded remediation candidate and zero-inference verification are separately approved.
