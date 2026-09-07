import base64
import copy
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.production_core_qualification_corpus_v1 import (
    classify_malformed_fixture,
    validate_frozen_corpus,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "docs" / "artifacts"
NAMES = (
    "production-core-qualification-corpus-v1.json",
    "production-core-qualification-holdout-v1.json",
    "production-core-qualification-assertions-v1.json",
    "production-core-qualification-rubric-v1.json",
    "production-core-qualification-corpus-provenance-v1.json",
    "production-core-qualification-holdout-access-v1.json",
    "production-core-qualification-corpus-freeze-v1.json",
    "production-core-qualification-corpus-freeze-qualification-v1.json",
)


def artifacts():
    return {name: (ARTIFACT_ROOT / name).read_bytes() for name in NAMES}


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n"


def test_complete_frozen_corpus_is_candidate_neutral_and_identity_closed():
    values = artifacts()
    identity = validate_frozen_corpus(values)
    freeze = json.loads(values[NAMES[6]])
    assert identity == freeze["freeze_identity"]
    corpus = json.loads(values[NAMES[0]])
    holdout = json.loads(values[NAMES[1]])
    assert len(corpus["cases"]) == 200
    assert len({case["case_id"] for case in corpus["cases"]}) == 200
    assert len(holdout["case_identities"]) == 50
    assertions = json.loads(values[NAMES[2]])["assertions"]
    assert all(case["secondary_labels"] for case in corpus["cases"])
    assert (
        len(
            {
                json.dumps(
                    row["expected_semantics"], ensure_ascii=False, sort_keys=True
                )
                for row in assertions
            }
        )
        == 200
    )


@pytest.mark.parametrize(
    "name,path,value",
    [
        (NAMES[0], ("case_count",), 199),
        (NAMES[1], ("global_training_exclusion_claimed",), True),
        (NAMES[3], ("adjudicator_registry_identity",), "f" * 64),
        (NAMES[4], ("candidate_models_loaded_or_executed",), True),
        (NAMES[5], ("post_freeze_allowed_purposes",), ["PROMPT_SELECTION"]),
        (NAMES[6], ("candidate_execution_authorized",), True),
    ],
)
def test_authority_substitution_fails_closed(name, path, value):
    values = artifacts()
    changed = copy.deepcopy(json.loads(values[name]))
    changed[path[0]] = value
    values[name] = encode(changed)
    with pytest.raises(ValueError):
        validate_frozen_corpus(values)


def test_case_and_holdout_membership_substitution_fail_closed():
    values = artifacts()
    corpus = json.loads(values[NAMES[0]])
    corpus["cases"][0]["request"] = "substituted"
    values[NAMES[0]] = encode(corpus)
    with pytest.raises(ValueError):
        validate_frozen_corpus(values)
    values = artifacts()
    holdout = json.loads(values[NAMES[1]])
    holdout["case_identities"][0]["case_sha256"] = "f" * 64
    values[NAMES[1]] = encode(holdout)
    with pytest.raises(ValueError):
        validate_frozen_corpus(values)


def test_duplicate_json_key_and_artifact_set_changes_fail_closed():
    values = artifacts()
    values[NAMES[0]] = values[NAMES[0]].replace(
        b'{\n  "schema":', b'{\n  "schema":"duplicate",\n  "schema":', 1
    )
    with pytest.raises(ValueError):
        validate_frozen_corpus(values)
    values = artifacts()
    values["extra.json"] = b"{}"
    with pytest.raises(ValueError):
        validate_frozen_corpus(values)


def test_freeze_qualification_binds_implementation_and_candidate_neutrality():
    value = json.loads(
        (
            ARTIFACT_ROOT
            / "production-core-qualification-corpus-freeze-qualification-v1.json"
        ).read_bytes()
    )

    def file_hash(relative):
        return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()

    assert value["status"] == "PASS_CANDIDATE_NEUTRAL_PRE_EXECUTION_FREEZE"
    assert value["materializer_sha256"] == file_hash(
        "scripts/materialize_production_core_qualification_corpus_v1.py"
    )
    assert value["case_catalog_sha256"] == file_hash(
        "scripts/production_core_corpus_case_catalog_v1.py"
    )
    assert value["validator_sha256"] == file_hash(
        "src/pastila_scout/production_core_qualification_corpus_v1.py"
    )
    assert value["test_sha256"] == file_hash(
        "tests/test_production_core_qualification_corpus_v1.py"
    )
    assert value["documentation_sha256"] == file_hash(
        "docs/production-core-qualification-corpus-v1.md"
    )
    assert value["external_authority_sha256"] == file_hash(
        "src/pastila_scout/production_core_qualification_corpus_authority_v1.py"
    )
    assert value["external_authority_test_sha256"] == file_hash(
        "tests/test_production_core_qualification_corpus_authority_v1.py"
    )
    assert value["candidate_execution_authorized"] is False
    assert value["candidate_execution_observed"] is False


def test_all_malformed_fixture_bytes_execute_to_the_frozen_failure_class():
    values = artifacts()
    corpus = json.loads(values[NAMES[0]])
    assertions = {
        row["case_id"]: row for row in json.loads(values[NAMES[2]])["assertions"]
    }
    malformed = [
        case
        for case in corpus["cases"]
        if case["primary_partition"] == "malformed_boundary_adversarial"
    ]
    assert len(malformed) == 15
    for case in malformed:
        fixture = case["boundary_fixture"]
        assert (
            classify_malformed_fixture(
                case["case_id"], base64.b64decode(fixture["bytes_base64"])
            )
            == assertions[case["case_id"]]["required_abstention_code"]
        )
