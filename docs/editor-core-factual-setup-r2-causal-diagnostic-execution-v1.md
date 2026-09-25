# R2 causal diagnostic execution boundary v1

This boundary is fixture-only. It binds the four factorial arms and twelve
arm/seed slots to published commit `e4858a37f98890618d4e59579bf074043a3c81b7`.
It grants no model-load, optimizer, training, inference, parent-selection,
promotion, or release authority.

The fixture worker validates UTF-8 byte-span to tokenizer-token mapping,
matched row ordering, teacher-forced full and critical likelihood aggregation
before and after each future run,
adapter deltas, train acquisition, replay retention, development evaluation,
slot output isolation, zero-step behavior, and all predeclared stop rules.
The production tokenizer and ML runtime remain outside this boundary.
