# Semantic Admission V2 — constrained Run 3 design and preflight

## Outcome

The bounded Run 3 design is complete and its zero-inference preflight passed. No Run 3 execution authority was issued and no provider or model call was made.

## Frozen execution design

- Diagnostic universe: the ten frozen owner-adjudicated `HMCV1-SASC-01` through `HMCV1-SASC-10` cases.
- Gate order: factual-semantic Gate F, then story-specificity Gate S.
- Gate F: constrained V2.3 executor and evaluator.
- Gate S: unchanged V2.2 evaluator and ordinary executor.
- Maximum execution budget: exactly two planned calls per case, twenty calls total.
- Expected labels remain hidden from both generation paths.
- Precedence is fail closed: Gate F indeterminate, Gate F failure, Gate S indeterminate, Gate S non-pass, then admission only when both gates pass.
- Every raw provider result or exception must be durably written to the call ledger before it is returned or propagated. The per-case journal is written after coordination.
- Outputs, if later authorized, remain quarantined diagnostic evidence with no curriculum, training, or runtime authority.

## Zero-inference verification

The preflight constructed both executor types without invoking either one. It bound all twenty request and prompt hashes, verified the ten-case universe and twenty-call ceiling, verified the empty output targets, and confirmed that the separately required execution-authority artifact is absent.

Result: `PASS`.

## Preserved failed attempt

The first preflight launch stopped before executor construction because the directly launched script could not resolve its `scripts` namespace import. That failure is preserved separately. The import was made compatible with direct script execution, after which the zero-inference preflight passed. Neither attempt performed inference.

## Authority boundary

This bundle freezes design and zero-inference readiness only. It does not authorize Run 3, inference, curriculum exposure, enrichment, recovery, prompt or model modification, runtime activation, or training. The immutable governed factual authority remains separate.

## Recommended next step

Only under separate owner authorization, issue a narrowly bound execution-authority artifact for this exact plan identity and execute Run 3 once: ten cases, Gate F then Gate S, no retries or repairs, and no more than twenty provider calls. Preserve every raw result and exception through the durable ledger.
