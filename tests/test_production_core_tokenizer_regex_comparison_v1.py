import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/artifacts/production-core-tokenizer-regex-comparison-v1.json"
CORPUS = ROOT / "docs/artifacts/production-core-tokenizer-regex-comparison-corpus-v1.json"
PROBE = ROOT / "src/pastila_scout/production_core_tokenizer_materialization_probe_v1.py"
LAUNCHER = ROOT / "scripts/qualify_production_core_tokenizer_materialization_v1.sh"


def _value() -> dict[str, object]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_comparison_binds_pre_execution_frozen_corpus_and_runtime_path() -> None:
    value = _value()
    assert value["corpus_sha256"] == hashlib.sha256(CORPUS.read_bytes()).hexdigest()
    assert value["probe_sha256"] == hashlib.sha256(PROBE.read_bytes()).hexdigest()
    assert value["launcher_sha256"] == hashlib.sha256(LAUNCHER.read_bytes()).hexdigest()
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert corpus["status"] == "PRE_EXECUTION_FROZEN_SYNTHETIC_TOKENIZER_ONLY"
    assert corpus["case_count"] == len(corpus["cases"]) == 40
    assert len({item["case_id"] for item in corpus["cases"]}) == 40


def test_two_by_two_matrix_is_reproducible_without_overclaim() -> None:
    value = _value()
    matrix = value["matrix"]
    assert matrix["materialization_a"] == matrix["materialization_b"]
    comparison = value["comparison"]
    assert comparison["differing_case_ids"] == []
    assert comparison["differing_case_count"] == 0
    assert comparison["token_sequences_equal_for_frozen_corpus"] is True
    assert comparison["universal_tokenizer_equivalence_demonstrated"] is False
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert set(value["shared_case_tokens"]) == {
        item["case_id"] for item in corpus["cases"]
    }
    assert all(
        isinstance(token, int) and 0 <= token < 131072
        for tokens in value["shared_case_tokens"].values()
        for token in tokens
    )


def test_committed_tokens_reconstruct_both_observation_identities() -> None:
    value = _value()
    materialization = json.loads(
        (ROOT / "docs/artifacts/production-core-candidate-tokenizer-materialization-v1.json")
        .read_text(encoding="utf-8")
    )
    common = {
        "schema": "pastila-production-core-tokenizer-materialization-probe",
        "schema_version": 1,
        "files": materialization["tokenizer_object"]["ordered_files"],
        "corpus_sha256": value["corpus_sha256"],
        "tokenizer_class": "TokenizersBackend",
        "vocabulary_size": 131072,
        "case_tokens": value["shared_case_tokens"],
        "technical_output_envelope": {
            "byte_ceiling": 6268,
            "byte_classification": "EXACT_CANONICAL_MAXIMUM",
            "byte_witness_sha256": "3be0ab93fd2bbf415be2ae5a5344a7017b723294383dea97c3a40607267fe820",
            "witness_token_count": 4390,
            "token_ceiling": 6268,
            "token_classification": "CONSERVATIVE_BYTE_TIGHT_TOKEN_CEILING",
            "tokenizer_exact_maximum_claimed": False,
            "tokenizer_byte_tight_definition_proven": True,
        },
        "model_loaded": False,
        "inference_executed": False,
        "candidate_result_inspected": False,
        "network": "DENY_ALL_NEW_NAMESPACE",
    }
    expected = {
        "frozen-default": value["matrix"]["materialization_a"][
            "frozen_default_observation_sha256"
        ],
        "fixed": value["matrix"]["materialization_a"]["fixed_observation_sha256"],
    }
    for mode, digest in expected.items():
        observation = {**common, "mode": mode}
        encoded = json.dumps(
            observation, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        assert hashlib.sha256(encoded).hexdigest() == digest


def test_comparison_does_not_select_policy_or_execute_candidates() -> None:
    value = _value()
    assert value["remaining_owner_decision"] is None
    assert value["authority_effect"] == {
        "selects_regex_mode": True,
        "selected_for_qualification_execution_profile_v1": "fix_mistral_regex=True",
        "missing_flag_or_runtime_warning": "FAIL_CLOSED",
        "profile_specific_only": True,
        "defines_global_core_v2_tokenizer_policy": False,
        "promotes_candidate": False,
        "claims_universal_equivalence_with_frozen_default": False,
        "emits_technical_token_ceiling": False,
        "executes_model_or_inference": False,
        "inspects_candidate_result": False,
        "network_activity": False,
    }
    notice = value["runtime_notice"]
    assert notice["frozen_default_stderr_sha256"] == (
        "4425935b0a695ecb79d5d3b975e8b3fbd73594c24ae6deb1bb235491faae873d"
    )
    assert notice["frozen_default_stderr_size_bytes"] == 348
    assert notice["frozen_default_stderr_mismatch"] == "FAIL_CLOSED_COMPARISON_ONLY"
