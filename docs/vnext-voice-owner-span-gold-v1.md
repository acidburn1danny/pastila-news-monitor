# VNext VOICE span-level owner gold v1

This boundary creates a conservative pilot dataset from exact, non-overlapping factual-setup and owner-commentary line spans in the frozen train and validation families. It performs no rewriting, completion, or quota filling.

Only episodes 22–30 assigned to train or validation are read by the builder. Episodes 31–34 and the prior Qwen3 bakeoff remain model-unexposed holdouts. Mechanism roles are recorded separately as individual, supporting, and composition annotations under Humor Mechanics Curriculum V1.

The pilot is intentionally not sufficient for LoRA training: it contains 16 records, partial mechanism coverage, no completed negative/abstention set, and limited blind holdout evidence. Factual authority and constrained projection remain runtime concerns.
