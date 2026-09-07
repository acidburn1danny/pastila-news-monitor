import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.production_core_qualification_corpus_terminal_authority_v1 import (
    validate_terminal_corpus_authority,
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


def test_terminal_authority_accepts_only_exact_freeze_and_qualification():
    assert (
        validate_terminal_corpus_authority(artifacts())
        == "89d13366227b63c29ca71a00426f4918a4d8e62c8e07de10aaa810f887e9611a"
    )


def test_self_consistent_qualification_substitution_is_rejected():
    values = artifacts()
    qualification = json.loads(values[NAMES[-1]])
    qualification["validator_sha256"] = "f" * 64
    body = dict(qualification)
    body.pop("qualification_identity")
    encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
    qualification["qualification_identity"] = hashlib.sha256(encoded).hexdigest()
    values[NAMES[-1]] = (
        json.dumps(qualification, ensure_ascii=False, indent=2).encode() + b"\n"
    )
    with pytest.raises(ValueError):
        validate_terminal_corpus_authority(values)
