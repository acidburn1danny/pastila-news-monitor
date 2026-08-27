# Stage P Role Coherence V1 Case 01 probe

Exactly one authorized evaluation-only Stage P call was attempted for frozen `HMCV1-SASC-01`. No retry, repair, selection, projector, Stage C, Case 10, or proof rerun occurred.

The runner loaded the tokenizer and model, began constrained generation, and recorded nine heartbeats through 143 generated tokens. It did not reach terminal EOS and produced no response file. The phase receipt correctly returned `STAGE_P_PROVIDER_OR_TRANSPORT_FAILURE` and fail-closed abstention.

Durable evidence localizes the failure. The model chose `REAL_WORLD_COMMITMENT`, then `PRESUPPOSED`, `NEW_UNSUPPORTED_EVENT`, and unresolved candidate modality/timing. Each enum was locally admitted by the grammar. At entry closure, the tuple violated the new role-coherence invariant, leaving an empty allowed-token set. The runner raised `EMPTY_ALLOWED_TOKEN_SET`.

This is a late constraint-projection defect, not a timeout, source-membership error, tokenizer incompatibility, or semantic Case 01 result. Case 01 acceptance remains unproven because no terminal ledger was produced.

The narrow remediation is zero-inference and grammar-only: condition each later enum's allowed choices on the selected entry type and already-selected authority state. Preserve strict schema and final tuple validation as defense-in-depth. Do not repair or reinterpret this failed output, and do not change the prompt based on this result alone.

Recommended next step, requiring separate authorization: implement role-conditioned enum projection, add exhaustive prefix/dead-end tests for all entry roles and authority-null/support combinations, and repeat real-tokenizer zero-inference compatibility. Stop before another model probe.
