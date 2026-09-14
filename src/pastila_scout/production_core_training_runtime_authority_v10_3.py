"""Fail-closed schema-repaired optimized training authority for Core V10."""

import hashlib
from collections.abc import Mapping

from pastila_scout.production_core_training_runtime_authority_v10_2 import canonical, expected_observation as predecessor_observation


def expected_observation() -> dict[str, object]:
    value = predecessor_observation()
    value.update({
        "source_commit": "5c1f69ecb57a63a07a0bddfbea6ad9fec9482b57",
        "source_tree": "18c3f4871ed75483fe8618b1bcbeb133e2501ed2",
        "trainer_sha256": "7cb7f7e4d3820155b40a49fa7e97f51eb6f29d775b1ec8b6d3efa410fedf7984",
        "predecessor_training_authority_identity": "a06dca57553584761a13524c93d0ca4782ff016f158344a5daf66d30e6782c3a",
        "predecessor_training_authority_sha256": "065f3415c2d529c396c1570e52a4f40e433e2df41e7447ccfb591ba028cabff0",
        "schema_cardinality_repair": "SCHEMA_4_EXACTLY_480_ROWS",
    })
    return value


def build_authority(observation: Mapping[str, object]) -> dict[str, object]:
    if dict(observation) != expected_observation():
        raise ValueError("V10.3 training authority observation mismatch")
    core = {
        "schema": "pastila-production-core-training-runtime-authority",
        "schema_version": "10.3",
        "status": "PASS_SCHEMA_REPAIRED_OPTIMIZED_DUAL_SUCCESSOR_V10_TRAINING_RUNTIME_ZERO_QUALIFICATION_ATTEMPTS",
        "observation": dict(observation),
        "full_training_authorized": True,
        "full_training_started": False,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return {**core, "training_runtime_authority_identity": hashlib.sha256(canonical(core)).hexdigest()}
