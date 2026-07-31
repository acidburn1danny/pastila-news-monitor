"""Canonical Module 2.9 identities and semantic field policy."""

SCRIPT_COMPOSER_ID = "pastila-acida-editorial-script-composer"
SCRIPT_COMPOSER_VERSION = "1.0.0"

CUSTOM_PATTERN = r"^custom:[a-z0-9]+(?:-[a-z0-9]+)*$"
FINGERPRINT_PATTERN = r"^[0-9a-f]{64}$"
IDENTITY_PATTERN = r"^scout:[a-z0-9]+(?:-[a-z0-9]+)*:[0-9a-f]{64}$"
SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"

SELF_FINGERPRINT_FIELDS = frozenset(
    {
        "profile_fingerprint",
        "policy_fingerprint",
        "request_fingerprint",
        "unit_fingerprint",
        "partial_fingerprint",
        "response_fingerprint",
        "acceptance_fingerprint",
        "span_fingerprint",
        "claim_fingerprint",
        "reference_fingerprint",
        "attribution_fingerprint",
        "annotation_fingerprint",
        "instruction_fingerprint",
        "constraint_fingerprint",
        "permission_fingerprint",
        "source_fingerprint",
        "decision_fingerprint",
        "conflict_fingerprint",
        "trace_entry_fingerprint",
        "traceability_fingerprint",
        "sentence_fingerprint",
        "paragraph_fingerprint",
        "beat_fingerprint",
        "segment_fingerprint",
        "transition_fingerprint",
        "callback_fingerprint",
        "script_draft_fingerprint",
        "authority_fingerprint",
        "result_fingerprint",
        "input_fingerprint",
        "lineage_fingerprint",
        "semantic_fingerprint",
    }
)

TRANSIENT_FIELDS = frozenset(
    {
        "timestamp",
        "created_at",
        "updated_at",
        "generated_at",
        "executed_at",
        "latency_ms",
        "usage",
        "input_tokens",
        "output_tokens",
        "retry_count",
        "attempt_count",
        "provider_request_id",
        "provider_execution_reference",
        "provider_execution_references",
        "runtime_id",
        "runtime_identifier",
        "storage_path",
        "filesystem_path",
        "transient_diagnostics",
        "validation_findings",
        "segment_validation_findings",
        "draft_readiness",
        "readiness",
    }
)

MEANINGFULLY_ORDERED_FIELDS = frozenset(
    {
        "target_segment_references",
        "target_beat_references",
        "structured_generated_units",
        "ordered_script_segment_ids",
        "script_segments",
        "ordered_script_beat_ids",
        "script_beats",
        "ordered_paragraph_ids",
        "paragraphs",
        "ordered_sentence_ids",
        "sentences",
        "transition_realizations",
        "callback_realizations",
    }
)

PRESENTATION_ANNOTATION_FIELDS = frozenset({"delivery_annotations"})

__all__ = (
    "CUSTOM_PATTERN",
    "FINGERPRINT_PATTERN",
    "IDENTITY_PATTERN",
    "MEANINGFULLY_ORDERED_FIELDS",
    "PRESENTATION_ANNOTATION_FIELDS",
    "SCRIPT_COMPOSER_ID",
    "SCRIPT_COMPOSER_VERSION",
    "SELF_FINGERPRINT_FIELDS",
    "SEMVER_PATTERN",
    "TRANSIENT_FIELDS",
)
