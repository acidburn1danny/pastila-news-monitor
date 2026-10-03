# VNext VOICE training-ready dataset freeze v1

All 69 top-level topic sections in train and validation families are inventoried. Twenty-four exact factual/commentary pairs remain admitted; 45 sections remain excluded because no additional exact pair can be admitted without semantic inference, rewriting, or generated completion.

The four abstention candidates remain evidence-only. They are not converted into model-visible examples because the current authority does not bind an exact input to an authoritative abstention output.

The manifest freezes content hashes for positive train/validation, context-mismatch negatives, and abstention evidence. Holdout episodes 31–34 are represented only by pre-existing family and source identities, with content access denied. Qwen3 bakeoff remains evaluation-only.

Readiness requires at least 60 train positives, 20 validation positives, 20,000 commentary tokens, adequate per-mechanism support, a 1:1 negative ratio, 16 authoritative model-visible abstention examples, zero duplication/leakage, zero unsupported facts, and a passing blind evaluation. The current dataset fails these thresholds and no training is performed.
