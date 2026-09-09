# Core V2 Comparative Candidate Qualification Mechanism V1

Status: **offline-qualified and frozen before candidate inference**.

This boundary prepares, but does not itself authorize or perform, the comparative
qualification of the two experimental candidates. It cannot designate a
production model. Candidate promotion remains a separate owner decision.

The public generation contains exactly two clean materializations, three
repetitions, 200 frozen cases and two opaque aliases: 2,400 scheduled rows. A
locally generated 256-bit secret randomizes and deterministically orders the
rows. Only its SHA-256 commitment is public. The alias mapping remains outside
Git and must not be disclosed to either adjudicator before both adjudications
are terminal.

Both candidates receive the same case-derived user request. Candidate-specific
system prompts and adapters remain part of each frozen candidate identity, not
part of the shared request. The output contract is exactly Structured
Qualification Response V1. Raw bytes are always retained byte-for-byte. A
canonical UTF-8 JSON response proceeds to semantic adjudication; an invalid
response is represented in the blinded packet by its exact Base64 bytes and
SHA-256 identity and receives a fail-closed per-case structural result. Invalid
candidate behavior never becomes a batch infrastructure failure. Repair,
extraction, truncation, retry and redraw remain prohibited.
Absence of terminal EOS is the same per-case structural failure. Structural
FAIL is terminal evaluator authority: no semantic-adjudication authority is
issued for that packet, so a later human receipt cannot override it with PASS.

Ordinal 7 completed all 2,400 executions and its byte-exact evidence remains
preserved, but it is invalid as a comparative semantic qualification because
the common request did not materialize the complete frozen response contract.
Its blinded packets must not be sent for adjudication and its outputs must not
be extracted or repaired. The ordinal-8 successor embeds the exact schema
constants, enums, branch invariants, binding rules, compact JSON/no-fence
framing, and immediate-EOF rule in every common request. It is a new frozen
generation, never a retry or redraw.

The complete ordinal-8 request was tokenizer-qualified offline in both clean
materializations using the frozen `fix_mistral_regex=True` tokenizer. All 400
candidate/case combinations fit the 1,924-token input ceiling; the maximum is
1,568 tokens, attained by candidate V1.1 on `pcq-rom-011`. Both materializations
produce request/token-count root
`d4684f53edf9a33e745e7ad42ca75d4dce64a849e457899960f60e4ef47417e8`.
No model was loaded and no inference or network activity occurred.

Execution consumes the frozen content-addressed OCI rootfs tar through one open
descriptor, extracts a private rootfs, snapshots candidate directories, uses
read-only model and adapter mounts, and creates exactly one child network/PID/
mount boundary with no external interface. Actual interfaces, routes and mount
properties are probed before model loading. The parent custodian remains
non-networking for this qualification.
Input is capped at 1,924 tokens, output at 6,268 tokens and total context at
8,192. Load-plus-case-generation is capped at 600 seconds and process peak RSS
at 16,106,127,360 bytes. Every overflow fails closed.

An external heartbeat watchdog kills the batch when load or one generation
exceeds 600 seconds. The single attempt is consumed before launch; any failure
creates a terminal failure receipt over the partial artifact root and cannot be
retried or redrawn.

Each successful case produces immutable raw bytes, a self-bound runtime observation,
resource measurements, network/file-boundary logs and an execution receipt.
The host then validates the exact raw bytes and constructs candidate-blinded
packets bound to the corpus, assertion, rubric, registry and qualification
generation identities. Human Ed25519 receipts and semantic PASS/FAIL remain a
later execution output; fixture tests do not impersonate either adjudicator.
Role-specific export roots contain only blinded packets and a custody manifest;
candidate identities, the alias mapping, observations and private logs stay in
the custodian-only tree. A terminal completion identity binds the full private
artifact inventory and both export-custody identities.

No candidate inference may begin until this exact mechanism, generation and
candidate-object manifest pass independent review and are committed.
