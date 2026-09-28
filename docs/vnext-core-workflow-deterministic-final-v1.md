# VNext Core Workflow → Deterministic FINAL Vertical Slice v1

Status: isolated successor vertical slice; no active integration.

The slice merges workflow policy and deterministic FINAL in one product module while preserving the frozen workflow states and transitions. Only persisted, workflow-owned `ACCEPTED_SETUP` or explicitly approved `SOURCE_FALLBACK` artifacts can enter policy review. VOICE remains disabled and is represented by the existing `VOICE_DISABLED` state.

Policy authority is a SQLite-persisted, workflow-bound, single-use session. Approval, rejection and revision are explicit. FINAL requires a persisted `APPROVE_FINAL` decision and produces canonical UTF-8 JSON whose content-addressed blob and export bytes are identical. Replays are idempotent; conflicts, unowned inputs, drafts, abstentions and altered payloads fail closed.

SQLite schema v6 adds only `policy_sessions`. The workflow authority, product root, product lock, model closure, candidate state and historical evidence remain unchanged.
