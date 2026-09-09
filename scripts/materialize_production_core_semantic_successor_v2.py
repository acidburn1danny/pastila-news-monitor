"""Materialize candidate-neutral prospective semantic-authority successors."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


def canonical(v):
    return json.dumps(v, ensure_ascii=False, separators=(",", ":")).encode()


def seal(v, key):
    v[key] = hashlib.sha256(canonical(v)).hexdigest()
    return v


def write(name, v):
    (ART / name).write_text(
        json.dumps(v, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    unicode_auth = seal(
        {
            "schema": "pastila-production-core-unicode-uax29-authority",
            "schema_version": 1,
            "status": "OFFICIAL_UNICODE_16_AUTHORITY_CONTENT_ADDRESSED",
            "unicode_version": "16.0.0",
            "uax_revision": 45,
            "conformance": "UAX29-C3-1_DEFAULT_SENTENCE_BOUNDARIES",
            "resources": {
                "SentenceBreakProperty.txt": "20aab5eca3842c7a27cc6756d74488a4a5f744c8dca2948ec1128f26a60d1f79",
                "SentenceBreakTest.txt": "0aef84034ee1789eb71021454fac384e83080b05922272d63cf297f4bf08150e",
                "tr29-45.html": "4579c185bd45feac761de590d874aca71788e339b35179318a4c43412fd4f9e4",
            },
            "runtime_authority_identity": "baa7f72966196d6eada227d094033cff647eef2b35366f98876aa17f392aeebf",
            "substitution_prohibited": True,
        },
        "authority_identity",
    )
    write("production-core-unicode-16-uax29-authority-v1.json", unicode_auth)
    semantic = seal(
        {
            "schema": "pastila-core-v2-semantic-output-contract",
            "schema_version": 2,
            "status": "OWNER_APPROVED_PROSPECTIVE_SUCCESSOR",
            "supersedes_version": 1,
            "historical_v1_immutable": True,
            "unicode_unit": "NFC_UNICODE_SCALAR_VALUES",
            "qsu": {
                "authority_identity": unicode_auth["authority_identity"],
                "algorithm": "UNICODE_16_0_0_UAX29_C3_1_UNMODIFIED",
                "term": "QUALIFICATION_SENTENCE_UNIT",
                "locale_or_tailoring_allowed": False,
            },
            "factual": {
                "shape_authority": "FROZEN_CASE_REQUIRED_FACTUAL_SHAPE",
                "shapes": {
                    "MATERIAL_PROPOSITIONS": "2_TO_3",
                    "QUALIFICATION_SENTENCE_UNITS": "1_TO_2",
                },
                "maximum_unicode_scalars": 650,
                "one_text_block": True,
                "bullets_or_headings": False,
                "unsupported_or_changed_facts": 0,
                "source_binding_percent": 100,
            },
            "commentary": {
                "editorial_target_qsu": 3,
                "target_classification": "DIAGNOSTIC_ONLY_NON_FAILING",
                "target_qualification_effect": False,
                "hard_maximum_qsu": 5,
                "hard_maximum_unicode_scalars": 1000,
                "limits_independent": True,
                "structure": "PERMITTED_AND_REQUIRED_ONLY_WHEN_EXPLICITLY_REQUESTED",
            },
            "global": {
                "completion_terminal": True,
                "trailing_output": "FAIL",
                "overflow": "FAIL",
                "truncate": False,
                "retry_or_redraw": False,
            },
        },
        "contract_identity",
    )
    write("core-v2-semantic-output-contract-v2.json", semantic)
    response = seal(
        {
            "schema": "pastila-core-v2-structured-qualification-response-contract",
            "schema_version": 2,
            "status": "OWNER_APPROVED_PROSPECTIVE_SUCCESSOR",
            "semantic_contract_identity": semantic["contract_identity"],
            "required_fields": [
                "schema",
                "schema_version",
                "case_id",
                "request_identity",
                "output_type",
                "outcome",
                "text",
                "claim_bindings",
                "abstention_code",
            ],
            "optional_fields": [],
            "additional_fields_allowed": False,
            "schema_const": "pastila-core-v2-structured-qualification-response",
            "schema_version_const": 2,
            "output_types": ["FACTUAL", "COMMENTARY"],
            "outcomes": ["ANSWER", "ABSTAIN"],
            "claim_bindings": {
                "maximum": 3,
                "claim_indexes": "CONTIGUOUS_FROM_1_IN_MATERIAL_PROPOSITION_ORDER",
                "source_ids_per_claim": [1, 8],
                "aggregate_maximum": 24,
                "duplicates": False,
                "order": "STRICT_REQUEST_AUTHORITY_ORDER",
            },
            "abstention_codes": [
                "INSUFFICIENT_AUTHORITY",
                "CONFLICTING_AUTHORITY",
                "AMBIGUOUS_SCOPE",
                "UNRESOLVED_REFERENCE",
                "INSTRUCTION_AUTHORITY_CONFLICT",
                "CANNOT_SATISFY_OUTPUT_CONTRACT",
                "SAFETY_ENVELOPE_EXCEEDED",
            ],
            "serialization": "ONE_COMPACT_NFC_UTF8_OBJECT_THEN_EOF",
            "invalid_behavior": "FAIL_CLOSED_ZERO_MUTATION_NO_REPAIR_COERCION_TRUNCATION_RETRY_REDRAW",
            "evaluator_only_verdict": True,
        },
        "contract_identity",
    )
    write("core-v2-structured-qualification-response-v2.json", response)
    old_corpus = json.loads(
        (ART / "production-core-qualification-corpus-v1.json").read_bytes()
    )
    old_assert = json.loads(
        (ART / "production-core-qualification-assertions-v1.json").read_bytes()
    )
    assertions = copy.deepcopy(old_assert["assertions"])
    authorities = []
    for case, assertion in zip(old_corpus["cases"], assertions):
        assertion["hard_assertions"] = [
            x.replace("STRUCTURED_RESPONSE_V1", "STRUCTURED_RESPONSE_V2")
            for x in assertion["hard_assertions"]
        ]
        shape = None
        if case["output_type"] == "FACTUAL":
            count = len(assertion["expected_semantics"]["required_propositions"])
            shape = (
                "MATERIAL_PROPOSITIONS"
                if 2 <= count <= 3
                else "QUALIFICATION_SENTENCE_UNITS"
            )
            assertion["required_factual_shape"] = shape
        if case["primary_partition"] == "completion_eos_runaway":
            n = int(case["case_id"].rsplit("-", 1)[1])
            req = [
                "MAXIMUM_5_QSU",
                "TARGET_3_QSU_DIAGNOSTIC_ONLY_NON_FAILING",
                "MAXIMUM_1000_NFC_UNICODE_SCALARS",
            ]
            if n >= 11:
                req += ["EXPLICIT_CONTRAST", "EXPLICIT_COMPLETE_PUNCHLINE"]
            assertion["expected_semantics"]["completion_requirements"] = req
        authorities.append(
            {
                "case_id": case["case_id"],
                "case_sha256": case["case_sha256"],
                "required_factual_shape": shape,
                "expected_material_proposition_count": (
                    len(assertion["expected_semantics"]["required_propositions"])
                    if case["output_type"] == "FACTUAL"
                    else None
                ),
                "required_commentary_components": (
                    ["contrast", "punchline"]
                    if case["primary_partition"] == "completion_eos_runaway"
                    and int(case["case_id"].rsplit("-", 1)[1]) >= 11
                    else []
                ),
            }
        )
    corpus = seal(
        {
            "schema": "pastila-production-core-qualification-corpus-successor",
            "schema_version": 2,
            "status": "PROSPECTIVE_NO_CANDIDATE_EXECUTION",
            "historical_corpus_identity": old_corpus["corpus_identity"],
            "case_count": 200,
            "case_ids": [c["case_id"] for c in old_corpus["cases"]],
            "case_authorities": authorities,
            "distribution": "40/30/30/25/20/20/20/15",
            "minimum_project_controlled_true_holdout": 50,
            "global_training_exclusion_claimed": False,
        },
        "corpus_identity",
    )
    write("production-core-qualification-corpus-v2.json", corpus)
    assertion_art = seal(
        {
            "schema": "pastila-production-core-qualification-assertions",
            "schema_version": 2,
            "status": "PROSPECTIVE_NO_CANDIDATE_EXECUTION",
            "corpus_identity": corpus["corpus_identity"],
            "assertion_count": 200,
            "assertions": assertions,
        },
        "assertion_manifest_identity",
    )
    write("production-core-qualification-assertions-v2.json", assertion_art)
    rubric = seal(
        {
            "schema": "pastila-production-core-qualification-rubric-manifest",
            "schema_version": 2,
            "status": "PROSPECTIVE_FROZEN_BEFORE_ANY_NEW_GENERATION",
            "corpus_identity": corpus["corpus_identity"],
            "assertion_manifest_identity": assertion_art["assertion_manifest_identity"],
            "semantic_contract_identity": semantic["contract_identity"],
            "structured_response_contract_identity": response["contract_identity"],
            "rules": {
                "hard_gate": "100_PERCENT_EACH_RUN_NO_COMPENSATION",
                "semantic_gate": "AT_LEAST_95_PERCENT_EACH_RUN_NO_COMPENSATION",
                "factual_atoms": "ZERO_UNSUPPORTED_OR_CHANGED_AND_100_PERCENT_SOURCE_BOUND",
                "abstention": "EXACT_EXPECTED_CODE",
                "commentary_target": "3_QSU_DIAGNOSTIC_ONLY_NO_SCORE_EFFECT",
                "commentary_hard_maximum": "5_QSU",
                "structure": "ONLY_EXPLICIT_REQUEST_REQUIREMENTS",
                "adjudication": "TWO_OWNER_REGISTERED_ED25519_RECEIPTS",
            },
        },
        "rubric_identity",
    )
    write("production-core-qualification-rubric-v2.json", rubric)
    module = ROOT / "src" / "pastila_scout" / "production_core_semantic_authority_v2.py"
    profile = seal(
        {
            "schema": "pastila-production-core-execution-profile",
            "schema_version": 2,
            "status": "OWNER_APPROVED_PROFILE_VALUES",
            "scope": "QUALIFICATION_EXECUTION_PROFILE_V1_ONLY_NOT_GLOBAL_POLICY",
            "semantic_contract_identity": semantic["contract_identity"],
            "technical": {
                "context_tokens": 8192,
                "input_tokens_max": 1924,
                "output_bytes_max": 6268,
                "output_tokens_max": 6268,
                "token_class": "CONSERVATIVE_BYTE_TIGHT",
                "wall_seconds": 600,
                "peak_rss_bytes": 16106127360,
                "structural_cancellation_ms": 500,
                "structural_wall_seconds": 1,
                "structural_rss_bytes": 67108864,
                "tokenizer_fix_mistral_regex": True,
                "greedy": True,
                "seed": 0,
                "nf4_bf16_double_quant": True,
                "processes": 1,
                "torch_threads": [1, 1],
                "network": "DENY_ALL",
                "overflow": "FAIL_NO_TRUNCATION_RETRY_REDRAW",
            },
            "semantic_successor_changes_technical_maximum": False,
        },
        "profile_identity",
    )
    write("production-core-execution-profile-v2.json", profile)
    framework = seal(
        {
            "schema": "pastila-production-core-model-qualification-framework",
            "schema_version": 2,
            "status": "PROSPECTIVE_AUTHORITY_CLOSED_NO_GENERATION_AUTHORIZED",
            "historical_ordinal8_immutable": True,
            "bindings": {
                "unicode_authority_identity": unicode_auth["authority_identity"],
                "semantic_contract_identity": semantic["contract_identity"],
                "structured_response_contract_identity": response["contract_identity"],
                "corpus_identity": corpus["corpus_identity"],
                "assertion_manifest_identity": assertion_art[
                    "assertion_manifest_identity"
                ],
                "rubric_identity": rubric["rubric_identity"],
                "execution_profile_identity": profile["profile_identity"],
                "shared_authority_module_sha256": file_sha(module),
            },
            "candidate_visible_authority_closure": "REQUIRED_EXACT",
            "candidate_execution_authorized": False,
            "qualification_generation_authorized": False,
            "promotion_effect": False,
        },
        "framework_identity",
    )
    write("production-core-model-qualification-framework-v2.json", framework)


if __name__ == "__main__":
    main()
