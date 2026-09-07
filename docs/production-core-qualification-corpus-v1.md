# Production Core Qualification Corpus V1

Status: **candidate-neutral, frozen before candidate execution**.

This boundary contains exactly 200 unique cases in the eight owner-approved,
exclusive primary partitions: 40 factual-authority, 30 uncertainty-retention,
30 summarization, 25 conflicting/insufficient-authority, 20 instruction
hierarchy, 20 completion/EOS, 20 Romanian editorial, and 15 malformed or
adversarial cases. Secondary labels may overlap but do not alter these counts.

Every case binds its request, requested output type, authority spans, request
identity, and case identity. The separate assertion manifest defines the
required outcome, expected propositions, prohibited claims, uncertainty,
source-span bindings, completion rules, and hard and semantic assertions for
every case. The catalog uses multiple scenario, conflict, injection, completion,
Romanian editorial, and malformed-input families rather than ordinal-only
copies. The rubric
binds the already approved non-compensating gates and the owner-registered
adjudicator registry. No candidate output, score, threshold selection, or
production designation contributed to the corpus.

## Project-controlled true holdout

The separate holdout manifest contains exactly 50 case IDs and case SHA-256
identities. The claim is `PROJECT_CONTROLLED_TRUE_HOLDOUT`: these cases are
excluded from project-controlled training, fine-tuning, adapter training,
prompt selection, threshold selection, qualification design, and prior
candidate evaluation. Post-freeze access is limited by purpose to integrity
validation, an authorized candidate evaluation, and independent semantic
adjudication by the two registered roles. This is a project-controlled access
claim, not an assertion that repository bytes are cryptographically secret.

Possible occurrence of identical or similar text in external base-model
pretraining is unknown and outside the holdout claim. No
`GLOBAL_TRAINING_EXCLUSION` is claimed.

## Freeze and access boundary

The corpus, holdout, assertions, rubric, provenance receipt, and access-control
receipt are separate canonical JSON artifacts. The terminal freeze record
binds every artifact byte identity and every semantic identity. All were
materialized from commit `587442835faa85084e7245759bb33ffbe141c7a3`
before any candidate execution. Altered membership, counts, content, authority,
access policy, provenance, or artifact bytes fail closed.

The qualification binds the generic validator and the external freeze-authority
implementation. A separate terminal authority then pins the exact freeze and
qualification artifact hashes and semantic identities. This ordering is
deliberately non-circular: the terminal root is commit-reviewed authority, not
an input to the qualification it authenticates. Consequently, recomputing every
internal identity after a semantic substitution cannot create an accepted
replacement authority.

This freeze authorizes neither candidate execution nor candidate promotion.
