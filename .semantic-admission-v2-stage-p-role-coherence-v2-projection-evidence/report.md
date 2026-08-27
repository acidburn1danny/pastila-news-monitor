# Stage P Role Coherence V2 role-conditioned projection

Constraint V2 resolves the exact late-dead-end defect demonstrated by the frozen Case 01 probe. Legal enum sets are now conditioned on entry role and authority-support state at each field. Illegal role combinations are never offered, while final tuple and strict schema validation remain in place.

Local exhaustive tests cover every entry role, null and non-null authority, each unresolved candidate axis, exact role-specific choice sets, and the observed bad continuation. All 30 combined V2 and V1 non-regression tests passed.

The frozen real tokenizer passed four legal streams across 747 token transitions. Every stream decoded exactly, reached terminal state, and admitted only EOS after completion. The observed `REAL_WORLD_COMMITMENT + UNRESOLVED` path was blocked at token 97 instead of failing at entry closure.

The tokenizer loaded once in WSL. Transformers imported torch transitively, but no model module, model weights, adapter, provider, or inference was invoked. The existing tokenizer-regex warning remains unchanged.

Recommended next bounded step, requiring separate authorization: bind a new V2 runner, durable executor, and one-shot Case 01 request to these identities, perform zero-inference construction checks, and stop before another model probe.
