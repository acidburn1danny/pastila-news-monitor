# Stage P Scope Graph Track-A liveness candidate

Result: **PASS — zero model, zero inference**.

The exact Run 2 heartbeat prefix and bound tokenizer falsified the initial `co` token dead-end hypothesis. Both baseline and candidate had four legal continuations after that prefix. The structural liveness defect occurs later: V1.1 exposes both coverage decisions even though the emitted complete/no-unresolved receipts permit only `COMPLETE`; incoherence is rejected only during terminal closure.

The candidate projects the coverage choice before emission. It also supplies token lookahead and a distinct hashed liveness receipt as defense-in-depth. Unsupported real-world propositions with null support remain representable. Nothing is runner-bound and no prompt, schema, model, or production behavior changed.
