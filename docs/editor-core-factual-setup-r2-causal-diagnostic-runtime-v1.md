# EDITOR factual setup R2 causal diagnostic: real runtime boundary v1

This successor binds the published factorial design at commit
`67946ad7375d7631ea184b974667e08de6db3292` to a real tokenizer and a future
training runtime. It does not authorize any real slot.

The tokenizer-only preflight verifies the exact tokenizer file, maps every T1
critical character span to every overlapping complete tokenizer label (with
the deterministic token-boundary expansion recorded), reconstructs the three
matched row orders, and stops before model imports. The worker places ML imports
behind a separate execution-authority gate. Outputs are distinct per arm and
seed; terminal, teacher-forced, adapter-delta, and semantic receipts are
content-addressed. Invalid runs may emit only bounded failure metadata and may
not emit partial eligible receipts.

T0/T1 changes only per-token loss weighting. S0/S1 changes only learning rate.
This remains development research without parent-selection authority.
