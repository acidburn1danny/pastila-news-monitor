"""Adversarial, zero-attempt checks of the separate alias-secret generation."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import materialize_production_core_successor_qualification_generation_v13 as successor  # noqa: E402


def fixture_secret():
    return {
        "schema": "pastila-production-core-candidate-alias-secret",
        "schema_version": 1,
        "nonce_hex": "1" * 64,
        "aliases": dict(zip(successor.ALIASES, successor.CANDIDATE_NAMES, strict=True)),
    }


def test_new_generation_changes_only_secret_dependent_public_fields():
    generation, qualification = successor.build(fixture_secret())
    old = json.loads(successor.SOURCE_GENERATION.read_bytes())
    old_qualification = json.loads(successor.SOURCE_QUALIFICATION.read_bytes())
    changed = {key for key in old if generation[key] != old[key]}
    assert changed == {
        "status", "alias_secret_commitment", "schedule", "schedule_lineage",
        "qualification_generation_identity",
    }
    assert {key for key in old_qualification if qualification[key] != old_qualification[key]} == {
        "status", "qualification_generation_identity", "mechanism_source_sha256", "qualification_identity",
    }
    assert len(generation["schedule"]) == 2400
    assert len({row["case_id"] for row in generation["schedule"]}) == 200
    assert generation["candidate_object_manifest_identity"] == old["candidate_object_manifest_identity"]
    assert generation["request_manifest_identity"] == old["request_manifest_identity"]
    assert generation["alias_secret_commitment"] != successor.HISTORICAL


def test_secret_shape_and_mutation_fail_closed():
    secret = fixture_secret()
    secret["nonce_hex"] = "z" * 64
    with pytest.raises(ValueError, match="secret malformed"):
        successor.build(secret)
    secret = fixture_secret()
    secret["aliases"]["CANDIDATE-A"] = secret["aliases"]["CANDIDATE-B"]
    with pytest.raises(ValueError, match="secret malformed"):
        successor.build(secret)


def test_published_source_tree_is_required(monkeypatch):
    monkeypatch.setattr(successor, "SOURCE_TREE", "0" * 40)
    with pytest.raises(ValueError, match="published source tree mismatch"):
        successor.build(fixture_secret())
