"""Terminal non-circular authority for the pre-inference qualification generation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

EXPECTED_ARTIFACT_SHA256 = {
    "production-core-candidate-object-manifest-v1.json": "551e6c2983e6d71664298432aa9b20e45b1677e3a45b8c6458a563cb913e83bf",
    "production-core-comparative-qualification-generation-v1.json": "9ea5994df9a3732ed9a8b9fde67d939a309f5f6e327db38c0039347ee4128797",
    "production-core-candidate-qualification-mechanism-v1.json": "27bb09e63a7c0b8c61254ac7c13b259801a1d45259f16d9b20d85ff91e6a488e",
}
EXPECTED_MANIFEST_IDENTITY = "51cae2453234d19fef6cd6bb1505beb7ae9bb8a27fcd152a61a6a7bb181a0420"
EXPECTED_GENERATION_IDENTITY = "254525ca4dbd811a2fc0108c5a5c4b967be84e9cea36a855a46a55396cbecce6"
EXPECTED_QUALIFICATION_IDENTITY = "5d5faa8be4b82a4027319647a70d56b23fb41b34f4cf50a7a6700df14417bc40"


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
