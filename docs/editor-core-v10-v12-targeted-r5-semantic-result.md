# Editor Core targeted R5 development decision

The independent frozen 12-case R5 holdout comparison is recorded in
`docs/artifacts/editor-core-v10-v12-targeted-r5-semantic-result.json` and is
bound to the published evaluation route at `88bfb41eb6ade95ef839425e157423a7319f0513`.
Both R2 step-9 and R5 step-6 produced 12 structurally valid responses and
preserved the requested epistemic distinctions. Ten responses were identical.
The two changed responses, cases 13 and 15, provided no semantic improvement;
R5 weakened the grammatical quality of attribution wording.

R5 step-6 is **rejected for development-parent selection**. R2 step-9 remains
the development parent. This decision does not discard R5's training or
evaluation evidence. The frozen holdout remains evaluation-only. The lexical
diagnostic check is not, by itself, a semantic selection rule.

This is a development decision only. It does not perform training,
adjudication, promotion, release, or certification.
