"""Fail-closed validation for the frozen candidate-neutral qualification corpus."""

from __future__ import annotations

import base64
import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from typing import Any

EXPECTED_PARTITIONS = {
    "factual_authority_unsupported_claims": 40,
    "qualification_uncertainty_retention": 30,
    "summarization_compression_meaning_preservation": 30,
    "conflicting_insufficient_authority_fail_closed": 25,
    "instruction_hierarchy_override_attempts": 20,
    "completion_eos_runaway": 20,
    "romanian_editorial_representative": 20,
    "malformed_boundary_adversarial": 15,
}
EXPECTED_HOLDOUT = 50
FREEZE_BASIS_COMMIT = "587442835faa85084e7245759bb33ffbe141c7a3"
FREEZE_BASIS_TREE = "c980a1236f76dfef13f9a4e73ad2cf26c35a2ef9"
REGISTRY_IDENTITY = "26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639"
ABSTENTION_CODES = {
    "INSUFFICIENT_AUTHORITY",
    "CONFLICTING_AUTHORITY",
    "AMBIGUOUS_SCOPE",
    "UNRESOLVED_REFERENCE",
    "INSTRUCTION_AUTHORITY_CONFLICT",
    "CANNOT_SATISFY_OUTPUT_CONTRACT",
    "SAFETY_ENVELOPE_EXCEEDED",
}
HARD_ASSERTIONS = (
    "STRUCTURED_RESPONSE_V1",
    "EXACT_CASE_AND_REQUEST_BINDING",
    "NO_TRAILING_OUTPUT",
    "ZERO_RETRY_REDRAW_MUTATION",
)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _load(data: bytes) -> dict[str, Any]:
    if type(data) is not bytes:
        raise ValueError("artifact snapshot must be immutable bytes")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("artifact JSON invalid") from exc
    if not isinstance(value, dict):
        raise TypeError("artifact must be an object")
    return value


def _self_identity(value: Mapping[str, Any], field: str) -> str:
    body = dict(value)
    claimed = body.pop(field, None)
    actual = sha256(canonical(body))
    if claimed != actual:
        raise ValueError(f"{field} mismatch")
    return actual


def _expect(
    value: Mapping[str, Any], fields: tuple[str, ...], schema: str, status: str
) -> None:
    if (
        tuple(value) != fields
        or value.get("schema") != schema
        or type(value.get("schema_version")) is not int
        or value.get("schema_version") != 1
        or value.get("status") != status
    ):
        raise ValueError("artifact schema/status/fields invalid")


def classify_malformed_fixture(case_id: str, data: bytes) -> str:
    """Execute the frozen malformed request bytes through their admission class."""
    if not case_id.startswith("pcq-mal-") or type(data) is not bytes:
        raise ValueError("malformed fixture authority invalid")
    ordinal = int(case_id.rsplit("-", 1)[1])
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except UnicodeDecodeError:
        if ordinal in {4, 12}:
            return "UNRESOLVED_REFERENCE"
        raise ValueError("unexpected invalid UTF-8 fixture")
    except (json.JSONDecodeError, ValueError):
        if ordinal in {11, 12}:
            return "AMBIGUOUS_SCOPE" if ordinal == 11 else "UNRESOLVED_REFERENCE"
        raise ValueError("unexpected malformed JSON fixture")
    if ordinal == 1:
        valid, code = value.get("source_span_ids") == ["missing"], "UNRESOLVED_REFERENCE"
    elif ordinal == 2:
        spans = value.get("authority_spans", [])
        valid, code = len({x.get("span_id") for x in spans}) != len(spans), "UNRESOLVED_REFERENCE"
    elif ordinal == 3:
        source = value.get("source", {})
        valid, code = source.get("utf8_end", 0) > len(str(source.get("bytes", "")).encode()), "UNRESOLVED_REFERENCE"
    elif ordinal == 5:
        valid, code = "unexpected" in value, "AMBIGUOUS_SCOPE"
    elif ordinal == 6:
        valid, code = value.get("case_id") != case_id, "UNRESOLVED_REFERENCE"
    elif ordinal == 7:
        suffix = str(value.get("request_identity", "")).split(":", 1)[-1]
        valid, code = any(c.isupper() for c in suffix), "UNRESOLVED_REFERENCE"
    elif ordinal == 8:
        roles = value.get("roles", [])
        valid, code = len({x.get("value") for x in roles if x.get("role") == "factual"}) > 1, "CONFLICTING_AUTHORITY"
    elif ordinal == 9:
        valid, code = value.get("authority_spans") == [], "INSUFFICIENT_AUTHORITY"
    elif ordinal == 10:
        valid, code = not isinstance(value, dict), "AMBIGUOUS_SCOPE"
    elif ordinal == 13:
        valid, code = len(value.get("source_span_ids", [])) > 24, "CANNOT_SATISFY_OUTPUT_CONTRACT"
    elif ordinal == 14:
        valid, code = value.get("output_type") not in {"FACTUAL", "COMMENTARY"}, "CANNOT_SATISFY_OUTPUT_CONTRACT"
    elif ordinal == 15:
        valid, code = len(set(value.get("dates", []))) > 1 and value.get("authority") == "equal", "CONFLICTING_AUTHORITY"
    else:
        valid, code = False, ""
    if not valid:
        raise ValueError("fixture does not instantiate declared fault")
    return code


