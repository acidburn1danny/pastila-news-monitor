# OpenAI Controlled Revision provider output reconstruction

Part 5B corrects the OpenAI-specific output ownership boundary. The old strict
schema requested a complete `EpisodeDraft`, including authoritative identity,
protected structures, and deterministically derived text. JSON Schema could validate
the object shape but not the domain's cross-field invariants.

The provider now returns `OpenAIControlledRevisionProviderOutput`, a strict list of
authorized component edits. Depending on component type, it contains only editable
text: opening, closing, transition text, story prose fields, or a CTA bridge. It
contains no episode ID, ordering authority, lineage, fingerprints, contract version,
gateway identity, assembled text, or teleprompter text. Unknown properties and
duplicate references are rejected.

The projector supplies only the targeted source components as untrusted data and
lists the required canonical component references. Protected draft content is no
longer sent merely so the model can echo it. References are checked against the
invocation after structural DTO validation.

The deterministic reconstructor begins with the authoritative source draft, applies
exactly one returned edit for every authorized target, preserves all component IDs
and ordering, restores all untargeted state from the source, and calls the existing
`derive_assembled_text` algorithm. `teleprompter_text` is also computed from the
assembled result at this boundary; later teleprompter formatting remains a separate
deterministic pipeline stage. The unchanged `EpisodeDraft` validators then validate
the reconstructed aggregate. Lineage and fingerprints continue to come from the
invocation and existing gateway factory.

External failures remain content-free. Provider DTO validation additionally retains
safe internal metadata: validation stage, error count, first top-level field,
Pydantic error category, and presence classification. It never retains input values,
raw validation messages, prompts, source text, revised text, responses, credentials,
or stack traces.

The internal provider-output format intentionally breaks compatibility with the old
unsafe complete-draft shape. No persisted OpenAI response payloads or production
callers require dual-format support.

The live smoke test uses the synthetic E2E-01 fixture, one attempt, one SDK request,
no fallback, and the configured model from `config/config.yaml`. It skips by default:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test_openai_controlled_revision_part5b.py
```

Explicit one-request execution:

```powershell
$env:SCOUT_RUN_LIVE_OPENAI_PART5B='1'
.\.venv\Scripts\python.exe scripts\smoke_test_openai_controlled_revision_part5b.py
Remove-Item Env:SCOUT_RUN_LIVE_OPENAI_PART5B
```

The Part 4 and Part 5 opt-in flags do not activate this harness. Output is limited to
content-free status, counters, availability flags, duration, and token usage.
