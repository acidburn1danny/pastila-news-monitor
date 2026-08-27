# Scope Graph V1.1 — frozen-tokenizer compatibility

Result: **PASS**. Five valid streams totaling 1,406 token transitions decoded exactly, remained allowed at every transition, reached terminal state, and allowed only EOS afterward. The invalid null-support `GOVERNED_EVENT` stream was blocked at token index 75.

The known frozen Mistral-regex warning remains unchanged. Torch was imported transitively by Transformers, but no model module or weights were loaded and no request, runner, provider, or inference action occurred.
