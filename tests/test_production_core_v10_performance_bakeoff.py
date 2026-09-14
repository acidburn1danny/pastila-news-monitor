import json
from pathlib import Path

import pytest

from scripts.train_production_core_candidate_successor_v1 import (
    PERFORMANCE_VARIANT_CAPABILITIES,
    assistant_logit_span,
)

from scripts.materialize_production_core_v10_performance_bakeoff_configs import (
    VARIANTS,
    materialize,
)


def test_bakeoff_configs_are_batch_only_and_reproducible(tmp_path):
    first = materialize(tmp_path / "a")
    second = materialize(tmp_path / "b")
    assert first == second
    assert first["hard_gate_speedup"] == 3
    assert first["target_speedup"] == 4
    assert first["stretch_speedup"] == 5
    assert set(first["variants"]) == set(VARIANTS)
    for metadata in first["variants"].values():
        value = json.loads((tmp_path / "a" / metadata["path"]).read_bytes())
        assert value["performance_bakeoff_only"] is True
        assert value["full_training_authorized"] is False
        assert value["qualification_attempt_consumed"] is False


def test_trainer_rejects_unknown_or_full_performance_variant():
    source = (Path(__file__).resolve().parents[1] / "scripts/train_production_core_candidate_successor_v1.py").read_text()
    assert '"FLASH_ONLY"' in source
    assert '"EFFICIENT_ONLY"' in source
    assert 'mode != "BATCH_SMOKE"' in source
    assert 'sdpa_kernel(SDPBackend.FLASH_ATTENTION)' in source
    assert 'sdpa_kernel(SDPBackend.EFFICIENT_ATTENTION)' in source
    assert 'sdpa_attention.use_gqa_in_sdpa = lambda attention_mask, key, value: False' in source
    assert 'torch.autocast(device_type="cuda", dtype=torch.bfloat16)' in source
    assert '"performance-telemetry.jsonl"' in source
    assert '"BACKWARD_COMPLETED_POSITION_{position}"' in source
    assert '"flex_attention"' in source


def test_variant_capabilities_are_centralized_and_fail_closed():
    assert set(PERFORMANCE_VARIANT_CAPABILITIES) == set(VARIANTS)
    assert PERFORMANCE_VARIANT_CAPABILITIES["BF16_FLASH_REPEAT_KV_SELECTIVE_LOGITS"] == {
        "bf16",
        "flash",
        "repeat_kv",
        "selective_logits",
    }
    assert PERFORMANCE_VARIANT_CAPABILITIES[
        "BF16_FLEX_ATTENTION_SELECTIVE_LOGITS_DIAGNOSTIC"
    ] == {"bf16", "flex", "selective_logits"}


def test_frozen_profile_schema_has_full_corpus_cardinality():
    source = (Path(__file__).resolve().parents[1] / "scripts/train_production_core_candidate_successor_v1.py").read_text()
    assert "3: 480, 4: 480" in source


def test_assistant_logit_span_predicts_every_assistant_token_including_eos():
    assert assistant_logit_span(2400, 2641) == (2399, 2640)
    assert len(range(*assistant_logit_span(2400, 2641))) == 241
    with pytest.raises(SystemExit, match="selective-logit span mismatch"):
        assistant_logit_span(2641, 2641)
