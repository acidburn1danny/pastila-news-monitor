import hashlib
import json
from pathlib import Path

from scripts.materialize_production_core_v10_performance_freeze import build, canonical

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/production-core-v10-performance-bakeoff-freeze.json"


def test_freeze_is_reproducible_and_preserves_authority_boundaries():
    value = json.loads(ARTIFACT.read_bytes())
    assert build() == value
    identity = value.pop("freeze_identity")
    assert hashlib.sha256(canonical(value)).hexdigest() == identity
    assert value["hard_gate_pass"] is True
    assert value["target_gate_pass"] is False
    assert value["candidate_execution_performed"] is False
    assert value["qualification_attempt_consumed"] is False


def test_flex_is_rejected_and_selected_loss_is_stable():
    value = build()
    assert value["flex_attention_disposition"]["status"] == "REJECTED_SEMANTIC_NON_EQUIVALENCE"
    assert value["flex_attention_disposition"]["further_bakeoff_authorized"] is False
    assert {run["loss"] for run in value["selected_repetitions"]} == {"0.19140107929706573"}
    assert value["selected_variant"] == "BF16_FLASH_REPEAT_KV_SELECTIVE_LOGITS"
