# Stage P runner V3 zero-inference preflight

Runner V3 connects the approved incremental prefix tracker and cache-canonicalized trie projector to the existing durable Stage P lifecycle. Exact runner, controller, projector, and tracker identities are checked by the host executor before launch.

The first tokenizer-only attempt exposed a transitive `pydantic` dependency caused by importing the broader semantic-admission package in the isolated WSL model environment. It stopped before model loading. V3 now loads only its exact governed modules under a minimal package namespace. A subsequent over-broad every-token baseline comparison was manually terminated and quarantined without promoted evidence.

The accepted bounded real-tokenizer preflight used the unchanged 131,072-token tokenizer, constructed both baseline and candidate 221,961-node tries, and compared 18 deterministic checkpoints across short and 400-character ledger strings. Allowed-token sets had zero divergences and the controller used the incremental path. The known Mistral tokenizer-regex warning remains recorded; tokenizer behavior was not changed.

Eighteen focused tests passed. They cover exact identities, construction without WSL/model activity, controller-to-baseline equivalence, absence of full DFA replay in the V3 callback, evidence boundaries, and preservation of timeout-surviving host and runner lifecycle events. No model was imported or loaded, no provider was called, and no inference was performed.

This candidate has no production, runtime-integration, model-probe, proof-rerun, curriculum, or training authority. After owner approval, the narrow next step is one evaluation-only Stage-P-only Case 01 probe with durable receipts, followed by another stop.
