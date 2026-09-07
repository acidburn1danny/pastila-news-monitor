"""Terminal non-circular authority for the pre-inference qualification generation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

EXPECTED_ARTIFACT_SHA256 = {
    "production-core-candidate-object-manifest-v1.json": "551e6c2983e6d71664298432aa9b20e45b1677e3a45b8c6458a563cb913e83bf",
    "production-core-comparative-qualification-generation-v1.json": "cde90ee7e34fa5a176f6b69790fad68d1beee5cd2649e92baa786556a2deb8a4",
    "production-core-candidate-qualification-mechanism-v1.json": "1b8073b4f2a5e64ad77e77f60d750ded51bf4284f6204ce26a1c0844c69c5437",
}
EXPECTED_MANIFEST_IDENTITY = "51cae2453234d19fef6cd6bb1505beb7ae9bb8a27fcd152a61a6a7bb181a0420"
EXPECTED_GENERATION_IDENTITY = "6ebd356f7e42ca8192f4e362127f17f169337d24923274dad472b5e43f3509cb"
EXPECTED_QUALIFICATION_IDENTITY = "809cd7ea8b0ebf3835d931f376b3d782b9f9a685b4f328915aba5373e0ba2a1c"


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
