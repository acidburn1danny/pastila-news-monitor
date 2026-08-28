# Construction-Obligation V2 one-shot load-only result

The single authorized attempt completed the NF4 base-model load, attached the frozen adapter, and released the model process. The canonical WSL receipt recorded return code 0, no timeout, and 38.362 seconds elapsed. Durable lifecycle evidence records `MODEL_LOAD_STARTED`, `MODEL_LOAD_COMPLETED`, `MODEL_LOAD_CLEANUP_COMPLETED`, and the terminal `LOAD_ONLY_COMPLETED_AND_RELEASED` result.

The load emitted two compatibility warnings: Transformers declined a configured tied-weight relationship because both checkpoint weights were present with different values, and PEFT reported missing adapter keys associated with the preserved vision tower. The latter is material to compatibility adjudication. Load completion does not establish adapter completeness, semantic equivalence, generation readiness, or runtime/production eligibility.

The transport receipt preserved the exact stderr SHA-256, but raw stderr was printed to the host tool stream rather than durably persisted. This bundle does not reconstruct or fabricate the missing raw stream. The warning classes above are limited to what was directly observed during the attempt.

No tokenizer, prompt, generation, inference, retry, fallback, probe, or Stage C operation occurred. The one-shot authority is consumed. Any compatibility investigation or future execution requires separate authorization; no rerun is implied.
