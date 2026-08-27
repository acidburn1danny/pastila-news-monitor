# Stage P evidence and trace remediation V1

Tracks B and C of the approved Case 01 remediation design are implemented without inference. Frozen V3 remains unchanged; the reconciled evaluation executor is separately versioned V4.

The V2 phase receipt invokes an evaluator exactly once, persists returned UTF-8 bytes before validation, and records transport, raw persistence, schema validation, and source membership independently. Reconstructing the frozen Case 01 evidence now correctly retains the 1,462-byte raw ledger and classifies only source membership as failed.

The lifecycle reconciler validates actor/filename/sequence bindings, runner and dependency identities, phase order, and an ordered tree identity. Against the 46 frozen Case 01 records it correctly reports model load, generation, terminal EOS, and response persistence as observed, while host timeout was not observed before the terminal event. Identity or sequence drift makes all derived claims unavailable.

V4 binds this reconciliation into the generic trace after normal exit and before re-raising timeout. Legacy success booleans are derived only from observed lifecycle events; the complete four-state evidence remains in the bound reconciliation receipt.

Sixteen focused tests passed. No provider or model was called, and no prompt, schema, decoding constraint, Stage C, runtime, curriculum, or training behavior changed.
