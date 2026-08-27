# Stage P Case 01 failure remediation design V1

The probe did not fail in WSL startup, model loading, constrained decoding, EOS, JSON syntax, or ledger schema. It failed at the independent exact source-membership boundary: P1 copied factual-authority text into `candidate_span`. This is a source-role error, not factual unsafety and not a transport failure.

The remediation is split into three independently testable tracks. Track A clarifies that Stage P inventories only propositions carried by the commentary; the factual summary is support lookup authority, never inventory input. An optional dynamic substring constraint is retained as defense-in-depth design work, not assumed necessary. It must allow every exact non-empty substring, preserve Romanian/JSON bytes and multiple valid ledgers, and may never repair or snap output to a source span.

Track B separates provider, raw persistence, schema validation, and source-membership validation receipts. Once raw bytes exist, later failures retain their exact path, hash, and size. Track C keeps the durable append-only lifecycle authoritative and makes the generic trace a bound derived index with four-state phase statuses rather than misleading default booleans.

The safest sequence is to implement Tracks B and C first using only captured evidence and synthetic fixtures. Next, construct and zero-inference verify a separately versioned source-role prompt candidate and optional substring projector. Owner review should choose prompt-only or prompt-plus-decoding based on compatibility evidence. No model call is needed until that choice is frozen.

This design grants no implementation, prompt, contract, runner, runtime, inference, Stage C, proof-rerun, curriculum, or training authority.
