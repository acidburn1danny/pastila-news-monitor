"""Terminal non-circular authority for the pre-inference qualification generation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

EXPECTED_ARTIFACT_SHA256 = {
    "production-core-candidate-object-manifest-v1.json": "551e6c2983e6d71664298432aa9b20e45b1677e3a45b8c6458a563cb913e83bf",
    "production-core-comparative-qualification-generation-v1.json": "082d07795f0e90e6504a41f371533f343520a222a1b08abdd2c50a24319748f2",
    "production-core-candidate-qualification-mechanism-v1.json": "b6cf1e352aa628e79ddbab12c14986cb2e30a62f126d7ec63d1d7db68ff802a3",
}
EXPECTED_MANIFEST_IDENTITY = "51cae2453234d19fef6cd6bb1505beb7ae9bb8a27fcd152a61a6a7bb181a0420"
EXPECTED_GENERATION_IDENTITY = "80058a04ee40c896a71c950b83c242af160479fcce5bd495577c57cea9d0bc04"
EXPECTED_QUALIFICATION_IDENTITY = "9b3e78f2ac858fbef5f471fe4af449884bfbf2f0da272c1d3e388da0da1b68bb"


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
