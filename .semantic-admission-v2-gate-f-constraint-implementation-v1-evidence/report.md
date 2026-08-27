# Gate-F constraint implementation V1

The evaluation-only streaming DFA is implemented as a standard-library-only module with no production import edge. It enforces the fixed root and field order, Gate-F decisions and governed codes, status values, nullable JSON strings and escapes, confidence range, PASS/non-PASS invariants, decisive-reason requirement, eight-record and 8,000-character bounds, and EOS only after a complete object.

The property suite covers all canonical response classes, chunk invariance, fences, prose, trailing bytes, wrong gate/key/code, confidence violations, missing decisive evidence, escapes, multiple records, bounds, token framing, terminal EOS, and empty-set failure. Twenty-six implementation/design tests pass.

The first WSL attempt revealed that the frozen inference virtual environment lacks Pydantic. The module was made self-contained and is loaded directly, avoiding the application package import graph. The corrected tokenizer-only run exhaustively projected all 131,072 vocabulary IDs at five representative states. Canonical PASS and FAIL token streams terminate correctly; root framing excludes fences; EOS is unavailable before completion.

Performance is not acceptable for runner integration. The full-prefix correctness projector took up to 3.055936 seconds for one free-string step, above the 0.25-second evaluation threshold. It is frozen as a correctness oracle only. No runner was modified and no model/provider call occurred.

The next bounded step is an optimized prefix-trie and immutable-DFA-state cache. It must prove allowed-token equivalence to this oracle over representative and randomized states, preserve contextual decode correctness, and meet the per-step/cache bounds before any model inference.
