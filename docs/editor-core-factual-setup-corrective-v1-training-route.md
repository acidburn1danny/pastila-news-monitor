# EDITOR Factual Setup Corrective v1 training route

This bounded route is tied to published dataset commit `5a5537ff9eb076a289b8fde6b306c38c11085899`, manifest `50b387a0025025f5daac68cd65ab5570a731f9bb0db2a82c023921829e806a88`, config `2b813d0485a3d3e186e4b5a4c88139af83d8d54fb25e759cee0921ee94da230b`, and R2 step-9.

The frozen execution recipe is one epoch over 72 rows, batch size 1, gradient accumulation 8, nine optimizer steps, BF16 compute, and a fresh paged AdamW 8-bit optimizer at learning rate `5e-7`. Only the final step-9 output is retained.

The shell route requires an explicit owner authorization environment flag, validates every frozen identity, runs the published zero-step gate, isolates the process from the network, and mounts inputs read-only. Fixture smoke imports no ML runtime, creates no optimizer, loads no model, and performs no training.

`--preflight-only` executes the complete source, runtime, model, parent, corpus, config, manifest, output-root and zero-step validation chain, then exits before runtime extraction, chroot, model load or optimizer creation. `--execute-authorized` remains separately guarded by the owner-authorization environment flag.

The 24-case corrective holdout and all historical holdouts are absent from the execution route. EDITOR remains limited to a factual 2–3 sentence setup; VOICE and CHIEF EDITOR objectives are excluded.
