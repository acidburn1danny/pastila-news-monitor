import copy
import json
from pathlib import Path

import pytest

from pastila_scout.production_core_technical_output_envelope_v1 import (
    BRANCHES,
    canonical_response_bytes,
    derive_synthetic_envelope,
    qualified_finite_space,
)


class CharacterTokenizer:
    identity = "sha256:" + "1" * 64

    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(ord(character) for character in text)


QUALIFICATION = (
    Path(__file__).resolve().parents[1]
    / "docs/artifacts/production-core-technical-output-envelope-qualification-v1.json"
)


def _response(output_type: str, outcome: str, text: str | None) -> dict[str, object]:
    claims = (
        [{"claim_index": 1, "source_span_ids": ["sha256:" + "a" * 64]}]
        if output_type == "FACTUAL" and outcome == "ANSWER"
        else []
    )
    return {
        "schema": "pastila-core-v2-structured-qualification-response",
        "schema_version": 1,
        "case_id": "synthetic-001",
        "request_identity": "sha256:" + "b" * 64,
        "output_type": output_type,
        "outcome": outcome,
        "text": text,
        "claim_bindings": claims,
        "abstention_code": None if outcome == "ANSWER" else "INSUFFICIENT_AUTHORITY",
    }


def _space():
    responses = (
        _response("FACTUAL", "ANSWER", "Știință și sursă."),
        _response("COMMENTARY", "ANSWER", "Observație. Dezvoltare. Poantă."),
        _response("FACTUAL", "ABSTAIN", None),
        _response("COMMENTARY", "ABSTAIN", None),
    )
    return qualified_finite_space(responses, identity="synthetic-space-v1", covered_branches=BRANCHES)


def test_canonical_bytes_are_compact_utf8_nfc_and_terminal() -> None:
    response = _response("COMMENTARY", "ANSWER", "S\u0326tiință / \\\"exact\\\"")
    encoded = canonical_response_bytes(response)
    assert encoded.startswith(b'{"schema":')
    assert not encoded.startswith(b"\xef\xbb\xbf")
    assert not encoded.endswith(b"\n")
    assert b" / " in encoded
    assert b"\\/" not in encoded
    assert "Știință" in encoded.decode("utf-8")
    assert b'\\\\\\"exact\\\\\\"' in encoded


@pytest.mark.parametrize("value", ["", "a/b", "a\\b", "a b", "a%20b", "a?b", "a#b", "x" * 129])
def test_source_span_id_rejects_prohibited_or_oversized_values(value: str) -> None:
    response = _response("FACTUAL", "ANSWER", "Fapt unu. Fapt doi.")
    response["claim_bindings"][0]["source_span_ids"] = [value]
    with pytest.raises(ValueError, match="source_span_id"):
        canonical_response_bytes(response)


def test_sha256_subform_is_lowercase_canonical() -> None:
    response = _response("FACTUAL", "ANSWER", "Fapt unu. Fapt doi.")
    response["claim_bindings"][0]["source_span_ids"] = ["sha256:" + "A" * 64]
    with pytest.raises(ValueError, match="noncanonical sha256"):
        canonical_response_bytes(response)


def test_order_extra_fields_controls_and_surrogates_fail_closed() -> None:
    response = _response("COMMENTARY", "ANSWER", "Text")
    reordered = {key: response[key] for key in reversed(response)}
    with pytest.raises(ValueError, match="field order"):
        canonical_response_bytes(reordered)
    extra = copy.deepcopy(response)
    extra["extra"] = None
    with pytest.raises(ValueError, match="field order"):
        canonical_response_bytes(extra)
    for invalid in ("line\nfeed", "\ud800"):
        changed = copy.deepcopy(response)
        changed["text"] = invalid
        with pytest.raises(ValueError):
            canonical_response_bytes(changed)


