# Staged Gate F Cases 01/10 proof — Run 1

The exact proof failed before semantic evidence was produced. Both Stage P calls reached the configured 240-second subprocess timeout. Each case therefore abstained with `STAGE_P_PROVIDER_OR_TRANSPORT_FAILURE`; Stage C was not called. Two calls were consumed, two authorized calls remained unused, and no retry, repair, selection, Gate S call, or runtime mutation occurred.

The fail-closed coordinator and call-ceiling behavior worked exactly as designed. The required semantic outcomes were not observed, so neither case passes the acceptance contract and the staged candidate gains no further authority.

The host diagnostic trace retained the initial `inference_started=false` value because the runner lifecycle file lived inside the temporary subprocess directory and became unavailable after timeout. That host value must not be interpreted as proof that WSL model inference never began. The runner inference state after launch is unknown. This is an evidence-durability defect independent of the Stage P timeout.

Recommended next step: a design-only Stage P timeout and lifecycle-durability analysis. It should isolate model-load time, trie/prewarm time, per-token projection cost, generation progress, token ceiling, and terminal reachability; move runner lifecycle capture to an append-only path that survives timeout; and specify bounded remediation. Do not rerun Cases 01/10 until that design is approved and a zero-inference remediation candidate passes review.
