# Construction-Obligation V2 V1.1 load-only validation

The single authorized V1.1 attempt completed with return code 0. The supervisor
loaded the frozen model, attached the frozen adapter, validated the exact
compatibility receipt, released the child resources, and emitted a terminal
`LOAD_ONLY_COMPLETED_COMPATIBILITY_VALIDATED_AND_RELEASED` lifecycle record.

The validated receipt identity is
`8ddafa5e60e892abf56a2b67d9ab646deb94a7b024e739ea8ea967c45e3ec39f`.
It classifies exactly 336 absent vision-side LoRA keys as the previously proved
structural zero-delta target overmatch. No unexpected missing or extra keys were
accepted. The PEFT warning was caught inside the child and did not escape into
the raw host stderr.

Raw stdout, raw stderr, the canonical WSL receipt, and all four append-only
lifecycle records are preserved byte-for-byte and bound by the manifest. Raw
stderr contains only weight-loading progress and the known Transformers tied
weight configuration warning.

Post-cleanup GPU observation was 15,025 MiB free and 953 MiB used on CUDA device
0. This observation confirms release at inspection time; it grants no ongoing
runtime claim.

Generation, retry, fallback, probe, and Stage C counts are all zero. This bundle
grants no generation readiness, runtime authority, or production authority.
