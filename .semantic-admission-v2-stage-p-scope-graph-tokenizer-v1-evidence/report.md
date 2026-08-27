# Stage P Scope Graph V1 — frozen-tokenizer compatibility

Result: **PASS**. Four structurally distinct streams totaling **1,160 tokens/transitions** decoded byte-exactly, remained permitted at every next-token boundary, reached terminal state, and allowed only EOS after closure.

The frozen tokenizer emitted its previously recorded Mistral-regex warning. No repair flag was applied because changing tokenization would break the frozen tokenizer identity. `transformers` imported Torch transitively, but no model module or weights were loaded and no runner, provider, or inference call occurred.

The first two profile launches stopped before tokenizer loading because the reboot changed the registered WSL distribution name and the virtual environment exposes `python3` rather than `python`. The third launch used the resolved immutable environment and produced this evidence.
