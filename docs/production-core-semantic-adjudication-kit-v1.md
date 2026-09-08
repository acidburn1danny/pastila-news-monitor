# Core V2 Semantic Adjudication Kit V1

Status: **candidate-neutral synthetic qualification only**.

This offline kit authenticates two independent human decisions without making
the candidate responsible for its own verdict. It does not run a model, contain
candidate output, designate adjudicators, or promote a candidate.

Each reviewer receives the same candidate-blinded case, output, assertion,
rubric, and adjudicator-registry identities. `ADJUDICATOR_A` and
`ADJUDICATOR_B` sign separate canonical
receipts with distinct owner-registered identities and Ed25519 keys. Only two
valid `PASS` receipts over the exact owner-supplied qualification authority
aggregate to `PASS`. Every other state fails closed. Candidate aliases are
restricted to the opaque values `CANDIDATE-A` and `CANDIDATE-B`.

## Key handling

Generate each private key on its evaluator's computer. Never copy or commit the
private key. Export only the public key. The owner registration is consumed as
one byte-exact, SHA-256-bound registry snapshot. The production loader rejects
duplicate or reordered fields, noncanonical key encoding, non-Ed25519 SPKI
bytes, identity mismatch, and non-independent registrations. It materializes
the public keys only from that validated snapshot; caller-selected
role/person/key mappings are not a production authority path.

The production registry wrapper consumes the exact canonical blind-packet
bytes, verifies the packet identity and raw-output Base64/SHA-256 binding, and
derives receipt authority exclusively from that snapshot. Structural `FAIL`
is terminal before signature verification; neither signed semantic `PASS`
receipts nor caller-selected expected-authority fields can override it.
Before adjudication, the wrapper also requires the packet's unique membership
in a canonical export inventory whose root is bound by an explicitly
owner-authorized custody identity produced after qualification execution.

The kit accepts an explicit OpenSSL runtime manifest for the executable,
`libcrypto`, and `libssl`. It snapshots their verified bytes before execution
and supplies an isolated empty configuration/provider directory and explicit
`PATH`; inherited OpenSSL configuration cannot alter the result. It does not
search `PATH`, download a verifier, or accept verifier substitution. Signing
and verification use Ed25519 raw-message mode. Receipt identity is SHA-256 over
the exact canonical signed message followed by the raw signature bytes.

## Independence and lifecycle

Reviewers must not learn the candidate identity or the other reviewer's verdict
before both receipts are terminal. Missing, duplicate, malformed, mismatched,
or invalidly signed receipts fail closed. A disagreement or `INDETERMINATE`
result also fails closed; it cannot trigger a retry or redraw.

The approved `PROJECT_CONTROLLED_TRUE_HOLDOUT` claim excludes the holdout from
all project-controlled training, fine-tuning, adapter training, prompt and
threshold selection, qualification design, and prior candidate evaluation.
Possible occurrence of identical or similar text in external base-model
pretraining is unknown and outside this claim. `GLOBAL_TRAINING_EXCLUSION` is
not claimed.

This generation contains synthetic fixtures only. Corpus creation, candidate
execution, adjudication receipts, and promotion remain separate authorities.
The registry identity is a signed receipt field and an exact expected-authority
field, so a receipt from a stale or substituted registry cannot be aggregated.