def validate_frozen_corpus(artifacts: Mapping[str, bytes]) -> str:
    """Validate the complete artifact set and return its freeze identity."""
    names = (
        "production-core-qualification-corpus-v1.json",
        "production-core-qualification-holdout-v1.json",
        "production-core-qualification-assertions-v1.json",
        "production-core-qualification-rubric-v1.json",
        "production-core-qualification-corpus-provenance-v1.json",
        "production-core-qualification-holdout-access-v1.json",
        "production-core-qualification-corpus-freeze-v1.json",
        "production-core-qualification-corpus-freeze-qualification-v1.json",
    )
    if tuple(artifacts) != names:
        raise ValueError("artifact set/order invalid")
    values = {name: _load(artifacts[name]) for name in names}
    corpus, holdout, assertions, rubric, provenance, access, freeze, qualification = (
        values.values()
    )
    _expect(
        corpus,
        (
            "schema",
            "schema_version",
            "status",
            "freeze_basis_commit",
            "freeze_basis_tree",
            "case_count",
            "cases",
            "corpus_identity",
        ),
        "pastila-production-core-qualification-corpus",
        "FROZEN_BEFORE_CANDIDATE_EXECUTION",
    )
    _expect(
        holdout,
        (
            "schema",
            "schema_version",
            "status",
            "claim",
            "global_training_exclusion_claimed",
            "external_pretraining_disclaimer",
            "case_count",
            "case_identities",
            "holdout_identity",
        ),
        "pastila-production-core-project-controlled-true-holdout",
        "FROZEN_BEFORE_CANDIDATE_EXECUTION",
    )
    _expect(
        assertions,
        (
            "schema",
            "schema_version",
            "status",
            "corpus_identity",
            "assertion_count",
            "assertions",
            "assertion_manifest_identity",
        ),
        "pastila-production-core-qualification-assertion-manifest",
        "FROZEN_BEFORE_CANDIDATE_EXECUTION",
    )
    _expect(
        rubric,
        (
            "schema",
            "schema_version",
            "status",
            "corpus_identity",
            "rules",
            "adjudicator_registry_identity",
            "rubric_identity",
        ),
        "pastila-production-core-qualification-rubric-manifest",
        "FROZEN_BEFORE_CANDIDATE_EXECUTION",
    )
    _expect(
        provenance,
        (
            "schema",
            "schema_version",
            "status",
            "created_by",
            "creation_method",
            "materializer_sha256",
            "case_catalog_sha256",
            "freeze_utc",
            "freeze_basis_commit",
            "freeze_basis_tree",
            "candidate_models_loaded_or_executed",
            "candidate_outputs_inspected",
            "training_tuning_prompt_threshold_inputs_used",
            "artifacts",
            "provenance_identity",
        ),
        "pastila-production-core-corpus-provenance-receipt",
        "TERMINAL_PRE_CANDIDATE_FREEZE",
    )
    _expect(
        access,
        (
            "schema",
            "schema_version",
            "status",
            "holdout_identity",
            "freeze_utc",
            "content_access_before_freeze",
            "post_freeze_allowed_purposes",
            "registered_adjudicator_roles",
            "post_freeze_excluded_project_activities",
            "candidate_runner_receives_case_only_at_frozen_evaluation_time",
            "claim_scope",
            "global_training_exclusion_claimed",
            "access_receipt_identity",
        ),
        "pastila-production-core-holdout-access-control-receipt",
        "FROZEN_ACCESS_POLICY_BEFORE_CANDIDATE_EXECUTION",
    )
    _expect(
        freeze,
        (
            "schema",
            "schema_version",
            "status",
            "freeze_utc",
            "freeze_basis_commit",
            "freeze_basis_tree",
            "corpus_identity",
            "holdout_identity",
            "assertion_manifest_identity",
            "rubric_identity",
            "provenance_identity",
            "access_receipt_identity",
            "artifact_sha256",
            "candidate_execution_authorized",
            "candidate_execution_observed",
            "freeze_identity",
        ),
        "pastila-production-core-qualification-corpus-freeze",
        "FROZEN_CANDIDATE_NEUTRAL_NO_CANDIDATE_EXECUTION",
    )
    _expect(
        qualification,
        (
            "schema",
            "schema_version",
            "status",
            "freeze_identity",
            "freeze_artifact_sha256",
            "materializer_sha256",
            "case_catalog_sha256",
            "validator_sha256",
            "test_sha256",
            "documentation_sha256",
            "external_authority_sha256",
            "external_authority_test_sha256",
            "candidate_execution_authorized",
            "candidate_execution_observed",
            "qualification_identity",
        ),
        "pastila-production-core-qualification-corpus-freeze-qualification",
        "PASS_CANDIDATE_NEUTRAL_PRE_EXECUTION_FREEZE",
    )
    corpus_identity = _self_identity(corpus, "corpus_identity")
    holdout_identity = _self_identity(holdout, "holdout_identity")
    assertion_identity = _self_identity(assertions, "assertion_manifest_identity")
    rubric_identity = _self_identity(rubric, "rubric_identity")
    provenance_identity = _self_identity(provenance, "provenance_identity")
    access_identity = _self_identity(access, "access_receipt_identity")
    freeze_identity = _self_identity(freeze, "freeze_identity")
    qualification_identity = _self_identity(qualification, "qualification_identity")
    cases = corpus.get("cases")
    if (
        corpus.get("status") != "FROZEN_BEFORE_CANDIDATE_EXECUTION"
        or corpus.get("freeze_basis_commit") != FREEZE_BASIS_COMMIT
        or corpus.get("freeze_basis_tree") != FREEZE_BASIS_TREE
        or corpus.get("case_count") != 200
        or not isinstance(cases, list)
        or len(cases) != 200
    ):
        raise ValueError("corpus authority invalid")
    ids = [case.get("case_id") for case in cases]
    if len(set(ids)) != 200 or Counter(
        case.get("primary_partition") for case in cases
    ) != Counter(EXPECTED_PARTITIONS):
        raise ValueError("case distribution invalid")
    case_hashes = {}
    fixture_codes = {}
    for case in cases:
        if tuple(case) != (
            "case_id",
            "primary_partition",
            "secondary_labels",
            "output_type",
            "request",
            "authority_spans",
            "boundary_fixture",
            "request_identity",
            "case_sha256",
        ):
            raise ValueError("case fields/order invalid")
        body = dict(case)
        claimed = body.pop("case_sha256", None)
        request_body = dict(body)
        request_claimed = request_body.pop("request_identity", None)
        if (
            request_claimed != "sha256:" + sha256(canonical(request_body))
            or claimed != sha256(canonical(body))
            or not isinstance(case.get("authority_spans"), list)
            or not case["authority_spans"]
            or case.get("output_type") not in {"FACTUAL", "COMMENTARY"}
            or not isinstance(case.get("case_id"), str)
            or not isinstance(case.get("request"), str)
            or not case["request"]
            or not isinstance(case.get("secondary_labels"), list)
            or not case["secondary_labels"]
            or len(set(case["secondary_labels"])) != len(case["secondary_labels"])
            or any(
                not isinstance(label, str) or not label
                for label in case["secondary_labels"]
            )
        ):
            raise ValueError("case identity invalid")
        for span in case["authority_spans"]:
            if tuple(span) != ("span_id", "text") or not all(
                isinstance(span.get(key), str) and span[key]
                for key in ("span_id", "text")
            ):
                raise ValueError("authority span invalid")
        if len({span["span_id"] for span in case["authority_spans"]}) != len(
            case["authority_spans"]
        ):
            raise ValueError("authority span duplicated")
        boundary = case["boundary_fixture"]
        if case["primary_partition"] == "malformed_boundary_adversarial":
            if not isinstance(boundary, dict) or tuple(boundary) != (
                "media_type",
                "bytes_base64",
                "bytes_sha256",
                "execution_stage",
            ):
                raise ValueError("malformed boundary fixture absent")
            try:
                fixture_bytes = base64.b64decode(
                    boundary["bytes_base64"], validate=True
                )
            except Exception as exc:
                raise ValueError("malformed fixture encoding invalid") from exc
            if (
                base64.b64encode(fixture_bytes).decode("ascii")
                != boundary["bytes_base64"]
                or sha256(fixture_bytes) != boundary["bytes_sha256"]
                or boundary["media_type"] != "application/json"
                or boundary["execution_stage"] != "PRE_CANDIDATE_REQUEST_VALIDATION"
            ):
                raise ValueError("malformed fixture identity invalid")
            fixture_codes[case["case_id"]] = classify_malformed_fixture(
                case["case_id"], fixture_bytes
            )
        elif boundary is not None:
            raise ValueError("boundary fixture on non-malformed case")
        case_hashes[case["case_id"]] = claimed
    entries = holdout.get("case_identities")
    if (
        holdout.get("case_count") != EXPECTED_HOLDOUT
        or not isinstance(entries, list)
        or len(entries) != EXPECTED_HOLDOUT
    ):
        raise ValueError("holdout count invalid")
    if len({entry.get("case_id") for entry in entries}) != EXPECTED_HOLDOUT or any(
        case_hashes.get(entry.get("case_id")) != entry.get("case_sha256")
        for entry in entries
    ):
        raise ValueError("holdout identity membership invalid")
    if any(tuple(entry) != ("case_id", "case_sha256") for entry in entries):
        raise ValueError("holdout entry fields/order invalid")
    if (
        holdout.get("claim") != "PROJECT_CONTROLLED_TRUE_HOLDOUT"
        or holdout.get("global_training_exclusion_claimed") is not False
    ):
        raise ValueError("holdout claim invalid")
    assertion_rows = assertions.get("assertions")
    if (
        assertions.get("corpus_identity") != corpus_identity
        or assertions.get("assertion_count") != 200
        or not isinstance(assertion_rows, list)
        or len(assertion_rows) != 200
        or len({x.get("case_id") for x in assertion_rows}) != 200
        or {x.get("case_id") for x in assertion_rows} != set(ids)
    ):
        raise ValueError("assertion closure invalid")
    case_by_id = {case["case_id"]: case for case in cases}
    for row in assertion_rows:
        if tuple(row) != (
            "case_id",
            "case_sha256",
            "required_output_type",
            "required_outcome",
            "required_abstention_code",
            "expected_semantics",
            "hard_assertions",
            "semantic_assertions",
        ):
            raise ValueError("assertion fields/order invalid")
        case = case_by_id[row["case_id"]]
        semantics = row.get("expected_semantics")
        malformed = case["primary_partition"] == "malformed_boundary_adversarial"
        if (
            row.get("case_sha256") != case_hashes[row["case_id"]]
            or row.get("required_output_type")
            != case_by_id[row["case_id"]]["output_type"]
            or row.get("required_outcome") not in {"ANSWER", "ABSTAIN"}
            or (row.get("required_outcome") == "ANSWER")
            != (row.get("required_abstention_code") is None)
            or not isinstance(row.get("hard_assertions"), list)
            or len(row["hard_assertions"]) != 4
            or not isinstance(row.get("semantic_assertions"), list)
            or len(row["semantic_assertions"]) != 5
            or not isinstance(row.get("expected_semantics"), dict)
            or not isinstance(
                row["expected_semantics"].get("required_propositions"), list
            )
            or not isinstance(row["expected_semantics"].get("prohibited_claims"), list)
            or not isinstance(
                row["expected_semantics"].get("required_source_span_bindings"),
                list,
            )
            or not isinstance(
                row["expected_semantics"].get("completion_requirements"), list
            )
        ):
            raise ValueError("case assertion authority invalid")
        if tuple(semantics) != (
            "required_propositions",
            "prohibited_claims",
            "required_source_span_bindings",
            "uncertainty_required",
            "completion_requirements",
            "required_theme",
            "required_style",
            "fault_injection",
            "required_abstention_code",
            "boundary_fixture",
        ):
            raise ValueError("semantic oracle fields/order invalid")
        list_fields = (
            "required_propositions",
            "prohibited_claims",
            "uncertainty_required",
            "completion_requirements",
        )
        if any(
            len(semantics[field]) != len(set(semantics[field]))
            or any(
                not isinstance(value, str) or not value for value in semantics[field]
            )
            for field in list_fields
        ):
            raise ValueError("semantic oracle values invalid")
        expected_semantic_codes = (
            f"PRIMARY_PARTITION:{case['primary_partition']}",
            "CASE_SPECIFIC_EXPECTED_PROPOSITIONS",
            "CASE_SPECIFIC_PROHIBITED_CLAIMS",
            "CASE_SPECIFIC_SOURCE_BINDINGS",
            "CASE_SPECIFIC_COMPLETION",
        )
        if (
            tuple(row["hard_assertions"]) != HARD_ASSERTIONS
            or tuple(row["semantic_assertions"]) != expected_semantic_codes
        ):
            raise ValueError("assertion codes duplicated")
        known_spans = {span.get("span_id") for span in case["authority_spans"]}
        bound_spans = [
            span_id
            for group in semantics["required_source_span_bindings"]
            for span_id in group
        ]
        if (
            any(span_id not in known_spans for span_id in bound_spans)
            or (
                row["required_outcome"] == "ABSTAIN"
                and (
                    semantics["required_propositions"]
                    or semantics["required_source_span_bindings"]
                )
            )
            or (
                row["required_outcome"] == "ANSWER"
                and row["required_output_type"] == "FACTUAL"
                and not semantics["required_propositions"]
            )
            or semantics.get(
                "required_abstention_code", row["required_abstention_code"]
            )
            != row["required_abstention_code"]
            or semantics["boundary_fixture"] != case["boundary_fixture"]
            or (
                row["required_abstention_code"] is not None
                and row["required_abstention_code"] not in ABSTENTION_CODES
            )
            or (
                malformed
                and fixture_codes[row["case_id"]] != row["required_abstention_code"]
            )
            or any(
                not isinstance(group, list) or not group
                for group in semantics["required_source_span_bindings"]
            )
            or any(
                len(group) != len(set(group))
                for group in semantics["required_source_span_bindings"]
            )
            or (
                row["required_outcome"] == "ANSWER"
                and row["required_output_type"] == "FACTUAL"
                and len(semantics["required_propositions"])
                != len(semantics["required_source_span_bindings"])
            )
        ):
            raise ValueError("case-specific semantic oracle invalid")
        commentary = row["required_output_type"] == "COMMENTARY"
        if (
            malformed
            != (
                isinstance(semantics["fault_injection"], str)
                and bool(semantics["fault_injection"])
                and semantics["boundary_fixture"] is not None
            )
            or (not malformed and semantics["fault_injection"] is not None)
            or commentary
            != (
                isinstance(semantics["required_theme"], str)
                and isinstance(semantics["required_style"], str)
            )
            or (
                not commentary
                and (
                    semantics["required_theme"] is not None
                    or semantics["required_style"] is not None
                )
            )
        ):
            raise ValueError("branch-specific semantic oracle invalid")
    expected_rules = {
        "hard_gate": "100_PERCENT_EACH_RUN_NO_COMPENSATION",
        "semantic_gate": "AT_LEAST_95_PERCENT_EACH_RUN_NO_COMPENSATION",
        "factual_atoms": "ZERO_UNSUPPORTED_OR_CHANGED_AND_100_PERCENT_SOURCE_BOUND",
        "abstention": "EXACT_EXPECTED_CODE",
        "adjudication": "TWO_OWNER_REGISTERED_ED25519_RECEIPTS",
    }
    if (
        rubric.get("corpus_identity") != corpus_identity
        or rubric.get("adjudicator_registry_identity") != REGISTRY_IDENTITY
        or rubric.get("rules") != expected_rules
    ):
        raise ValueError("rubric authority invalid")
    excluded = access.get("post_freeze_excluded_project_activities")
    if (
        access.get("holdout_identity") != holdout_identity
        or access.get("post_freeze_allowed_purposes")
        != [
            "INTEGRITY_VALIDATION",
            "AUTHORIZED_CANDIDATE_EVALUATION",
            "INDEPENDENT_SEMANTIC_ADJUDICATION",
        ]
        or access.get("registered_adjudicator_roles")
        != ["ADJUDICATOR_A", "ADJUDICATOR_B"]
        or excluded
        != [
            "training",
            "fine_tuning",
            "adapter_training",
            "prompt_selection",
            "threshold_selection",
            "qualification_design",
            "prior_candidate_evaluation",
        ]
        or access.get("global_training_exclusion_claimed") is not False
    ):
        raise ValueError("holdout access authority invalid")
    if (
        provenance.get("candidate_models_loaded_or_executed") is not False
        or provenance.get("candidate_outputs_inspected") is not False
        or provenance.get("training_tuning_prompt_threshold_inputs_used") is not False
        or provenance.get("created_by")
        != "OPENAI_CODEX_CANDIDATE_NEUTRAL_SYNTHETIC_FIXTURE_GENERATOR"
        or provenance.get("creation_method")
        != "REVIEWABLE_MULTI_FAMILY_CASE_CATALOG_WITH_CASE_SPECIFIC_SEMANTIC_ORACLES"
    ):
        raise ValueError("provenance is not candidate-neutral")
    if (
        provenance.get("freeze_basis_commit") != FREEZE_BASIS_COMMIT
        or provenance.get("freeze_basis_tree") != FREEZE_BASIS_TREE
        or access.get("claim_scope") != "PROJECT_CONTROLLED_ACTIVITIES_ONLY"
        or access.get("candidate_runner_receives_case_only_at_frozen_evaluation_time")
        is not True
    ):
        raise ValueError("freeze provenance/access binding invalid")
    expected = {name: sha256(artifacts[name]) for name in names[:6]}
    if provenance.get("artifacts") != {name: expected[name] for name in names[:4]}:
        raise ValueError("provenance artifact closure invalid")
    bindings = {
        "corpus_identity": corpus_identity,
        "holdout_identity": holdout_identity,
        "assertion_manifest_identity": assertion_identity,
        "rubric_identity": rubric_identity,
        "provenance_identity": provenance_identity,
        "access_receipt_identity": access_identity,
    }
    if (
        any(freeze.get(key) != value for key, value in bindings.items())
        or freeze.get("freeze_basis_commit") != FREEZE_BASIS_COMMIT
        or freeze.get("freeze_basis_tree") != FREEZE_BASIS_TREE
        or freeze.get("freeze_utc") != provenance.get("freeze_utc")
        or freeze.get("freeze_utc") != access.get("freeze_utc")
        or freeze.get("artifact_sha256") != expected
        or freeze.get("candidate_execution_authorized") is not False
        or freeze.get("candidate_execution_observed") is not False
    ):
        raise ValueError("freeze closure invalid")
    if (
        qualification.get("freeze_identity") != freeze_identity
        or qualification.get("freeze_artifact_sha256") != sha256(artifacts[names[6]])
        or qualification.get("candidate_execution_authorized") is not False
        or qualification.get("candidate_execution_observed") is not False
        or len(qualification_identity) != 64
    ):
        raise ValueError("qualification closure invalid")
    return freeze_identity


__all__ = ("validate_frozen_corpus",)
