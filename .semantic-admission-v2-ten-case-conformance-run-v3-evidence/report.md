# Semantic Admission V2 — constrained Run 3 report

## Outcome

Run 3 executed exactly once and failed closed before model inference. All twenty scheduled evaluator attempts were durably recorded. The Windows-to-WSL service launch returned `Wsl/Service/E_ACCESSDENIED` for both executor paths, so no model loaded and no raw semantic judgment was produced.

This is an infrastructure result, not a measurement of Semantic Admission V2 correctness.

## Counts

- Ten frozen cases evaluated.
- Ten Gate F attempts and ten Gate S attempts.
- Twenty evaluator exceptions and twenty `INDETERMINATE` gate decisions.
- Ten final `ADMISSION_ABSTAINED` decisions.
- Zero admissions and therefore zero false admissions.
- Zero model responses and zero inference starts.
- Zero retries, repairs, selections, or replacements.

## Failure localization

The durable Core diagnostic traces show that each executor was invoked and attempted to launch its WSL runner. WSL returned `Access is denied. Error code: Wsl/Service/E_ACCESSDENIED`. The failure occurred before runner lifecycle evidence, model loading, or inference. Gate F reported `constrained Core V1.2 local runner failed`; Gate S reported `Core V1.2 local runner failed`.

The admission coordinator handled every failure conservatively: both gates became indeterminate and precedence produced abstention. No current runtime behavior was affected.

## Acceptance-contract conclusion

The ten owner-adjudicated classifications were not semantically tested because neither gate returned a judgment. Run 3 demonstrates fail-closed behavior under a shared execution dependency failure, but supplies no evidence for true-positive, true-negative, false-positive, or false-negative semantic performance.

## Authority boundary

The result is quarantined evaluation evidence only. It grants no curriculum, training, prompt, model, production, or runtime authority. Run 3 must remain immutable and must not be retried, repaired, overwritten, or presented as a semantic conformance pass.

## Recommended next step

Run a zero-inference dependency/access preflight from an execution context permitted to access the WSL service. It should prove only that both exact runner paths can launch and complete their existing preflight/lifecycle checks without loading the model. If that succeeds, request separate owner authorization for a newly identified one-shot run preserving the same frozen cases and acceptance contract. Run 3 remains preserved as the failed infrastructure attempt.
