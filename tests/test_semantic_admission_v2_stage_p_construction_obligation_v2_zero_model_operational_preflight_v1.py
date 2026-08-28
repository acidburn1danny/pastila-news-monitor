from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_zero_model_operational_preflight_v1 import (
    ZERO_MODEL_PREFLIGHT_IDENTITY,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_zero_model_operational_preflight_v1.py"
)
ARTIFACT = (
    ROOT
    / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-zero-model-operational-preflight-v1.json"
)


def test_identity_and_strict_zero_model_surface():
    value = json.loads(ARTIFACT.read_bytes())
    fields = value["identity_derivation"]["ordered_utf8_fields"]
    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == ZERO_MODEL_PREFLIGHT_IDENTITY
    )
    source = SOURCE.read_text("utf-8")
    for forbidden in (
        "transformers",
        "tokenizers",
        "torch",
        "peft",
        "from_pretrained",
        ".generate(",
    ):
        assert forbidden not in source
    assert value["authority"]["tokenizer_loading"] is False
    assert value["authority"]["model_loading"] is False
