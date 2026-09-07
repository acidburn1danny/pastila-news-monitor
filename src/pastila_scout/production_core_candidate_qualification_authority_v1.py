"""Terminal non-circular authority for the pre-inference qualification generation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

EXPECTED_ARTIFACT_SHA256 = {
    "production-core-candidate-object-manifest-v1.json": "551e6c2983e6d71664298432aa9b20e45b1677e3a45b8c6458a563cb913e83bf",
    "production-core-comparative-qualification-generation-v1.json": "2b23402d58a6b143c94152e285cdc9fa1b588bc84d333b15de85c6a158626950",
    "production-core-candidate-qualification-mechanism-v1.json": "ccb23295442afade5eff00a4c50745dd5e4020df13f8bf60a50193c888291a18",
}
EXPECTED_MANIFEST_IDENTITY = "51cae2453234d19fef6cd6bb1505beb7ae9bb8a27fcd152a61a6a7bb181a0420"
EXPECTED_GENERATION_IDENTITY = "b865af83fe360eb19c4f1fe07ad953becf38daedf6282e7c4f85027dc649eeac"
EXPECTED_QUALIFICATION_IDENTITY = "52968d6040ecd05cb968412eb3272c8cf55be6fa76125e94829cb536a87da91f"


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
