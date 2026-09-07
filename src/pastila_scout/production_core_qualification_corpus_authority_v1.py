"""Externally pinned authority for the frozen Core V2 qualification corpus."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from pastila_scout.production_core_qualification_corpus_v1 import (
    validate_frozen_corpus,
)

AUTHORIZED_FREEZE_IDENTITY = (
    "89d13366227b63c29ca71a00426f4918a4d8e62c8e07de10aaa810f887e9611a"
)
AUTHORIZED_FREEZE_ARTIFACT_SHA256 = (
    "58fafb8944c4e6754ce8c2d06f2ee6b624e651d38b5a430613305754f03a4cd5"
)


def validate_authorized_frozen_corpus(artifacts: Mapping[str, bytes]) -> str:
    freeze_identity = validate_frozen_corpus(artifacts)
    freeze_bytes = artifacts["production-core-qualification-corpus-freeze-v1.json"]
    if (
        freeze_identity != AUTHORIZED_FREEZE_IDENTITY
        or hashlib.sha256(freeze_bytes).hexdigest() != AUTHORIZED_FREEZE_ARTIFACT_SHA256
    ):
        raise ValueError("authorized corpus artifact identity mismatch")
    return freeze_identity


__all__ = (
    "AUTHORIZED_FREEZE_IDENTITY",
    "validate_authorized_frozen_corpus",
)
