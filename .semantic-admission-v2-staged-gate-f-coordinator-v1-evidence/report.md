# Staged Gate F Coordinator V1 — zero-inference report

The evaluation-only coordinator implements the frozen Stage P → validation → Stage C sequence with a hard maximum of two calls and no retry, repair, or selection. A Stage P exception, invalid output/source span, or INDETERMINATE ledger stops after one call and records one unused call; Stage C is never invoked.

Each case receives a new append-only evidence directory. Canonical request bytes are persisted before invocation. Raw response bytes are persisted with exclusive creation before schema or source validation. Provider exceptions, validation outcomes, stage evaluator/prompt/grammar/model identities, input hashes, call consumption, precedence, and the aggregate receipt are separately recorded. Existing evidence cannot be overwritten by rerunning the same case identity.

All execution tests use deterministic scripted callables or forbidden callables; they are not model/provider calls. Coordinator construction invokes neither stage. No Core model, WSL runner, provider, Gate S, application runtime, curriculum, or training path is imported or invoked.

The next step, after owner approval, is the previously bounded evaluation-only Cases 01/10 proof: at most four provider calls total, no retries, expected annotations hidden, raw evidence quarantined, and exact two-case acceptance required. That probe needs separate explicit authorization.