def test_contract_types_cardinalities_and_branch_invariants_fail_closed() -> None:
    factual = _response("FACTUAL", "ANSWER", "Fapt unu. Fapt doi.")
    invalid_values = []
    wrong_version = copy.deepcopy(factual)
    wrong_version["schema_version"] = True
    invalid_values.append(wrong_version)
    noncontiguous = copy.deepcopy(factual)
    noncontiguous["claim_bindings"][0]["claim_index"] = 2
    invalid_values.append(noncontiguous)
    missing_claims = copy.deepcopy(factual)
    missing_claims["claim_bindings"] = []
    invalid_values.append(missing_claims)
    commentary_claim = _response("COMMENTARY", "ANSWER", "Observație.")
    commentary_claim["claim_bindings"] = factual["claim_bindings"]
    invalid_values.append(commentary_claim)
    bad_abstain = _response("FACTUAL", "ABSTAIN", None)
    bad_abstain["text"] = "not null"
    invalid_values.append(bad_abstain)
    for invalid in invalid_values:
        with pytest.raises(ValueError):
            canonical_response_bytes(invalid)


def test_synthetic_derivation_is_reproducible_and_never_production_authority() -> None:
    first = derive_synthetic_envelope(
        _space(), CharacterTokenizer(), tokenizer_closure_validator=lambda tokenizer: True
    )
    second = derive_synthetic_envelope(
        _space(), CharacterTokenizer(), tokenizer_closure_validator=lambda tokenizer: True
    )
    assert first == second
    assert first["production_value_authority"] is False
    assert first["candidate_model_executed"] is False
    assert first["candidate_result_inspected"] is False
    assert first["byte_maximum"] > 0
    assert first["token_exact_maximum"] > 0
    assert len(first["response_space_sha256"]) == 64


def test_incomplete_space_or_unqualified_tokenizer_fails_closed() -> None:
    with pytest.raises(ValueError, match="complete qualified finite fixture"):
        qualified_finite_space(
            (_response("FACTUAL", "ANSWER", "Fapt unu. Fapt doi."),),
            identity="incomplete",
            covered_branches={"FACTUAL_ANSWER"},
        )
    with pytest.raises(ValueError, match="tokenizer closure"):
        derive_synthetic_envelope(
            _space(), CharacterTokenizer(), tokenizer_closure_validator=lambda tokenizer: False
        )


def test_declared_branch_coverage_cannot_replace_actual_response_coverage() -> None:
    repeated = tuple(
        _response("FACTUAL", "ANSWER", "Fapt unu. Fapt doi.") for _ in range(4)
    )
    with pytest.raises(ValueError, match="response bytes do not cover"):
        qualified_finite_space(
            repeated, identity="false-coverage", covered_branches=BRANCHES
        )


def test_same_logical_space_identity_cannot_hide_response_substitution() -> None:
    original = _space()
    changed_responses = list(original.responses)
    changed_responses[1] = _response("COMMENTARY", "ANSWER", "Alt text complet.")
    substituted = qualified_finite_space(
        changed_responses, identity=original.identity, covered_branches=BRANCHES
    )
    first = derive_synthetic_envelope(
        original, CharacterTokenizer(), tokenizer_closure_validator=lambda tokenizer: True
    )
    second = derive_synthetic_envelope(
        substituted,
        CharacterTokenizer(),
        tokenizer_closure_validator=lambda tokenizer: True,
    )
    assert first["space_identity"] == second["space_identity"]
    assert first["response_space_sha256"] != second["response_space_sha256"]
    assert first["receipt_sha256"] != second["receipt_sha256"]


def test_qualification_receipts_and_witnesses_recompute_exactly() -> None:
    reproduction = json.loads(QUALIFICATION.read_text(encoding="utf-8"))[
        "synthetic_reproduction"
    ]
    actual = [
        derive_synthetic_envelope(
            _space(),
            CharacterTokenizer(),
            tokenizer_closure_validator=lambda tokenizer: True,
        )
        for _ in range(2)
    ]
    assert [item["receipt_sha256"] for item in actual] == reproduction[
        "deterministic_invocation_receipt_sha256"
    ]
    for field in (
        "response_space_sha256",
        "tokenizer_identity",
        "response_count",
        "byte_maximum",
        "byte_witness_sha256",
        "token_exact_maximum",
        "token_witness_sha256",
    ):
        assert all(item[field] == reproduction[field] for item in actual)
