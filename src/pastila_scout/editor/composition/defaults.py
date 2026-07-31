"""Canonical identity and policy constants for Module 2.8."""

COMPOSITION_ENGINE_ID = "pastila-acida-editorial-composition-engine"
COMPOSITION_ENGINE_VERSION = "1.0.0"

REQUIRED_UPSTREAM_MODULES = (
    "editorial-memory",
    "editorial-persona",
    "editorial-philosophy",
    "editorial-decision-framework",
    "editorial-voice",
    "audience-model",
    "story-architecture",
    "spoken-communication-engine",
    "romanian-conversational-engine",
    "editorial-language-learning-engine",
)

EDITORIAL_PRECEDENCE = (
    "factual-integrity",
    "legal-precision",
    "attribution",
    "editor-in-chief",
    "safety-and-dignity",
    "approved-editorial-decision",
    "story-architecture",
    "spoken-communication",
    "romanian-conversational",
    "persona-and-philosophy",
    "editorial-voice",
    "audience",
    "established-learned-guidance",
    "emerging-learned-guidance",
    "optional-composition-optimization",
)

VOLATILE_FIELDS = frozenset(
    {
        "timestamp",
        "created_at",
        "updated_at",
        "generated_at",
        "runtime_id",
        "runtime_identifier",
        "filesystem_path",
        "storage_path",
        "transient_diagnostics",
    }
)

SELF_FINGERPRINT_FIELDS = frozenset(
    {
        "input_fingerprint",
        "composition_fingerprint",
        "segment_fingerprint",
        "beat_fingerprint",
        "sequence_fingerprint",
        "arc_fingerprint",
        "arc_step_fingerprint",
        "binding_fingerprint",
        "constraint_fingerprint",
        "arc_conflict_fingerprint",
        "transition_fingerprint",
        "callback_fingerprint",
        "priority_fingerprint",
        "tone_fingerprint",
        "emphasis_fingerprint",
        "rhythm_fingerprint",
        "traceability_fingerprint",
        "decision_fingerprint",
        "conflict_fingerprint",
    }
)

MEANINGFULLY_ORDERED_FIELDS = frozenset(
    {
        "approved_segments",
        "ordered_segment_ids",
        "segment_plans",
        "ordered_beat_ids",
        "beats",
        "ordered_arc_step_ids",
        "arc_steps",
        "segment_bindings",
        "ordered_tone_steps",
        "transition_plans",
        "callback_plans",
    }
)

__all__ = (
    "COMPOSITION_ENGINE_ID",
    "COMPOSITION_ENGINE_VERSION",
    "EDITORIAL_PRECEDENCE",
    "REQUIRED_UPSTREAM_MODULES",
)
