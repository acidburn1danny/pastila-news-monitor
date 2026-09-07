"""Terminal non-circular authority for Core V2 corpus qualification V1."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from pastila_scout.production_core_qualification_corpus_authority_v1 import (
    AUTHORIZED_FREEZE_IDENTITY,
    validate_authorized_frozen_corpus,
)

AUTHORIZED_QUALIFICATION_IDENTITY = (
    "fb405417923b827a0672d99dca476d53fe4651db52d409d2ad0459412f325935"
)
AUTHORIZED_QUALIFICATION_ARTIFACT_SHA256 = (
    "f536eb380f89a4740cf78eb103ee0aef7957ee64ebbfb3f6d7dba9a77f956404"
)


def validate_terminal_corpus_authority(artifacts: Mapping[str, bytes]) -> str:
    freeze_identity = validate_authorized_frozen_corpus(artifacts)
    qualification_bytes = artifacts[
        "production-core-qualification-corpus-freeze-qualification-v1.json"
    ]
    if (
        hashlib.sha256(qualification_bytes).hexdigest()
        != AUTHORIZED_QUALIFICATION_ARTIFACT_SHA256
    ):
        raise ValueError("terminal qualification artifact identity mismatch")
    qualification = json.loads(qualification_bytes)
    if qualification.get("qualification_identity") != AUTHORIZED_QUALIFICATION_IDENTITY:
        raise ValueError("terminal qualification semantic identity mismatch")
    if qualification.get("freeze_identity") != AUTHORIZED_FREEZE_IDENTITY:
        raise ValueError("terminal freeze/qualification binding mismatch")
    return freeze_identity


__all__ = (
    "AUTHORIZED_QUALIFICATION_IDENTITY",
    "validate_terminal_corpus_authority",
)
