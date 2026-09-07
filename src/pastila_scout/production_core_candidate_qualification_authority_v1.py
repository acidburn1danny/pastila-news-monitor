"""Terminal non-circular authority for the pre-inference qualification generation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

EXPECTED_ARTIFACT_SHA256 = {
    "production-core-candidate-object-manifest-v1.json": "551e6c2983e6d71664298432aa9b20e45b1677e3a45b8c6458a563cb913e83bf",
    "production-core-comparative-qualification-generation-v1.json": "8215ddbd3c0bc9b890ea58192b257185ecba41df3b436185e17ade4e797098e9",
    "production-core-candidate-qualification-mechanism-v1.json": "6c99a8e7c03a48c8dda5d7bafed476f6cf5d9bceb087202b1f86f2454090107a",
}
EXPECTED_MANIFEST_IDENTITY = "51cae2453234d19fef6cd6bb1505beb7ae9bb8a27fcd152a61a6a7bb181a0420"
EXPECTED_GENERATION_IDENTITY = "870c84ac320153ab20070f2b2106a1dc1c09339d791cf6616b81dc8da0d5c8a6"
EXPECTED_QUALIFICATION_IDENTITY = "d005ff8ae53d7a1165ae6a668c4cc2d369866035425b26a4fba640922247b84b"


def validate_terminal_candidate_qualification_authority(
    artifacts: Mapping[str, bytes],
) -> str:
    if set(artifacts) != set(EXPECTED_ARTIFACT_SHA256):
        raise ValueError("terminal qualification artifact set mismatch")
    values: dict[str, object] = {}
    for name, expected in EXPECTED_ARTIFACT_SHA256.items():
        raw = artifacts[name]
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("terminal qualification artifact byte mismatch")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise TypeError("terminal qualification artifact schema mismatch")
        values[name] = value
    manifest = values["production-core-candidate-object-manifest-v1.json"]
    generation = values["production-core-comparative-qualification-generation-v1.json"]
    qualification = values["production-core-candidate-qualification-mechanism-v1.json"]
    if (
        manifest.get("manifest_identity") != EXPECTED_MANIFEST_IDENTITY
        or generation.get("qualification_generation_identity") != EXPECTED_GENERATION_IDENTITY
        or qualification.get("qualification_identity") != EXPECTED_QUALIFICATION_IDENTITY
        or qualification.get("candidate_manifest_identity") != EXPECTED_MANIFEST_IDENTITY
        or qualification.get("qualification_generation_identity") != EXPECTED_GENERATION_IDENTITY
    ):
        raise ValueError("terminal qualification semantic identity mismatch")
    return EXPECTED_GENERATION_IDENTITY


__all__ = (
    "EXPECTED_ARTIFACT_SHA256",
    "EXPECTED_GENERATION_IDENTITY",
    "EXPECTED_MANIFEST_IDENTITY",
    "EXPECTED_QUALIFICATION_IDENTITY",
    "validate_terminal_candidate_qualification_authority",
)
