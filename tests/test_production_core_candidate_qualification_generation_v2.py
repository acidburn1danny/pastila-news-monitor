import copy
import hashlib
import json
import runpy
from pathlib import Path
from unittest.mock import patch

import pytest

from pastila_scout.production_core_candidate_qualification_generation_v2 import (
    CORPUS_IDENTITY,
    GenerationAuthorityError,
    canonical,
    identity,
    materialize_request_authorities,
    validate_generation,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


def load(name):
    return json.loads((ART / name).read_bytes())


def unseal(value, field):
    core = dict(value)
    recorded = core.pop(field)
    assert recorded == identity(core)


def test_exact_200_requests_derive_from_successor_authority():
    requests = load("production-core-candidate-request-manifest-v2.json")
    unseal(requests, "request_manifest_identity")
    expected = materialize_request_authorities(
        load("production-core-qualification-corpus-v1.json"),
        load("production-core-qualification-corpus-v2.json"),
    )
    assert requests["requests"] == expected
    assert len(expected) == len({row["case_id"] for row in expected}) == 200
    assert all(
        hashlib.sha256(row["candidate_visible_request"].encode()).hexdigest()
        == row["candidate_visible_request_sha256"]
        for row in expected
    )


def test_validator_controllable_authority_is_candidate_visible_1_to_1():
    prompts = [
        row["candidate_visible_request"]
        for row in load("production-core-candidate-request-manifest-v2.json")[
            "requests"
        ]
    ]
    common = (
        "schema='pastila-core-v2-structured-qualification-response'",
        "schema_version=2",
        "keys exactly in this order",
        "^[a-z0-9][a-z0-9._-]{0,127}$",
        "^sha256:[0-9a-f]{64}$",
        "FACTUAL or COMMENTARY",
        "ANSWER or ABSTAIN",
        "4-5 are permitted",
        "more than 5 fails",
        "1000 NFC Unicode scalar values",
        "Unicode 16.0.0 UAX #29 C3-1",
        "Pattern_White_Space",
        "650 NFC Unicode scalar values",
        "MATERIAL_PROPOSITIONS",
        "QUALIFICATION_SENTENCE_UNITS",
        "claim_bindings contains 1-3",
        "1-8 unique opaque ASCII IDs",
        "at most 24 unique references globally",
        "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
        "INSUFFICIENT_AUTHORITY",
        "No extra/missing/duplicate fields",
        "6268 UTF-8 bytes",
        "6268 tokenizer tokens",
        "followed immediately by EOF",
    )
    assert all(all(rule in prompt for rule in common) for prompt in prompts)
    for row, prompt in zip(
        load("production-core-candidate-request-manifest-v2.json")["requests"],
        prompts,
        strict=True,
    ):
        candidate_input = json.loads(prompt.split("\nINPUT=", 1)[1])
        assert candidate_input == {
            "case_id": row["case_id"],
            "request_identity": row["request_identity"],
            "output_type": row["output_type"],
            "required_factual_shape": row["required_factual_shape"],
            "expected_material_proposition_count": row[
                "expected_material_proposition_count"
            ],
            "required_commentary_components": row["required_commentary_components"],
            "request": candidate_input["request"],
            "authority_spans": candidate_input["authority_spans"],
        }


def test_generation_closes_all_authorities_and_has_no_stale_policy():
    generation = load("production-core-comparative-qualification-generation-v2.json")
    requests = load("production-core-candidate-request-manifest-v2.json")
    validate_generation(
        generation,
        requests,
        load("production-core-candidate-object-manifest-v2.json"),
        {
            "A": load("production-core-candidate-input-envelope-a-v2.json"),
            "B": load("production-core-candidate-input-envelope-b-v2.json"),
        },
        load("production-core-qualification-corpus-v1.json"),
        load("production-core-qualification-corpus-v2.json"),
    )
    assert generation["authority_bindings"] == {
        "public_ref": "refs/heads/foundation/core-v2-production-core-qualification-framework",
        "public_commit": "017cc14f8c89dc9039505fb722e1fbd88e3e3c15",
        "public_tree": "5642521282d251d44c6ca308bef121958b23a48d",
        "unicode_authority_identity": "2bc9eb507adfd6d3cb45c6c73d04711e61b0b2f98712daf23ad968de2c30d8fc",
        "semantic_contract_identity": "5ff45b99134e4b4be865949b54202743ef96db276674eefe0185b4f7163b1410",
        "structured_response_contract_identity": "088ffa8ed7536f732b71b46bdb4f161594518f35a909ea21868044c2902b15e4",
        "corpus_identity": CORPUS_IDENTITY,
        "assertion_manifest_identity": "cce045e9093fb2a92b86339d3f7c7a4e0cd99d85782dc3967826341a7860571c",
        "rubric_identity": "659339bac91cfbdf993c7b57555dfd9191e609816db76e60bc41f13d0dfba1a6",
        "execution_profile_identity": "06aae46a8dce5eeedbd87cd122e935dcc51e17c221d6efb689b80f20bcda621f",
        "framework_identity": "9d8bb34d7ae7a7527ab0916e37a0e0537f156c5b35f7e580e36863efabfbb3c6",
        "holdout_identity": "0a051049c78b893d44968fb02f2df86a3534de803e623ba056d15059a3365c5a",
        "adjudicator_registry_identity": "26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639",
    }
    encoded = canonical(generation)
    assert b"ordinal8" not in encoded and b"structured-response-v1" not in encoded
    assert generation["candidate_execution_performed"] is False
    assert generation["retry_or_redraw_authorized"] is False


def test_stale_and_caller_selected_authority_fail_closed():
    generation = load("production-core-comparative-qualification-generation-v2.json")
    requests = load("production-core-candidate-request-manifest-v2.json")
    candidate_manifest = load("production-core-candidate-object-manifest-v2.json")
    receipts = {
        "A": load("production-core-candidate-input-envelope-a-v2.json"),
        "B": load("production-core-candidate-input-envelope-b-v2.json"),
    }
    historical = load("production-core-qualification-corpus-v1.json")
    successor = load("production-core-qualification-corpus-v2.json")
    for mutate in (
        lambda value: value["authority_bindings"].update(
            semantic_contract_identity="0" * 64
        ),
        lambda value: value.update(schedule=list(reversed(value["schedule"]))),
        lambda value: value.update(request_manifest_identity="0" * 64),
    ):
        changed = copy.deepcopy(generation)
        mutate(changed)
        core = dict(changed)
        core.pop("qualification_generation_identity")
        changed["qualification_generation_identity"] = identity(core)
        with pytest.raises(GenerationAuthorityError):
            validate_generation(
                changed,
                requests,
                candidate_manifest,
                receipts,
                historical,
                successor,
            )
    rebound_requests = copy.deepcopy(requests)
    rebound_requests["requests"][0]["candidate_visible_request"] += "substitution"
    core = dict(rebound_requests)
    core.pop("request_manifest_identity")
    rebound_requests["request_manifest_identity"] = identity(core)
    changed = copy.deepcopy(generation)
    changed["request_manifest_identity"] = rebound_requests["request_manifest_identity"]
    core = dict(changed)
    core.pop("qualification_generation_identity")
    changed["qualification_generation_identity"] = identity(core)
    with pytest.raises(GenerationAuthorityError, match="identity|rederivation"):
        validate_generation(
            changed,
            rebound_requests,
            candidate_manifest,
            receipts,
            historical,
            successor,
        )
    changed_history = copy.deepcopy(historical)
    changed_history["cases"][0]["request"] += " substituted"
    with pytest.raises(GenerationAuthorityError, match="historical corpus"):
        materialize_request_authorities(changed_history, successor)
    rebound_receipts = copy.deepcopy(receipts)
    for receipt in rebound_receipts.values():
        receipt["runtime_closure_sha256"] = "0" * 64
        core = dict(receipt)
        core.pop("receipt_identity")
        receipt["receipt_identity"] = identity(core)
    changed = copy.deepcopy(generation)
    changed["input_envelope_receipt_identities"] = {
        label: receipt["receipt_identity"]
        for label, receipt in rebound_receipts.items()
    }
    core = dict(changed)
    core.pop("qualification_generation_identity")
    changed["qualification_generation_identity"] = identity(core)
    with pytest.raises(GenerationAuthorityError, match="identity|receipt authority"):
        validate_generation(
            changed,
            requests,
            candidate_manifest,
            rebound_receipts,
            historical,
            successor,
        )


def test_two_envelope_materializations_converge_and_are_no_inference():
    a = load("production-core-candidate-input-envelope-a-v2.json")
    b = load("production-core-candidate-input-envelope-b-v2.json")
    for receipt in (a, b):
        unseal(receipt, "receipt_identity")
        assert receipt["maximum_input_tokens"] == 1690
        assert receipt["maximum_input_tokens"] <= receipt["input_token_ceiling"]
        assert receipt["request_count"] == 200
        assert receipt["rendering_count"] == 400
        assert receipt["model_loaded"] is False
        assert receipt["inference_executed"] is False
        assert receipt["candidate_execution_performed"] is False
        assert receipt["network"] == "DENY_ALL_NEW_NAMESPACE"
    for field in (
        "request_manifest_identity",
        "tokenizer_sha256",
        "tokenizer_load_semantics",
        "runtime_closure_sha256",
        "maximum_input_tokens",
        "attaining_renderings",
        "token_count_root",
    ):
        assert a[field] == b[field]


def test_pure_generation_inputs_are_deterministic_without_writing_authority():
    historical = load("production-core-qualification-corpus-v1.json")
    successor = load("production-core-qualification-corpus-v2.json")
    first = materialize_request_authorities(historical, successor)
    second = materialize_request_authorities(historical, successor)
    assert canonical(first) == canonical(second)


def test_secret_escape_rejected_before_any_directory_creation():
    namespace = runpy.run_path(
        str(ROOT / "scripts/materialize_production_core_candidate_qualification_v2.py"),
        run_name="stage2_secret_test",
    )
    with patch.object(Path, "mkdir") as mkdir:
        with pytest.raises(SystemExit, match="containment"):
            namespace["_secret"](ROOT.parent / "must-not-be-created", False)
        mkdir.assert_not_called()


def test_qualification_self_binds_mechanism_and_zero_execution():
    value = load("production-core-candidate-generation-qualification-v2.json")
    unseal(value, "qualification_identity")
    for path, expected in value["mechanism_source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    assert value["candidate_visible_mapping"] == "COMPLETE_1_TO_1"
    assert value["candidate_execution_performed"] is False
    assert value["network_activity"] is False
