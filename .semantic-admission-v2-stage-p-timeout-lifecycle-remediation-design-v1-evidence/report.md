# Stage P timeout and lifecycle-durability analysis

Both proof cases failed at essentially the same 240-second boundary, but the available evidence cannot locate the time-consuming phase. The WSL lifecycle target was temporary and disappeared on timeout, so the host trace's unchanged initial flags are not reliable evidence about runner progress.

The strongest performance hypothesis is quadratic prefix work: every constrained-generation callback decodes the entire generated token sequence and rebuilds the DFA from its initial state. Stage P can emit a much longer object than Gate F. The enhanced tokenizer-only canonical-stream exercise also took materially longer than trie construction/prewarming alone. This is plausible, not proven; startup/model-load delay and failure to reach terminal EOS remain viable explanations.

The recommended remediation order is deliberately narrow:

1. Persist append-only lifecycle and partial-output checkpoints outside temporary directories so every timeout remains diagnosable.
2. Characterize the current callback with the real tokenizer but no model across 1/4/8-entry ledgers.
3. Prove an incremental-prefix tracker has byte-identical allowed-token sets and safely rebuilds on tokenizer-decoding divergence.
4. Freeze and review that candidate before one separately authorized Stage-P-only Case 01 diagnostic.

No timeout, output ceiling, prompt, schema, tokenizer, model, or semantic boundary should change based on the current evidence. The two unused calls from failed Run 1 do not authorize another execution.
