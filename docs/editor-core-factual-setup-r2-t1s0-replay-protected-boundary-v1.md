# T1/S0 Replay-Protected fixture execution boundary

This boundary validates six matched fixture slots: two arms by three seeds. It binds the published protocol and pack, R2 step-9, recipe S0, the frozen evaluator, deterministic decoding, and tokenizer identity.

The tokenizer rule selects every contiguous token whose offset intersects a critical span wholly contained in the assistant `text` value. Output roots must be distinct and empty. Teacher-forced full-target and critical-span diagnostics, deterministic development scoring, and deterministic replay scoring remain separate receipts.

Terminal interpretation is fail-closed: incomplete arm or seed evidence cannot produce a decision; any material replay regression produces `STOP`; retained replay with loss of targeted gain produces `REVISE`; replicated gain with complete retention can produce `CONTINUE_RESEARCH`. No state grants parent-selection authority.

This implementation is fixture-only. It contains no model loader, optimizer creation, real training, or real inference authority.
