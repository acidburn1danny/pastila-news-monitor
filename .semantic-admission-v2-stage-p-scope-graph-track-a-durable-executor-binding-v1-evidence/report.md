# Track-A durable executor binding

Result: **PASS — zero inference; Case 01 blocked**.

The durable executor is identity-bound to the approved Track-A runner. It reads only authenticated append-only `RUNNER_EXCEPTION` evidence for `StagePConstraintLivenessErrorV1`, validates the exact receipt shape, and persists `HOST_CONSTRAINT_LIVENESS_FAILURE_CLASSIFIED` with decoded byte count/hash and DFA position. Ordinary provider/transport failures remain separately classified. Malformed liveness receipts fail closed.

Construction and synthetic receipt verification performed no WSL runner call, tokenizer/model load, provider call, or inference.
