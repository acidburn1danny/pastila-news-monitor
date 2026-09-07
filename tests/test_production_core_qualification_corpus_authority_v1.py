from pathlib import Path

import pytest

import pastila_scout.production_core_qualification_corpus_authority_v1 as authority
from pastila_scout.production_core_qualification_corpus_authority_v1 import (
    AUTHORIZED_FREEZE_IDENTITY,
    validate_authorized_frozen_corpus,
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


def test_exact_frozen_authority_is_accepted():
    assert validate_authorized_frozen_corpus(artifacts()) == AUTHORIZED_FREEZE_IDENTITY


def test_fully_rebound_semantic_drift_is_rejected_by_external_authority(monkeypatch):
    values = artifacts()
    monkeypatch.setattr(authority, "validate_frozen_corpus", lambda _: "f" * 64)
    with pytest.raises(ValueError):
        validate_authorized_frozen_corpus(values)
